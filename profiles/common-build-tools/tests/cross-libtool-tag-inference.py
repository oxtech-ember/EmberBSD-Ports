#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that the cross libtool infers the C tag for the plain compiler.

Autoconf appended its C23 option to the compiler in the generated C tag.
Packages whose configure calls the compiler without that option then
stopped with "specify a tag with '--tag'" (libpcap, libdvdplay, db18).
The test configures cross/cross-libtool-base in its own WRKOBJDIR and
asks the generated script to compile in dry-run mode with and without
the option.
"""

import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()
    makeconf = args.makeconf.resolve(strict=True)
    work = args.work.resolve()
    if work.exists():
        parser.error("Work directory already exists")
    work.mkdir(parents=True)
    recipe = args.pkgsrc.resolve(strict=True) / "cross/cross-libtool-base"
    base = [args.bmake, "-C", str(recipe), "MAKECONF=" + str(makeconf),
            "WRKOBJDIR=" + str(work / "obj")]
    env = dict(os.environ, MAKECONF=str(makeconf))
    # Build it the way a cross TOOL_DEPENDS does: natively, with the
    # target settings of the cross configuration.
    target = subprocess.run(base + ["-v", "CROSSTARGETSETTINGS"], check=True,
                            text=True, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    base += shlex.split(target.stdout) + ["USE_CROSS_COMPILE=no"]
    query = subprocess.run(base + ["-v", "WRKSRC", "-v", "SH"], check=True,
                           text=True, env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    wrksrc, shell = query.stdout.split()
    with open(work / "configure.log", "w") as log:
        subprocess.run(base + ["configure"], env=env, stdin=subprocess.DEVNULL,
                       stdout=log, stderr=subprocess.STDOUT)
    script = Path(wrksrc) / "libtool"
    if not script.exists():
        print("FAIL: configure did not create %s" % script)
        raise SystemExit(1)
    text = script.read_text(errors="replace")
    head = text.split("# ### BEGIN LIBTOOL TAG CONFIG:", 1)[0]
    match = re.search(r'^CC="([^"]*)"$', head, re.MULTILINE)
    if not match or not shlex.split(match.group(1)):
        print("FAIL: no C tag compiler in %s" % script)
        raise SystemExit(1)
    compiler = shlex.split(match.group(1))[0]
    source = work / "t.c"
    source.write_text("int ember_tag_probe;\n")
    failures = []
    for extra in ([], ["-std=gnu23"]):
        command = [shell, str(script), "--dry-run", "--mode=compile",
                   compiler] + extra + ["-c", str(source)]
        result = subprocess.run(command, cwd=work, text=True,
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode != 0:
            failures.append("%s: %s" % (" ".join([compiler] + extra),
                                        result.stdout.strip().splitlines()[-1:]))
    if failures:
        print("FAIL: C tag CC=%r; %s" % (match.group(1), "; ".join(failures)))
        raise SystemExit(1)
    print("PASS: C tag CC=%r infers plain and -std=gnu23 compiles" % match.group(1))


if __name__ == "__main__":
    main()
