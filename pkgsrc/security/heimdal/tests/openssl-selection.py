#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise Heimdal OpenSSL provider selection through the real pkgsrc recipe."""
import os
from pathlib import Path
import subprocess
import tempfile


def required(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"set {name} to run this check")
    return value


def run_query(bmake, pkgdir, makefile, pkgsrc, makeconf, variables, assignments):
    env = dict(os.environ, MAKECONF=str(makeconf), PKGSRCDIR=str(pkgsrc))
    command = [
        bmake, "-C", str(pkgdir), "-f", str(makefile), *assignments,
        "_MAKEVARS_MK=defined", "show-vars", f"VARNAMES={variables}",
    ]
    result = subprocess.run(
        command, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    if result.returncode:
        raise SystemExit(
            f"bmake provider query failed ({result.returncode}):\n{result.stderr[-2000:]}"
        )
    return result.stdout.splitlines()


def expect(label, actual, expected):
    if actual != expected:
        raise SystemExit(
            f"{label}: expected {expected!r}, got {actual!r}"
        )
    print(f"ok: {label}")


def write_preference_config(path, base, preference):
    base_text = str(base)
    if '"' in base_text or "\n" in base_text:
        raise SystemExit("unsupported quoted or multiline MAKECONF path")
    path.write_text(f'.include "{base_text}"\nPREFER.openssl= {preference}\n')


def main():
    bmake = str(Path(required("BMAKE")).resolve())
    pkgsrc = Path(required("PKGSRCDIR")).resolve()
    ports = Path(required("PORTS_SOURCE")).resolve()
    cross_makeconf = Path(required("CROSS_MAKECONF")).resolve()
    base_version = required("OPENSSL_BASE_VERSION")
    pkgdir = pkgsrc / "security/heimdal"
    makefile = Path(os.environ.get(
        "HEIMDAL_MAKEFILE", str(ports / "pkgsrc/security/heimdal/Makefile")
    )).resolve()
    with tempfile.TemporaryDirectory(prefix="heimdal-openssl-selection-") as tmp:
        tmpdir = Path(tmp)
        native_conf = tmpdir / "native.mk"
        pkgsrc_conf = tmpdir / "pkgsrc.mk"
        write_preference_config(native_conf, cross_makeconf, "native")
        write_preference_config(pkgsrc_conf, cross_makeconf, "pkgsrc")
        four = "PREFER.openssl USE_BUILTIN.openssl BUILTIN_VERSION.openssl"
        expect(
            "cross default prefers pkgsrc",
            run_query(bmake, pkgdir, makefile, pkgsrc, cross_makeconf, four,
                      ["USE_CROSS_COMPILE=yes"]),
            ["pkgsrc", "no", base_version],
        )
        expect(
            "cross caller selects the common base provider",
            run_query(bmake, pkgdir, makefile, pkgsrc, native_conf, four,
                      ["USE_CROSS_COMPILE=yes"]),
            ["native", "yes", base_version],
        )
        prefix = run_query(
            bmake, pkgdir, makefile, pkgsrc, native_conf,
            "BUILDLINK_PREFIX.openssl", ["USE_CROSS_COMPILE=yes"],
        )
        expect("base OpenSSL uses the target /usr prefix", prefix, ["/usr"])
        expect(
            "cross caller explicitly retains pkgsrc OpenSSL",
            run_query(bmake, pkgdir, makefile, pkgsrc, pkgsrc_conf, four,
                      ["USE_CROSS_COMPILE=yes"]),
            ["pkgsrc", "no", base_version],
        )
        for preference, conf in (("native", native_conf), ("pkgsrc", pkgsrc_conf)):
            actual = run_query(
                bmake, pkgdir, makefile, pkgsrc, conf, "PREFER.openssl",
                ["USE_CROSS_COMPILE=no"],
            )
            expect(
                f"native mode preserves caller preference {preference}",
                actual, [preference],
            )


if __name__ == "__main__":
    main()
