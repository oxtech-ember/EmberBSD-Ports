#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Verify the common Node source and every pkgsrc patch against the release."""
import argparse
import ast
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import sysconfig
import tarfile

sys.dont_write_bytecode = True

p = argparse.ArgumentParser()
for option in ('archive', 'recipe', 'patch', 'work', 'gyp-source', 'gyp-pkgsrc', 'sdk-source'):
    p.add_argument('--' + option, type=Path, required=True)
a = p.parse_args()
archive, recipe, patch, gyp = (x.resolve(strict=True) for x in (a.archive, a.recipe, a.patch, a.gyp_source))
subprocess.run([sys.executable, '-B', '-I', '-S', str(a.gyp_pkgsrc / 'devel/gyp/files/verify-source.py'),
                '--sdk-source', str(a.sdk_source), '--source', str(gyp), '--pkgsrc-root', str(a.gyp_pkgsrc)], check=True)
work = a.work.resolve()
assert not work.exists(), 'work directory must be new'
with archive.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == 'a7f6204ff63b6a2cd274d48903285abb86ed53a99070e532d4c2fd787457d9e6'
work.mkdir(parents=True)
with tarfile.open(archive) as stream:
    stream.extractall(work, filter='data')
source = work / 'node-v26.13.1'
distinfo = (recipe / 'distinfo').read_text()
patches = sorted((recipe / 'patches').glob('patch-*'))
assert patches, 'no package patches'
for item in patches:
    data = b''.join(line for line in item.read_bytes().splitlines(keepends=True) if b'$NetBSD' not in line)
    digest = hashlib.sha1(data).hexdigest()
    assert f'SHA1 ({item.name}) = {digest}' in distinfo, item.name
    subprocess.run([str(patch), '--batch', '--forward', '--fuzz=0', '-p0', '-i', str(item)],
                   cwd=source, check=True, stdout=subprocess.DEVNULL)
common = (source / 'common.gypi').read_text()
assert common.count('netbsd openbsd') == 2
assert "'MACOSX_DEPLOYMENT_TARGET': '<(mac_deployment_target)'" in common
assert '(3, 15)' in (source / 'configure').read_text()
assert 'GYP_MACOS_SDK_PATH' in (gyp / 'pylib/gyp/xcode_emulation.py').read_text()
assert 'GYP_LIBTOOL' in (gyp / 'pylib/gyp/generator/make.py').read_text()
hash_header = (source / 'deps/v8/src/base/hashing.h').read_text()
assert not re.search(r'namespace std\s*\{\s*template\s*<typename T>\s*requires', hash_header)
assert 'base::hash<CanonicalGroup>' in (source / 'deps/v8/src/wasm/canonical-types.h').read_text()
# -S disables site initialization; use only the selected interpreter's
# installed dependencies needed by the selected GYP source.
site = Path(sysconfig.get_path('purelib')).resolve(strict=True)
assert site.is_relative_to(Path(sys.prefix).resolve()), site
sys.path.insert(0, str(site))
import packaging
assert Path(packaging.__file__).resolve().is_relative_to(site)
sys.path.insert(0, str(gyp / 'pylib'))
from gyp.input import CheckedEval, GypError
# Abseil contains both Darwin and Windows conditions; duplicate keys would
# discard a platform or cause checked GYP generation to fail.
CheckedEval((source / 'tools/v8_gypfiles/abseil.gyp').read_text())
assert CheckedEval('{"key": ["value", {"inner": "text"}]}') == {"key": ["value", {"inner": "text"}]}
for value in ('{1:"value"}', '{b"key":"value"}', '{**{}}',
              '{"key":1}', '{"key":True}', '{"key":None}', '{"key":b"bytes"}',
              '{"key":open("MUST-NOT-EXIST","w")}', '{"key":[str(x) for x in []]}',
              '{"key":"one", "key":"two"}'):
    try:
        CheckedEval(value)
    except (TypeError, GypError, AssertionError):
        pass
    else:
        raise AssertionError('invalid GYP input was accepted: ' + value)
assert not (Path.cwd() / 'MUST-NOT-EXIST').exists()
result = subprocess.run([sys.executable, '-B', str(source / 'configure'), '--help'], cwd=source,
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
assert result.returncode == 0, result.stderr
unsupported = ('import runpy,sys;sys.version_info=(3,16,0,\"final\",0);'
               'sys.argv=[sys.argv[1],\"--help\"];runpy.run_path(sys.argv[0],run_name=\"__main__\")')
result = subprocess.run([sys.executable, '-B', '-I', '-c', unsupported, str(source / 'configure')],
                        cwd=source, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
assert result.returncode != 0 and 'Please use' in result.stderr, result.stderr
subprocess.run([sys.executable, '-B', '-I', '-S', str(a.gyp_pkgsrc / 'devel/gyp/files/verify-source.py'),
                '--sdk-source', str(a.sdk_source), '--source', str(gyp), '--pkgsrc-root', str(a.gyp_pkgsrc)], check=True)
print(f'Node 26.13.1 checksum and {len(patches)} patches; GYP parser, Darwin inputs and V8 contracts: PASS')
