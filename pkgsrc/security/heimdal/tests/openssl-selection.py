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


def run_provider_state(bmake, pkgdir, makefile, pkgsrc, makeconf, assignments):
    names = (
        "PREFER.openssl", "USE_BUILTIN.openssl", "BUILTIN_VERSION.openssl",
        "HEIMDAL_OPENSSL_ROOT", "BUILDLINK_DIR", "CONFIGURE_ARGS",
        "BUILDLINK_PREFIX.openssl", "_CROSS_DESTDIR",
    )
    values = run_query(bmake, pkgdir, makefile, pkgsrc, makeconf,
                       " ".join(names), assignments)
    if len(values) != len(names):
        raise SystemExit(f"bmake returned {len(values)} provider rows; expected {len(names)}")
    return dict(zip(names, values))


def run_guard(bmake, pkgdir, makefile, pkgsrc, makeconf, assignments,
              expected_success, label):
    env = dict(os.environ, MAKECONF=str(makeconf), PKGSRCDIR=str(pkgsrc))
    command = [bmake, "-C", str(pkgdir), "-f", str(makefile), *assignments,
               "_MAKEVARS_MK=defined", "check-heimdal-openssl-provider"]
    result = subprocess.run(
        command, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    if (result.returncode == 0) != expected_success:
        raise SystemExit(
            f"{label}: expected {'success' if expected_success else 'failure'}, "
            f"got rc={result.returncode}: {result.stdout[-1000:]}{result.stderr[-1000:]}"
        )
    print(f"ok: {label}")


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
    preference_line = (f'PREFER.openssl= {preference}\n' if preference is not None
                       else '.undef PREFER.openssl\n')
    path.write_text(f'.include "{base_text}"\n{preference_line}')


def check_configure_provider(state, provider_root, label):
    expect(label + " configure root", [state["HEIMDAL_OPENSSL_ROOT"]], [provider_root])
    if "--with-openssl=" + provider_root not in state["CONFIGURE_ARGS"]:
        raise SystemExit(
            f"{label}: configure arguments do not use resolved OpenSSL root: "
            f"{state['CONFIGURE_ARGS']!r}"
        )
    print(f"ok: {label} configure argument uses resolved OpenSSL root")


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
        default_conf = tmpdir / "default.mk"
        native_conf = tmpdir / "native.mk"
        pkgsrc_conf = tmpdir / "pkgsrc.mk"
        write_preference_config(default_conf, cross_makeconf, None)
        write_preference_config(native_conf, cross_makeconf, "native")
        write_preference_config(pkgsrc_conf, cross_makeconf, "pkgsrc")
        cross_assignments = ["USE_CROSS_COMPILE=yes"]
        default = run_provider_state(bmake, pkgdir, makefile, pkgsrc,
                                     default_conf, cross_assignments)
        expect(
            "cross default prefers pkgsrc",
            [default["PREFER.openssl"], default["USE_BUILTIN.openssl"],
             default["BUILTIN_VERSION.openssl"]],
            ["pkgsrc", "no", base_version],
        )
        expect("pkgsrc default uses its physical buildlink root",
               [default["HEIMDAL_OPENSSL_ROOT"]], [default["BUILDLINK_DIR"]])
        check_configure_provider(default, default["BUILDLINK_DIR"], "pkgsrc default")

        native = run_provider_state(bmake, pkgdir, makefile, pkgsrc,
                                    native_conf, cross_assignments)
        expect(
            "cross caller selects the common base provider",
            [native["PREFER.openssl"], native["USE_BUILTIN.openssl"],
             native["BUILTIN_VERSION.openssl"]],
            ["native", "yes", base_version],
        )
        expect("base OpenSSL uses the target /usr prefix",
               [native["BUILDLINK_PREFIX.openssl"]], ["/usr"])
        expected_base_root = str(Path(native["_CROSS_DESTDIR"]) /
                                 native["BUILDLINK_PREFIX.openssl"].lstrip("/"))
        check_configure_provider(native, expected_base_root, "base OpenSSL")
        if not (Path(expected_base_root) / "lib/libcrypto.so").is_file():
            raise SystemExit("Selected base OpenSSL lacks target libcrypto.so")
        print("ok: selected base OpenSSL libcrypto.so exists in target sysroot")

        run_guard(bmake, pkgdir, makefile, pkgsrc, native_conf,
                  cross_assignments, True, "actual base-provider guard")
        buildlink_lib = Path(native["BUILDLINK_DIR"]) / "lib/libcrypto.so"
        if buildlink_lib.exists():
            raise SystemExit(f"Expected base provider not to create {buildlink_lib}")
        run_guard(bmake, pkgdir, makefile, pkgsrc, native_conf,
                  [*cross_assignments, "HEIMDAL_OPENSSL_ROOT=" + native["BUILDLINK_DIR"]],
                  False, "old buildlink-only guard fails for base provider")
        run_guard(bmake, pkgdir, makefile, pkgsrc, native_conf,
                  [*cross_assignments, "HEIMDAL_OPENSSL_ROOT="],
                  False, "empty OpenSSL provider root is rejected")

        pkgsrc_state = run_provider_state(bmake, pkgdir, makefile, pkgsrc,
                                          pkgsrc_conf, cross_assignments)
        expect(
            "cross caller explicitly retains pkgsrc OpenSSL",
            [pkgsrc_state["PREFER.openssl"], pkgsrc_state["USE_BUILTIN.openssl"],
             pkgsrc_state["BUILTIN_VERSION.openssl"]],
            ["pkgsrc", "no", base_version],
        )
        check_configure_provider(pkgsrc_state, pkgsrc_state["BUILDLINK_DIR"],
                                 "explicit pkgsrc OpenSSL")
        fixture_root = tmpdir / "pkgsrc-buildlink"
        (fixture_root / "lib").mkdir(parents=True)
        (fixture_root / "lib/libcrypto.so").write_bytes(b"")
        run_guard(bmake, pkgdir, makefile, pkgsrc, pkgsrc_conf,
                  [*cross_assignments, "HEIMDAL_OPENSSL_ROOT=" + str(fixture_root)],
                  True, "pkgsrc buildlink guard accepts selected library")

        synthetic = run_query(
            bmake, pkgdir, makefile, pkgsrc, native_conf, "HEIMDAL_OPENSSL_ROOT",
            [*cross_assignments, "USE_BUILTIN.openssl=yes",
             "_CROSS_DESTDIR=/private/tmp/known/sysroot",
             "BUILDLINK_PREFIX.openssl=/usr",
             "BUILDLINK_DIR=/private/tmp/known/buildlink"],
        )
        expect("provider root preserves 'no' inside a path", synthetic,
               ["/private/tmp/known/sysroot/usr"])
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
