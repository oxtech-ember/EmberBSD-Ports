#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD actual-helper package and target selection regression.
"""Test orchestration boundaries. Fixtures do not compile or run target code."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
HELPER = Path(os.environ.get("RUST_TARGET_HELPER", Path(__file__).with_name("rust-target-package.rb")))

STUB = r'''
import json, os, sys
from pathlib import Path
c = json.loads(Path(os.environ['FIXTURE_CONFIG']).read_text())
args = sys.argv[1:]
role = Path(sys.argv[0]).name
triple = c['arch'] + '-unknown-netbsd'
with open(c['trace'], 'a') as log:
    log.write(json.dumps({'role': role, 'args': args}) + '\n')
if role == 'pkg_info':
    if args[0] == '-e':
        assert args == ['-e', c['package'] + '{,nb[0-9]*}'], args
        print(c['reply'])
    else:
        assert args == ['-qL', c['reply']], args
        print('\n'.join(c['files']))
elif role == 'pkg_admin':
    assert args == ['check', c['reply']], args
elif role.endswith('--netbsd-gcc'):
    if args == ['-dumpmachine']:
        print(c['gcc_target'])
    elif args == ['-dumpfullversion']:
        print(c['gcc_version'])
    else:
        assert '--sysroot=' + c['sysroot'] in args, args
        assert '-B' + c['sysroot'] + '/usr/pkg/gcc16/lib/gcc/' + c['arch'] + '--netbsd/16.2.0/' in args, args
        output = Path(args[args.index('-o') + 1])
        output.write_text('#!/bin/sh\nexit 0\n')
        output.chmod(0o755)
elif role == 'rustc':
    assert not any(arg.startswith('--sysroot') for arg in args), args
    assert not os.environ.get('RUSTC_BOOTSTRAP')
    if '--target' in args:
        assert args[args.index('--target') + 1] == triple, args
    if '--print' in args:
        assert args == ['--target', triple, '--print', 'target-libdir'], args
        print(c['host'] + '/lib/rustlib/' + triple + '/lib')
    else:
        output = Path(args[args.index('-o') + 1])
        output.write_text('#!/bin/sh\nexit 0\n')
        output.chmod(0o755)
elif role == 'cargo':
    assert args == ['build', '--offline', '--release', '--target', triple], args
    linker_key = 'CARGO_TARGET_' + triple.upper().replace('-', '_') + '_LINKER'
    assert os.environ[linker_key] == c['work'] + '/netbsd-cc'
    assert '"' + triple + '"' in Path('build.rs').read_text()
    assert os.environ['CARGO_NET_OFFLINE'] == 'true'
    output = Path(os.environ['CARGO_TARGET_DIR'], triple, 'release/ember_target_std_check')
    output.parent.mkdir(parents=True)
    output.write_text('target Cargo artifact fixture\n')
else:
    raise AssertionError('unexpected tool: ' + role)
'''


class PackageConsumers(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="rust-package-host-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.helper = self.root / "source/profiles/common-build-tools/tests/rust-target-package.rb"
        self.helper.parent.mkdir(parents=True)
        self.helper.write_bytes(HELPER.read_bytes())
        probe = self.root / "source/probes/rust-cross-std"
        probe.mkdir(parents=True)
        for name in ("runtime.rs", "consumer.c", "run-on-target.sh"):
            shutil.copyfile(ROOT / "probes/rust-cross-std" / name, probe / name)

    def run_helper(self, target="aarch64", *, explicit=True, suffix="", reply=None,
                   gcc_target=None, gcc_version="16.2.0", component_change=None):
        arch = {"aarch64": "aarch64", "amd64": "x86_64"}[target]
        case = self.root / str(len(list(self.root.iterdir())))
        case.mkdir()
        host, tools, sysroot, work = (case / name for name in ("host", "tools", "sysroot", "output"))
        for path in (host / "bin", host / "sbin", tools / "bin", sysroot):
            path.mkdir(parents=True)
        component = host / "lib/rustlib" / (arch + "-unknown-netbsd") / "lib"
        component.mkdir(parents=True)
        # Synthetic manifests have different lengths. The helper must use the
        # registered package list, not a count from one release or architecture.
        for index in range(3 if target == "aarch64" else 5):
            (component / f"component-{index}.rmeta").write_text("target data fixture\n")
        owned = [str(p) for p in sorted(component.iterdir())]
        license_path = host / "share/licenses/rust-std/LICENSE-MIT"
        license_path.parent.mkdir(parents=True)
        license_path.write_text("license fixture\n")
        owned.append(str(license_path))
        if component_change == "missing":
            Path(owned[0]).unlink()
        elif component_change == "unowned":
            (component / "extra.rmeta").write_text("unregistered fixture\n")
        elif component_change == "duplicate":
            owned.append(owned[0])
        elif component_change == "empty":
            for path in component.iterdir():
                path.unlink()
            owned = [str(license_path)]
        recipe = ROOT / "profiles/common-build-tools/recipes/lang" / ("rust-std-" + arch + "-netbsd/Makefile")
        package = re.search(r"^PKGNAME=\s*(\S+)", recipe.read_text(), re.MULTILINE).group(1)
        config = dict(arch=arch, package=package, reply=reply if reply is not None else package + suffix,
                      files=owned, host=str(host),
                      sysroot=str(sysroot), work=str(work), trace=str(case / "calls.jsonl"),
                      gcc_target=gcc_target or arch + "--netbsd", gcc_version=gcc_version)
        config_path = case / "config.json"
        config_path.write_text(json.dumps(config))
        for path in (host / "bin/rustc", host / "bin/cargo", host / "bin/cargo-cbuild",
                     host / "bin/cargo-cinstall", host / "sbin/pkg_info", host / "sbin/pkg_admin",
                     tools / "bin" / (arch + "--netbsd-gcc")):
            path.write_text("#!" + sys.executable + "\n" + STUB)
            path.chmod(0o755)
        args = ["--target", target] if explicit else []
        env = dict(os.environ, FIXTURE_CONFIG=str(config_path))
        result = subprocess.run([os.environ.get("RUBY", "ruby"), str(self.helper), *args,
                                 str(host), str(tools), str(sysroot), str(work)],
                                env=env, text=True, capture_output=True)
        trace = Path(config["trace"])
        calls = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
        return result, calls, work, package

    def assert_consumers(self, result, calls, work, arch):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sum(c["role"] == "pkg_admin" for c in calls), 1)
        self.assertEqual(sum(c["role"] == "cargo" for c in calls), 1)
        target_rust = [c for c in calls if c["role"] == "rustc" and "--target" in c["args"] and "-o" in c["args"]]
        self.assertEqual(len(target_rust), 2)
        self.assertTrue(all(c["args"][c["args"].index("--target") + 1] == arch + "-unknown-netbsd" for c in target_rust))
        self.assertEqual(len((work / "providers.sha256").read_text().splitlines()),
                         4 + (3 if arch == "aarch64" else 5))
        for name in ("rust-runtime", "librust-runtime.so", "rust-c-consumer", "rust-cargo-consumer", "native-control"):
            self.assertTrue((work / name).is_file(), name)

    def test_default_current_package(self):
        result, calls, work, _ = self.run_helper(explicit=False)
        self.assert_consumers(result, calls, work, "aarch64")

    def test_selected_targets_and_package_revisions(self):
        for target, arch in (("aarch64", "aarch64"), ("amd64", "x86_64")):
            for suffix in ("", "nb12"):
                with self.subTest(target=target, suffix=suffix):
                    result, calls, work, _ = self.run_helper(target, suffix=suffix)
                    self.assert_consumers(result, calls, work, arch)

    def test_wrong_package_replies_stop_before_consumers(self):
        for target, arch in (("aarch64", "aarch64"), ("amd64", "x86_64")):
            package = "rust-std-" + arch + "-netbsd-1.99.1"
            for reply in (package.replace("1.99.1", "1.99.0"),
                          package.replace(arch, "riscv64"), package + "\n" + package,
                          package + "nbx", "prefix-" + package):
                with self.subTest(target=target, reply=reply):
                    result, calls, _, _ = self.run_helper(target, reply=reply)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("target package is not registered uniquely", result.stderr)
                    self.assertEqual([c["role"] for c in calls], ["pkg_info"])

    def test_wrong_compiler_stops_before_compilation(self):
        for target in ("aarch64", "amd64"):
            for kwargs in ({"gcc_target": "riscv64--netbsd"}, {"gcc_version": "15.2.0"}):
                with self.subTest(target=target, kwargs=kwargs):
                    result, calls, _, _ = self.run_helper(target, **kwargs)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("wrong GCC16 target compiler", result.stderr)
                    self.assertFalse(any("-o" in c["args"] or c["role"] == "cargo" for c in calls))

    def test_component_manifest_mismatch_stops_before_consumers(self):
        for target in ("aarch64", "amd64"):
            for change in ("missing", "unowned", "duplicate", "empty"):
                with self.subTest(target=target, change=change):
                    result, calls, _, _ = self.run_helper(target, component_change=change)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("empty or mismatched target component manifest", result.stderr)
                    self.assertFalse(any("-o" in c["args"] or c["role"] == "cargo" for c in calls))

    def test_invalid_target_has_no_side_effects(self):
        result = subprocess.run([os.environ.get("RUBY", "ruby"), str(self.helper),
                                 "--target", "riscv64", "host", "tools", "sysroot", "output"],
                                cwd=self.root, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage:", result.stderr)
        self.assertFalse((self.root / "output").exists())


if __name__ == "__main__":
    unittest.main()
