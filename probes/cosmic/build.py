#!/usr/bin/env python3
"""Cross-check current COSMIC with the shared stable Rust and GCC providers."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tarfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--component", choices=["cosmic-session", "cosmic-comp"], required=True)
parser.add_argument("--archive", type=Path, required=True)
parser.add_argument("--host-prefix", type=Path, required=True)
parser.add_argument("--cross-tools", type=Path, required=True)
parser.add_argument("--sysroot", type=Path, required=True)
parser.add_argument("--cargo-home", type=Path, required=True)
parser.add_argument("--work", type=Path, required=True)
parser.add_argument("--mode", choices=["fetch", "check", "build"], default="check")
parser.add_argument("--jobs", type=int, default=1)
args = parser.parse_args()
assert args.jobs > 0 and not args.work.exists(), "Use positive jobs and a new work directory"
manifest = Path(__file__).with_name("sources.tsv")
expected = next(line.split("\t")[1] for line in manifest.read_text().splitlines()
                if line.startswith(args.component + "\t"))
assert hashlib.sha256(args.archive.read_bytes()).hexdigest() == expected
for path in (args.host_prefix, args.cross_tools, args.sysroot, args.cargo_home, args.work):
    assert path.is_absolute() and "\n" not in str(path)
rustc = args.host_prefix / "bin/rustc"
cargo = args.host_prefix / "bin/cargo"
gcc = args.cross_tools / "bin/aarch64--netbsd-gcc"
assert subprocess.check_output([gcc, "-dumpfullversion"], text=True).strip() == "16.2.0"
assert subprocess.check_output([gcc, "-dumpmachine"], text=True).strip() == "aarch64--netbsd"
version = subprocess.check_output([rustc, "-vV"], text=True)
assert "rustc 1.99.1 (58cf8f9c3 2026-10-13)\n" in version
assert "commit-hash: 58cf8f9c35b355199727627d07ae34a4e2846d67\n" in version
args.work.mkdir(parents=True)
source_root = args.work / "source"
with tarfile.open(args.archive) as archive:
    archive.extractall(source_root, filter="data")
trees = list(source_root.iterdir())
assert len(trees) == 1 and trees[0].is_dir()
source = trees[0]
lock = source / "Cargo.lock"
lock_hash = hashlib.sha256(lock.read_bytes()).hexdigest()
crt = args.sysroot / "usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0"
for name, compiler in [("cc", gcc), ("cxx", args.cross_tools / "bin/aarch64--netbsd-g++")]:
    wrapper = args.work / ("netbsd-" + name)
    command = [str(compiler), "--sysroot=" + str(args.sysroot), "-B" + str(crt) + "/",
               "-L" + str(args.sysroot / "usr/pkg/gcc16/lib"), "-Wl,-rpath,/usr/pkg/gcc16/lib"]
    wrapper.write_text("#!/bin/sh\nexec " + shlex.join(command) + ' "$@"\n')
    wrapper.chmod(0o755)
environment = dict(os.environ)
for name in ("RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTC_BOOTSTRAP", "RUSTC_WRAPPER",
             "RUSTC_WORKSPACE_WRAPPER", "DYLD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES"):
    environment.pop(name, None)
environment.update({
    "PATH": str(args.host_prefix / "bin") + os.pathsep + environment["PATH"],
    "RUSTC": str(rustc), "RUSTDOC": str(args.host_prefix / "bin/rustdoc"),
    "CARGO_HOME": str(args.cargo_home), "CARGO_TARGET_DIR": str(args.work / "target"),
    "CARGO_TARGET_AARCH64_UNKNOWN_NETBSD_LINKER": str(args.work / "netbsd-cc"),
    "CC_aarch64_unknown_netbsd": str(args.work / "netbsd-cc"),
    "CXX_aarch64_unknown_netbsd": str(args.work / "netbsd-cxx"),
    "AR_aarch64_unknown_netbsd": str(args.cross_tools / "bin/aarch64--netbsd-ar"),
    "PKG_CONFIG": str(args.host_prefix / "bin/pkg-config"), "PKG_CONFIG_ALLOW_CROSS": "1",
    "PKG_CONFIG_SYSROOT_DIR": str(args.sysroot),
    "PKG_CONFIG_LIBDIR": os.pathsep.join(str(args.sysroot / path) for path in
        ("usr/pkg/lib/pkgconfig", "usr/pkg/share/pkgconfig", "usr/lib/pkgconfig")),
    "LC_ALL": "C", "TMPDIR": str(args.work / "tmp"),
})
(args.work / "tmp").mkdir()
command = [str(cargo), args.mode, "--locked", "--target", "aarch64-unknown-netbsd"]
if args.mode == "fetch":
    # Procedural macros and build scripts also need the native host closure.
    command += ["--target", "aarch64-apple-darwin"]
else:
    command += ["--offline", "--jobs", str(args.jobs), "--no-default-features"]
    if args.component == "cosmic-session":
        command += ["--features", "autostart"]
with (args.work / "cargo.log").open("wb") as output:
    result = subprocess.run(command, cwd=source, env=environment, stdout=output, stderr=subprocess.STDOUT)
assert hashlib.sha256(lock.read_bytes()).hexdigest() == lock_hash, "The upstream lock changed"
receipt = {"component": args.component, "source_sha256": expected, "lock_sha256": lock_hash,
           "compiler": version, "command": command, "status": result.returncode,
           "target_linker": str(args.work / "netbsd-cc"), "jobs": args.jobs}
(args.work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
raise SystemExit(result.returncode)
