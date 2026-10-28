#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check V8 cache salt parity for GN and GYP and source changes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
a = parser.parse_args()
tool = a.source / 'tools/gen-version-hash-salt.py'
with tempfile.TemporaryDirectory(prefix='v8-cache-salt-') as directory:
    work = Path(directory)
    root = work / 'build'
    root.mkdir()
    receipt = work / 'source.json'
    record = {'format': 'emberbsd-prepared-source', 'version': 1,
              'package': 'lang/v8', 'identity': {'unrelated': 'ignored'},
              'tree_sha256': '0123456789abcdef' * 4}
    receipt.write_text(json.dumps(record))
    def run(*args):
        return subprocess.run([sys.executable, str(tool), *map(str, args)],
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    gn = run('--receipt', receipt)
    assert gn.returncode == 0 and gn.stdout.strip() == '0123456789abcdef'
    output = root / 'gen/src/utils/version-hash-salt.inc'
    gyp = run('--header', output, '--build-root', root, '--receipt', receipt)
    assert gyp.returncode == 0 and output.read_text() == '#define V8_VERSION_HASH_SALT "' + gn.stdout.strip() + '"\n'
    before = output.stat().st_mtime_ns
    assert run('--header', output, '--build-root', root, '--receipt', receipt).returncode == 0
    assert output.stat().st_mtime_ns == before
    record['tree_sha256'] = 'f' * 64
    receipt.write_text(json.dumps(record))
    assert run('--receipt', receipt).stdout.strip() == 'f' * 16
    assert run('--header', output, '--build-root', root, '--receipt', receipt).returncode == 0
    assert 'f' * 16 in output.read_text()
    escaped = work / 'outside-v8-header'
    assert run('--header', escaped, '--build-root', root, '--receipt', receipt).returncode != 0
    assert not escaped.exists()
    record['tree_sha256'] = '../invalid'
    receipt.write_text(json.dumps(record))
    assert run('--receipt', receipt).returncode != 0
    file = work / 'patch'
    file.write_bytes(b'line\r\nnext\n')
    expected = hashlib.sha256(b'patch\nline\nnext\n').hexdigest()[:16]
    assert run(file).stdout.strip() == expected
print('V8 GN/GYP source salt parity, invalidation, legacy mode: PASS')
