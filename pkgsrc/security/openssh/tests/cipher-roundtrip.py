#!/usr/bin/env python3
"""Compile and run the selected OpenSSH cipher against an existing native build."""
import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", type=Path, required=True)
    parser.add_argument("--cipher-source", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True,
                        help="completed native OpenSSH build with config.h and archives")
    parser.add_argument("--crypto-prefix", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    cc, source, build, prefix, work = (p.resolve() for p in (
        args.cc, args.cipher_source, args.build_dir, args.crypto_prefix, args.work_dir))
    work.mkdir(parents=True, exist_ok=True)
    flags = ["-fsanitize=address,undefined"] if args.sanitize else []
    cipher_object = work / "cipher-roundtrip.o"
    exe = work / "cipher-roundtrip"
    subprocess.run([str(cc), *flags, "-DHAVE_CONFIG_H", "-I", str(build),
                    "-I", str(prefix / "include"), "-c", str(source),
                    "-o", str(cipher_object)], check=True, cwd=work)
    subprocess.run([str(cc), *flags, "-I", str(build), "-I", str(prefix / "include"),
                    str(Path(__file__).with_suffix(".c")), str(cipher_object),
                    str(build / "libssh.a"), str(build / "openbsd-compat/libopenbsd-compat.a"),
                    "-L", str(prefix / "lib"), f"-Wl,-rpath,{prefix / 'lib'}",
                    "-lcrypto", "-lz", "-o", str(exe)], check=True, cwd=work)
    subprocess.run([str(exe)], check=True, cwd=work)


if __name__ == "__main__":
    main()
