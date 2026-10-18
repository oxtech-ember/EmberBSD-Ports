#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), execute the actual loader callback body.
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: epoxy-loader-callback.py MESA_RENDER_SOURCE NEW_WORK")
    source = Path(sys.argv[1]).resolve(strict=True)
    work = Path(sys.argv[2])
    if not work.is_absolute() or work.exists() or work.is_symlink():
        raise SystemExit("NEW_WORK must be new and absolute")
    work.mkdir(parents=True)
    callback = re.search(r"static int\nloaded_library\(.*?^}\n", source.read_text(), re.MULTILINE | re.DOTALL)
    if callback is None:
        raise SystemExit("missing actual loader callback")
    # Host data fixture: only the field read by the actual callback, not a loader or renderer.
    (work / "callback.c").write_text('''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct dl_phdr_info { const char *dlpi_name; };
''' + callback[0] + '''int main(int argc, char **argv) {
    struct dl_phdr_info info;
    int result;
    if (argc != 3) return 2;
    info.dlpi_name = argv[1];
    result = loaded_library(&info, sizeof(info), (void *)"/tmp/consumer");
    printf("callback returned %d\\n", result);
    return result == atoi(argv[2]) ? 0 : 3;
}
''')
    cc = shlex.split(os.environ.get("CC", "cc"))
    result = subprocess.run([*cc, "-std=c11", "-Wall", "-Wextra", "-Werror", str(work / "callback.c"),
                             "-o", str(work / "callback-test")], capture_output=True, text=True, timeout=120, check=False)
    (work / "compile.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit("callback fixture compile failed")
    failed = []
    cases = {"base-loader": ("/libexec/ld.elf_so", 0), "usr-loader": ("/usr/libexec/ld.elf_so", 0),
             "foreign-library": ("/private/tmp/foreign/libLLVM.so", 1)}
    for name, (path, expected) in cases.items():
        result = subprocess.run([str(work / "callback-test"), path, str(expected)],
                                capture_output=True, text=True, timeout=10, check=False)
        (work / (name + ".log")).write_text(result.stdout + result.stderr)
        valid = result.returncode == 0 and f"callback returned {expected}\n" in result.stdout
        if expected == 1:
            valid = valid and "unexpected loaded library" in result.stderr
        print(f"{'PASS' if valid else 'FAIL'}: {name} returns to iterator caller")
        if not valid:
            failed.append(name)
    with source.open("rb") as stream:
        source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    (work / "source.sha256").write_text(f"{source_hash}  {source}\n")
    if failed:
        raise SystemExit("failed callback cases: " + ", ".join(failed))


if __name__ == "__main__":
    main()
