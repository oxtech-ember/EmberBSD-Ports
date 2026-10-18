#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real pkg_create metadata regression.
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 2:
    sys.exit('Use HOST_PKG_CREATE NEW_WORK')
create, work = args[0], Path(args[1]).absolute()
work.mkdir()
cross = Path(__file__).resolve().parents[1] / 'cross'
sys.path.insert(0, str(cross))
spec = importlib.util.spec_from_file_location('preparer', cross / 'prepare-llvm-python315.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
(work / 'payload/bin').mkdir(parents=True)
(work / 'payload/bin/test').write_text('test payload')
(work / 'comment').write_text('Package metadata regression')
(work / 'description').write_text('Not an installed compiler package.')
original = '@cwd /usr/pkg\n@name llvm-plist-fixture-1.0\nbin/test\n@comment MD5:old\n@ignore\n+COMMENT\n@ignore\n+DESC\n'
for fixed in (False, True):
    name = 'fixed' if fixed else 'baseline'
    text = helper.prepare_packlist(original) if fixed else ''.join(line for line in original.splitlines(keepends=True) if not line.startswith('@comment MD5:'))
    plist, archive = work / (name + '.plist'), work / (name + '.tgz')
    plist.write_text(text)
    result = subprocess.run([create, '-p', str(work / 'payload'), '-I', '/usr/pkg', '-f', str(plist), '-c', str(work / 'comment'), '-d', str(work / 'description'), str(archive)], capture_output=True)
    assert result.returncode == 0, result.stderr
    result = subprocess.run(['/usr/bin/tar', '-xOf', str(archive), '+CONTENTS'], check=True, capture_output=True, text=True)
    (work / (name + '-contents')).write_text(result.stdout)
    names = re.findall(r'^@ignore\n(\+[^\n]+)\n', result.stdout, re.M)
    assert (len(names) == len(set(names))) == fixed
assert helper.prepare_packlist('@ignore\nprivate-file\n') == '@ignore\nprivate-file\n'
print('PASS: causal duplicate metadata baseline; repaired transformation preserves one generated control entry')
