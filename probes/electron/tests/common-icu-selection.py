#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify selected host and target ICU source provenance."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_electron', owner / 'electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp); ports = root/'ports'; export = root/'export'; sysroot = root/'sysroot'; stage = root/'stage'; work = root/'work'
    for recipe in (ports/'pkgsrc/textproc/icu', export/'textproc/icu'):
        (recipe/'patches').mkdir(parents=True); (recipe/'patches/patch-test').write_text('patch')
        (recipe/'distinfo').write_text('distinfo')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    recipe = ports/'pkgsrc/textproc/icu'
    record = 'textproc/icu/distinfo: '+sha(recipe/'distinfo')+'\ntextproc/icu/patches/patch-test: '+sha(recipe/'patches/patch-test')+'\n'
    packages = (stage/'pkgdb/icu-host', sysroot/'usr/pkg/pkgdb/icu-target', sysroot/'usr/pkg/pkgdb/icu-devel-target')
    for pkg in packages:
        pkg.mkdir(parents=True); (pkg/'+BUILD_INFO').write_text(('PKGPATH=textproc/icu-devel\n' if pkg.name == 'icu-devel-target' else 'PKGPATH=textproc/icu\n')); (pkg/'+BUILD_VERSION').write_text(record)
    work.mkdir(); (work/'selection.json').write_text(json.dumps({'identity': {'inputs': [str(packages[0]/'+BUILD_INFO')]}}))
    opts = SimpleNamespace(shared_icu=True, sysroot=sysroot, ports_source=ports, host_buildlink_pkgsrc=export)
    class Process:
        @staticmethod
        def capture(*args, **kwargs): return SimpleNamespace(stdout=b'79.1\n')
    env = {'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK': str(work)}
    build.common_icu(opts, {'process': Process()}, SimpleNamespace(tool=lambda _: '/pkg-config'), env, root/'view')
    assert env['EMBERBSD_SHARED_ICU_VERSION'] == '79.1'
    assert env['EMBERBSD_SHARED_ICU_SOURCE_SHA256']
    (packages[1]/'+BUILD_VERSION').write_text(record.replace(sha(recipe/'distinfo'), '0'*64))
    try:
        build.common_icu(opts, {'process': Process()}, SimpleNamespace(tool=lambda _: '/pkg-config'), env, root/'view')
    except ValueError: pass
    else: raise AssertionError('stale target source metadata accepted')
    (packages[0]/'+BUILD_INFO').unlink()
    try:
        build.common_icu(opts, {'process': Process()}, SimpleNamespace(tool=lambda _: '/pkg-config'), env, root/'view')
    except (ValueError, FileNotFoundError): pass
    else: raise AssertionError('missing host package accepted')
print('PASS: common ICU source identity and missing/mismatch checks')
