#!/usr/bin/env python3
"""Cross-check current COSMIC with the shared stable Rust and GCC providers."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
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


def apply_patch(root, patch_path, output):
    result = subprocess.run(
        ["patch", "-p1", "--batch", "--forward", "-i", str(patch_path)],
        cwd=root, stdout=output, stderr=subprocess.STDOUT)
    assert result.returncode == 0, f"Patch failed: {patch_path}"


def prepare_cargo_home(base, work, component):
    """Overlay the supplied Cargo home and apply target patches to private sources."""
    overlay = work / "cargo-home"
    overlay.mkdir()
    for name in (".global-cache",):
        source = base / name
        if source.exists():
            (overlay / name).write_bytes(source.read_bytes())
    for name in (".package-cache", ".package-cache-mutate"):
        (overlay / name).touch()

    (overlay / "registry").mkdir()
    for name in ("cache", "index"):
        source = base / "registry" / name
        assert source.exists(), f"Missing Cargo registry cache: {source}"
        os.symlink(source, overlay / "registry" / name, target_is_directory=True)

    patches = Path(__file__).with_name("patches")
    registry_patches = {
        "libc-0.2.191": [patches / "libc-netbsd-current-abi.patch"],
        "kqueue-sys-1.0.4": [patches / "kqueue-sys-netbsd-current-abi.patch"],
        "rustix-1.1.5": [patches / "rustix-eventfd-netbsd.patch",
                         patches / "rustix-netbsd-current-abi.patch",
                         patches / "rustix-statvfs-favail.patch"],
        "drm-0.14.1": patches / "drm-rustix-1.1.5-lifetime.patch",
        "libdisplay-info-sys-0.3.0": patches / "libdisplay-info-sys-0.3-system-0.4.patch",
        "gettext-sys-0.27.0": patches / "gettext-sys-netbsd-setlocale.patch",
    }
    required = {"gettext-sys-0.27.0", "libc-0.2.191"}
    if component == "cosmic-comp":
        required |= {"rustix-1.1.5", "drm-0.14.1", "libdisplay-info-sys-0.3.0",
                     "kqueue-sys-1.0.4"}
    else:
        required.add("rustix-1.1.5")
    found = set()
    log_path = work / "patches.log"
    source_roots = base / "registry" / "src"
    target_roots = overlay / "registry" / "src"
    target_roots.mkdir()
    with log_path.open("wb") as patch_log:
        for source_root in sorted(source_roots.iterdir()):
            target_root = target_roots / source_root.name
            target_root.mkdir()
            for package in sorted(source_root.iterdir()):
                target_package = target_root / package.name
                patch_paths = registry_patches.get(package.name)
                if patch_paths is None:
                    os.symlink(package, target_package, target_is_directory=True)
                    continue
                shutil.copytree(package, target_package)
                if not isinstance(patch_paths, list):
                    patch_paths = [patch_paths]
                for patch_path in patch_paths:
                    apply_patch(target_package, patch_path, patch_log)
                if package.name.startswith("rustix-"):
                    c_source = (target_package / "src/backend/libc/c.rs").read_text()
                    fs_source = (target_package / "src/backend/libc/fs/syscalls.rs").read_text()
                    assert 'link_name = "__kevent100"' in c_source
                    assert 'link_name = "__dup3100"' in c_source
                    assert 'link_name = "__fstatvfs90"' in c_source
                    assert "f_favail: from.f_favail as u64" in fs_source
                    assert "f_favail_uses_available_inode_count" in fs_source
                    if package.name in {"rustix-1.1.4", "rustix-1.1.5"}:
                        assert 'target_os = "netbsd"' in (target_package / "src/event/mod.rs").read_text()
                elif package.name == "libdisplay-info-sys-0.3.0":
                    assert '< 0.5.0' in (target_package / "Cargo.toml").read_text()
                elif package.name == "gettext-sys-0.27.0":
                    assert 'link_name = "__setlocale50"' in (target_package / "lib.rs").read_text()
                elif package.name == "libc-0.2.191":
                    netbsd = target_package / "src/unix/bsd/netbsdlike/netbsd/mod.rs"
                    netbsd_source = netbsd.read_text()
                    statvfs = target_package / "src/new/netbsd/sys/statvfs.rs"
                    statvfs_source = statvfs.read_text()
                    assert 'link_name = "__kevent100"' in netbsd_source
                    assert 'link_name = "__dup3100"' in netbsd_source
                    assert "pub ext: [u64; 4]" in netbsd_source
                    assert "Padding<[u64; 4]>" in statvfs_source
                    assert "pub f_mntfromlabel" in statvfs_source
                elif package.name == "kqueue-sys-1.0.4":
                    kqueue_source = (target_package / "src/lib.rs").read_text()
                    assert 'link_name = "__kevent100"' in kqueue_source
                    assert "pub ext: [u64; 4]" in kqueue_source
                elif package.name == "drm-0.14.1":
                    drm_manifest = (target_package / "Cargo.toml").read_text()
                    property_source = (target_package / "src/control/property.rs").read_text()
                    assert 'version = "1.1.5"' in drm_manifest
                    assert "Value<'_>" in property_source
                found.add(package.name)

        assert required <= found, f"Missing locked Cargo sources for patches: {required - found}"

        git = overlay / "git"
        git.mkdir()
        source_db = base / "git" / "db"
        assert source_db.exists(), f"Missing Cargo git cache: {source_db}"
        os.symlink(source_db, git / "db", target_is_directory=True)
        source_checkouts = base / "git" / "checkouts"
        target_checkouts = git / "checkouts"
        target_checkouts.mkdir()
        git_patches = {
            "libcosmic-41009aea1d72760b": {
                "d922ac3": patches / "libcosmic-softbuffer-rustix-1.1.5.patch"},
            "rust-atomicwrites-65d10ea72c60eb36": {
                "043ab48": patches / "atomicwrites-rustix-1.1.5.patch"},
            "smithay-312425d48e59d8c8": {
                "8a27023": patches / "smithay-rand-0.10.patch"},
        }
        required_git = {(repository, checkout) for repository, checkouts in git_patches.items()
                        for checkout in checkouts} if component == "cosmic-comp" else set()
        found_git = set()
        for repository in sorted(source_checkouts.iterdir()):
            target_repository = target_checkouts / repository.name
            checkout_patches = git_patches.get(repository.name) if component == "cosmic-comp" else None
            if checkout_patches is None:
                os.symlink(repository, target_repository, target_is_directory=True)
                continue
            target_repository.mkdir()
            for checkout in sorted(repository.iterdir()):
                target_checkout = target_repository / checkout.name
                patch_path = checkout_patches.get(checkout.name)
                if patch_path is None:
                    os.symlink(checkout, target_checkout, target_is_directory=True)
                    continue
                shutil.copytree(checkout, target_checkout, symlinks=True)
                apply_patch(target_checkout, patch_path, patch_log)
                found_git.add((repository.name, checkout.name))
                if repository.name.startswith("smithay-"):
                    assert "use rand::{RngExt, distr::Alphanumeric};" in (
                        target_checkout / "src/utils/sealed_file.rs").read_text()
                elif repository.name.startswith("rust-atomicwrites-"):
                    assert 'version = "1.1.5"' in (target_checkout / "Cargo.toml").read_text()
                elif repository.name.startswith("libcosmic-"):
                    iced = target_checkout / "iced/Cargo.toml"
                    assert 'softbuffer = "0.4.8"' in iced.read_text()
                    for rel in ("iced/wgpu/Cargo.toml", "iced/winit/Cargo.toml"):
                        assert 'version = "0.38"' not in (target_checkout / rel).read_text()
        assert required_git <= found_git, (
            f"Missing locked Cargo Git sources for patches: {required_git - found_git}")
    return overlay, log_path


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
upstream_lock_hash = hashlib.sha256(lock.read_bytes()).hexdigest()
source_patch_log = args.work / "source-patches.log"
if args.component == "cosmic-comp":
    with source_patch_log.open("wb") as output:
        apply_patch(source, Path(__file__).with_name("patches") /
                    "cosmic-comp-current-lock.patch", output)
else:
    source_patch_log = None
lock_hash = hashlib.sha256(lock.read_bytes()).hexdigest()
effective_cargo_home, patch_log = prepare_cargo_home(args.cargo_home, args.work, args.component)
drm_patch_source = None
if args.component == "cosmic-comp":
    with patch_log.open("ab") as output:
        apply_patch(source, Path(__file__).with_name("patches") /
                    "cosmic-comp-atomic-try-update.patch", output)
    for name in ("src/shell/element/stack.rs", "src/utils/ids.rs"):
        assert "fetch_update" not in (source / name).read_text()

    drm_candidates = list((effective_cargo_home / "registry/src").glob("*/drm-0.14.1"))
    assert len(drm_candidates) == 1, "Missing patched DRM 0.14.1 source"
    drm_patch_source = drm_candidates[0]
    manifest = source / "Cargo.toml"
    manifest_text = manifest.read_text()
    patch_table = manifest_text.rfind("[patch.crates-io]")
    assert patch_table >= 0 and manifest_text.rfind("\n[", patch_table + 1) < 0
    assert "drm-ports-current" not in manifest_text
    manifest_text = manifest_text.rstrip() + (
        '\ndrm-ports-current = { package = "drm", path = "' +
        str(drm_patch_source) + '" }\n')
    manifest.write_text(manifest_text)
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
    "CARGO_HOME": str(effective_cargo_home), "CARGO_TARGET_DIR": str(args.work / "target"),
    "CARGO_TARGET_AARCH64_UNKNOWN_NETBSD_LINKER": str(args.work / "netbsd-cc"),
    "CC_aarch64_unknown_netbsd": str(args.work / "netbsd-cc"),
    "CXX_aarch64_unknown_netbsd": str(args.work / "netbsd-cxx"),
    "AR_aarch64_unknown_netbsd": str(args.cross_tools / "bin/aarch64--netbsd-ar"),
    # gettext-sys does not recognize NetBSD as a system-gettext target and
    # otherwise tries to cross-build GNU gettext, including host utilities.
    "GETTEXT_DIR": str(args.sysroot / "usr/pkg"),
    "GETTEXT_INCLUDE_DIR": str(args.sysroot / "usr/pkg/include/gettext"),
    "PKG_CONFIG": str(args.host_prefix / "bin/pkg-config"), "PKG_CONFIG_ALLOW_CROSS": "1",
    "PKG_CONFIG_SYSROOT_DIR": str(args.sysroot),
    "PKG_CONFIG_LIBDIR": os.pathsep.join(str(args.sysroot / path) for path in
        ("usr/pkg/lib/pkgconfig", "usr/pkg/share/pkgconfig", "usr/lib/pkgconfig")),
    "LC_ALL": "C", "TMPDIR": str(args.work / "tmp"),
})
(args.work / "tmp").mkdir()
abi_command = None
abi_status = None
abi_symbols = None
if args.mode != "fetch":
    abi_source = Path(__file__).with_name("tests") / "netbsd-abi.c"
    abi_object = args.work / "netbsd-abi.o"
    abi_command = [str(gcc), "--sysroot=" + str(args.sysroot), "-D_NETBSD_SOURCE", "-std=c11",
                   "-Wall", "-Wextra", "-Werror", "-fanalyzer", "-c", str(abi_source),
                   "-o", str(abi_object)]
    abi_log = args.work / "netbsd-abi.log"
    with abi_log.open("wb") as output:
        abi_result = subprocess.run(abi_command, env=environment, stdout=output,
                                    stderr=subprocess.STDOUT)
    abi_status = abi_result.returncode
    assert abi_status == 0, f"NetBSD ABI header contract failed; see {abi_log}"
    nm = args.cross_tools / "bin/aarch64--netbsd-nm"
    abi_symbols = subprocess.check_output([nm, "-u", abi_object], text=True)
    symbols = {line.split()[-1] for line in abi_symbols.splitlines() if line.split()}
    expected_symbols = {"__kevent100", "__dup3100", "__statvfs90", "__fstatvfs90"}
    assert expected_symbols <= symbols, f"Target headers selected unexpected symbols: {symbols}"
    compatibility_symbols = {"__kevent50", "dup3", "statvfs", "fstatvfs"}
    assert compatibility_symbols.isdisjoint(symbols), (
        f"Target headers selected compatibility symbols: {symbols & compatibility_symbols}")
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
assert hashlib.sha256(lock.read_bytes()).hexdigest() == lock_hash, "The patched Cargo.lock changed"
receipt = {"component": args.component, "source_sha256": expected,
           "upstream_lock_sha256": upstream_lock_hash, "lock_sha256": lock_hash,
           "compiler": version, "command": command, "status": result.returncode,
           "abi_command": abi_command, "abi_status": abi_status,
           "abi_symbols": abi_symbols,
           "target_linker": str(args.work / "netbsd-cc"), "cargo_home": str(effective_cargo_home),
           "patch_log": str(patch_log) if patch_log else None,
           "drm_patch_source": str(drm_patch_source) if drm_patch_source else None,
           "source_patch_log": str(source_patch_log) if source_patch_log else None,
           "jobs": args.jobs}
(args.work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
raise SystemExit(result.returncode)
