"""Model keys are read in the governor only.

Fails on any `settings.<NAME>` read outside `news/summaries/providers/governor.py`
where NAME is a model key, and on any log call or f-string inside the
governor that references a key variable. The list is explicit: the table and
email keys are legitimately read elsewhere.
"""

import ast
from pathlib import Path

from .base import Rule, Violation

SETTINGS_NAME = "settings"
MODEL_KEY_FIELDS = frozenset(
    {
        "GEMINI_API_KEY",
        "GEMINI_API_KEYS",
        "GROQ_API_KEY",
        "GROQ_API_KEYS",
        "MISTRAL_API_KEY",
        "MISTRAL_API_KEYS",
        "NVIDIA_API_KEY",
        "NVIDIA_API_KEYS",
        "OLLAMA_API_KEY",
        "OLLAMA_API_KEYS",
        "CLOUDFLARE_AI_TOKEN",
        "CLOUDFLARE_AI_TOKENS",
        "ANTHROPIC_API_KEY",
        "ENGINE_API_KEY",
        "OWN_GENERATION_API_KEY",
    }
)
GOVERNOR = "news/summaries/providers/governor.py"
KEY_VARIABLE_HINTS = ("key", "token", "secret")
LOG_CALL_NAMES = frozenset(
    {"debug", "info", "warning", "error", "exception", "critical", "log"}
)

MESSAGE_OUTSIDE = "reads settings.{attribute} outside the governor; model keys are read in {governor} only"
MESSAGE_LOGGED = (
    "the governor logs or formats a key variable ({name}); keys never leave the module"
)


def _names_in(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def check_with_path(tree: ast.Module, path: Path) -> list[Violation]:
    violations: list[Violation] = []
    in_governor = path.as_posix().endswith(GOVERNOR)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in MODEL_KEY_FIELDS:
            value = node.value
            if (
                isinstance(value, ast.Name)
                and value.id == SETTINGS_NAME
                and not in_governor
            ):
                violations.append(
                    (
                        node.lineno,
                        MESSAGE_OUTSIDE.format(attribute=node.attr, governor=GOVERNOR),
                    )
                )
        if in_governor and isinstance(node, ast.Call):
            func = node.func
            is_log = isinstance(func, ast.Attribute) and func.attr in LOG_CALL_NAMES
            if is_log:
                for name in _names_in(node):
                    if (
                        any(hint in name.lower() for hint in KEY_VARIABLE_HINTS)
                        and name != "key_for"
                    ):
                        violations.append(
                            (node.lineno, MESSAGE_LOGGED.format(name=name))
                        )
        if in_governor and isinstance(node, ast.JoinedStr):
            for name in _names_in(node):
                if any(hint in name.lower() for hint in KEY_VARIABLE_HINTS):
                    violations.append((node.lineno, MESSAGE_LOGGED.format(name=name)))
    return violations


RULE = Rule(
    name="llm-key-boundary",
    skip_code="llm-key",
    summary="model keys are read in the governor only and never logged",
    check_with_path=check_with_path,
)
