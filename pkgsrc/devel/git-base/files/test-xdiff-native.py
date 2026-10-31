#!/usr/bin/env python3
"""Exercise source-level xdiff compatibility using a selected host compiler."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path,
                        help="staged share/git-xdiff-source directory")
    parser.add_argument("--cc", required=True, type=Path)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    cc = args.cc.resolve(strict=True)
    own = Path(__file__).resolve().parent
    files = sorted((source / "xdiff").glob("*.c"))
    if len(files) != 7:
        raise SystemExit("expected seven Git xdiff C sources")
    for check in ("test-xdiff-hooks.c", "test-xdiff-defaults.c"):
        subprocess.run([str(cc), "-std=c11", "-Werror=macro-redefined", "-I", str(source),
                        "-fsyntax-only", str(own / check)], check=True)
    with tempfile.TemporaryDirectory(prefix="git-xdiff-test-") as tmp:
        binary = Path(tmp) / "test-xdiff"
        subprocess.run([str(cc), "-std=c11", "-Werror", "-fsanitize=address,undefined",
                        "-fno-sanitize-recover=all", "-fno-omit-frame-pointer",
                        "-DTEST_XDL_RETURNS", "-I", str(own), "-I", str(source / "xdiff"),
                        '-DXDL_COMPAT_HEADER="test-xdiff-compat.h"',
                        str(own / "test-xdiff-runtime.c"), *map(str, files),
                        "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
