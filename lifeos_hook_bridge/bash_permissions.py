# ABOUTME: Finds executable Bash subcommands for LifeOS permission rule checks.
# ABOUTME: Keeps quoted text separate and exposes only documented wrapper commands.

import re
import shlex
from tree_sitter import Language, Parser
import tree_sitter_bash


_LANGUAGE = Language(tree_sitter_bash.language())
_DURATION = re.compile(r"[0-9]+(?:\.[0-9]+)?[smhd]?\Z")
_WRAPPERS = frozenset({"timeout", "time", "nice", "nohup", "stdbuf", "command", "builtin", "noglob"})
_ALLOW_REQUIRES_REVIEW = frozenset({
    "process_substitution", "variable_assignment",
    "function_definition", "for_statement", "while_statement", "if_statement", "case_statement",
})


def _unwrapped(node, source: bytes) -> str | None:
    children = node.named_children
    if not children or children[0].type != "command_name":
        return None
    words = [source[child.start_byte:child.end_byte].decode("utf-8") for child in children]
    name = words[0]
    if name not in _WRAPPERS:
        return None
    position = 1
    if name == "timeout":
        while position < len(words) and words[position].startswith("-"):
            option = words[position]
            position += 1
            if option in {"-s", "--signal", "-k", "--kill-after"}:
                position += 1
            elif option == "--":
                break
        if position >= len(words) or not _DURATION.fullmatch(words[position]):
            return None
        position += 1
    elif name == "time":
        while position < len(words) and words[position] in {"-p", "--portability", "--"}:
            position += 1
    elif name == "nice":
        if position < len(words) and words[position] == "-n":
            position += 2
        elif position < len(words) and re.fullmatch(r"-[0-9]+", words[position]):
            position += 1
    elif name == "stdbuf":
        while position < len(words) and re.fullmatch(r"-[ioe].+", words[position]):
            position += 1
    elif name == "command":
        if position < len(words) and words[position] in {"-v", "-V"}:
            return None
        if position < len(words) and words[position] in {"-p", "--"}:
            position += 1
    elif name == "builtin" and position < len(words) and words[position] == "--":
        position += 1
    if position >= len(children) or children[position].type not in {"word", "number"}:
        return None
    return source[children[position].start_byte:node.end_byte].decode("utf-8").strip()


def bash_command_forms(command: str, *, checked_file_targets: bool = False) -> tuple[list[tuple[str, ...]], bool, bool]:
    """Return each Bash command and its recognized wrapper-free form."""
    source = command.encode("utf-8")
    root = Parser(_LANGUAGE).parse(source).root_node
    forms = []
    allow_requires_review = False

    def visit(node):
        nonlocal allow_requires_review
        if node.type in _ALLOW_REQUIRES_REVIEW:
            allow_requires_review = True
        if node.type == "file_redirect":
            redirect = source[node.start_byte:node.end_byte].decode("utf-8").strip()
            target = node.named_children[-1] if node.named_children else None
            target_text = source[target.start_byte:target.end_byte].decode("utf-8") if target else ""
            if (not checked_file_targets and target_text != "/dev/null"
                    and not re.fullmatch(r"[0-9]*[<>]&(?:[0-9]+|-)", redirect)):
                allow_requires_review = True
        if node.type == "command":
            raw = source[node.start_byte:node.end_byte].decode("utf-8").strip()
            if raw:
                unwrapped = _unwrapped(node, source)
                forms.append((raw, unwrapped) if unwrapped else (raw,))
        for child in node.named_children:
            visit(child)

    visit(root)
    parsed = not root.has_error and bool(forms)
    if (parsed and len(forms) == 1 and len(root.named_children) == 1
            and root.named_children[0].type == "redirected_statement"):
        forms[0] = (*forms[0], command.strip())
    return forms, parsed, parsed and not allow_requires_review


def bash_file_targets(command: str) -> tuple[list[tuple[str, str]], bool]:
    """Find literal files read or written by Bash redirections and tee."""
    source = command.encode("utf-8")
    root = Parser(_LANGUAGE).parse(source).root_node
    targets: list[tuple[str, str]] = []
    certain = not root.has_error

    def literal(node) -> str | None:
        raw = source[node.start_byte:node.end_byte].decode("utf-8")
        if node.type not in {"word", "string", "raw_string"} or node.named_children:
            return None
        try:
            parts = shlex.split(raw)
        except ValueError:
            return None
        if len(parts) != 1 or any(char in parts[0] for char in "$`*?[]") or parts[0].startswith("~"):
            return None
        return parts[0]

    def visit(node):
        nonlocal certain
        if node.type == "file_redirect":
            raw = source[node.start_byte:node.end_byte].decode("utf-8").strip()
            children = node.named_children
            target = children[-1] if children else None
            target_text = source[target.start_byte:target.end_byte].decode("utf-8") if target else ""
            if target_text != "/dev/null" and not re.fullmatch(r"[0-9]*[<>]&(?:[0-9]+|-)", raw):
                name = literal(target) if target is not None else None
                if name is None:
                    certain = False
                else:
                    operator = raw[:target.start_byte - node.start_byte].strip()
                    targets.append(("read" if operator.endswith("<") else "write", name))
        elif node.type == "command":
            children = node.named_children
            if children and children[0].type == "command_name":
                name = source[children[0].start_byte:children[0].end_byte].decode("utf-8")
                if name == "tee":
                    options_done = False
                    for child in children[1:]:
                        word = literal(child)
                        if word is None:
                            certain = False
                        elif not options_done and word == "--":
                            options_done = True
                        elif not options_done and word.startswith("-"):
                            if word not in {"-a", "--append", "-i", "--ignore-interrupts", "-p"}:
                                certain = False
                        else:
                            targets.append(("write", word))
        for child in node.named_children:
            visit(child)

    visit(root)
    return targets, certain
