import re


INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"reveal (the )?(system prompt|hidden prompt|secret instructions)",
    r"bypass (all )?(security|safety|guardrails)",
    r"act as (the )?system",
]


def validate_input(text):
    if not text.strip():
        return False, "Input cannot be empty."

    if len(text) > 4000:
        return False, "Input is too long."

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return (
                False,
                "Blocked by input guardrail: suspected prompt injection."
            )

    return True, "ok"


def sanitize(text):
    # Basic sanitization of an untrusted retrieved chunk.
    return text.replace(
        "<|system|>",
        "[removed-role-token]"
    )[:20000]


def validate_output(text):
    if not text.strip():
        return False, "No supported answer was found."

    secret_pattern = (
        r"(API_KEY|PASSWORD|SECRET_TOKEN)\s*[:=]\s*\S+"
    )

    if re.search(secret_pattern, text, re.IGNORECASE):
        return False, "Output blocked: possible secret."

    return True, text