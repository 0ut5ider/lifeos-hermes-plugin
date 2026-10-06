# ABOUTME: Extracts a bounded error text from a failed native LifeOS or Hermes process.
# ABOUTME: Installation, mount, and update failures report it so the owner can see the cause.
DETAIL_LINES = 8
DETAIL_CHARACTERS = 1000


def failure_detail(result) -> str:
    """Return the last lines of error output, or of standard output when no error text exists."""
    for text in (result.stderr, result.stdout):
        lines = [line.rstrip() for line in (text or '').splitlines() if line.strip()]
        if lines:
            return '\n'.join(lines[-DETAIL_LINES:])[-DETAIL_CHARACTERS:]
    return ''


def failure_message(label: str, result) -> str:
    detail = failure_detail(result)
    message = f'{label} exited with code {result.returncode}'
    return f'{message}: {detail}' if detail else message
