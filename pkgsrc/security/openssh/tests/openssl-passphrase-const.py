#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compile the patched OpenSSH passphrase declaration against provider APIs."""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path


DECLARATION = re.compile(
    r"(?ms)^\s*int blen, len = strlen\(_passphrase\);\n"
    r"(?P<guard>#if OPENSSL_VERSION_NUMBER[^\n]*\n.*?^#endif)\n"
    r"\s*const EVP_CIPHER \*cipher = \(len > 0\) \? EVP_aes_128_cbc\(\) : NULL;"
)


def run(command, *, expected, label, cwd):
    result = subprocess.run(command, cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if expected == "cast-failure":
        if result.returncode == 0 or "cast-qual" not in result.stderr:
            raise RuntimeError(f"{label}: expected cast-qual failure, rc={result.returncode}\n"
                               f"{result.stderr}")
    elif result.returncode != 0:
        raise RuntimeError(f"{label}: rc={result.returncode}\n{result.stderr}")
    print(f"{label}: rc={result.returncode}")


def source_fixture(guard, expected_major):
    return f'''#include <openssl/pem.h>
#include <openssl/opensslv.h>
#include <string.h>
#if OPENSSL_VERSION_MAJOR != {expected_major}
#error unexpected OpenSSL provider major
#endif
typedef unsigned char u_char;
int check(BIO *bio, RSA *rsa, EC_KEY *ec, EVP_PKEY *pkey,
    const char *_passphrase)
{{
    int len = strlen(_passphrase);
{guard}
    const EVP_CIPHER *cipher = (len > 0) ? EVP_aes_128_cbc() : NULL;
    return PEM_write_bio_RSAPrivateKey(bio, rsa, cipher, passphrase, len, NULL, NULL) +
        PEM_write_bio_ECPrivateKey(bio, ec, cipher, passphrase, len, NULL, NULL) +
        PEM_write_bio_PrivateKey(bio, pkey, cipher, passphrase, len, NULL, NULL);
}}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True,
                        help="prepared OpenSSH sshkey.c with the Ports patch applied")
    parser.add_argument("--openssl3-sysroot", type=Path, required=True)
    parser.add_argument("--openssl4-prefix", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    cc, source, sysroot, prefix, work = (p.resolve() for p in (
        args.cc, args.source, args.openssl3_sysroot, args.openssl4_prefix, args.work_dir))
    work.mkdir(parents=True, exist_ok=True)
    guard_match = DECLARATION.search(source.read_text())
    if guard_match is None:
        raise RuntimeError("could not extract the passphrase declaration from sshkey.c")
    guard = guard_match.group("guard")
    if "0x30000000L" not in guard or "LIBRESSL_VERSION_NUMBER" not in guard:
        raise RuntimeError("the extracted guard does not select const OpenSSL 3+ API")

    with tempfile.TemporaryDirectory(dir=work) as tmp:
        temp = Path(tmp)
        fixture = temp / "provider-api.c"
        code3 = source_fixture(guard, 3)
        code4 = source_fixture(guard, 4)
        fixture.write_text(code3)
        common = [str(cc), "-std=c11", "-fsyntax-only", "-Werror", "-Werror=cast-qual",
                  "-Wno-deprecated-declarations"]
        openssl3 = [*common, "--target=x86_64--netbsd", f"--sysroot={sysroot}",
                    str(fixture)]
        run(openssl3, expected="pass", label="OpenSSL 3 target API", cwd=temp)

        old_guard = guard.replace("0x30000000L", "0x40000000L", 1)
        fixture.write_text(source_fixture(old_guard, 3))
        run(openssl3, expected="cast-failure",
            label="OpenSSL 3 pre-fix negative control", cwd=temp)
        fixture.write_text(code4)
        openssl4 = [*common, f"-I{prefix / 'include'}", str(fixture)]
        run(openssl4, expected="pass", label="OpenSSL 4 native API", cwd=temp)

        legacy_fixture = temp / "libressl-branch.c"
        legacy_fixture.write_text(f'''#include <stddef.h>
typedef unsigned char u_char;
static int legacy_api(unsigned char *p) {{ return p != 0; }}
int check(const char *_passphrase) {{
    int len = 1;
{guard}
    _Static_assert(_Generic((passphrase), u_char *: 1, default: 0),
        "LibreSSL compatibility branch must keep a mutable passphrase pointer");
    return legacy_api(passphrase);
}}
''')
        legacy = [str(cc), "-std=c11", "-Werror", "-fsyntax-only",
                  "-DOPENSSL_VERSION_NUMBER=0x40000000L",
                  "-DLIBRESSL_VERSION_NUMBER=0x3050000fL", str(legacy_fixture)]
        run(legacy, expected="pass", label="LibreSSL mutable-API branch selection", cwd=temp)


if __name__ == "__main__":
    main()
