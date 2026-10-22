#!/usr/bin/env python3
"""Run retained GCC16 regressions against exact PartitionAlloc source expressions.

The runner writes only to a caller-selected, new work directory. It uses the
EmberBSD SDK API 1 and its checked process, path, inventory, and JSON helpers.
"""

import argparse
import os
import pathlib
import re
import shutil
import struct
import sys

sys.dont_write_bytecode = True

PARTITION_ALLOC_CC = pathlib.Path(
    "base/allocator/partition_allocator/src/partition_alloc/partition_alloc.cc"
)
SHIM_HEADER = pathlib.Path(
    "base/allocator/partition_allocator/src/partition_alloc/shim/"
    "allocator_shim_override_libc_symbols.h"
)
MACRO_ANCHOR = "// Check that the GetInSlotMetadataIndexMultiplierShift() calculation is"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-source", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--patch", required=True)
    parser.add_argument("--ports-root", required=True)
    parser.add_argument("--cxx", required=True)
    parser.add_argument("--sysroot", required=True)
    parser.add_argument("--workdir", required=True)
    return parser.parse_args()


ARGS = parse_args()
SDK_ROOT = pathlib.Path(ARGS.sdk_source).resolve(strict=True)
sys.path.insert(0, str(SDK_ROOT / "src"))
import emberbsd_sdk
from emberbsd_sdk import inventory, jsonio, paths, process
from emberbsd_sdk import errors
from emberbsd_sdk.errors import CommandError

if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
    raise SystemExit("unsupported EmberBSD SDK API; expected API_VERSION == 1")
if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 15):
    raise SystemExit("this host-tool regression requires CPython 3.15")
for module in (emberbsd_sdk, errors, inventory, jsonio, paths, process):
    module_path = pathlib.Path(module.__file__).resolve(strict=True)
    if module_path.parent != SDK_ROOT / "src" / "emberbsd_sdk":
        raise SystemExit(f"SDK module loaded from an unexpected source: {module_path}")


def write_bytes(path, data, mode=0o644):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, mode)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def write_text(path, value, mode=0o644):
    write_bytes(path, value.encode("utf-8", "strict"), mode)


def split_macro_arguments(value):
    depth = 0
    quote = None
    escaped = False
    for index, char in enumerate(value):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            return value[:index].strip(), value[index + 1 :].strip()
    raise ValueError("production macro call has no top-level message argument")


def extract_production_call(source_text):
    anchor = source_text.find(MACRO_ANCHOR)
    if anchor < 0:
        raise ValueError("production source lost the metadata-multiplier comment anchor")
    start = source_text.find("STATIC_ASSERT_OR_PA_CHECK(", anchor)
    if start < 0:
        raise ValueError("production source has no assertion after its multiplier anchor")
    open_paren = source_text.find("(", start)
    depth = 0
    quote = None
    escaped = False
    close_paren = None
    for index in range(open_paren, len(source_text)):
        char = source_text[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                close_paren = index
                break
    if close_paren is None:
        raise ValueError("unterminated production assertion macro")
    arguments = source_text[open_paren + 1 : close_paren]
    condition, message = split_macro_arguments(arguments)
    return {
        "call": "STATIC_ASSERT_OR_PA_CHECK(" + arguments + ");",
        "condition": condition,
        "message": message,
    }


def extract_size_t_bits_declaration(source_text):
    match = re.search(
        r"constexpr\s+size_t\s+kSizeTBits\s*=\s*"
        r"static_cast<size_t>\(std::numeric_limits<size_t>::digits\);",
        source_text,
    )
    return match.group(0) if match else ""


def main():
    source_root = paths.canonical_existing(ARGS.source_root)
    sdk_root = paths.canonical_existing(ARGS.sdk_source)
    patch_path = paths.canonical_existing(ARGS.patch)
    ports_root = paths.canonical_existing(ARGS.ports_root)
    sysroot = paths.canonical_existing(ARGS.sysroot)
    compiler = paths.canonical_existing(ARGS.cxx)
    workdir = paths.canonical_new(ARGS.workdir)
    if not pathlib.Path(ARGS.workdir).is_absolute():
        raise ValueError("--workdir must be an absolute path")
    if os.path.lexists(workdir):
        raise ValueError(f"refusing existing work directory: {workdir}")
    for input_path in (source_root, sdk_root, patch_path, ports_root, sysroot, compiler):
        paths.reject_overlap(workdir, input_path)
    for relpath in (PARTITION_ALLOC_CC, SHIM_HEADER):
        paths.regular_file(source_root / relpath)
    paths.regular_file(patch_path)
    paths.regular_file(compiler)
    os.mkdir(workdir, 0o755)

    logdir = pathlib.Path(workdir) / "logs"
    os.mkdir(logdir, 0o755)
    command_number = 0
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
        "TMPDIR": str(workdir),
        "LC_ALL": "C",
        "MAKECONF": "/dev/null",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_LAZY_FETCH": "1",
    }

    def capture(argv, cwd, label):
        nonlocal command_number
        command_number += 1
        prefix = logdir / f"{command_number:03d}-{label}"
        try:
            result = process.capture([str(item) for item in argv], cwd=str(cwd), env=env)
            returncode, stdout, stderr = 0, result.stdout, result.stderr
        except CommandError as error:
            returncode, stdout, stderr = error.returncode, error.stdout, error.stderr
        write_bytes(str(prefix) + ".stdout", stdout)
        write_bytes(str(prefix) + ".stderr", stderr)
        jsonio.write_json(
            str(prefix) + ".json",
            {
                "argv": [str(item) for item in argv],
                "cwd": str(cwd),
                "returncode": returncode,
                "stdout_path": str(prefix) + ".stdout",
                "stdout_sha256": inventory.sha256_file(str(prefix) + ".stdout"),
                "stderr_path": str(prefix) + ".stderr",
                "stderr_sha256": inventory.sha256_file(str(prefix) + ".stderr"),
            },
            exclusive=True,
        )
        return {"returncode": returncode, "stdout": stdout, "stderr": stderr}

    def require(result, description):
        if result["returncode"] != 0:
            detail = (result["stderr"] + result["stdout"]).decode("utf-8", "replace")
            raise RuntimeError(f"{description} failed; see retained command logs\n{detail}")

    git = shutil.which("git", path=env["PATH"])
    if git is None:
        raise RuntimeError("git not found in the explicit host PATH")
    git = paths.canonical_existing(git)
    revision = capture([git, "rev-parse", "HEAD"], source_root, "source-head")
    require(revision, "source HEAD query")
    source_head = revision["stdout"].decode("ascii", "strict").strip()
    ports_revision = capture([git, "rev-parse", "HEAD"], ports_root, "ports-head")
    require(ports_revision, "Ports HEAD query")
    ports_head = ports_revision["stdout"].decode("ascii", "strict").strip()
    sdk_revision = capture([git, "rev-parse", "HEAD"], sdk_root, "sdk-head")
    require(sdk_revision, "SDK HEAD query")
    sdk_head = sdk_revision["stdout"].decode("ascii", "strict").strip()

    files = (PARTITION_ALLOC_CC, SHIM_HEADER)
    original_hashes = {
        rel.as_posix(): inventory.sha256_file(str(source_root / rel)) for rel in files
    }
    patch_hash = inventory.sha256_file(patch_path)
    stage_root = pathlib.Path(workdir) / "stage"
    before_root = stage_root / "before"
    after_root = stage_root / "after"

    def copy_pair(destination):
        for rel in files:
            output = destination / rel
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_root / rel, output)

    stage_root.mkdir()
    before_root.mkdir()
    after_root.mkdir()
    copy_pair(before_root)
    copy_pair(after_root)
    forward = capture([git, "apply", "--check", str(patch_path)], before_root, "patch-forward-check")
    if forward["returncode"] == 0:
        current_state = "baseline"
        require(capture([git, "apply", str(patch_path)], after_root, "patch-forward-apply"), "forward patch")
    else:
        reverse = capture([git, "apply", "--reverse", "--check", str(patch_path)], after_root, "patch-reverse-check")
        require(reverse, "reverse patch applicability check")
        current_state = "patched"
        require(capture([git, "apply", "--reverse", str(patch_path)], before_root, "patch-reverse-apply"), "reverse patch")
    require(capture([git, "apply", "--check", str(patch_path)], before_root, "patch-roundtrip-forward"), "forward roundtrip check")
    require(capture([git, "apply", "--reverse", "--check", str(patch_path)], after_root, "patch-roundtrip-reverse"), "reverse roundtrip check")

    before_cc = (before_root / PARTITION_ALLOC_CC).read_text(encoding="utf-8")
    after_cc = (after_root / PARTITION_ALLOC_CC).read_text(encoding="utf-8")
    before_call = extract_production_call(before_cc)
    after_call = extract_production_call(after_cc)
    after_bits = extract_size_t_bits_declaration(after_cc)
    if before_call["condition"] == after_call["condition"] or not after_bits:
        raise RuntimeError("source diff did not yield distinct, width-bounded production conditions")

    fixture_root = pathlib.Path(workdir) / "fixtures"
    os.mkdir(fixture_root, 0o755)
    compiler_base = [
        str(compiler),
        f"--sysroot={sysroot}",
        "-std=c++20",
        "-Wall",
        "-Wextra",
        "-Werror",
    ]
    results = []

    compiler_version = capture([compiler, "-dumpfullversion"], fixture_root, "compiler-version")
    require(compiler_version, "compiler full version query")
    compiler_version_text = compiler_version["stdout"].decode("ascii", "strict").strip()
    compiler_machine = capture([compiler, "-dumpmachine"], fixture_root, "compiler-machine")
    require(compiler_machine, "compiler target query")
    compiler_machine_text = compiler_machine["stdout"].decode("ascii", "strict").strip()
    compiler_banner = capture([compiler, "--version"], fixture_root, "compiler-banner")
    require(compiler_banner, "compiler identity query")
    compiler_banner_text = compiler_banner["stdout"].decode("utf-8", "replace")
    if not compiler_version_text.startswith("16.") or compiler_machine_text != "aarch64--netbsd" or "GCC" not in compiler_banner_text:
        raise RuntimeError(
            "selected compiler must be GCC 16 for aarch64--netbsd; got "
            f"version={compiler_version_text!r}, machine={compiler_machine_text!r}"
        )

    def compile_case(label, source_text, extra, output=None, success_expected=True,
                     diagnostic=None, forbidden_diagnostics=()):
        source_file = fixture_root / f"{label}.cc"
        write_text(source_file, source_text)
        argv = list(compiler_base) + list(extra)
        if output is None:
            argv += ["-fsyntax-only", str(source_file)]
        else:
            argv += ["-c", str(source_file), "-o", str(output)]
        result = capture(argv, fixture_root, label)
        message = (result["stderr"] + result["stdout"]).decode("utf-8", "replace")
        passed = (result["returncode"] == 0) if success_expected else (result["returncode"] != 0)
        if diagnostic is not None:
            passed = passed and diagnostic in message
        present = [token for token in forbidden_diagnostics if token.lower() in message.lower()]
        passed = passed and not present
        results.append({
            "test": label,
            "pass": bool(passed),
            "returncode": result["returncode"],
            "diagnostic": message,
            "forbidden_diagnostics": list(forbidden_diagnostics),
            "forbidden_diagnostics_present": present,
            "source_sha256": inventory.sha256_file(str(source_file)),
            "object_path": str(output) if output is not None else None,
            "object_sha256": inventory.sha256_file(str(output)) if output is not None and pathlib.Path(output).is_file() else None,
        })
        return result

    def shift_fixture(call, declaration, constexpr, shift_value):
        if constexpr:
            getter = f"constexpr size_t GetInSlotMetadataIndexMultiplierShift() {{ return {shift_value}; }}"
            page = "constexpr size_t SystemPageSize() { return 4096; }"
            macro = "#define STATIC_ASSERT_OR_PA_CHECK(condition, message) static_assert(condition, message)"
        else:
            getter = f"inline size_t GetInSlotMetadataIndexMultiplierShift() {{ return {shift_value}; }}"
            page = "inline size_t SystemPageSize() { return 4096; }"
            macro = "#define STATIC_ASSERT_OR_PA_CHECK(condition, message) do { if (!(condition)) return false; } while (false)"
        declaration_block = declaration + "\n" if declaration else ""
        return (
            "#include <cstddef>\n#include <limits>\n"
            "using size_t = std::size_t;\n"
            "namespace partition_alloc::internal {\n"
            "struct InSlotMetadata { char value; };\n"
            "constexpr size_t kSuperPageSize = 2 * 1024 * 1024;\n"
            f"{getter}\n{page}\n}}\n"
            "namespace partition_alloc {\n"
            f"{declaration_block}{macro}\n"
            "bool CheckExtractedProductionAssertion() {\n"
            f"  {call['call']}\n"
            "  return true;\n}\n}\n"
        )

    compile_case(
        "production-shift-before-fails-sign-compare",
        shift_fixture(before_call, "", False, "3"),
        ["-Werror=sign-compare"],
        success_expected=False,
        diagnostic="[-Werror=sign-compare]",
    )
    compile_case(
        "production-shift-after-compiles",
        shift_fixture(after_call, after_bits, False, "3"),
        ["-Werror=sign-compare"],
        output=fixture_root / "production-shift-after.o",
    )

    boundary_text = shift_fixture(after_call, after_bits, True, "std::numeric_limits<size_t>::digits")
    compile_case(
        "production-shift-width-boundary-rejected-before-shift",
        boundary_text,
        [],
        success_expected=False,
        diagnostic=after_call["message"].strip('"'),
        forbidden_diagnostics=("shift count", "shift exponent", "greater than or equal to the precision"),
    )
    valid_text = shift_fixture(after_call, after_bits, True, "3")
    compile_case(
        "production-shift-constant-valid-case",
        valid_text,
        [],
        output=fixture_root / "production-shift-valid.o",
    )

    shim_source = r'''#include <stddef.h>
void* ShimMalloc(size_t, void*);
void ShimFree(void*, void*);
void* ShimRealloc(void*, size_t, void*);
void* ShimCalloc(size_t, size_t, void*);
void* ShimMemalign(size_t, size_t, void*);
void* ShimValloc(size_t, void*);
void* ShimPvalloc(size_t);
int ShimPosixMemalign(void**, size_t, size_t);
size_t ShimGetSizeEstimate(const void*, void*);
#include "partition_alloc/shim/allocator_shim_override_libc_symbols.h"
'''
    shim_fixture = fixture_root / "shim"
    os.mkdir(shim_fixture, 0o755)
    netbsd_stub = shim_fixture / "netbsd"
    (netbsd_stub / "partition_alloc").mkdir(parents=True)
    write_text(
        netbsd_stub / "partition_alloc" / "buildflags.h",
        "#ifndef TEST_BUILD_FLAGS_H\n#define TEST_BUILD_FLAGS_H\n"
        "#include \"partition_alloc/buildflag.h\"\n"
        "#define PA_BUILDFLAG_INTERNAL_USE_ALLOCATOR_SHIM() (1)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_CHROMEOS() (0)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_ANDROID() (0)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_NETBSD() (1)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_WIN() (0)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_APPLE() (0)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_POSIX() (1)\n#endif\n",
    )
    shim_cc = fixture_root / "shim-header-smoke.cc"
    write_text(shim_cc, shim_source)
    source_include_before = before_root / "base/allocator/partition_allocator/src"
    source_include_after = after_root / "base/allocator/partition_allocator/src"
    real_source_include = pathlib.Path(source_root) / "base/allocator/partition_allocator/src"
    netbsd_real_header = pathlib.Path(sysroot) / "usr/include/malloc.h"
    if not netbsd_real_header.is_file():
        raise RuntimeError(f"target sysroot has no malloc.h: {netbsd_real_header}")
    before_shim = capture(
        compiler_base + ["-I" + str(netbsd_stub), "-I" + str(source_include_before), "-I" + str(real_source_include), "-fsyntax-only", str(shim_cc)],
        fixture_root,
        "netbsd-shim-before",
    )
    before_diagnostic = (before_shim["stderr"] + before_shim["stdout"]).decode("utf-8", "replace")
    results.append({
        "test": "NetBSD production shim conflicts before patch",
        "pass": before_shim["returncode"] != 0 and "conflicting declaration" in before_diagnostic and "malloc_usable_size" in before_diagnostic,
        "returncode": before_shim["returncode"],
        "diagnostic": before_diagnostic,
        "sysroot_malloc_header_sha256": inventory.sha256_file(str(netbsd_real_header)),
    })
    after_object = fixture_root / "netbsd-shim-after.o"
    after_shim = capture(
        compiler_base + ["-I" + str(netbsd_stub), "-I" + str(source_include_after), "-I" + str(real_source_include), "-c", str(shim_cc), "-o", str(after_object)],
        fixture_root,
        "netbsd-shim-after",
    )
    after_diagnostic = (after_shim["stderr"] + after_shim["stdout"]).decode("utf-8", "replace")
    object_bytes = after_object.read_bytes() if after_object.is_file() else b""
    elf_facts = None
    if len(object_bytes) >= 20 and object_bytes[:4] == b"\x7fELF":
        byte_order = "little" if object_bytes[5] == 1 else "big" if object_bytes[5] == 2 else "unknown"
        if byte_order != "unknown":
            elf_type, elf_machine = struct.unpack_from("<HH" if byte_order == "little" else ">HH", object_bytes, 16)
            elf_facts = {"class": object_bytes[4], "byte_order": byte_order, "type": elf_type, "machine": elf_machine}
    results.append({
        "test": "NetBSD production shim compiles after patch with GCC16",
        "pass": after_shim["returncode"] == 0 and after_object.is_file()
                and elf_facts == {"class": 2, "byte_order": "little", "type": 1, "machine": 183},
        "returncode": after_shim["returncode"],
        "diagnostic": after_diagnostic,
        "object_path": str(after_object),
        "object_sha256": inventory.sha256_file(str(after_object)) if after_object.is_file() else None,
        "object_magic": object_bytes[:20].hex() if object_bytes else None,
        "elf_facts": elf_facts,
    })

    nonbsd_root = shim_fixture / "non-netbsd"
    (nonbsd_root / "partition_alloc").mkdir(parents=True)
    (nonbsd_root / "sys").mkdir()
    write_text(
        nonbsd_root / "partition_alloc" / "buildflags.h",
        "#include \"partition_alloc/buildflag.h\"\n"
        "#define PA_BUILDFLAG_INTERNAL_USE_ALLOCATOR_SHIM() (1)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_CHROMEOS() (0)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_ANDROID() (0)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_APPLE() (0)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_POSIX() (1)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_WIN() (0)\n"
        "#define PA_BUILDFLAG_INTERNAL_IS_NETBSD() (0)\n",
    )
    write_text(
        nonbsd_root / "partition_alloc" / "build_config.h",
        "#ifndef PARTITION_ALLOC_BUILD_CONFIG_H_\n#define PARTITION_ALLOC_BUILD_CONFIG_H_\n"
        "#include \"partition_alloc/buildflag.h\"\n"
        "#include \"partition_alloc/buildflags.h\"\n#endif\n",
    )
    write_text(
        nonbsd_root / "malloc.h",
        "#ifndef TEST_MALLOC_H\n#define TEST_MALLOC_H\n#include <stddef.h>\n"
        "#ifdef __cplusplus\nextern \"C\" {\n#endif\n"
        "size_t malloc_usable_size(void*);\n"
        "#ifdef __cplusplus\n}\n#endif\n#endif\n",
    )
    write_text(nonbsd_root / "sys" / "cdefs.h", "#ifndef TEST_CDEFS_H\n#define TEST_CDEFS_H\n#define __THROW\n#endif\n")
    other_before = capture(
        compiler_base + ["-I" + str(nonbsd_root), "-I" + str(source_include_before), "-I" + str(real_source_include), "-fsyntax-only", str(shim_cc)],
        fixture_root,
        "non-netbsd-shim-before",
    )
    other_after = capture(
        compiler_base + ["-I" + str(nonbsd_root), "-I" + str(source_include_after), "-I" + str(real_source_include), "-fsyntax-only", str(shim_cc)],
        fixture_root,
        "non-netbsd-shim-after",
    )
    results.append({
        "test": "non-NetBSD void-pointer declaration preserved before and after",
        "pass": other_before["returncode"] == 0 and other_after["returncode"] == 0,
        "before_returncode": other_before["returncode"],
        "after_returncode": other_after["returncode"],
        "boundary": "mocked non-NetBSD libc/build-config headers, not a native non-NetBSD SDK",
    })

    final_input_hashes = {
        rel.as_posix(): inventory.sha256_file(str(pathlib.Path(source_root) / rel)) for rel in files
    }
    if final_input_hashes != original_hashes:
        raise RuntimeError("source input files changed during the read-only regression")

    summary = {
        "source_head": source_head,
        "sdk_head": sdk_head,
        "ports_head": ports_head,
        "source_state_at_start": current_state,
        "source_input_hashes": original_hashes,
        "source_input_hashes_at_end": final_input_hashes,
        "source_inputs_unchanged": final_input_hashes == original_hashes,
        "patch_sha256": patch_hash,
        "sdk_source": str(sdk_root),
        "sdk_api_version": emberbsd_sdk.API_VERSION,
        "sdk_modules": {module.__name__: str(pathlib.Path(module.__file__).resolve()) for module in (emberbsd_sdk, errors, inventory, jsonio, paths, process)},
        "python": {"executable": str(pathlib.Path(sys.executable).resolve()), "version": list(sys.version_info[:3]), "sha256": inventory.sha256_file(str(pathlib.Path(sys.executable).resolve()))},
        "compiler": {"path": str(compiler), "sha256": inventory.sha256_file(str(compiler)), "sysroot": str(sysroot)},
        "compiler_target": {"dumpfullversion": compiler_version_text, "dumpmachine": compiler_machine_text, "banner": compiler_banner_text},
        "workdir": str(workdir),
        "invocation": [str(pathlib.Path(sys.executable).resolve()), "-B", "-I", "-S", str(pathlib.Path(__file__).resolve()), *sys.argv[1:]],
        "production_condition_before": before_call["condition"],
        "production_condition_after": after_call["condition"],
        "results": results,
        "passed": sum(1 for result in results if result["pass"]),
        "total": len(results),
    }
    jsonio.write_json(str(pathlib.Path(workdir) / "summary.json"), summary, exclusive=True)
    snapshot = inventory.snapshot_tree(str(workdir))
    jsonio.write_json(str(pathlib.Path(workdir) / "inventory.json"), snapshot, exclusive=True)
    print(jsonio.json_bytes(summary).decode("utf-8"), end="")
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
