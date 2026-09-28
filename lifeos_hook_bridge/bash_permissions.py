# ABOUTME: Finds executable Bash subcommands for LifeOS permission rule checks.
# ABOUTME: Keeps quoted text separate and exposes only documented wrapper commands.

import re
from tree_sitter import Language, Parser
import tree_sitter_bash


_LANGUAGE = Language(tree_sitter_bash.language())
_DURATION = re.compile(r"[0-9]+(?:\.[0-9]+)?[smhd]?\Z")
_WRAPPERS = frozenset({"timeout", "time", "nice", "nohup", "stdbuf", "command", "builtin", "noglob"})
_ALLOW_REQUIRES_REVIEW = frozenset({
    "file_redirect", "heredoc_redirect", "process_substitution", "variable_assignment",
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


def bash_command_forms(command: str) -> tuple[list[tuple[str, ...]], bool, bool]:
    """Return each Bash command and its recognized wrapper-free form."""
    source = command.encode("utf-8")
    root = Parser(_LANGUAGE).parse(source).root_node
    forms = []
    allow_requires_review = False

    def visit(node):
        nonlocal allow_requires_review
        if node.type in _ALLOW_REQUIRES_REVIEW:
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
    return forms, parsed, parsed and not allow_requires_review
