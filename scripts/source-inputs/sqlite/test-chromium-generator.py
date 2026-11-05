#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check Chromium SQLite flags are read as literal data, never executed."""
import argparse
import importlib.util
from pathlib import Path
import sys
import tempfile
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk-source',type=Path,required=True)
p.add_argument('--chromium',type=Path,required=True)
a=p.parse_args(); sys.argv=[sys.argv[0],'--sdk-source',str(a.sdk_source.resolve(strict=True))]
path=Path(__file__).with_name('generate-chromium.py'); spec=importlib.util.spec_from_file_location('sqlite_generator',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=a.chromium.resolve(strict=True)
common=m.flags_from_gni(root/'sqlite_common_configuration_flags.gni','sqlite_common_configuration_flags')
chrome=m.flags_from_gni(root/'sqlite_chromium_configuration_flags.gni','sqlite_chromium_configuration_flags')
assert all(x in common for x in ('SQLITE_ENABLE_ICU','SQLITE_HAVE_SQLITE3R','SQLITE_SECURE_DELETE','SQLITE_OMIT_LOAD_EXTENSION'))
assert 'SQLITE_DQS=0' in chrome
dev=m.flags_from_gni(root/'sqlite_dev_configuration_flags.gni','sqlite_dev_configuration_flags')
assert 'SQLITE_ENABLE_EXPLAIN_COMMENTS' in dev
with tempfile.TemporaryDirectory(prefix='sqlite-gni-test-') as tmp:
    f=Path(tmp)/'flags.gni'
    for data in ("flags = [__import__('os').system('false')]\n", "flags = ['SQLITE_X;bad']\n", "flags = ['SQLITE_A']\nflags = ['SQLITE_B']\n"):
        f.write_text(data)
        try: m.flags_from_gni(f,'flags')
        except (ValueError, m.SDKError): pass
        else: raise AssertionError('nonliteral, unsafe or duplicate GNI flags accepted')
print('PASS: Chromium SQLite recovery/privacy flags and literal-only parsing')
