#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise explicit prepared-source refresh with nested WRKSRC fixtures."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

p = __import__('argparse').ArgumentParser()
p.add_argument('--sdk-source', required=True, type=Path)
a = p.parse_args()
sys.path.insert(0, str(a.sdk_source / 'src'))
from emberbsd_sdk import archive_metadata, jsonio, paths, sourceprep
assert archive_metadata.ARCHIVE_METADATA_API == 1 and sourceprep.SOURCE_PREPARATION_API == 2

scripts = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

patch = load('stage_local_patch_refresh', scripts / 'stage-local-patch-refresh.py')
refresh = load('stage_local_source_refresh', scripts / 'stage-local-source-refresh.py')
sdk = dict(paths=paths, sourceprep=sourceprep, archive_metadata=archive_metadata, jsonio=jsonio)

with tempfile.TemporaryDirectory(prefix='pkgsrc-source-refresh-test-') as temp:
    root = Path(temp)
    recipe = root / 'pkgsrc/lang/llvm'
    recipe.mkdir(parents=True)
    work = root / 'objects/lang/llvm/work'
    retained = work / 'nested/llvm-src'
    retained.mkdir(parents=True)
    scope = 'tools/llvm-objcopy/Objcopy.cpp'
    scope_b = 'tools/llvm-objcopy/Archive.cpp'
    scope_c = 'test/tools/llvm-objcopy/MachO/reexport.test'
    interpreter = 'tools/opt-viewer/extract-reproducers.py'
    subst_scope = 'build-tools/python-path.in'
    neighbor = 'build-tools/neighbor.in'
    chmod_scope = 'sample/test.rb'
    unchanged = 'llvm/include/llvm/Config/llvm-config.h'
    (retained / scope).parent.mkdir(parents=True)
    (retained / unchanged).parent.mkdir(parents=True)
    (retained / scope_c).parent.mkdir(parents=True)
    (retained / scope).write_bytes(b'old objcopy\n')
    (retained / scope_b).write_bytes(b'old archive\n')
    (retained / unchanged).write_bytes(b'generated stable\n')
    (retained / interpreter).parent.mkdir(parents=True)
    (retained / interpreter).write_bytes(b'#!/Users/smolev/Downloads/EmberBSD/host-pkg-llvm/bin/python3.15\nscript\n')
    (retained / subst_scope).parent.mkdir(parents=True)
    (retained / subst_scope).write_bytes(b'python=/old/native/python\n')
    (retained / neighbor).write_bytes(b'python=@PYTHON@\n')
    (retained / chmod_scope).parent.mkdir(parents=True)
    (retained / chmod_scope).write_bytes(b'#!/usr/bin/env ruby\n')
    (retained / chmod_scope).chmod(0o644)
    (work / '.patch_done').write_bytes(b'old patch cookie\n')
    (work / '.configure_done').write_text('configured\n')
    obj = work / 'nested/llvm-src/cmake-pkgsrc-build/CMakeCache.txt'
    obj.parent.mkdir(parents=True)
    obj.write_bytes(b'preserve build output')
    obj_stat = obj.stat()

    fake = root / 'bmake'
    fake.write_text('#!' + sys.executable + '\n' + '''import os, pathlib, sys
args = sys.argv[1:]
recipe = pathlib.Path(args[args.index('-C') + 1])
wrkdir = pathlib.Path([x.split('=', 1)[1] for x in args if x.startswith('WRKDIR=')][-1] if any(x.startswith('WRKDIR=') for x in args) else recipe / 'work')
src_name = 'other/source' if os.environ.get('ALT_WRKSRC') and '.source-refresh-' in str(wrkdir) else 'nested/llvm-src'
if 'show-var' in args:
    var = args[-1].split('=', 1)[1]
    print(wrkdir if var == 'WRKDIR' else wrkdir / src_name)
elif 'show-vars' in args:
    for var in ('WRKDIR', 'WRKSRC'):
        print(wrkdir if var == 'WRKDIR' else wrkdir / src_name)
elif 'extract' in args and 'patch' in args:
    src = wrkdir / src_name
    (src / 'tools/llvm-objcopy').mkdir(parents=True)
    (src / 'llvm/include/llvm/Config').mkdir(parents=True)
    (src / 'build-tools').mkdir(parents=True)
    (src / 'sample').mkdir(parents=True)
    (src / 'tools/llvm-objcopy/Objcopy.cpp').write_bytes(b'new objcopy\\n')
    (src / 'tools/llvm-objcopy/Archive.cpp').write_bytes(b'new archive\\n' if os.environ.get('CHANGE_SCOPE_B') else b'old archive\\n')
    (src / 'test/tools/llvm-objcopy/MachO').mkdir(parents=True)
    (src / 'test/tools/llvm-objcopy/MachO/reexport.test').write_bytes(b'added test\\n')
    (src / 'llvm/include/llvm/Config/llvm-config.h').write_bytes(b'generated stable\\n')
    (src / 'tools/opt-viewer').mkdir(parents=True)
    (src / 'tools/opt-viewer/extract-reproducers.py').write_bytes(b'#!/usr/bin/env python3\\nscript\\n')
    (src / 'build-tools/python-path.in').write_bytes(b'python=@PYTHON@\\n')
    (src / 'build-tools/neighbor.in').write_bytes(b'python=@PYTHON@\\n')
    (src / 'sample/test.rb').write_bytes(b'#!/usr/bin/env ruby\\n')
    (src / 'sample/test.rb').chmod(0o755)
    (wrkdir / '.patch_done').write_bytes(b'current pkgsrc cookie\\n')
elif 'pre-configure' in args or 'do-configure-pre-hook' in args:
    src = wrkdir / src_name
    if 'pre-configure' in args:
        path = src / 'build-tools/python-path.in'
        path.write_bytes(path.read_bytes().replace(b'@PYTHON@', b'/native/bin/python3'))
        (src / 'sample/test.rb').chmod(0o644)
    if 'do-configure-pre-hook' in args:
        script = src / 'tools/opt-viewer/extract-reproducers.py'
        data = script.read_bytes().replace(b'#!/usr/bin/env python3', b'#!/Users/smolev/Downloads/EmberBSD/host-pkg-llvm/bin/python3.15', 1)
        script.write_bytes(data)
        if os.environ.get('REPLACE_CALLED'):
            pathlib.Path(os.environ['REPLACE_CALLED']).write_text('called')
elif 'build-clean' in args:
    fail = os.environ.get('FAIL_BUILD_CLEAN')
    if fail and not pathlib.Path(fail).exists():
        pathlib.Path(fail).write_text('failed once')
        raise SystemExit(1)
else:
    raise SystemExit('unexpected fake bmake invocation: ' + repr(args))
''')
    fake.chmod(0o755)
    replaced_marker = root / 'replace-interpreter-called'
    os.environ['REPLACE_CALLED'] = str(replaced_marker)
    def run(expected_failure=False, fail_clean=None, error=None, scope_override=None):
        old = os.environ.get('FAIL_BUILD_CLEAN')
        if fail_clean:
            os.environ['FAIL_BUILD_CLEAN'] = str(fail_clean)
        try:
            result = refresh.source_refresh(sdk, patch, fake, recipe, work,
                                            ['WRKDIR=' + str(work)],
                                            scope_override or [scope, scope_b, scope_c,
                                                               subst_scope, chmod_scope])
        except Exception as exc:
            if not expected_failure:
                raise
            if error:
                assert error in str(exc), str(exc)
            return exc
        else:
            assert not expected_failure
            return result
        finally:
            if old is None:
                os.environ.pop('FAIL_BUILD_CLEAN', None)
            else:
                os.environ['FAIL_BUILD_CLEAN'] = old

    # Actual nested WRKSRC fixture: only the authorized TU changes, the
    # unchanged recipe-generated header matches, and the retained build tree stays intact.
    assert run() is True
    assert (retained / scope).read_bytes() == b'new objcopy\n'
    assert (retained / scope_b).read_bytes() == b'old archive\n'
    assert (retained / scope_c).read_bytes() == b'added test\n'
    assert (retained / subst_scope).read_bytes() == b'python=/native/bin/python3\n'
    assert (retained / neighbor).read_bytes() == b'python=@PYTHON@\n'
    assert (retained / chmod_scope).stat().st_mode & 0o777 == 0o644
    assert (retained / unchanged).read_bytes() == b'generated stable\n'
    assert (retained / interpreter).read_bytes().startswith(
        b'#!/Users/smolev/Downloads/EmberBSD/host-pkg-llvm/bin/python3.15\n')
    assert replaced_marker.exists()
    assert (work / '.patch_done').read_bytes() == b'current pkgsrc cookie\n'
    assert obj.read_bytes() == b'preserve build output'
    assert obj.stat().st_mtime_ns == obj_stat.st_mtime_ns
    assert run() is False

    # An unconfigured retained stage skips all pre-configure transforms.
    (retained / interpreter).write_bytes(b'#!/usr/bin/env python3\nscript\n')
    (retained / subst_scope).write_bytes(b'python=@PYTHON@\n')
    (retained / chmod_scope).chmod(0o755)
    (work / '.configure_done').unlink()
    replaced_marker.unlink()
    assert run() is False
    assert (retained / interpreter).read_bytes() == b'#!/usr/bin/env python3\nscript\n'
    assert (retained / subst_scope).read_bytes() == b'python=@PYTHON@\n'
    assert (retained / chmod_scope).stat().st_mode & 0o777 == 0o755
    assert not replaced_marker.exists()
    (retained / interpreter).write_bytes(
        b'#!/Users/smolev/Downloads/EmberBSD/host-pkg-llvm/bin/python3.15\nscript\n')
    (work / '.configure_done').write_text('configured\n')

    # A divergence outside the authorized scope refuses before transaction;
    # object bytes and timestamps remain unchanged.
    (retained / scope).write_bytes(b'old objcopy\n')
    (retained / unchanged).write_bytes(b'wrong generated header\n')
    (work / '.patch_done').write_bytes(b'old patch cookie\n')
    unchanged_stat = (retained / unchanged).stat()
    obj_stat = obj.stat()
    run(expected_failure=True, error='unexpected source difference outside explicit scope')
    assert (retained / scope).read_bytes() == b'old objcopy\n'
    assert (retained / unchanged).stat().st_mtime_ns == unchanged_stat.st_mtime_ns
    assert (work / '.patch_done').read_bytes() == b'old patch cookie\n'
    assert obj.stat().st_mtime_ns == obj_stat.st_mtime_ns

    # A newly prepared WRKSRC may not silently move relative to the locked stage.
    os.environ['ALT_WRKSRC'] = 'yes'
    try:
        run(expected_failure=True, error='candidate WRKSRC relative path differs')
    finally:
        os.environ.pop('ALT_WRKSRC', None)
    assert (retained / scope).read_bytes() == b'old objcopy\n'
    assert (retained / scope_b).read_bytes() == b'old archive\n'

    # build-clean failure leaves the ordinary journal; replay with the same
    # prepared candidate finishes cleanup without losing retained objects.
    (retained / unchanged).write_bytes(b'generated stable\n')
    fail_marker = root / 'build-clean-failed'
    run(expected_failure=True, fail_clean=fail_marker)
    assert (work / '.emberbsd-patch-refresh.json').exists()
    assert (retained / scope).read_bytes() == b'new objcopy\n'
    os.environ['CHANGE_SCOPE_B'] = 'yes'
    try:
        run(expected_failure=True, error='candidate has new authorized source changes outside the pending journal')
    finally:
        os.environ.pop('CHANGE_SCOPE_B', None)
    assert (retained / scope_b).read_bytes() == b'old archive\n'
    run()
    assert not (work / '.emberbsd-patch-refresh.json').exists()
    assert obj.stat().st_mtime_ns == obj_stat.st_mtime_ns

    # A terminal journal left by the existing transaction's stage-cleaned
    # interruption has no backup tree; the common transaction still completes it.
    (retained / scope).write_bytes(b'old objcopy\n')
    (work / '.patch_done').write_bytes(b'old patch cookie\n')
    original_transaction = patch.transaction
    def interrupt_after_stage_cleaned(*args, **kwargs):
        def interrupt(point):
            if point == 'stage-cleaned':
                raise RuntimeError('interrupted after staging cleanup')
        kwargs['inject'] = interrupt
        return original_transaction(*args, **kwargs)
    patch.transaction = interrupt_after_stage_cleaned
    run(expected_failure=True, error='interrupted after staging cleanup')
    patch.transaction = original_transaction
    assert (work / '.emberbsd-patch-refresh.json').exists()
    assert not (work / '.emberbsd-patch-refresh').exists()
    run()
    assert not (work / '.emberbsd-patch-refresh.json').exists()

    # A rollback can also be interrupted after its backup tree is removed.
    # The retry must use the restored live preimage before starting afresh.
    (retained / scope).write_bytes(b'old objcopy\n')
    (work / '.patch_done').write_bytes(b'old patch cookie\n')
    def interrupt_after_rollback_cleaned(*args, **kwargs):
        def interrupt(point):
            if point == 'file-0':
                raise RuntimeError('force transaction rollback')
            if point == 'stage-cleaned':
                raise RuntimeError('interrupted after rollback staging cleanup')
        kwargs['inject'] = interrupt
        return original_transaction(*args, **kwargs)
    patch.transaction = interrupt_after_rollback_cleaned
    try:
        run(expected_failure=True, error='interrupted after rollback staging cleanup')
    finally:
        patch.transaction = original_transaction
    assert (work / '.emberbsd-patch-refresh.json').exists()
    assert not (work / '.emberbsd-patch-refresh').exists()
    assert (retained / scope).read_bytes() == b'old objcopy\n'
    run()
    assert (retained / scope).read_bytes() == b'new objcopy\n'
    assert not (work / '.emberbsd-patch-refresh.json').exists()

    # Addition rollback is journaled as old_sha=None; retry after rollback
    # cleanup must verify the leaf remains absent before adding it again.
    added = retained / scope_c
    added.unlink()
    (work / '.patch_done').write_bytes(b'old patch cookie\n')
    def interrupt_added_rollback(*args, **kwargs):
        def interrupt(point):
            if point == 'file-0':
                raise RuntimeError('force added-leaf rollback')
            if point == 'stage-cleaned':
                raise RuntimeError('interrupted after added-leaf rollback cleanup')
        kwargs['inject'] = interrupt
        return original_transaction(*args, **kwargs)
    patch.transaction = interrupt_added_rollback
    try:
        run(expected_failure=True, error='interrupted after added-leaf rollback cleanup',
            scope_override=[scope_c])
    finally:
        patch.transaction = original_transaction
    assert not added.exists()
    assert (work / '.emberbsd-patch-refresh.json').exists()
    assert not (work / '.emberbsd-patch-refresh').exists()
    run(scope_override=[scope_c])
    assert added.read_bytes() == b'added test\n'
    assert not (work / '.emberbsd-patch-refresh.json').exists()

print('Prepared source refresh fixtures passed.')
