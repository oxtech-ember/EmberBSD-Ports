#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check actual binding compiler outputs.

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description='Compare actual system-SQLite binding objects before and after repair')
parser.add_argument('before_object', type=Path)
parser.add_argument('after_object', type=Path)
parser.add_argument('nm', type=Path)
args = parser.parse_args()
records = []
globals_ = {'sqlite3_version', 'sqlite3_temp_directory', 'sqlite3_data_directory'}
for path in (args.before_object, args.after_object):
    result = subprocess.run([str(args.nm), '-g', '-P', str(path)],
                            text=True, capture_output=True, check=True)
    symbols = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 2:
            symbols[fields[0].removeprefix('_')] = fields[1]
    definitions = {name: symbols[name] for name in globals_
                   if name in symbols and symbols[name].upper() != 'U'}
    records.append({'object_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'sqlite_data_definitions': definitions,
                    'sqlite_library_import': symbols.get('sqlite3_libversion')})
if set(records[0]['sqlite_data_definitions']) != globals_:
    raise RuntimeError('The baseline does not reproduce all three invalid definitions')
if records[1]['sqlite_data_definitions']:
    raise RuntimeError('The repaired binding still defines system SQLite data')
if records[1]['sqlite_library_import'] != 'U':
    raise RuntimeError('The repaired binding does not import the real SQLite version API')
print(json.dumps({'status': 'PASS', 'scope': 'Actual compiled system-SQLite binding objects. The baseline defines all three system globals. The repair removes those definitions and retains the SQLite API import.',
                  'before': records[0], 'after': records[1]}, indent=2))
