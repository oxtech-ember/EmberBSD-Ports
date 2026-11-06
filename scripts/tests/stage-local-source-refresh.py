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
    unchanged = 'llvm/include/llvm/Config/llvm-config.h'
    (retained / scope).parent.mkdir(parents=True)
    (retained / unchanged).parent.mkdir(parents=True)
    (retained / scope).write_bytes(b'old objcopy\n')
    (retained / unchanged).write_bytes(b'generated stable\n')
    (work / '.patch_done').write_bytes(b'old patch cookie\n')
    obj = work / 'nested/llvm-src/cmake-pkgsrc-build/CMakeCache.txt'
    obj.parent.mkdir(parents=True)
    obj.write_bytes(b'preserve build output')
    obj_stat = obj.stat()

    fake = root / 'bmake'
    fake.write_text('#!' + sys.executable + '\n' + '''import os, pathlib, sys
args = sys.argv[1:]
recipe = pathlib.Path(args[args.index('-C') + 1])
wrkdir = pathlib.Path([x.split('=', 1)[1] for x in args if x.startswith('WRKDIR=')][-1] if any(x.startswith('WRKDIR=') for x in args) else recipe / 'work')
if 'show-var' in args:
    var = args[-1].split('=', 1)[1]
    print(wrkdir if var == 'WRKDIR' else wrkdir / 'nested/llvm-src')
elif 'show-vars' in args:
    for var in ('WRKDIR', 'WRKSRC'):
        print(wrkdir if var == 'WRKDIR' else wrkdir / 'nested/llvm-src' if var == 'WRKSRC' else 'llvm-src')
elif 'extract' in args and 'patch' in args:
    src = wrkdir / 'nested/llvm-src'
    (src / 'tools/llvm-objcopy').mkdir(parents=True)
    (src / 'llvm/include/llvm/Config').mkdir(parents=True)
    (src / 'tools/llvm-objcopy/Objcopy.cpp').write_bytes(b'new objcopy\\n')
    (src / 'llvm/include/llvm/Config/llvm-config.h').write_bytes(b'generated stable\\n')
    (wrkdir / '.patch_done').write_bytes(b'current pkgsrc cookie\\n')
elif 'build-clean' in args:
    fail = os.environ.get('FAIL_BUILD_CLEAN')
    if fail and not pathlib.Path(fail).exists():
        pathlib.Path(fail).write_text('failed once')
        raise SystemExit(1)
else:
    raise SystemExit('unexpected fake bmake invocation: ' + repr(args))
''')
    fake.chmod(0o755)
    def run(expected_failure=False, fail_clean=None):
        old = os.environ.get('FAIL_BUILD_CLEAN')
        if fail_clean:
            os.environ['FAIL_BUILD_CLEAN'] = str(fail_clean)
        try:
            refresh.source_refresh(sdk, patch, fake, recipe, work, ['WRKDIR=' + str(work)], [scope])
        except Exception:
            if not expected_failure:
                raise
        else:
            assert not expected_failure
        finally:
            if old is None:
                os.environ.pop('FAIL_BUILD_CLEAN', None)
            else:
                os.environ['FAIL_BUILD_CLEAN'] = old

    # Actual nested WRKSRC fixture: only the authorized TU changes, the
    # unchanged recipe-generated header matches, and the retained build tree stays intact.
    run()
    assert (retained / scope).read_bytes() == b'new objcopy\n'
    assert (retained / unchanged).read_bytes() == b'generated stable\n'
    assert (work / '.patch_done').read_bytes() == b'current pkgsrc cookie\n'
    assert obj.read_bytes() == b'preserve build output'
    assert obj.stat().st_mtime_ns == obj_stat.st_mtime_ns

    # A divergence outside the authorized scope refuses before transaction;
    # object bytes and timestamps remain unchanged.
    (retained / scope).write_bytes(b'old objcopy\n')
    (retained / unchanged).write_bytes(b'wrong generated header\n')
    (work / '.patch_done').write_bytes(b'old patch cookie\n')
    unchanged_stat = (retained / unchanged).stat()
    obj_stat = obj.stat()
    run(expected_failure=True)
    assert (retained / scope).read_bytes() == b'old objcopy\n'
    assert (retained / unchanged).stat().st_mtime_ns == unchanged_stat.st_mtime_ns
    assert (work / '.patch_done').read_bytes() == b'old patch cookie\n'
    assert obj.stat().st_mtime_ns == obj_stat.st_mtime_ns

    # build-clean failure leaves the ordinary journal; replay with the same
    # prepared candidate finishes cleanup without losing retained objects.
    (retained / unchanged).write_bytes(b'generated stable\n')
    fail_marker = root / 'build-clean-failed'
    run(expected_failure=True, fail_clean=fail_marker)
    assert (work / '.emberbsd-patch-refresh.json').exists()
    assert (retained / scope).read_bytes() == b'new objcopy\n'
    run()
    assert not (work / '.emberbsd-patch-refresh.json').exists()
    assert obj.stat().st_mtime_ns == obj_stat.st_mtime_ns

print('Prepared source refresh fixtures passed.')
