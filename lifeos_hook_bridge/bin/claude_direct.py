#!/usr/bin/env python3
# ABOUTME: Runs LifeOS child inference against a selected Hermes provider or local gateway.
# ABOUTME: Emits the small Claude CLI JSON envelope that LifeOS Inference.ts reads.

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def configure_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--print", action="store_true", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", choices=("minimal", "low", "medium", "high", "xhigh", "max", "ultra"), default="medium")
    parser.add_argument("--output-format", choices=("json",), required=True)
    parser.add_argument("--system-prompt")
    parser.add_argument("--system-prompt-file")
    parser.add_argument("--setting-sources")
    parser.add_argument("--allowedTools", default="")
    parser.add_argument("--tools", default="")
    parser.add_argument("--exclude-dynamic-system-prompt-sections", action="store_true")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LifeOS local child inference")
    configure_arguments(parser)
    return parser.parse_args()


def _validate_arguments(args: argparse.Namespace) -> None:
    if (args.system_prompt is None) == (args.system_prompt_file is None):
        raise ValueError("exactly one system prompt source is required")
    if args.allowedTools not in ("", "Read") or args.tools not in ("",):
        raise ValueError("only LifeOS inference without tools or with Read image references is supported")


def _message_content(prompt: str, allow_images: bool) -> str | list[dict[str, object]]:
    if not allow_images:
        return prompt
    lines = prompt.splitlines()
    separator = lines.index("") if "" in lines else -1
    references = lines[:separator] if separator >= 0 else []
    if not references or any(not line.startswith("@") for line in references):
        return prompt
    content: list[dict[str, object]] = []
    for reference in references:
        path = Path(reference[1:]).expanduser()
        media_type = mimetypes.guess_type(path.name)[0]
        if media_type not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
            raise ValueError(f"unsupported image type: {path.name}")
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            },
        })
    content.append({"type": "text", "text": "\n".join(lines[separator + 1:])})
    return content


def _hermes_content(content: str | list[dict[str, object]]) -> str | list[dict[str, object]]:
    if isinstance(content, str):
        return content
    converted = []
    for block in content:
        if block["type"] == "image":
            source = block["source"]
            converted.append({"type": "image_url", "image_url": {
                "url": f"data:{source['media_type']};base64,{source['data']}"
            }})
        else:
            converted.append(block)
    return converted


def _field(value: object, key: str, default: object = None) -> object:
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def _run_hermes_provider(args: argparse.Namespace, system_prompt: str,
                         content: str | list[dict[str, object]], provider: str) -> int:
    from agent.auxiliary_client import call_llm, extract_content_or_reasoning

    response = call_llm(
        provider=provider, model=args.model,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": _hermes_content(content)}],
        max_tokens=int(os.environ.get("LIFEOS_CHILD_MAX_TOKENS", "4096")),
        timeout=180, reasoning_config={"enabled": True, "effort": args.effort},
        allow_provider_fallback=False,
    )
    choices = _field(response, "choices", [])
    first_choice = choices[0] if choices else {}
    model = str(_field(response, "model", args.model) or args.model)
    usage = _field(response, "usage", {})
    output_tokens = _field(usage, "completion_tokens", 0)
    print(json.dumps({
        "result": extract_content_or_reasoning(response),
        "is_error": False,
        "stop_reason": _field(first_choice, "finish_reason"),
        "modelUsage": {model: {"outputTokens": output_tokens or 0}},
    }))
    return 0


def main(args: argparse.Namespace | None = None) -> int:
    args = args if args is not None else _arguments()
    _validate_arguments(args)
    system_prompt = args.system_prompt if args.system_prompt is not None else Path(args.system_prompt_file).read_text()
    content = _message_content(sys.stdin.read(), args.allowedTools == "Read")
    provider = os.environ.get("LIFEOS_CHILD_PROVIDER", "").strip()
    if provider:
        return _run_hermes_provider(args, system_prompt, content, provider)
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "").rstrip("/")
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    if not base_url or not token:
        raise ValueError("local gateway URL and bearer token are required")
    request_body = {
        "model": args.model,
        "max_tokens": int(os.environ.get("LIFEOS_CHILD_MAX_TOKENS", "4096")),
        "output_config": {"effort": args.effort},
        "system": system_prompt,
        "messages": [{"role": "user", "content": content}],
    }
    endpoint = base_url + ("/messages" if base_url.endswith("/v1") else "/v1/messages")
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            message = json.load(response)
    except urllib.error.HTTPError as error:
        print(json.dumps({"result": "", "is_error": True, "api_error_status": error.code}))
        return 1

    text = "".join(
        block.get("text", "") for block in message.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    )
    model = str(message.get("model") or args.model)
    output_tokens = message.get("usage", {}).get("output_tokens", 0)
    print(json.dumps({
        "result": text,
        "is_error": message.get("type") == "error",
        "stop_reason": message.get("stop_reason"),
        "modelUsage": {model: {"outputTokens": output_tokens}},
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, urllib.error.URLError) as error:
        print(json.dumps({"result": "", "is_error": True, "api_error_status": None}))
        print(f"LifeOS child inference failed: {error}", file=sys.stderr)
        sys.exit(1)
