#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
"""Exercise mkimage and dumpimage on a small external-data FIT."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mkimage", type=Path, required=True)
    parser.add_argument("--dumpimage", type=Path, required=True)
    parser.add_argument("--host-prefix", type=Path, required=True)
    args = parser.parse_args()
    env = os.environ.copy()
    env["PATH"] = str(args.host_prefix.resolve() / "bin")

    with tempfile.TemporaryDirectory(prefix="uboot-tools-") as tmp:
        root = Path(tmp)
        payload = b"U-Boot FIT round-trip\n" * 37
        (root / "payload.bin").write_bytes(payload)
        (root / "image.its").write_text('''/dts-v1/;
/ {
    description = "Native U-Boot tools round-trip";
    #address-cells = <1>;
    images {
        payload {
            description = "test payload";
            data = /incbin/("payload.bin");
            type = "firmware";
            arch = "riscv";
            compression = "none";
            hash-1 { algo = "sha256"; };
        };
    };
    configurations {
        default = "conf";
        conf { description = "test"; firmware = "payload"; };
    };
};
''')
        subprocess.run([str(args.mkimage.resolve()), "-E", "-f", "image.its",
                        "image.itb"], cwd=root, env=env, check=True)
        result = subprocess.run(
            [str(args.host_prefix.resolve() / "bin/fdtget"), "-t", "bx",
             "image.itb", "/images/payload/hash-1", "value"],
            cwd=root, env=env, check=True, capture_output=True, text=True)
        digest = bytes(int(part, 16) for part in result.stdout.split())
        if digest != hashlib.sha256(payload).digest():
            raise SystemExit("FIT payload hash does not match")
        subprocess.run([str(args.dumpimage.resolve()), "-l", "image.itb"],
                       cwd=root, env=env, check=True)
        subprocess.run([str(args.dumpimage.resolve()), "-T", "flat_dt", "-p",
                        "0", "-o", "extracted.bin", "image.itb"],
                       cwd=root, env=env, check=True)
        if (root / "extracted.bin").read_bytes() != payload:
            raise SystemExit("FIT payload changed during round-trip")
    print("FIT external-data round-trip passed")


if __name__ == "__main__":
    main()
