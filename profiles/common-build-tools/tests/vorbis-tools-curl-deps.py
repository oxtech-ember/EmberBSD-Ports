#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that native audio/vorbis-tools depends on the libraries in libcurl.la.

libtool links ogg123 to every library in libcurl.la's dependency_libs.
Before the fix the macOS check-shlibs stopped the native build because
nghttp2, libidn2, libunistring, openssl and zlib were not runtime
dependencies.
"""

import argparse
import os
from pathlib import Path
import subprocess

# curl build option -> package paths whose libraries libcurl.la lists.
OPTION_PATHS = {
    None: ("devel/zlib",),
    "openssl": ("security/openssl",),
    "idn": ("devel/libidn2", "textproc/libunistring"),
    "http2": ("www/nghttp2",),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True,
                        help="MAKECONF of a NetBSD cross build on macOS")
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()
    makeconf = str(args.makeconf.resolve(strict=True))
    argv = [args.bmake, "-C", str(args.pkgsrc.resolve(strict=True) / "audio/vorbis-tools"),
            "MAKECONF=" + makeconf, "USE_CROSS_COMPILE=no",
            "-V", "${PKG_BUILD_OPTIONS.curl}", "-V", "${DEPENDS}"]
    result = subprocess.run(argv, check=True, text=True,
                            env=dict(os.environ, MAKECONF=makeconf),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    values = result.stdout.splitlines()
    if len(values) != 2:
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    options = set(values[0].split())
    depends = {d.rsplit(":", 1)[-1] for d in values[1].split()}
    missing = [path for option, paths in OPTION_PATHS.items()
               if option is None or option in options
               for path in paths if "../../" + path not in depends]
    if missing:
        print("FAIL: native vorbis-tools lacks " + ", ".join(missing))
        raise SystemExit(1)
    print("PASS: native vorbis-tools depends on the libraries in libcurl.la")


if __name__ == "__main__":
    main()
