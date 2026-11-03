#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise a complete ICU producer payload and its shared-stage consumer."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', type=Path, required=True)
parser.add_argument('--python', type=Path, required=True)
parser.add_argument('--work-parent', type=Path, required=True)
a = parser.parse_args()
repo = Path(__file__).resolve().parents[3]
script = repo / 'pkgsrc/textproc/icu/files/select-stage.py'
runtime = {'bin/derb', 'bin/icuinfo', 'bin/uconv', 'share/icu/79.1/LICENSE',
           'man/man1/derb.1', 'man/man1/uconv.1', 'lib/libicuuc.so.79.1'}
devel = {'bin/genrb', 'include/unicode/utypes.h', 'lib/libicuuc.so'}
with tempfile.TemporaryDirectory(prefix='icu-shared-stage-', dir=a.work_parent) as td:
    w = Path(td); source = w / 'source'; source.mkdir(); shared = w / 'shared'; dest = w / 'dest'
    def files(root):
        return {str(x.relative_to(root)): ('link:' + os.readlink(x) if x.is_symlink() else x.read_bytes())
                for x in root.rglob('*') if x.is_file() or x.is_symlink()}
    for name in (runtime | devel) - {'lib/libicuuc.so'}:
        p = source / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(name.encode())
    (source / 'lib/libicuuc.so').symlink_to('libicuuc.so.79.1')
    manifest = []
    for name, members in (('full', runtime | devel), ('runtime', runtime), ('devel', devel)):
        p = w / (name + '.plist'); p.write_text('\n'.join(sorted(members)) + '\n'); manifest.append(str(p))
    def run(*args, ok=True):
        result = subprocess.run([str(a.python), '-B', str(script), '--sdk-source', str(a.sdk_source),
                                 *map(str, args)], capture_output=True, text=True)
        if (result.returncode == 0) != ok:
            raise SystemExit('unexpected ICU stage outcome: ' + result.stdout + result.stderr)
    before = files(source)
    bad = w / 'bad.plist'; bad.write_text('\n'.join(sorted(runtime | devel | {'unexpected'})) + '\n')
    run('handoff-runtime', source, bad, manifest[1], manifest[2], shared, ok=False)
    if files(source) != before or shared.exists():
        raise SystemExit('mismatched metadata mutated source or created shared stage')
    alias = w / 'source-link'; alias.symlink_to(source, target_is_directory=True)
    run('handoff-runtime', alias, *manifest, shared, ok=False)
    if files(source) != before or shared.exists():
        raise SystemExit('symlinked stage mutated source or created shared stage')
    # A producer that changes during the copy must not leave a usable stage.
    sys.path.insert(0, str(a.sdk_source / 'src'))
    sys.path.insert(0, str(script.parent))
    spec = importlib.util.spec_from_file_location('icu_select_stage', script)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    original_copy = module.shutil.copytree
    def change_during_copy(src, dst, *args, **kwargs):
        result = original_copy(src, dst, *args, **kwargs)
        if str(src) == str(source):
            (source / 'bin/derb').write_bytes(b'concurrent change')
        return result
    module.shutil.copytree = change_during_copy
    try:
        try:
            module.copy_complete(str(source), str(shared), manifest)
        except ValueError:
            pass
        else:
            raise SystemExit('source mutation during transfer was accepted')
    finally:
        module.shutil.copytree = original_copy
    if shared.exists():
        raise SystemExit('failed transfer left a shared stage')
    (source / 'bin/derb').write_bytes(before['bin/derb'])
    run('handoff-runtime', source, *manifest, shared)
    if set(files(source)) != runtime or files(shared) != before:
        raise SystemExit('runtime or complete handoff differs from original payload')
    run('copy-devel', shared, dest, *manifest)
    if set(files(dest)) != devel or files(shared) != before:
        raise SystemExit('devel copy changed or lost the shared source payload')
print('PASS: complete ICU handoff, both payloads and mismatch refusal before mutation')
