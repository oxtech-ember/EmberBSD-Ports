#!/usr/bin/env python3
"""Check the two staged upstream commands, including stdin and failures."""
import os
from pathlib import Path
import subprocess
import sys

if not __debug__:
    raise SystemExit("run the test without Python optimization")

stage, source = map(Path, sys.argv[1:3])
env = os.environ.copy()
env["LC_ALL"] = "C"
env["DYLD_LIBRARY_PATH"] = str(stage / "lib")
env["LD_LIBRARY_PATH"] = str(stage / "lib")


def run(name, *args, input=None):
    return subprocess.run(
        [str(stage / "bin" / name), *map(str, args)], input=input,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False,
    )


normal = run("sha1dcsum", "-", input=b"abc")
assert normal.returncode == 0 and normal.stdout.startswith(
    b"a9993e364706816aba3e25717850c26c9cd0d89d "
), normal
missing_path = source / "test" / "does-not-exist"
missing = run("sha1dcsum", missing_path)
assert missing.returncode == 1 and not missing.stdout and missing.stderr == (
    b"cannot open file: " + os.fsencode(missing_path) + b": No such file or directory\n"
), missing
collision = run("sha1dcsum", source / "test" / "shattered-1.pdf")
assert collision.returncode == 0 and collision.stdout.startswith(
    b"16e96b70000dd1e7c85b8368ee197754400e58ec "
), collision
partial = run("sha1dcsum_partialcoll", source / "test" / "sha1_reducedsha_coll.bin")
assert partial.returncode == 0 and partial.stdout.startswith(
    b"dd39885a2a5d8f59030b451e00cb45da9f9d3828 "
), partial
print("upstream CLI stdin, error and collision vectors passed")
