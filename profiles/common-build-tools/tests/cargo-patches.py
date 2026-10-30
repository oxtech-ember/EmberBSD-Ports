#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise exact patching, Cargo checksums, repetition and rejection paths."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--prefix', type=Path, required=True)
p.add_argument('--patch', type=Path, required=True)
a = p.parse_args()
source = Path(__file__).resolve().parents[1] / 'cargo-patches.py'
spec = importlib.util.spec_from_file_location('cargo_patches', source)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
h = lambda data: hashlib.sha256(data.encode()).hexdigest()
with tempfile.TemporaryDirectory(prefix='cargo-patch-test-') as tmp:
    base = Path(tmp); vendor = base/'vendor'; vendor.mkdir(); registry = base/'registry'; registry.mkdir()
    root = vendor/'example-1.2.3'; root.mkdir()
    original = '[package]\nname = "example"\nversion = "1.2.3"\n'
    (root/'Cargo.toml').write_text(original); (root/'src').mkdir()
    (root/'src/lib.rs').write_text('old\n')
    (root/'.cargo-checksum.json').write_text(json.dumps({'package': 'archive-sha', 'files': {'src/lib.rs': h('old\n')}}))
    (registry/'example.patch').write_text('--- a/src/lib.rs\n+++ b/src/lib.rs\n@@ -1 +1 @@\n-old\n+new\n')
    manifest = {'example-1.2.3': {'patch': 'example.patch', 'files': {'src/lib.rs': {'before': h('old\n'), 'after': h('new\n')}}}}
    (registry/'registry.json').write_text(json.dumps(manifest))
    def run(): module.apply(vendor, registry, a.patch, a.prefix)
    run(); run()
    assert (root/'src/lib.rs').read_text() == 'new\n'
    check = json.loads((root/'.cargo-checksum.json').read_text())
    assert check == {'package': 'archive-sha', 'files': {'src/lib.rs': h('new\n')}}
    (root/'src/lib.rs').write_text('tampered\n')
    try: run(); raise AssertionError('modified input accepted')
    except ValueError: pass
    (root/'src/lib.rs').unlink(); (root/'src/lib.rs').symlink_to('/etc/passwd')
    try: run(); raise AssertionError('unsafe symlink accepted')
    except ValueError: pass
    (root/'src/lib.rs').unlink(); (root/'src/lib.rs').write_text('new\n')
    check['files']['src/lib.rs'] = 'bad'; (root/'.cargo-checksum.json').write_text(json.dumps(check))
    try: run(); raise AssertionError('wrong checksum accepted')
    except ValueError: pass
    try: module.apply(vendor, registry, Path('/usr/bin/patch'), a.prefix); raise AssertionError('outside tool accepted')
    except ValueError: pass
    check['files']['src/lib.rs'] = h('new\n'); (root/'.cargo-checksum.json').write_text(json.dumps(check))
    (registry/'example.patch').write_text('--- a/../../escape\n+++ b/../../escape\n@@ -1 +1 @@\n-x\n+y\n')
    try: run(); raise AssertionError('unsafe patch header accepted')
    except ValueError: pass
with tempfile.TemporaryDirectory(prefix='cargo-create-delete-test-') as tmp:
    base=Path(tmp); vendor=base/'vendor'; vendor.mkdir(); registry=base/'registry'; registry.mkdir()
    root=vendor/'example-1.2.3'; root.mkdir(); (root/'src').mkdir()
    (root/'Cargo.toml').write_text('[package]\nname = "example"\nversion = "1.2.3"\n')
    (root/'src/old.rs').write_text('old\n')
    (root/'.cargo-checksum.json').write_text(json.dumps({'package':'archive-sha','files':{'src/old.rs':h('old\n')}}))
    (registry/'example.patch').write_text('--- a/src/old.rs\n+++ /dev/null\n@@ -1 +0,0 @@\n-old\n--- /dev/null\n+++ b/src/new.rs\n@@ -0,0 +1 @@\n+new\n')
    manifest={'example-1.2.3':{'patch':'example.patch','files':{'src/old.rs':{'before':h('old\n'),'after':None},'src/new.rs':{'before':None,'after':h('new\n')}}}}
    (registry/'registry.json').write_text(json.dumps(manifest))
    def run(): module.apply(vendor,registry,a.patch,a.prefix)
    run(); run()
    assert not (root/'src/old.rs').exists() and (root/'src/new.rs').read_text()=='new\n'
    assert json.loads((root/'.cargo-checksum.json').read_text())['files']=={'src/new.rs':h('new\n')}
    (root/'src/old.rs').write_text('old\n')
    try: run(); raise AssertionError('partial state accepted')
    except ValueError: pass
    (root/'src/old.rs').unlink(); (root/'src/new.rs').unlink(); (root/'src/old.rs').symlink_to('/etc/passwd')
    try: run(); raise AssertionError('symlink accepted')
    except ValueError: pass
    (root/'src/old.rs').unlink(); (root/'src/old.rs').write_text('old\n'); (root/'src/new.rs').symlink_to('/etc/passwd')
    try: run(); raise AssertionError('created file symlink accepted')
    except ValueError: pass
    manifest['example-1.2.3']['files']['src/new.rs']['before']=h('fake\n')
    (registry/'registry.json').write_text(json.dumps(manifest))
    (root/'src/new.rs').unlink()
    try: run(); raise AssertionError('mismatched operation accepted')
    except ValueError: pass
with tempfile.TemporaryDirectory(prefix="cargo-semver-test-") as tmp:
    base = Path(tmp); vendor = base / "vendor"; vendor.mkdir(); registry = base / "registry"; registry.mkdir()
    for version in ("0.4.0-alpha.12", "5.3.1+1.23.1", "1.2.3-alpha--nightly.1+build--tag"):
        name = "example-" + version; root = vendor / name; root.mkdir()
        (root / "Cargo.toml").write_text('[package]\nname = "example"\nversion = "' + version + '"\n')
        (root / "value").write_text("old\n")
        (root / ".cargo-checksum.json").write_text(json.dumps({"package": "archive", "files": {"value": h("old\n")}}))
        (registry / "example.patch").write_text("--- a/value\n+++ b/value\n@@ -1 +1 @@\n-old\n+new\n")
        spec = {name: {"patch": "example.patch", "files": {"value": {"before": h("old\n"), "after": h("new\n")}}}}
        (registry / "registry.json").write_text(json.dumps(spec))
        module.apply(vendor, registry, a.patch, a.prefix)
        assert (root / "value").read_text() == "new\n"
    for unsafe in ("../escape-1.2.3", "example-1.2.3+../escape", "example-1.2.3-alpha/escape"):
        (registry / "registry.json").write_text(json.dumps({unsafe: {}}))
        try: module.apply(vendor, registry, a.patch, a.prefix); raise AssertionError("unsafe crate identifier accepted")
        except ValueError as error: assert "invalid exact crate identifier" in str(error)
print('Cargo patch create/delete, checksums, idempotence and rejection: PASS')
print('Cargo patch exact inputs, checksums, idempotence and rejection: PASS')
