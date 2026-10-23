#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check real exported SQLite source metadata.
"""Check the shared provider, its source family, and the Tcl namespace."""

import argparse
import hashlib
from pathlib import Path
import sys
import zipfile

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', required=True, type=Path)
parser.add_argument('--bmake', required=True, type=Path)
parser.add_argument('--makeconf', required=True, type=Path)
parser.add_argument('--pkgsrc', required=True, type=Path)
parser.add_argument('--distfiles', required=True, type=Path)
parser.add_argument('--cross', action='store_true')
args = parser.parse_args()
sys.path.insert(0, str(args.sdk_source.resolve(strict=True) / 'src'))
from emberbsd_sdk import API_VERSION, jsonio, process
from emberbsd_sdk.errors import SDKError
from emberbsd_sdk.inventory import sha256_file

if API_VERSION != 1:
    parser.error('EmberBSD SDK host API 1 is required')

variables = ('PKGNAME', 'DISTNAME', 'DISTINFO_FILE', 'CONFIGURE_ARGS',
             'CPPFLAGS', 'PKG_FAIL_REASON', 'PKG_SKIP_REASON',
             'SQLITE3_VERSION', 'TCL_SQLITE3_VERSION', 'PLIST_SUBST',
             'CONFIGURE_ENV', 'TOOLS_SCRIPT.native-cc',
             'NATIVE_MACHINE_GNU_PLATFORM', 'MACHINE_GNU_PLATFORM',
             'OPSYS', 'PKG_OPTIONS', 'DEPENDS')
family = {'databases/sqlite3': ('sqlite3', 'sqlite-autoconf-3540100.tar.gz'),
          'databases/sqlite3-tcl': ('sqlite3-tcl', 'sqlite-autoconf-3540100.tar.gz'),
          'databases/sqlite3-diff': ('sqlite3-diff', 'sqlite-src-3540100.zip'),
          'databases/sqlite3-docs': ('sqlite3-docs', 'sqlite-doc-3540100.zip'),
          'devel/lemon': ('lemon-1.0', 'sqlite-src-3540100.zip')}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def query(package):
    command = [str(args.bmake), '-C', str(args.pkgsrc / package),
               'MAKECONF=' + str(args.makeconf),
               'USE_CROSS_COMPILE=' + ('yes' if args.cross else 'no')]
    for variable in variables:
        command += ['-V', '${' + variable + '}']
    values = process.capture(command).stdout.decode().splitlines()
    require(len(values) == len(variables), 'Unexpected bmake output: ' + package)
    row = dict(zip(variables, values))
    require(not row['PKG_FAIL_REASON'] and not row['PKG_SKIP_REASON'],
            'pkgsrc rejected ' + package + ': ' + str(row))
    return row


try:
    require(not (args.pkgsrc / 'local-robotics/sqlite3').exists(),
            'The duplicate robotics provider is still exported')
    rows = {}
    for package, (name, archive) in family.items():
        row = query(package)
        expected_name = name + ('.' if package == 'devel/lemon' else '-') + '3.54.1'
        require(row['PKGNAME'] == expected_name, 'Wrong package version: ' + package)
        data = (args.distfiles / archive).read_bytes()
        distinfo = args.pkgsrc / package / row['DISTINFO_FILE']
        text = distinfo.read_text()
        for algorithm, label in [('blake2s', 'BLAKE2s'), ('sha512', 'SHA512')]:
            checksum = hashlib.new(algorithm, data).hexdigest()
            require(f'{label} ({archive}) = {checksum}' in text,
                    'Wrong source checksum: ' + package)
        require(f'Size ({archive}) = {len(data)} bytes' in text,
                'Wrong source size: ' + package)
        row['archive_sha256'] = sha256_file(args.distfiles / archive)
        rows[package] = row
    if args.cross:
        for package in ('databases/sqlite3', 'databases/sqlite3-tcl',
                        'databases/sqlite3-diff'):
            row = rows[package]
            configure = row['CONFIGURE_ARGS'].split()
            require('--build=' + row['NATIVE_MACHINE_GNU_PLATFORM'] in configure,
                    'Missing native build platform: ' + package)
            target = row['MACHINE_GNU_PLATFORM'].replace('--', '-unknown-')
            require('--host=' + target in configure,
                    'Missing cross target platform: ' + package)
            require('CC_FOR_BUILD=' in row['CONFIGURE_ENV'] and
                    'native-cc' in row['CONFIGURE_ENV'] and
                    row['TOOLS_SCRIPT.native-cc'].startswith('exec '),
                    'Missing native compiler routing: ' + package)
    features = rows['databases/sqlite3']['CONFIGURE_ARGS'].split()
    require(all(x in features for x in ('--fts3', '--fts4', '--fts5', '--rtree',
            '--geopoly', '--column-metadata', '--dbstat', '--session',
            '--enable-math', '--enable-threadsafe', '--enable-load-extension')),
            'A shared SQLite feature is missing')
    sqlite = rows['databases/sqlite3']
    readline = 'readline' in sqlite['PKG_OPTIONS'].split()
    if sqlite['OPSYS'] == 'Darwin':
        require(not readline and '--disable-readline' in features and
                'editline' not in sqlite['DEPENDS'],
                'Darwin host SQLite would select a readline package')
    else:
        require(readline and '--disable-readline' not in features,
                'Target SQLite lost its readline selection')
    require('--with-system-sqlite' in rows['databases/sqlite3-tcl']['CONFIGURE_ARGS'],
            'Tcl extension would build a second SQLite library')
    tcl = query('lang/tcl')
    require(tcl['TCL_SQLITE3_VERSION'] == '3.53.4', 'Bundled Tcl wrapper identity changed')
    require('TCL_SQLITE3_VERSION=3.53.4' in tcl['PLIST_SUBST'],
            'Bundled Tcl wrapper PLIST lost its private version')
    with zipfile.ZipFile(args.distfiles / 'sqlite-doc-3540100.zip') as archive:
        expected = sorted('share/doc/sqlite3/' + name.split('/', 1)[1]
                          for name in archive.namelist() if not name.endswith('/'))
    actual = sorted(line for line in (args.pkgsrc / 'databases/sqlite3-docs/PLIST')
                    .read_text().splitlines() if line and not line.startswith('@'))
    require(actual == expected, 'Documentation PLIST differs from the official archive')
    print(jsonio.json_bytes({'schema': 'sqlite-metadata-check-v1', 'packages': rows,
                            'tcl_wrapper': tcl, 'documentation_files': len(actual)}).decode(), end='')
except (SDKError, OSError, ValueError, zipfile.BadZipFile) as error:
    parser.exit(1, str(error) + '\n')
