#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Transform staged Python sysconfig metadata
# so build-host paths do not ship in the target package.
"""Rewrite _sysconfigdata*.py / _sysconfig_vars*.json for cross installs.

Usage:
  target-pkgconfig-sysconfig.py FILE --sysroot ROOT [--sysroot ROOT ...]
                                    [--builddir DIR ...]

Exit 0 on success (file may be unchanged). Exit 1 on parse/write failure.
"""
from __future__ import annotations

import argparse
import ast
import json
import pprint
import re
import sys
from pathlib import Path
from typing import Any, List

# Keys whose values are build-tree only; neutralize to empty string.
BUILD_ONLY_KEYS = {
    "abs_srcdir",
    "abs_builddir",
    "srcdir",
    "COVERAGE_INFO",
    "COVERAGE_REPORT",
    "RUNSHARED",
    "PYTHON_FOR_BUILD",
    "PYTHON_FOR_FREEZE",
    "TESTPYTHON",
    "TESTRUNNER",
    "FREEZE_MODULE",
    "FREEZE_MODULE_BOOTSTRAP",
    "CONFIG_ARGS",
}

CROSS_TOOLS_BIN = re.compile(
    r"/[^\s\"]*/cross-tools/bin/+?(?:[^/\s\"]+/)*([A-Za-z0-9._+-]+)"
)
BUILDLINK_LIB = re.compile(
    r"/[^\s\"'();]*/\.buildlink/lib/(lib[A-Za-z0-9._+-]+\.so[A-Za-z0-9._*]*)"
)
# Absolute path token: starts with / and stops at whitespace/quotes/;()=
PATH_TOKEN = re.compile(r"/(?:[^\s\"'();=]+)")


def longest_first(paths: List[str]) -> List[str]:
    return sorted({p.rstrip("/") for p in paths if p}, key=len, reverse=True)


def transform_string(value: str, sysroots: List[str], builddirs: List[str]) -> str:
    """Token-wise rewrite of a single string value."""
    out = value

    # Strip --sysroot=<selected>[/...] entirely (with or without trailing path).
    for root in sysroots:
        out = re.sub(
            r"(^|(?<=\s))--sysroot=" + re.escape(root) + r"(?:/[^\s\"]*)?",
            "",
            out,
        )

    # .buildlink libs -> /usr/pkg/lib/<soname>
    out = BUILDLINK_LIB.sub(r"/usr/pkg/lib/\1", out)

    # cross-tools wrappers -> basename
    out = CROSS_TOOLS_BIN.sub(r"\1", out)

    # Selected sysroot spellings: drop the root; keep a trailing path suffix.
    for root in sysroots:
        out = out.replace(root + "/", "/")
        out = re.sub(
            r"(^|(?<=[\s=\"':,;]))" + re.escape(root) + r"(?=\s|$|[\"';])",
            r"\1",
            out,
        )

    def replace_build_token(match: "re.Match[str]") -> str:
        token = match.group(0)
        base = token.rsplit("/", 1)[-1]
        if "/bin/" in token and base and re.fullmatch(r"[A-Za-z0-9._+-]+", base):
            return base
        return ""

    for root in builddirs:
        pattern = re.compile(re.escape(root) + r"(?:/[^\s\"'();=]*)?")
        out = pattern.sub(replace_build_token, out)

    out = re.sub(r"[ \t]{2,}", " ", out).strip()
    return out


def transform_value(value: Any, sysroots: List[str], builddirs: List[str], key: str = "") -> Any:
    if isinstance(value, str):
        if key in BUILD_ONLY_KEYS:
            return ""
        return transform_string(value, sysroots, builddirs)
    if isinstance(value, list):
        return [transform_value(v, sysroots, builddirs) for v in value]
    if isinstance(value, dict):
        return {k: transform_value(v, sysroots, builddirs, key=str(k)) for k, v in value.items()}
    return value


def load_py(path: Path) -> tuple[str, dict, str]:
    text = path.read_text(encoding="utf-8")
    # Prefer assignment to build_time_vars = {...}
    m = re.search(r"(?m)^build_time_vars\s*=\s*", text)
    if not m:
        raise ValueError("no build_time_vars assignment found")
    start = m.end()
    # Parse the dict expression with literal_eval by finding matching braces
    if start >= len(text) or text[start] != "{":
        # Might be a name or call; fall back to exec in empty dict (still validate)
        raise ValueError("build_time_vars is not a dict literal")
    depth = 0
    end = None
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise ValueError("unbalanced braces in build_time_vars")
    data = ast.literal_eval(text[start:end])
    if not isinstance(data, dict):
        raise ValueError("build_time_vars is not a dict")
    prefix = text[: m.start()]
    suffix = text[end:]
    return prefix + "build_time_vars = ", data, suffix


def dump_py(prefix: str, data: dict, suffix: str) -> str:
    # Use pprint for a stable, re-parsable dict literal.
    body = pprint.pformat(data, width=100, sort_dicts=False)
    # Ensure assignment form
    if not prefix.endswith("= ") and not prefix.endswith("="):
        prefix = prefix.rstrip() + " = "
    out = prefix + body
    # Preserve trailing newline convention
    if suffix:
        out += suffix
    elif not out.endswith("\n"):
        out += "\n"
    return out


def process(path: Path, sysroots: List[str], builddirs: List[str]) -> bool:
    """Return True if the file was modified."""
    sysroots = longest_first(sysroots)
    builddirs = longest_first(builddirs)
    name = path.name
    if name.startswith("_sysconfig_vars") and name.endswith(".json"):
        original = path.read_text(encoding="utf-8")
        data = json.loads(original)
        if not isinstance(data, dict):
            raise ValueError("sysconfig json root is not a dict")
        new_data = transform_value(data, sysroots, builddirs)
        new_text = json.dumps(new_data, indent=2, sort_keys=False) + "\n"
        # Validate
        json.loads(new_text)
        if new_text != original and new_text.rstrip() + "\n" != original:
            # Compare semantically too
            if json.loads(original) == new_data and original.strip() == new_text.strip():
                return False
        if json.dumps(json.loads(original), sort_keys=True) == json.dumps(new_data, sort_keys=True):
            # Only whitespace/formatting would change; still rewrite if content transformed
            pass
        if new_data != json.loads(original):
            path.write_text(new_text, encoding="utf-8")
            # Re-parse validate
            json.loads(path.read_text(encoding="utf-8"))
            return True
        return False

    if name.startswith("_sysconfigdata") and name.endswith(".py"):
        original = path.read_text(encoding="utf-8")
        prefix, data, suffix = load_py(path)
        new_data = transform_value(data, sysroots, builddirs)
        new_text = dump_py(prefix, new_data, suffix)
        # Validate by re-parsing
        tmp_path_text = new_text
        # Re-extract and literal_eval
        m = re.search(r"(?m)^build_time_vars\s*=\s*", tmp_path_text)
        if not m:
            raise ValueError("rewrite lost build_time_vars")
        start = m.end()
        depth = 0
        end = None
        for i, ch in enumerate(tmp_path_text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            raise ValueError("rewrite produced unbalanced braces")
        checked = ast.literal_eval(tmp_path_text[start:end])
        if checked != new_data:
            raise ValueError("rewrite failed round-trip literal_eval")
        if new_data != data:
            path.write_text(new_text, encoding="utf-8")
            return True
        return False

    raise ValueError(f"unsupported sysconfig file: {name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--sysroot", action="append", default=[])
    ap.add_argument("--builddir", action="append", default=[])
    args = ap.parse_args()
    path = Path(args.file)
    try:
        changed = process(path, args.sysroot, args.builddir)
    except Exception as exc:  # noqa: BLE001 — fail closed with clear error
        print(f"target-pkgconfig-sysconfig: {path}: {exc}", file=sys.stderr)
        return 1
    if changed:
        print(f"target-pkgconfig: neutralized python sysconfig paths in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
