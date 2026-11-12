#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Reference: electron/electron PR #55742.
"""Check revoked RSA key coverage in both selected Electron source providers.

Run on the effective build inputs, including the common Node provider, after
source preparation. This verifies blocklist data, not TLS runtime behavior.
The runtime must also pass Node's test-tls-spki-blocklist.js and the Electron
certificate/session tests on the resulting binaries.
"""
import argparse
from pathlib import Path
import re

# SHA-256 of DER SubjectPublicKeyInfo, not whole-certificate fingerprints.
# Published in Electron 45.3.1 patches for eMudhra G2B/G2C revocation.
REVOKED = frozenset("""
04db3b7ddf683b1d4b5b64fe743a3a8d8c3d71f0c339d7dc25b343e665a9eb5b
34556838281688d1c967d43d1372a1bbaf389277222f03e1017b18b348a1f00e
8429351035ba90ba14ef3f7ae38ca35480605a0296aa6c263c6a9b26bb9a48e1
aa4216dc80a7299ae6de08444bea2c588dc873631ebc563c0776d83a1b61e3ce
c2690b6bf35a9364e697735ec630bfd9d2cd59040e3908a66765168e3282b04e
1a942e3925b809896b4b291a8cd2e7bc5f1d533aa523b8353b2df377b0f0adbe
0169613548123dab14afffcb5a3f0e804c70ac903f29ecad55ed43dc75f13881
c073efb31422ff4db99dc24d7442438e942c73cd3c61b529a8ba32542e946b86
""".split())


def check(path, marker):
    text = path.read_text()
    start = text.index(marker)
    body = text[start:text.index("};", start)]
    # Strip comments so documentary hashes cannot satisfy a compiled entry.
    body = re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.S)
    entries = re.findall(r"\{((?:\s*0x[0-9a-fA-F]{2}\s*,?){32})\s*\}", body)
    hashes = {"".join(re.findall(r"0x([0-9a-fA-F]{2})", entry)).lower()
              for entry in entries}
    missing = REVOKED - hashes
    if missing:
        raise ValueError(f"{path}: missing compiled RSA SPKIs: {', '.join(sorted(missing))}")
    print(f"PASS: {path}: all eight revoked RSA keys in compiled blocklist")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-source", type=Path, required=True)
    parser.add_argument("--chromium-source", type=Path, required=True)
    args = parser.parse_args()
    check(args.node_source / "src/crypto/crypto_context.cc", "constexpr SpkiHash kBlockedSPKIs[]")
    check(args.chromium_source / "net/cert/cert_verify_proc_blocklist.inc", "kSPKIBlockList")


if __name__ == "__main__":
    main()
