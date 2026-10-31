#!/usr/bin/env python3
"""Test staged SHA1DC consumers and its instrumented upstream sources."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--cc", required=True, type=Path)
    args = parser.parse_args()
    stage = args.stage.resolve(strict=True)
    source = args.source.resolve(strict=True)
    cc = args.cc.resolve(strict=True)
    own = Path(__file__).resolve().parent
    vector = source / "test" / "shattered-1.pdf"
    env = os.environ.copy()
    env["DYLD_LIBRARY_PATH"] = str(stage / "lib")
    env["LD_LIBRARY_PATH"] = str(stage / "lib")
    subprocess.run([sys.executable, str(own / "test-cli.py"), str(stage),
                    str(source)], env=env, check=True)
    with tempfile.TemporaryDirectory(prefix="sha1dc-test-") as tmp:
        tmp = Path(tmp)
        common = [str(cc), "-Wall", "-Wextra", "-Werror", "-I" + str(stage / "include"),
                  str(own / "test-api.c")]
        builds = {
            "static": [str(stage / "lib" / "libsha1detectcoll.a")],
            "shared": ["-L" + str(stage / "lib"), "-lsha1detectcoll"],
            "asan-ubsan": ["-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                           "-fno-omit-frame-pointer",
                           str(source / "lib" / "sha1.c"),
                           str(source / "lib" / "ubc_check.c")],
        }
        for name, flags in builds.items():
            binary = tmp / name
            subprocess.run(common + flags + ["-o", str(binary)], env=env, check=True)
            subprocess.run([str(binary), str(vector)], env=env, check=True)
            print(name + " API vectors passed", flush=True)
        instrumented = tmp / "instrumented"
        (instrumented / "bin").mkdir(parents=True)
        (instrumented / "lib").mkdir()
        command = instrumented / "bin" / "sha1dcsum"
        subprocess.run([str(cc), "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                        "-fno-omit-frame-pointer",
                        "-I" + str(source / "lib"), str(source / "src" / "main.c"),
                        str(source / "lib" / "sha1.c"), str(source / "lib" / "ubc_check.c"),
                        "-o", str(command)], env=env, check=True)
        (instrumented / "bin" / "sha1dcsum_partialcoll").symlink_to("sha1dcsum")
        subprocess.run([sys.executable, str(own / "test-cli.py"), str(instrumented),
                        str(source)], env=env, check=True)
        print("asan-ubsan CLI vectors passed", flush=True)


if __name__ == "__main__":
    main()
