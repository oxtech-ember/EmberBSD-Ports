#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Actual Node configure entry and checked GYP generation on selected Python 3.15."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

NEW_PATCHES = ('patch-configure', 'patch-tools_gyp_pylib_gyp_input.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'distfile', 'patch', 'work'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15):
        parser.error('run with the selected Python 3.15 provider')
    if not args.work.is_absolute() or args.work.exists():
        parser.error('use a new absolute work directory')
    args.work.mkdir()
    recipe = args.work/'pkgsrc/lang/nodejs24'
    shutil.copytree(args.pkgsrc/'lang/nodejs24', recipe)
    outer = Path(__file__).resolve().parents[1]/'patches/pkgsrc-nodejs24-python315.patch'
    already_applied = all((recipe/'patches'/name).is_file() for name in NEW_PATCHES)
    command = [str(args.patch), '-f', '-F0', '-p0', '-i', str(outer)]
    command += ['--dry-run', '-R'] if already_applied else ['-N']
    result = subprocess.run(command, cwd=args.work/'pkgsrc', capture_output=True, text=True)
    if result.returncode or 'fuzz' in result.stdout.lower():
        raise RuntimeError(result.stdout+result.stderr)
    pins = {}
    for line in (recipe/'distinfo').read_text().splitlines():
        match = re.fullmatch(r'(BLAKE2s|SHA512|Size|SHA1) \(([^)]+)\) = (.+)', line)
        if match:pins.setdefault(match[2], {})[match[1]] = match[3]
    data = args.distfile.read_bytes();source_pin = pins[args.distfile.name]
    assert hashlib.blake2s(data).hexdigest() == source_pin['BLAKE2s']
    assert hashlib.sha512(data).hexdigest() == source_pin['SHA512']
    assert str(len(data))+' bytes' == source_pin['Size']
    source = args.work/'node-v24.22.1'
    patches = [recipe/'patches'/name for name in sorted(pins) if 'SHA1' in pins[name]]
    # Extract the real configure/GYP scripts and all portability patch targets.
    # This source regression does not need Chromium/V8's unmodified test tree.
    needed = {'configure', 'configure.py', 'tools/icu/icu_versions.json'}
    for path in patches:
        needed.update(re.findall(r'^\+\+\+ ([^\s]+)', path.read_text(), re.MULTILINE))
    with tarfile.open(args.distfile, mode='r|xz') as archive:
        for member in archive:
            prefix, separator, relative = member.name.partition('/')
            assert prefix == source.name
            if (relative in needed or relative.startswith(('tools/gyp/', 'tools/configure.d/'))
                    or (relative.startswith('tools/') and relative.count('/') == 1 and relative.endswith('.py'))):
                archive.extract(member, args.work, filter='data')
    def apply(path):
        data = b''.join(line for line in path.read_bytes().splitlines(keepends=True) if b'$NetBSD' not in line)
        assert hashlib.sha1(data).hexdigest() == pins[path.name]['SHA1'], path.name
        result = subprocess.run([str(args.patch), '-f', '-N', '-F0', '-E', '-p0', '-i', str(path)],
                                cwd=source, capture_output=True, text=True)
        if result.returncode or 'fuzz' in result.stdout.lower():raise RuntimeError(path.name+'\n'+result.stdout+result.stderr)
        if path.name in NEW_PATCHES:assert 'offset' not in result.stdout.lower(), result.stdout
    for path in patches:
        if path.name not in NEW_PATCHES:apply(path)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    # Keep the selected interpreter and its declared packaging module; no pip,
    # interpreter search or target Node is used by this regression.
    def run(name, argv, cwd=source):
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
        (args.work/(name+'.log')).write_text(result.stdout+result.stderr)
        return result
    config = [sys.executable, '-B', str(source/'configure'), '--help']
    result = run('configure-before', config)
    assert result.returncode and 'Please use python3.14' in result.stderr
    import_gyp = 'import sys;sys.path.insert(0,sys.argv[1]);import gyp.input\n'
    before = import_gyp + 'print(gyp.input.CheckedEval(' + repr('{"key": "value"}') + '))'
    result = run('gyp-before', [sys.executable, '-B', '-I', '-c', before,
                              str(source/'tools/gyp/pylib')])
    assert result.returncode and "has no attribute 'Str'" in result.stderr
    for name in NEW_PATCHES:apply(recipe/'patches'/name)
    result = run('configure-after', config)
    assert not result.returncode and 'Node.js configure: Found Python 3.15.' in result.stdout, result.stdout+result.stderr
    unsupported = ('import runpy,sys;sys.version_info=(3,16,0,"final",0);'
                   'sys.argv=[sys.argv[1],"--help"];runpy.run_path(sys.argv[0],run_name="__main__")')
    result = run('configure-unsupported', [sys.executable, '-B', '-I', '-c',
                                          unsupported, str(source/'configure')])
    assert result.returncode and 'Please use python3.15' in result.stderr
    cases = import_gyp + '''
assert gyp.input.CheckedEval('{"key": ["value", {"inner": "text"}]}') == {"key": ["value", {"inner": "text"}]}
try:gyp.input.CheckedEval('{"key":"one", "key":"two"}')
except gyp.input.GypError as error:assert "Key 'key' repeated at level 1" in str(error)
else:raise AssertionError('duplicate key accepted')
for text in ('{1:"value"}', '{b"key":"value"}', '{**{}}'):
    try:gyp.input.CheckedEval(text)
    except AssertionError:pass
    else:raise AssertionError('non-string key accepted: '+text)
for text in ('{"key":1}', '{"key":True}', '{"key":None}', '{"key":b"bytes"}', '{"key":open("MUST-NOT-EXIST","w")}', '{"key":[str(x) for x in []]}'):
    try:gyp.input.CheckedEval(text)
    except TypeError:pass
    else:raise AssertionError('non-string value accepted: '+text)
from pathlib import Path
assert not Path('MUST-NOT-EXIST').exists()
print('11 checked-parser contracts passed')
'''
    result = run('checked-parser', [sys.executable, '-B', '-I', '-c', cases, str(source/'tools/gyp/pylib')])
    assert not result.returncode, result.stdout+result.stderr
    fixture = args.work/'generator';fixture.mkdir()
    build = fixture/'fixture.gyp';build.write_text("{'targets':[{'target_name':'probe','type':'none','variables':{'selected':'python315'}}]}\n")
    command = [sys.executable, '-B', str(source/'tools/gyp/gyp_main.py'), '--check', '-f', 'gypd', '--depth='+str(fixture), str(build)]
    result = run('gyp-generate', command, fixture)
    assert not result.returncode and (fixture/'fixture.gypd').is_file(), result.stdout+result.stderr
    assert 'python315' in (fixture/'fixture.gypd').read_text()
    (fixture/'fixture.gypd').unlink()
    build.write_text("{'targets':[], 'targets':[]}\n")
    result = run('gyp-duplicate', command, fixture)
    assert result.returncode and "Key 'targets' repeated" in result.stderr
    assert not (fixture/'fixture.gypd').exists()
    summary = {'source':'Node24.22.1','patches':len(patches),'parser_contracts':11,
               'causal_failures':['configure version refusal','removed ast.Str'],
               'scope':'configure entry/help and real checked gypd generation; no full shared-dependency configure, compiler, Node runtime or target execution'}
    (args.work/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':main()
