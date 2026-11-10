#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Transform staged Python sysconfig metadata
# so build-host paths do not ship in the target package.
"""Rewrite Python sysconfig metadata for cross installs.

Handles _sysconfigdata*.py, _sysconfig_vars*.json, and the consumer-facing
lib/python*/config-*/Makefile next to a staged CPython install.
With --recompile-pyc, rebuild matching _sysconfigdata bytecode from the
sanitized .py using the installed path as dfile.

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
    "PYTHON_FOR_REGEN",
    "TESTPYTHON",
    "TESTRUNNER",
    "FREEZE_MODULE",
    "FREEZE_MODULE_BOOTSTRAP",
    "CONFIG_ARGS",
}

CROSS_TOOLS_BIN = re.compile(
    r"/[^\s\"]*/(?:cross|target)-tools/bin/+?(?:[^/\s\"]+/)*([A-Za-z0-9._+-]+)"
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

    # cross-tools / target-tools wrappers -> basename
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


INSTALL_KEYS = {
    "INSTALL",
    "INSTALL_DATA",
    "INSTALL_PROGRAM",
    "INSTALL_SCRIPT",
    "INSTALL_SHARED",
}
# Build-host ownership in either order: -o user -g group, or -g group -o user.
INSTALL_OWNER = re.compile(
    r"[ \t]+-(?:o[ \t]+\S+[ \t]+-g|g[ \t]+\S+[ \t]+-o)[ \t]+\S+"
)


def strip_install_owner(value: str) -> str:
    return INSTALL_OWNER.sub("", value)


def transform_value(value: Any, sysroots: List[str], builddirs: List[str], key: str = "") -> Any:
    if isinstance(value, str):
        if key in BUILD_ONLY_KEYS:
            return ""
        out = transform_string(value, sysroots, builddirs)
        if key in INSTALL_KEYS:
            out = strip_install_owner(out).strip()
        return out
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


ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)([ \t]*\??[+]?=)(.*)$", re.S)


def _fold_make_value(value: str) -> str:
    """Join Makefile continuation lines, keeping a single space between pieces."""
    parts: List[str] = []
    for phys in value.splitlines():
        if phys.endswith("\\"):
            phys = phys[:-1]
        if not parts:
            parts.append(phys)
        else:
            parts.append(phys.strip())
    if not parts:
        return ""
    rest = [p for p in parts[1:] if p != ""]
    if not rest:
        return parts[0]
    return parts[0].rstrip() + " " + " ".join(rest)


def _assignment_needs_rewrite(
    key: str, raw_val: str, sysroots: List[str], builddirs: List[str]
) -> bool:
    folded = _fold_make_value(raw_val)
    if key in BUILD_ONLY_KEYS and "/" in folded:
        return True
    if key in INSTALL_KEYS and INSTALL_OWNER.search(raw_val):
        return True
    for root in list(sysroots) + list(builddirs):
        if root and root in raw_val:
            return True
    if CROSS_TOOLS_BIN.search(raw_val) or BUILDLINK_LIB.search(raw_val):
        return True
    if re.search(r"/(?:cross|target)-tools/", raw_val) or ".buildlink" in raw_val:
        return True
    if "--sysroot=" in raw_val:
        return True
    return False


def process_makefile(path: Path, sysroots: List[str], builddirs: List[str]) -> bool:
    """Rewrite path-bearing assignments in a CPython lib/python*/config-*/Makefile.

    Assignments that do not name a host/build path or build-host install
    ownership are kept byte-identical, including continuation backslashes.
    """
    original = path.read_text(encoding="utf-8")
    out: List[str] = []
    buf = ""
    changed = False

    def flush_logical(block: str) -> None:
        nonlocal changed
        if not block:
            return
        ended_nl = block.endswith("\n")
        body = block[:-1] if ended_nl else block
        m = ASSIGN.match(body)
        if not m:
            out.append(block)
            return
        key, op, raw_val = m.group(1), m.group(2), m.group(3)
        if not _assignment_needs_rewrite(key, raw_val, sysroots, builddirs):
            out.append(block)
            return
        folded = _fold_make_value(raw_val)
        lead_m = re.match(r"[ \t]*", folded)
        lead = lead_m.group(0) if lead_m else ""
        core = folded[len(lead) :]
        if key in BUILD_ONLY_KEYS:
            # Keep already-portable values such as srcdir=.
            if "/" in core.strip():
                new_core = ""
                lead = ""
            else:
                new_core = transform_string(core, sysroots, builddirs)
        else:
            new_core = transform_string(core, sysroots, builddirs)
            if key in INSTALL_KEYS:
                new_core = strip_install_owner(new_core).strip()
        new_block = f"{key}{op}{lead}{new_core}"
        if ended_nl:
            new_block += "\n"
        if new_block != block:
            changed = True
        out.append(new_block)

    for line in original.splitlines(keepends=True):
        if buf:
            buf += line
            if not line.rstrip("\n").endswith("\\"):
                flush_logical(buf)
                buf = ""
            continue
        if line.rstrip("\n").endswith("\\"):
            buf = line
            continue
        flush_logical(line)
    if buf:
        flush_logical(buf)
    new_text = "".join(out)
    if changed and new_text != original:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def is_python_config_makefile(path: Path) -> bool:
    if path.name != "Makefile":
        return False
    return bool(re.search(r"/lib/python[^/]+/config-[^/]+/Makefile$", path.as_posix()))


PYC_NEEDLES = (
    b".buildlink",
    b"cross-tools",
    b"target-tools",
    b"/Volumes/",
    b"/Users/",
    b"work.NetBSD",
)


def _python_lib_version(path: Path) -> tuple[int, int]:
    m = re.search(r"/lib/python(\d+)\.(\d+)/", path.as_posix())
    if not m:
        raise ValueError(f"not a lib/pythonX.Y path: {path}")
    return int(m.group(1)), int(m.group(2))


def recompile_sysconfig_pyc(
    src: Path, destdir: str, sysroots: List[str], builddirs: List[str]
) -> None:
    """Rebuild _sysconfigdata*.pyc from a sanitized .py with an installed dfile.

    The running interpreter must match the staged lib/pythonX.Y version.
    Existing optimize levels are regenerated; the usual 0 and opt-1 files
    are always written so pkgsrc plist-python.awk entries stay present.
    """
    import os
    import py_compile
    import tempfile

    want = _python_lib_version(src)
    have = sys.version_info[:2]
    if have != want:
        raise ValueError(
            f"host python {have[0]}.{have[1]} does not match lib/python{want[0]}.{want[1]}"
        )
    dest = str(Path(destdir)).rstrip("/")
    src_s = str(src)
    prefix = dest + "/"
    if src_s != dest and not src_s.startswith(prefix):
        raise ValueError(f"{src} is not under destdir {dest}")
    dfile = src_s[len(dest) :] if src_s.startswith(prefix) else src_s
    if not dfile.startswith("/"):
        dfile = "/" + dfile
    tag = f"cpython-{have[0]}{have[1]}"
    cache = src.parent / "__pycache__"
    cache.mkdir(parents=True, exist_ok=True)
    planned = {
        cache / f"{src.stem}.{tag}.pyc": 0,
        cache / f"{src.stem}.{tag}.opt-1.pyc": 1,
    }
    for existing in cache.glob(f"{src.stem}.{tag}*.pyc"):
        name = existing.name
        if f".{tag}.opt-" in name:
            try:
                opt = int(name.rsplit(".opt-", 1)[1].split(".")[0])
            except ValueError as exc:
                raise ValueError(f"unrecognized sysconfig pyc name: {name}") from exc
            planned[existing] = opt
        elif name == f"{src.stem}.{tag}.pyc":
            planned[existing] = 0
    needles = list(PYC_NEEDLES)
    for root in list(sysroots) + list(builddirs):
        if root:
            needles.append(root.encode("utf-8"))
    for cfile, opt in planned.items():
        fd, tmp_name = tempfile.mkstemp(
            prefix=cfile.name + ".", suffix=".tmp", dir=str(cache)
        )
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            py_compile.compile(
                str(src),
                cfile=str(tmp),
                dfile=dfile,
                optimize=opt,
                invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH,
            )
            data = tmp.read_bytes()
            for needle in needles:
                if needle and needle in data:
                    raise ValueError(
                        f"recompiled {cfile.name} still names {needle!r}"
                    )
            os.replace(str(tmp), str(cfile))
        finally:
            if tmp.exists():
                tmp.unlink()
        rel = str(cfile)
        if rel.startswith(prefix):
            rel = rel[len(dest) :]
        print(f"target-pkgconfig: regenerated python sysconfig bytecode {rel}")



def process(path: Path, sysroots: List[str], builddirs: List[str]) -> bool:
    """Return True if the file was modified."""
    sysroots = longest_first(sysroots)
    builddirs = longest_first(builddirs)
    name = path.name
    if is_python_config_makefile(path):
        return process_makefile(path, sysroots, builddirs)
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

    raise ValueError(f"unsupported sysconfig file: {path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--recompile-pyc", metavar="FILE")
    ap.add_argument("--destdir")
    ap.add_argument("--sysroot", action="append", default=[])
    ap.add_argument("--builddir", action="append", default=[])
    args = ap.parse_args()
    if args.recompile_pyc:
        if not args.destdir:
            print("target-pkgconfig-sysconfig: --destdir is required with --recompile-pyc", file=sys.stderr)
            return 2
        path = Path(args.recompile_pyc)
        try:
            recompile_sysconfig_pyc(path, args.destdir, args.sysroot, args.builddir)
        except Exception as exc:  # noqa: BLE001 — fail closed with clear error
            print(f"target-pkgconfig-sysconfig: {path}: {exc}", file=sys.stderr)
            return 1
        return 0
    if not args.file:
        print("target-pkgconfig-sysconfig: FILE or --recompile-pyc is required", file=sys.stderr)
        return 2
    path = Path(args.file)
    try:
        changed = process(path, args.sysroot, args.builddir)
    except Exception as exc:  # noqa: BLE001 — fail closed with clear error
        print(f"target-pkgconfig-sysconfig: {path}: {exc}", file=sys.stderr)
        return 1
    if changed:
        kind = "config Makefile" if is_python_config_makefile(path) else "sysconfig"
        print(f"target-pkgconfig: neutralized python {kind} paths in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
