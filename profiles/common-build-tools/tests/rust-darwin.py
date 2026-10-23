#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the real Darwin Rust LLVM namespace.
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def mixed_preflight(original_arg, work_arg):
    """Reject a real partial rewrite before the first package mutation."""
    original = Path(original_arg).resolve(strict=True)
    work = Path(work_arg)
    if not work.is_absolute() or work.exists() or work.is_symlink() or work.is_relative_to(original):
        raise SystemExit("Use a new absolute work directory outside the input")
    work.mkdir()
    prefix = work / "runtime"
    prefix.mkdir()
    commands = []
    for name in ["bin", "lib", "libexec"]:
        argv = ["/bin/cp", "-cR", str(original / name), str(prefix / name)]
        process = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        commands.append(dict(argv=argv, exit=process.returncode, stderr=process.stderr))
        if process.returncode:
            raise RuntimeError(process.stderr)
    source = Path(__file__).resolve().parents[3] / "pkgsrc/lang/rust-bin/files/darwin-llvm.py"
    spec = importlib.util.spec_from_file_location("rust_darwin_preflight", source)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    image = prefix / "bin/rustfmt"
    for argv in [["/usr/bin/install_name_tool", "-change", helper.OLD, helper.NEW, str(image)],
                 ["/usr/bin/codesign", "--force", "--sign", "-", "--preserve-metadata=identifier,entitlements,requirements,flags,runtime", str(image)],
                 ["/usr/bin/codesign", "--verify", "--strict", str(image)]]:
        process = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        commands.append(dict(argv=argv, exit=process.returncode, stderr=process.stderr))
        if process.returncode:
            raise RuntimeError(process.stderr)
    graph = helper.inventory(prefix)
    assert len(graph) == 43
    for name in ["lib/libLLVM.dylib", "lib/rustlib/aarch64-apple-darwin/lib/libLLVM.dylib"]:
        assert all(part["identity"] == helper.OLD for part in graph[name].values())
    for name in ["bin/rustc", next(name for name in graph if name.startswith("lib/librustc_driver-"))]:
        assert all(any(lib == helper.OLD for _, lib in part["imports"]) for part in graph[name].values())
    assert all(any(lib == helper.NEW for _, lib in part["imports"]) for part in graph["bin/rustfmt"].values())

    def state():
        result = {}
        for path in sorted(prefix.rglob("*")):
            name = str(path.relative_to(prefix))
            if path.is_symlink():
                result[name] = dict(link=os.readlink(path))
            elif path.is_file():
                result[name] = dict(mode=path.stat().st_mode, sha256=digest(path))
            else:
                result[name] = dict(mode=path.stat().st_mode)
        return result

    before = state()
    receipt = work / "unexpected-receipt.json"
    try:
        helper.isolate(prefix, receipt)
    except ValueError as error:
        refusal = str(error)
        assert "without private LLVM identities or imports" in refusal
    else:
        raise AssertionError("The mixed runtime was accepted")
    assert state() == before and not receipt.exists()
    guard = '''    for name, images in before.items():
        if any(image["identity"] == NEW or any(lib == NEW for _, lib in image["imports"]) for image in images.values()):
            raise ValueError(f"Use a fresh Rust stage without private LLVM identities or imports: {name}")
'''
    text = source.read_text()
    assert text.count(guard) == 1
    without_guard = work / "without-mixed-guard.py"
    without_guard.write_text(text.replace(guard, ""))
    spec = importlib.util.spec_from_file_location("rust_without_mixed_guard", without_guard)
    control = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(control)
    rename = Path.rename
    boundary = []

    class FirstRename(RuntimeError):
        pass

    def stop_at_rename(path, target):
        assert path == prefix / "lib/libLLVM.dylib"
        assert target == prefix / "lib/librustLLVM.dylib"
        boundary.append(dict(source=str(path), target=str(target)))
        raise FirstRename()

    try:
        Path.rename = stop_at_rename
        try:
            control.isolate(prefix, receipt)
        except FirstRename:
            pass
        else:
            raise AssertionError("The guard-removal witness did not reach mutation")
    finally:
        Path.rename = rename
    assert len(boundary) == 1 and state() == before and not receipt.exists()
    (work / "result.json").write_text(json.dumps(dict(helper_sha256=digest(source), commands=commands,
        mixed_image="bin/rustfmt", graph=graph, before=before, after=state(), refusal=refusal,
        guard_removed_first_rename=boundary, scope="Real43-image inventory and a real nonmandatory mixed import. Both OLD providers and mandatory imports remain. All files, names, links and modes are unchanged. Only the guard-removal witness intercepts the first rename."), indent=2) + "\n")
    print("PASS: a real mixed import is refused before edits; removing the guard reaches the first rename")


def main():
    if len(sys.argv) != 5 or sys.platform != "darwin":
        raise SystemExit("Usage on Darwin: rust-darwin.py ORIGINAL_RUST STAGED_RUST PKGSRC NEW_WORK")
    original, staged, tree = (Path(p).resolve(strict=True) for p in sys.argv[1:4])
    work = Path(sys.argv[4])
    if not work.is_absolute() or work.exists() or any(work.is_relative_to(p) for p in [original, staged, tree]):
        raise SystemExit("Use a new absolute work directory outside the inputs")
    work.mkdir()
    (work / "tmp").mkdir()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    env = {k: v for k, v in os.environ.items() if not k.startswith("DYLD_")}
    env.update(TMPDIR=str(work / "tmp"), TMP=str(work / "tmp"), TEMP=str(work / "tmp"), LC_ALL="C")
    records = []

    def run(name, argv, success=True, data=None, extra=None):
        process = subprocess.run(argv, cwd=work, env=dict(env, **(extra or {})), input=data, capture_output=True, timeout=120)
        (work / (name + ".stdout")).write_bytes(process.stdout)
        (work / (name + ".stderr")).write_bytes(process.stderr)
        records.append(dict(name=name, argv=argv, exit=process.returncode))
        (work / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
        if success and process.returncode:
            raise RuntimeError(f"{name}: {process.stderr.decode(errors='replace')}")
        return process

    repo = Path(__file__).resolve().parents[3]
    script = repo / "pkgsrc/lang/rust-bin/files/darwin-llvm.py"
    spec = importlib.util.spec_from_file_location("rust_darwin_llvm", script)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    version = run("version", [str(staged / "bin/rustc"), "-vV"]).stdout.decode()
    assert version.startswith("rustc 1.99.1 ") and "host: aarch64-apple-darwin\n" in version
    before, after = helper.inventory(original), helper.inventory(staged)
    providers = {name for name, arches in before.items() if any(image["identity"] == helper.OLD for image in arches.values())}
    consumers = {name for name, arches in before.items() if any(any(lib == helper.OLD for _, lib in image["imports"]) for image in arches.values())}
    assert len(before) == 43 and len(providers) == 2 and len(consumers) == 24
    translated = {name: str(Path(name).with_name("librustLLVM.dylib")) for name in providers}
    assert set(after) == (set(before) - providers) | set(translated.values())
    for name, arches in before.items():
        actual = after[translated.get(name, name)]
        assert set(actual) == set(arches)
        for arch, image in arches.items():
            result = actual[arch]
            assert result["identity"] == (helper.NEW if name in providers else image["identity"])
            assert result["rpaths"] == image["rpaths"], name
            assert result["imports"] == [[kind, helper.NEW if lib == helper.OLD else lib] for kind, lib in image["imports"]]
    driver = next(name for name in consumers if name.startswith("lib/librustc_driver-"))
    stds = list((original / "lib/rustlib/aarch64-apple-darwin/lib").glob("libstd-*.dylib"))
    assert len(stds) == 1
    std = str(stds[0].relative_to(original))
    relative = sorted(before)
    original_hashes = {name: digest(original / name) for name in relative}
    staged_hashes = {name: digest(staged / translated.get(name, name)) for name in relative}
    for name in relative:
        assert (original_hashes[name] != staged_hashes[name]) == (name in providers or name in consumers), name
    assert len({original_hashes[name] for name in providers}) == 1
    # Keep the earlier actual load-command-space regression.
    overflow = work / "legacy-libstd.dylib"
    shutil.copy2(original / std, overflow)
    result = run("legacy-absolute-overflow", ["/usr/bin/install_name_tool", "-id", str(work / ("prefix-" + "x" * 120) / std), str(overflow)], success=False)
    assert result.returncode and b"larger updated load commands do not fit" in result.stderr
    control = work / "private-control"
    control.mkdir()
    for name in ["bin", "lib", "libexec"]:
        if not (staged / name).exists():
            continue
        result = run("clone-control-" + name, ["/bin/cp", "-cR", str(staged / name), str(control / name)], success=False)
        if result.returncode:
            # Clone support is a copy optimization, not an acceptance gate.
            if (control / name).exists():
                shutil.rmtree(control / name)
            shutil.copytree(staged / name, control / name, symlinks=True)
    poison = {}
    for name in providers:
        path = control / name
        assert not path.exists() and not path.is_symlink()
        path.write_text("foreign common LLVM sentinel\n")
        poison[name] = digest(path)
    native_llvm = next(name for name in providers if name != "lib/libLLVM.dylib")
    llvm_bin = Path(native_llvm).parents[1] / "bin"
    run("foreign-global-ignored-rust", [str(control / "bin/rustc"), "-vV"])
    run("foreign-global-ignored-llvm", [str(control / llvm_bin / "llvm-ar"), "--version"])
    override = work / "loader-override"
    override.mkdir()
    generic = override / "libLLVM.dylib"
    shutil.copy2(original / std, generic)
    generic_hash = digest(generic)
    run("foreign-loader-override-ignored", [str(control / "bin/rustc"), "-vV"], extra=dict(DYLD_LIBRARY_PATH=str(override)))
    assert digest(generic) == generic_hash
    private = override / "librustLLVM.dylib"
    generic.rename(private)
    result = run("private-loader-override-refused", [str(control / "bin/rustc"), "-vV"], success=False, extra=dict(DYLD_LIBRARY_PATH=str(override)))
    assert result.returncode and b"librustLLVM.dylib" in result.stderr and b"Symbol not found:" in result.stderr
    assert digest(private) == generic_hash
    private.rename(generic)
    for index, name in enumerate(sorted(providers)):
        path = control / translated[name]
        saved = path.with_name("saved-provider.dylib")
        path.rename(saved)
        try:
            command = [str(control / "bin/rustc"), "-vV"] if name == "lib/libLLVM.dylib" else [str(control / llvm_bin / "llvm-ar"), "--version"]
            result = run("missing-private-provider-" + str(index), command, success=False)
            assert result.returncode and b"librustLLVM.dylib" in result.stderr
        finally:
            saved.rename(path)
    # Prove every real consumer needs the new import, including LLVM helpers.
    for index, name in enumerate(sorted(consumers)):
        path = control / name
        backup = work / ("consumer-backup-" + str(index))
        shutil.copy2(path, backup)
        try:
            run("generic-import-" + str(index), ["/usr/bin/install_name_tool", "-change", helper.NEW, helper.OLD, str(path)])
            run("sign-negative-" + str(index), ["/usr/bin/codesign", "--force", "--sign", "-", "--preserve-metadata=identifier,entitlements,requirements,flags,runtime", str(path)])
            command = [str(control / "bin/rustc"), "-vV"] if name == driver else [str(path), "--version"]
            result = run("unconverted-consumer-" + str(index), command, success=False)
            assert result.returncode and b"libLLVM.dylib" in result.stderr, name
        finally:
            path.unlink()
            backup.rename(path)
    run("restored-control-rust", [str(control / "bin/rustc"), "-vV"])
    run("restored-control-llvm", [str(control / llvm_bin / "llvm-ar"), "--version"])
    assert all(digest(control / name) == expected for name, expected in poison.items())
    refusal = work / "refuse-symlink"
    (refusal / "lib").mkdir(parents=True)
    (refusal / "lib/libLLVM.dylib").symlink_to(original / "lib/libLLVM.dylib")
    result = run("refuse-shared-alias", [sys.executable, "-B", str(script), str(refusal), str(work / "refused.json")], success=False)
    assert result.returncode and b"regular LLVM provider" in result.stderr
    assert not (work / "refused.json").exists()
    for index, name in enumerate(sorted(providers | consumers)):
        run("signature-" + str(index), ["/usr/bin/codesign", "--verify", "--strict", str(staged / translated.get(name, name))])
    source = repo / "probes/rust-cross-std/runtime.rs"
    shutil.copy2(source, work / "runtime.rs")
    binary = work / "native-consumer"
    run("compile", [str(staged / "bin/rustc"), "--sysroot", str(staged), "--edition=2024", str(work / "runtime.rs"), "-o", str(binary)])
    run("runtime", [str(binary)])
    for name in ["cargo", "cargo-clippy", "clippy-driver", "rustdoc", "rustfmt", "rust-analyzer"]:
        run("version-" + name, [str(staged / "bin" / name), "--version"])
    ir = work / "input.ll"
    ir.write_text("define i32 @answer() { ret i32 42 }\n")
    bitcode = work / "output.bc"
    run("llvm-as", [str(staged / llvm_bin / "llvm-as"), str(ir), "-o", str(bitcode)])
    run("llvm-opt-verify", [str(staged / llvm_bin / "opt"), "-passes=verify", "-disable-output", str(bitcode)])
    run("llvm-dis", [str(staged / llvm_bin / "llvm-dis"), str(bitcode), "-o", str(work / "output.ll")])
    assert "define i32 @answer()" in (work / "output.ll").read_text()
    run("rust-lld", [str(staged / llvm_bin / "rust-lld"), "-flavor", "gnu", "--version"])
    # Use the real package resolver. No fake package is registered.
    checker = tree / "mk/check/check-shlibs-macho.awk"
    prefix = "/" + staged.name
    result = run("package-load-commands", ["awk", "-f", str(checker)], data=("\n".join(after) + "\n").encode(), extra=dict(DESTDIR=str(staged.parent), PREFIX=prefix, WRKDIR=str(work / "separate-package-work"), SKIP_SYSTEM_LIBS="1", MACHO_USE_LOAD_COMMANDS="yes", PKG_INFO_CMD="/usr/bin/false", DEPENDS_FILE=str(work / "depends"), REQUIRES_FILE=str(work / "requires")))
    assert not result.stdout, result.stdout
    requires = (work / "requires").read_text()
    for old, new in translated.items():
        assert prefix + "/" + new in requires
        assert prefix + "/" + old + "\n" not in requires
    for name in relative:
        assert digest(original / name) == original_hashes[name]
        assert digest(staged / translated.get(name, name)) == staged_hashes[name]
    (work / "result.json").write_text(json.dumps(dict(original_sha256=original_hashes, staged_sha256=staged_hashes, actual_consumers=sorted(consumers), providers=sorted(providers), original_runtime_macho_images=len(before), staged_runtime_macho_images=len(after), common_llvm_sentinels_unchanged=True, runtime_source_sha256=digest(source), scope="Darwin AArch64 bin/lib/libexec runtime graph, all consumer loader failures, signatures, native allocation/thread/TLS/unwind, Rust/LLVM tools and actual package resolver. No document magic scan, package registration, target execution or leak acceptance."), indent=2) + "\n")
    print("PASS: both private LLVM identities, all24 consumers, causal loader refusals, native Rust/LLVM, actual package resolver and unchanged inputs")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--mixed-preflight" and sys.platform == "darwin":
        mixed_preflight(sys.argv[2], sys.argv[3])
    else:
        main()
