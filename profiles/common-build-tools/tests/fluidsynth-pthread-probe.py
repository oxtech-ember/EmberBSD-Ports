#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that audio/fluidsynth links with the pthread flags.

Before the fix the osal=cpp11 std::thread probe linked without -pthread on
NetBSD, and configure stopped.
"""

import argparse
import os
from pathlib import Path
import subprocess

VARIABLES = ("OPSYS", "PTHREAD_LDFLAGS", "LDFLAGS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True)
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()
    makeconf = args.makeconf.resolve(strict=True)
    argv = [args.bmake, "-C", str(args.pkgsrc.resolve(strict=True) / "audio/fluidsynth"),
            "MAKECONF=" + str(makeconf),
            # buildlink adds the pthread flags after the barrier.
            "_PKGSRC_BARRIER=yes"]
    for variable in VARIABLES:
        argv.extend(("-V", "${%s}" % variable))
    result = subprocess.run(argv, check=True, text=True,
                            env=dict(os.environ, MAKECONF=str(makeconf)),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    values = dict(zip(VARIABLES, result.stdout.splitlines()))
    if len(values) != len(VARIABLES):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    if values["OPSYS"] != "NetBSD":
        parser.error("Select a MAKECONF for a NetBSD target")
    flags = values["PTHREAD_LDFLAGS"].split()
    if not flags or not set(flags) <= set(values["LDFLAGS"].split()):
        print("FAIL: LDFLAGS lacks the pthread flags %r" % flags)
        raise SystemExit(1)
    print("PASS: fluidsynth links with %s" % " ".join(flags))


if __name__ == "__main__":
    main()
