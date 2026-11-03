#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the real pkg_create and X.509 pkg_admin with a bounded fixture."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
for name in ("pkg-create", "pkg-admin", "key", "certificate", "anchor", "work"):
    parser.add_argument("--" + name, required=True, type=Path)
a = parser.parse_args()
a.work.mkdir(parents=True, exist_ok=False)
payload = a.work / "payload"
payload.mkdir()
(payload / "sample.txt").write_text("signature fixture\n")
plist = a.work / "PLIST"
plist.write_text("@name signature-fixture-1.0\nsample.txt\n")
unsigned = a.work / "signature-fixture-1.0.tar"
signed = a.work / "signed.pkg"
config = a.work / "pkg_install.conf"
config.write_text("CERTIFICATE_ANCHOR_PKGS=" + str(a.anchor) + "\nVERIFIED_INSTALLATION=always\n")

def run(argv, expected):
    result = subprocess.run([str(x) for x in argv], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=30)
    if (result.returncode == 0) != expected:
        raise AssertionError(f"{argv!r}: {result.returncode}: {result.stderr.decode(errors='replace')}")

run([a.pkg_create, "-F", "none", "-p", payload, "-c", "-fixture", "-d", "-fixture",
     "-f", plist, unsigned], True)
with unsigned.open("ab") as f:
    f.write(bytes((-unsigned.stat().st_size) % 65536))
assert unsigned.stat().st_size > 0 and unsigned.stat().st_size % 65536 == 0
verify = [a.pkg_admin, "-C", config, "check-signature"]
run(verify + [unsigned], False)
run([a.pkg_admin, "x509-sign-package", unsigned, signed, a.key, a.certificate], True)
run(verify + [signed], True)
run(verify + [a.work / "missing.pkg"], False)
run(verify + [signed, a.work / "missing.pkg"], False)
print("PASS: full block signing, unsigned rejection, valid signature and missing archive")
