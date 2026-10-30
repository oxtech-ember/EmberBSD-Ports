#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify selected host and target Abseil source provenance."""
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
    for recipe in (ports/'pkgsrc/devel/abseil', export/'devel/abseil'):
        (recipe/'patches').mkdir(parents=True); (recipe/'patches/patch-test').write_text('patch')
        (recipe/'distinfo').write_text('distinfo')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    recipe = ports/'pkgsrc/devel/abseil'
    record = 'devel/abseil/distinfo: '+sha(recipe/'distinfo')+'\ndevel/abseil/patches/patch-test: '+sha(recipe/'patches/patch-test')+'\n'
    packages = (stage/'pkgdb/abseil-host', sysroot/'usr/pkg/pkgdb/abseil-target')
    for pkg in packages:
        pkg.mkdir(parents=True); (pkg/'+BUILD_INFO').write_text('PKGPATH=devel/abseil\n'); (pkg/'+BUILD_VERSION').write_text(record)
    work.mkdir(); (work/'selection.json').write_text(json.dumps({'identity': {'inputs': [str(packages[0]/'+BUILD_INFO')]}}))
    opts = SimpleNamespace(shared_abseil=True, sysroot=sysroot, ports_source=ports, host_buildlink_pkgsrc=export)
    class Process:
        @staticmethod
        def capture(*args, **kwargs): return SimpleNamespace(stdout=b'20260817\n')
    env = {'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK': str(work)}
    build.common_abseil(opts, {'process': Process()}, SimpleNamespace(tool=lambda _: '/pkg-config'), env, root/'view')
    assert env['EMBERBSD_SHARED_ABSEIL_VERSION'] == '20260817'
    assert env['EMBERBSD_SHARED_ABSEIL_SOURCE_SHA256']
    (packages[1]/'+BUILD_VERSION').write_text(record.replace(sha(recipe/'distinfo'), '0'*64))
    try:
        build.common_abseil(opts, {'process': Process()}, SimpleNamespace(tool=lambda _: '/pkg-config'), env, root/'view')
    except ValueError: pass
    else: raise AssertionError('stale target source metadata accepted')
    (packages[0]/'+BUILD_INFO').unlink()
    try:
        build.common_abseil(opts, {'process': Process()}, SimpleNamespace(tool=lambda _: '/pkg-config'), env, root/'view')
    except (ValueError, FileNotFoundError): pass
    else: raise AssertionError('missing host package accepted')
print('PASS: common Abseil source identity and missing/mismatch checks')
