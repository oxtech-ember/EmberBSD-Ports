#!/usr/bin/env python3
"""Check CJS locale behavior when the target libc has no uselocale()."""

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess


def extract_function(source):
    signature = "const char* gjs_set_thread_locale"
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def harness(function):
    return r"""#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <locale.h>
#include <stdlib.h>
#include <string.h>

typedef enum {
    GJS_LOCALE_CATEGORY_ALL = LC_ALL,
    GJS_LOCALE_CATEGORY_COLLATE = LC_COLLATE,
    GJS_LOCALE_CATEGORY_CTYPE = LC_CTYPE,
    GJS_LOCALE_CATEGORY_MESSAGES = LC_MESSAGES,
    GJS_LOCALE_CATEGORY_MONETARY = LC_MONETARY,
    GJS_LOCALE_CATEGORY_NUMERIC = LC_NUMERIC,
    GJS_LOCALE_CATEGORY_TIME = LC_TIME,
} GjsLocaleCategory;

#define EMBERBSD_NO_USELOCALE 1
""" + function + r"""

int main(void) {
    if (setlocale(LC_ALL, "C") == NULL)
        return 1;

    const char *current = setlocale(LC_ALL, NULL);
    const char *query = gjs_set_thread_locale(GJS_LOCALE_CATEGORY_ALL, NULL);
    if (current == NULL || query == NULL || strcmp(current, query) != 0)
        return 2;

    errno = 0;
    if (gjs_set_thread_locale(GJS_LOCALE_CATEGORY_ALL, "C") != NULL)
        return 3;
    if (errno != ENOTSUP)
        return 4;
    if (strcmp(setlocale(LC_ALL, NULL), "C") != 0)
        return 5;
    return 0;
}
"""


def compile_program(command, source, output, sanitizer=False):
    flags = ["-std=c11", "-Wall", "-Wextra", "-Werror",
             "-Werror=implicit-function-declaration", str(source), "-o", str(output)]
    if sanitizer:
        flags += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    subprocess.run(command + flags, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path,
                        help="unpatched CJS source directory for the pinned commit")
    parser.add_argument("work", type=Path)
    parser.add_argument("--cc", default="clang")
    parser.add_argument("--target-cc", help="optional GCC16 AArch64 NetBSD compiler")
    parser.add_argument("--target-sysroot", type=Path)
    parser.add_argument("--target-nm", help="optional matching AArch64 NetBSD nm")
    args = parser.parse_args()

    if (args.target_cc is None) != (args.target_sysroot is None):
        parser.error("--target-cc and --target-sysroot must be provided together")
    args.work.mkdir(parents=True, exist_ok=False)

    source = args.source / "libgjs-private/gjs-util.c"
    original = source.read_text()
    patch = Path(__file__).resolve().parents[1] / "patches/patch-libgjs-private_gjs-util.c"
    candidate_dir = args.work / "candidate"
    (candidate_dir / "libgjs-private").mkdir(parents=True)
    shutil.copyfile(source, candidate_dir / "libgjs-private/gjs-util.c")
    subprocess.run(["patch", "-f", "-F0", "-p0", "-d", str(candidate_dir),
                    "-i", str(patch)], check=True)

    candidate = (candidate_dir / "libgjs-private/gjs-util.c").read_text()
    if "gjs_compat_uselocale" in candidate or "#define uselocale" in candidate:
        raise RuntimeError("the target patch must not fake a uselocale implementation")

    program_source = args.work / "locale-portability.c"
    program_source.write_text(harness(extract_function(candidate)))
    native = shlex.split(args.cc)
    results = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "checks": [],
    }
    for sanitizer in (False, True):
        output = args.work / ("locale-native-san" if sanitizer else "locale-native")
        compile_program(native, program_source, output, sanitizer)
        subprocess.run([str(output)], check=True,
                       env={"ASAN_OPTIONS": "detect_leaks=0:halt_on_error=1",
                            "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1"})
        results["checks"].append({"kind": "native", "sanitizer": sanitizer,
                                  "status": "pass"})

    if args.target_cc:
        target = shlex.split(args.target_cc)
        target += ["--sysroot=" + str(args.target_sysroot)]
        output = args.work / "locale-aarch64-netbsd"
        compile_program(target, program_source, output)
        if args.target_nm:
            symbols = subprocess.check_output([args.target_nm, "-u", str(output)], text=True)
            if "uselocale" in symbols:
                raise RuntimeError("the unsupported target symbol remains undefined")
        results["checks"].append({"kind": "aarch64-netbsd-link", "status": "pass"})

    (args.work / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print("PASS: query reports the global locale; setters return ENOTSUP without changing it")


if __name__ == "__main__":
    main()
