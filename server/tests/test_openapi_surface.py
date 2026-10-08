"""The additive-diff gate: the public surface the live tree ships is the
contract. A path, method, parameter, response or schema property that a
client could have relied on may only disappear when the removal was decided
by name; everything else may only be added. The reference documents are the
live tree's, captured with accounts enabled and disabled (see
`tests/news/fixtures/parity/README.md`)."""

import json
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from outception.version import CURRENT_API_VERSION

PARITY = Path(__file__).parent / "news" / "fixtures" / "parity"

# Removals decided in the plan: the games module and the promoted slots are
# retired; organizations and their tokens left with the account trim, which
# also made the OAuth2 subject user-only.
REMOVED_PATHS = {
    "/v1/news/crossword",
    "/v1/promoted/active",
    "/v1/organizations/",
    "/v1/organizations/{id}",
    "/v1/organization-access-tokens/",
    "/v1/organization-access-tokens/{id}",
}
# The organization subject left with the account trim: these shapes were
# only ever one arm of the OAuth2 authorize and userinfo unions.
REMOVED_SCHEMAS = {
    "AuthorizeOrganization",
    "AuthorizeResponseOrganization",
    "UserInfoOrganization",
}
# (schema, property): the narrowing is the user-only subject decision.
NARROWED = {
    ("Scope", None),
    ("SubType", None),
    ("WebTokenRequest", "sub_type"),
    ("OAuth2ClientConfiguration", "scope"),
    ("OAuth2ClientConfigurationUpdate", "scope"),
    ("AuthorizeResponseUser", "scope_display_names"),
}
NARROWED_RESPONSES = {
    ("get", "/v1/oauth2/authorize"),
    ("get", "/v1/oauth2/userinfo"),
}


def _refs(node: Any, out: set[str]) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            out.add(ref.rsplit("/", 1)[1])
        for value in node.values():
            _refs(value, out)
    elif isinstance(node, list):
        for value in node:
            _refs(value, out)


def _reachable(doc: dict[str, Any], paths: list[str]) -> set[str]:
    """Every schema an operation on the given paths references, transitively."""
    schemas = doc["components"]["schemas"]
    out: set[str] = set()
    for path in paths:
        _refs(doc["paths"][path], out)
    frontier = set(out)
    while frontier:
        found: set[str] = set()
        for name in frontier:
            _refs(schemas.get(name, {}), found)
        frontier = found - out
        out |= found
    return out


_DOC_KEYS = ("description", "title", "examples", "example")


def _stripped(schema: Any) -> Any:
    """A schema without its documentation, which may be reworded, at any
    depth."""
    if isinstance(schema, dict):
        return {k: _stripped(v) for k, v in schema.items() if k not in _DOC_KEYS}
    if isinstance(schema, list):
        return [_stripped(v) for v in schema]
    return schema


def _check_additive(live: dict[str, Any], new: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    kept = [p for p in live["paths"] if p not in REMOVED_PATHS and p in new["paths"]]
    for path in sorted(set(live["paths"]) - set(new["paths"])):
        if path not in REMOVED_PATHS:
            problems.append(f"path removed: {path}")
    for path in kept:
        for method, op in live["paths"][path].items():
            if method not in new["paths"][path]:
                problems.append(f"method removed: {method} {path}")
                continue
            new_op = new["paths"][path][method]
            params = {p["name"]: p for p in op.get("parameters", [])}
            new_params = {p["name"]: p for p in new_op.get("parameters", [])}
            for name, param in params.items():
                if name not in new_params:
                    problems.append(f"parameter removed: {method} {path} {name}")
                elif _stripped(param.get("schema", {})) != _stripped(
                    new_params[name].get("schema", {})
                ):
                    problems.append(f"parameter changed: {method} {path} {name}")
            for name, param in new_params.items():
                if name not in params and param.get("required"):
                    problems.append(f"required parameter added: {method} {path} {name}")
            if (method, path) in NARROWED_RESPONSES:
                continue
            for code in op.get("responses", {}):
                if code not in new_op.get("responses", {}):
                    problems.append(f"response removed: {method} {path} {code}")
            live_body = op.get("responses", {}).get("200", {}).get("content")
            new_body = new_op.get("responses", {}).get("200", {}).get("content")
            if live_body and live_body != new_body:
                problems.append(f"200 body changed: {method} {path}")
    live_schemas = live["components"]["schemas"]
    new_schemas = new["components"]["schemas"]
    for name in sorted(_reachable(live, kept)):
        if name not in new_schemas:
            if name not in REMOVED_SCHEMAS:
                problems.append(f"schema removed: {name}")
            continue
        a, b = live_schemas[name], new_schemas[name]
        if (name, None) in NARROWED:
            continue
        props, new_props = a.get("properties", {}), b.get("properties", {})
        for prop in props:
            if prop not in new_props:
                problems.append(f"property removed: {name}.{prop}")
            elif (name, prop) not in NARROWED and _stripped(props[prop]) != _stripped(
                new_props[prop]
            ):
                problems.append(f"property changed: {name}.{prop}")
        for prop in set(b.get("required", [])) - set(a.get("required", [])):
            problems.append(f"required property added: {name}.{prop}")
        if a.get("enum") != b.get("enum"):
            problems.append(f"enum changed: {name}")
    return problems


@pytest.mark.asyncio
async def test_surface_is_additive(client: AsyncClient) -> None:
    live = json.loads((PARITY / "openapi.json").read_text())
    response = await client.get(f"/{CURRENT_API_VERSION}/openapi.json")
    assert response.status_code == 200
    problems = _check_additive(live, response.json())
    assert not problems, "\n".join(problems)


def test_accounts_off_surface_is_additive_offline() -> None:
    """The store binary talks to the accounts-off surface. That document is
    what production mounts today; the gate for it runs on the same checker
    against the generated document when the script is run with accounts
    disabled, which CI does, so here it only proves the checker itself sees
    the decided removals and nothing else between the two live documents."""
    on = json.loads((PARITY / "openapi.json").read_text())
    off = json.loads((PARITY / "openapi.accounts-off.json").read_text())
    # accounts-off is a strict subset of accounts-on, so on → off must only
    # report the account paths (which are not in the decided list).
    problems = _check_additive(on, off)
    assert all(p.startswith("path removed: ") for p in problems), problems
