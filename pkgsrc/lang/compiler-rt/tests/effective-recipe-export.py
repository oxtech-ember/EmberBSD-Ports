#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check runtime recipe receipts in checkout and exported pkgsrc layouts."""
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

root = Path(__file__).resolve().parents[4]
pkgsrc = root / 'pkgsrc'
owner_root = pkgsrc / 'lang/compiler-rt'
spec = importlib.util.spec_from_file_location('runtime_build', owner_root / 'files/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
source_spec = importlib.util.spec_from_file_location('runtime_source', owner_root / 'files/source.py')
source = importlib.util.module_from_spec(source_spec)
source_spec.loader.exec_module(source)
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def receipt(exported):
    calls = []
    def revision(git, path):
        calls.append((git, Path(path)))
        return 'a' * 40
    selected = SimpleNamespace(
        OWNER=owner_root, PORTS=root if not exported else root.parent,
        PKGSRC=pkgsrc, EXPORTED=exported,
        input_name=lambda path: 'pkgsrc/' + str(Path(path).relative_to(pkgsrc)),
        inventory=SimpleNamespace(sha256_file=digest), git_revision=revision,
        require=lambda condition, message: None if condition else (_ for _ in ()).throw(ValueError(message)),
        shared_export_revision=lambda: source.shared_export_revision(),
    )
    export = {'format': 'emberbsd-pkgsrc-shared-export', 'version': 4,
              'identity': {'api': 1, 'ports_commit': 'b' * 40}}
    source.EXPORTED = exported
    source.PKGSRC = pkgsrc
    source.SDKError = ValueError
    source.jsonio = SimpleNamespace(read_json=lambda path: export)
    result = build.effective_recipe(selected, {'recipe': {'files': {}}}, '/usr/bin/git')
    expected = {
        'pkgsrc/lang/compiler-rt/files/build.py',
        'pkgsrc/lang/compiler-rt/files/runtime.py',
        'pkgsrc/lang/compiler-rt/tests/runtime-c.c',
        'pkgsrc/lang/compiler-rt/tests/runtime-cxx.cpp',
    }
    assert set(result['files']) == expected, result['files']
    assert result['ports_revision'] == ('b' * 40 if exported else 'a' * 40)
    from emberbsd_sdk.llvm_runtime import _digest
    _digest(result['ports_revision'], 40)
    assert len(calls) == (0 if exported else 1), calls
    if calls:
        assert calls[0] == ('/usr/bin/git', root)
    if exported:
        valid = export
        for malformed in (
                {**valid, 'version': 2},
                {**valid, 'identity': {**valid['identity'], 'api': 2}},
                {**valid, 'identity': {**valid['identity'], 'ports_commit': 'not-a-revision'}},
                {**valid, 'identity': {**valid['identity'], 'ports_commit': 'a' * 39}},
        ):
            source.jsonio.read_json = lambda path, record=malformed: record
            try:
                build.effective_recipe(selected, {'recipe': {'files': {}}}, '/usr/bin/git')
            except ValueError:
                pass
            else:
                raise AssertionError('malformed or non-current export provenance was accepted')

receipt(False)
receipt(True)
print('PASS: checkout and exported recipe receipts preserve revision and pkgsrc paths')
