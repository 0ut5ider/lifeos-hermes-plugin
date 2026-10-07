# ABOUTME: Finds executable Bash subcommands for LifeOS permission rule checks.
# ABOUTME: Keeps quoted text separate and exposes only documented wrapper commands.

import os
import re
import shlex
from tree_sitter import Language, Parser
import tree_sitter_bash


_LANGUAGE = Language(tree_sitter_bash.language())
_DURATION = re.compile(r"[0-9]+(?:\.[0-9]+)?[smhd]?\Z")
_WRAPPERS = frozenset({"timeout", "time", "nice", "nohup", "stdbuf", "command", "builtin", "noglob", "env"})
_ALLOW_REQUIRES_REVIEW = frozenset({
    "process_substitution", "variable_assignment", "simple_expansion",
    "function_definition", "for_statement", "while_statement", "if_statement", "case_statement",
})


def _unwrapped(node, source: bytes) -> str | None:
    children = node.named_children
    position = 0
    while position < len(children) and children[position].type == 'variable_assignment':
        position += 1
    if position and position < len(children) and children[position].type == 'command_name':
        return source[children[position].start_byte:node.end_byte].decode('utf-8').strip()
    if not children or children[0].type != "command_name":
        return None
    words = [source[child.start_byte:child.end_byte].decode("utf-8") for child in children]
    name = words[0]
    if name not in _WRAPPERS:
        return None
    position = 1
    if name == "env":
        while position < len(words):
            word = words[position]
            if word in {'-i', '--ignore-environment'} or re.match(r'[A-Za-z_][A-Za-z0-9_]*=', word):
                position += 1
            elif word in {'-u', '--unset'}:
                if position + 1 >= len(words) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', words[position + 1]):
                    return None
                position += 2
            elif re.fullmatch(r'--unset=[A-Za-z_][A-Za-z0-9_]*', word):
                position += 1
            elif word == '--':
                position += 1
                break
            elif word.startswith('-'):
                return None
            else:
                break
    elif name == "timeout":
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
                aliases = [raw]
                current, current_source = node, source
                while (unwrapped := _unwrapped(current, current_source)) and unwrapped not in aliases:
                    aliases.append(unwrapped)
                    current_source = unwrapped.encode('utf-8')
                    parsed_inner = Parser(_LANGUAGE).parse(current_source).root_node
                    if parsed_inner.has_error or len(parsed_inner.named_children) != 1:
                        break
                    current = parsed_inner.named_children[0]
                if any(alias.startswith('env ') for alias in aliases):
                    allow_requires_review = True
                forms.append(tuple(aliases))
        for child in node.named_children:
            visit(child)

    visit(root)
    parsed = not root.has_error and bool(forms)
    if (parsed and len(forms) == 1 and len(root.named_children) == 1
            and root.named_children[0].type == "redirected_statement"):
        forms[0] = (*forms[0], command.strip())
    return forms, parsed, parsed and not allow_requires_review


def bash_file_targets(command: str) -> tuple[list[tuple[str, str]], bool]:
    """Find literal files opened by recognized Bash commands and redirects."""
    source = command.encode("utf-8")
    root = Parser(_LANGUAGE).parse(source).root_node
    targets: list[tuple[str, str]] = []
    certain = not root.has_error

    def literal(node) -> str | None:
        raw = source[node.start_byte:node.end_byte].decode("utf-8")
        if node.type not in {"word", "number", "string", "raw_string"} or node.named_children:
            return None
        try:
            parts = shlex.split(raw)
        except ValueError:
            return None
        if len(parts) != 1 or any(char in parts[0] for char in "$`*?[]") or parts[0].startswith("~"):
            return None
        return parts[0]

    def reader_operands(name, children):
        nonlocal certain
        if name == "awk":
            program_seen = False
            position = 0
            while position < len(children):
                word = literal(children[position])
                position += 1
                if word in {"-f", "--file"}:
                    if position >= len(children):
                        certain = False
                        return
                    program_file = literal(children[position])
                    if program_file is None:
                        certain = False
                    elif program_file != "-":
                        targets.append(("read", program_file))
                    position += 1
                    program_seen = True
                    continue
                if word is not None and word.startswith("-f") and len(word) > 2:
                    targets.append(("read", word[2:]))
                    program_seen = True
                    continue
                if word is not None and word.startswith("--file="):
                    targets.append(("read", word.split("=", 1)[1]))
                    program_seen = True
                    continue
                if word is not None and word.startswith("-") and not program_seen:
                    certain = False
                    return
                if not program_seen:
                    program_seen = True
                elif word is None:
                    certain = False
                elif word != "-":
                    targets.append(("read", word))
            return
        words = [literal(child) for child in children]
        if any(word is None for word in words):
            certain = False
            return
        if name == "find":
            expression_started = False
            for word in words:
                if word == "--" and not expression_started:
                    continue
                if word.startswith("-") or word in {"!", "("}:
                    expression_started = True
                if expression_started:
                    if word in {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint",
                                "-fprint0", "-fprintf", "-fls"}:
                        certain = False
                else:
                    targets.append(("read", word))
            return
        options_done = False
        script_seen = False
        grep_pattern_seen = False
        writes_files = False
        position = 0
        while position < len(words):
            word = words[position]
            position += 1
            if not options_done and word == "--":
                options_done = True
                continue
            if not options_done and word.startswith("-") and word != "-":
                if name == "cat" and word in {
                    "-A", "-b", "-e", "-E", "-n", "-s", "-t", "-T", "-u", "-v",
                    "--show-all", "--number-nonblank", "--show-ends", "--number",
                    "--squeeze-blank", "--show-tabs", "--show-nonprinting",
                }:
                    continue
                if name in {"head", "tail"}:
                    if word in {"-n", "--lines", "-c", "--bytes"}:
                        position += 1
                        if position > len(words):
                            certain = False
                        continue
                    if word in {"-q", "--quiet", "--silent", "-v", "--verbose"}:
                        continue
                    if re.fullmatch(r"-(?:n|c)[0-9]+", word) or re.fullmatch(
                        r"--(?:lines|bytes)=[0-9]+", word
                    ):
                        continue
                    if name == "tail" and word in {"-f", "-F", "--follow", "-r"}:
                        continue
                if name == "wc":
                    if word in {"--bytes", "--chars", "--lines", "--max-line-length", "--words"} or re.fullmatch(
                        r"-[cmlLw]+", word
                    ):
                        continue
                if name in {"grep", "rg"}:
                    if word in {"-e", "--regexp", "-f", "--file"}:
                        if position >= len(words):
                            certain = False
                            return
                        if word in {"-f", "--file"} and words[position] != "-":
                            targets.append(("read", words[position]))
                        position += 1
                        grep_pattern_seen = True
                        continue
                    if word.startswith("--regexp=") or word.startswith("-e") and len(word) > 2:
                        grep_pattern_seen = True
                        continue
                    if word.startswith("--file=") or word.startswith("-f") and len(word) > 2:
                        name_arg = word.split("=", 1)[1] if "=" in word else word[2:]
                        if name_arg != "-":
                            targets.append(("read", name_arg))
                        grep_pattern_seen = True
                        continue
                    if word in {"-n", "--line-number", "-i", "--ignore-case", "-v", "--invert-match",
                                "-E", "--extended-regexp", "-F", "--fixed-strings", "-G", "--basic-regexp",
                                "-P", "--perl-regexp", "-q", "--quiet", "-l", "--files-with-matches",
                                "-L", "--files-without-match", "-c", "--count", "-h", "--no-filename",
                                "-H", "--with-filename", "-s", "--no-messages"}:
                        continue
                    if word in {"-m", "--max-count", "-A", "--after-context", "-B", "--before-context",
                                "-C", "--context"}:
                        position += 1
                        if position > len(words):
                            certain = False
                        continue
                if name == "stat":
                    if word in {"-c", "--format", "--printf"}:
                        position += 1
                        if position > len(words):
                            certain = False
                        continue
                    if word in {"-f", "--file-system", "-L", "--dereference", "-t", "--terse"} or word.startswith(
                        ("--format=", "--printf=")
                    ):
                        continue
                if name == "diff":
                    if word in {"-U", "--unified-lines", "--label"}:
                        position += 1
                        if position > len(words):
                            certain = False
                        continue
                    if word in {"-u", "--unified", "-r", "--recursive", "-q", "--brief", "-N",
                                "--new-file", "-a", "--text", "-b", "--ignore-space-change", "-w",
                                "--ignore-all-space", "-B", "--ignore-blank-lines", "-i",
                                "--ignore-case", "-s", "--report-identical-files"} or re.fullmatch(
                        r"-U[0-9]+", word
                    ) or word.startswith("--label="):
                        continue
                if name == "sort":
                    if word in {"-o", "--output"}:
                        if position >= len(words):
                            certain = False
                            return
                        targets.append(("write", words[position]))
                        position += 1
                        continue
                    if word.startswith("--output=") or word.startswith("-o") and len(word) > 2:
                        targets.append(("write", word.split("=", 1)[1] if "=" in word else word[2:]))
                        continue
                    if word in {"-k", "--key", "-t", "--field-separator"}:
                        position += 1
                        if position > len(words):
                            certain = False
                        continue
                    if word in {"-r", "--reverse", "-n", "--numeric-sort", "-u", "--unique",
                                "-s", "--stable", "-f", "--ignore-case", "-b", "--ignore-leading-blanks",
                                "-d", "--dictionary-order", "-i", "--ignore-nonprinting", "-M",
                                "--month-sort", "-h", "--human-numeric-sort", "-V", "--version-sort",
                                "-c", "--check", "-m", "--merge"}:
                        continue
                if name == "ls" and (re.fullmatch(r"-[lah1dRStF]+", word) or word in {
                    "--all", "--almost-all", "--long", "--human-readable", "--directory",
                    "--recursive", "--classify", "--color=auto", "--color=never",
                }):
                    continue
                if name == "cut":
                    if word in {"-b", "--bytes", "-c", "--characters", "-f", "--fields", "-d",
                                "--delimiter", "--output-delimiter"}:
                        position += 1
                        if position > len(words):
                            certain = False
                        continue
                    if word in {"-s", "--only-delimited", "-n", "--complement", "-z", "--zero-terminated"}:
                        continue
                    if re.fullmatch(r"-[bcf].+", word) or word.startswith((
                        "--bytes=", "--characters=", "--fields=", "--delimiter=", "--output-delimiter=",
                    )):
                        continue
                if name == "file" and word in {
                    "-b", "--brief", "-i", "--mime", "--mime-type", "-L", "--dereference",
                    "-z", "--uncompress", "-0", "--print0",
                }:
                    continue
                if name == "sed":
                    if word in {"-n", "--quiet", "--silent", "-E", "-r", "-u", "-z", "-s"}:
                        continue
                    if word in {"-e", "--expression", "-f", "--file"}:
                        if position >= len(words):
                            certain = False
                            return
                        if word in {"-f", "--file"}:
                            targets.append(("read", words[position]))
                        position += 1
                        script_seen = True
                        continue
                    if word.startswith("--expression=") or word.startswith("-e") and len(word) > 2:
                        script_seen = True
                        continue
                    if word.startswith("--file=") or word.startswith("-f") and len(word) > 2:
                        targets.append(("read", word.split("=", 1)[1] if "=" in word else word[2:]))
                        script_seen = True
                        continue
                    if word == "-i" or word.startswith("--in-place") or word.startswith("-i"):
                        writes_files = True
                        continue
                certain = False
                return
            if name == "sed" and not script_seen:
                script_seen = True
                continue
            if name in {"grep", "rg"} and not grep_pattern_seen:
                grep_pattern_seen = True
                continue
            if word != "-":
                targets.append(("read", word))
                if writes_files:
                    targets.append(("write", word))
        if name == "sed":
            # A sed script can open additional files with r, w, or e commands.
            certain = False

    def changes_directory(node, data=source) -> bool:
        if node.type == "command":
            children = node.named_children
            if children and children[0].type == "command_name":
                name = data[children[0].start_byte:children[0].end_byte].decode("utf-8")
                if name in {"cd", "pushd", "popd"}:
                    return True
        return any(changes_directory(child, data) for child in node.named_children)

    def with_directory(target: str, directory: str) -> str:
        if directory == "." or os.path.isabs(target):
            return target
        return os.path.normpath(os.path.join(directory, target))

    def visit(node, directory="."):
        nonlocal certain
        if node.type in {"subshell", "command_substitution", "process_substitution", "pipeline"}:
            for child in node.named_children:
                visit(child, directory)
            return directory
        if node.type in {"if_statement", "while_statement", "for_statement", "case_statement",
                         "function_definition"} and changes_directory(node):
            certain = False
        if node.type in {"program", "list"}:
            current = directory
            previous = None
            for child in node.named_children:
                if previous is not None:
                    gap = source[previous.end_byte:child.start_byte]
                    if current != directory and (b";" in gap or b"&" in gap and b"&&" not in gap):
                        certain = False
                    if b"||" in gap and changes_directory(node):
                        certain = False
                current = visit(child, current)
                previous = child
            return current
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
                    targets.append(("read" if operator.endswith("<") else "write",
                                    with_directory(name, directory)))
        elif node.type == "command":
            children = node.named_children
            if children and children[0].type == 'variable_assignment':
                inner = _unwrapped(node, source)
                if inner is None:
                    certain = False
                else:
                    inner_targets, inner_certain = bash_file_targets(inner)
                    targets.extend((operation, with_directory(target, directory)) for operation, target in inner_targets)
                    certain = certain and inner_certain
                    inner_source = inner.encode('utf-8')
                    if changes_directory(Parser(_LANGUAGE).parse(inner_source).root_node, inner_source):
                        certain = False
                return directory
            if children and children[0].type == "command_name":
                name = source[children[0].start_byte:children[0].end_byte].decode("utf-8")
                if name == "cd":
                    if len(children) != 2:
                        certain = False
                        return directory
                    destination = literal(children[1])
                    if destination is None or destination == "-":
                        certain = False
                        return directory
                    return os.path.normpath(os.path.join(directory, destination))
                if name in {"pushd", "popd"}:
                    certain = False
                    return directory
                first_target = len(targets)
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
                elif name in {"cat", "head", "tail", "sed", "wc", "grep", "rg", "cut", "awk",
                              "stat", "diff", "sort", "ls", "file", "find"}:
                    reader_operands(name, children[1:])
                elif name in _WRAPPERS:
                    inner = _unwrapped(node, source)
                    if inner is None:
                        certain = False
                    else:
                        inner_targets, inner_certain = bash_file_targets(inner)
                        targets.extend(inner_targets)
                        certain = certain and inner_certain
                        inner_source = inner.encode("utf-8")
                        if changes_directory(Parser(_LANGUAGE).parse(inner_source).root_node, inner_source):
                            certain = False
                for index in range(first_target, len(targets)):
                    operation, target = targets[index]
                    targets[index] = (operation, with_directory(target, directory))
        for child in node.named_children:
            directory = visit(child, directory)
        return directory

    visit(root)
    return targets, certain
