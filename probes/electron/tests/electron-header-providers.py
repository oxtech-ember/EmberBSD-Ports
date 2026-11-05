#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Test selected installed package ownership and exact header projections."""
import argparse
import importlib.util
import hashlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--sdk-source', required=True, type=Path)
args = parser.parse_args()
owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/header-providers.py'
spec = importlib.util.spec_from_file_location('header_providers', owner)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp); prefix = root / 'sysroot/usr/pkg'; db = prefix / 'pkgdb'; db.mkdir(parents=True)
    host = root / 'host'; (host / 'sbin').mkdir(parents=True); (host / 'sbin/pkg_info').write_text('fixture')
    ports = root / 'ports/pkgsrc'; export = root / 'export'
    sys.path.insert(0, str(args.sdk_source / 'src'))
    from emberbsd_sdk import paths
    sdk = {'process': None, 'paths': paths}
    answers = {}; lists = {}; callbacks = []
    for name, (pkgpath, pattern, subtree, destination, required) in module.PROVIDERS.items():
        package_name = name + '-selected'; package = db / package_name; package.mkdir()
        (package / '+BUILD_INFO').write_text('PKGPATH=' + pkgpath + '\n')
        (package / '+BUILD_VERSION').write_text('metadata ' + name)
        (export / pkgpath).mkdir(parents=True)
        for path in required:
            item = prefix / path; item.parent.mkdir(parents=True, exist_ok=True); item.write_text(name)
        (package / '+CONTENTS').write_text(''.join(path + '\n@comment MD5:' + hashlib.md5(name.encode()).hexdigest() + '\n' for path in required))
        answers[pattern] = package_name
        lists[package_name] = ['/usr/pkg/' + path for path in required]
    class Process:
        @staticmethod
        def capture(args, env):
            value = answers[args[-1]] if '-E' in args else '\n'.join(lists[args[-1]])
            return SimpleNamespace(stdout=(value + '\n').encode())
    def verify(package, owner, exported, **kw):
        assert kw['distinfo'] and kw['allow_empty_patches']
        callbacks.append(kw['package_path'])
    options = SimpleNamespace(sysroot=root / 'sysroot', host_prefix=host, ports_source=root / 'ports', host_buildlink_pkgsrc=export)
    sdk['process'] = Process
    def select(): return module.select(options, sdk, None, {}, source_check=verify)
    result = select()
    assert set(result) == set(module.PROVIDERS) and len(callbacks) == 3
    assert result['fp16']['files'] == ['include/fp16.h', 'include/fp16/fp16.h']
    assert result['flatbuffers']['destination'] == 'third_party/flatbuffers/src/include/flatbuffers'
    assert select()['eigen3']['identity'] == result['eigen3']['identity']
    header = prefix / 'include/fp16.h'; before = header.stat()
    header.write_text('different content')
    os.utime(header, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert select()['fp16']['identity'] != result['fp16']['identity']
    cases = [('/usr/pkg/include/fp16.h', '/usr/pkg/include/../fp16.h'),
             ('/usr/pkg/include/fp16.h', '/usr/pkg/include/fp16/missing.h')]
    for old, new in cases:
        lists['fp16-selected'][0] = new
        try: select()
        except (ValueError, FileNotFoundError): pass
        else: raise AssertionError('accepted unsafe or unowned required file')
        lists['fp16-selected'][0] = old
    linked = prefix / 'include/fp16.h'
    linked.unlink(); outside = root / 'outside.h'; outside.write_text('outside')
    linked.symlink_to(outside)
    try: select()
    except ValueError: pass
    else: raise AssertionError('accepted header escaping selected prefix')
    linked.unlink(); linked.write_text('fp16')
    def reject_source(*args, **kwargs): raise ValueError('source patch metadata differs')
    try: module.select(options, sdk, None, {}, source_check=reject_source)
    except ValueError: pass
    else: raise AssertionError('accepted mismatched source metadata')
    answers['fp16>=0.0.0pre20260620'] += '\nother'
    try: select()
    except ValueError: pass
    else: raise AssertionError('accepted ambiguous package')
print('PASS: owned headers, exact mapping, stable metadata, negative controls')
