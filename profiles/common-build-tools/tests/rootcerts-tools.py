#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check actual pkgsrc metadata and generated script.
"""Check native generators and the explicit NetBSD 11 full-base script contract."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess


VARIABLES = ['PKG_FAIL_REASON', 'USE_TOOLS', 'TOOL_DEPENDS', 'DEPENDS',
             'AWK', 'SH', 'TOOLS_PATH.openssl', 'SUBST_VARS.paths',
             'SUBST_SED.paths', '_CERT_BUILD_ENV', 'USE_BUILTIN.openssl']
BASE = {'AWK': '/usr/bin/awk', 'ECHO': '/bin/echo', 'EXPR': '/bin/expr',
        'LN': '/bin/ln', 'LS': '/bin/ls', 'MKDIR': '/bin/mkdir', 'RM': '/bin/rm'}


def query(args, tree, name, *extra):
    command = [str(args.bmake), '-C', str(tree / 'security/mozilla-rootcerts'),
               f'MAKECONF={args.makeconf}', *extra]
    for key in VARIABLES:
        command += ['-v', key]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    lines = result.stdout.splitlines()
    assert len(lines) == len(VARIABLES), result.stdout
    values = dict(zip(VARIABLES, lines))
    (args.work / f'{name}.json').write_text(json.dumps(values, indent=2) + '\n')
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['pkgsrc', 'baseline-pkgsrc', 'makeconf', 'sysroot', 'bmake',
                'staged-script', 'certdata', 'os-source', 'work']:
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--os-commit', required=True)
    args = parser.parse_args()
    for key in vars(args):
        value = getattr(args, key)
        if isinstance(value, Path):
            setattr(args, key, value.resolve())
    args.work.mkdir(parents=True, exist_ok=False)
    assert not any((args.sysroot / p).exists() for p in ['usr/bin/awk', 'bin/echo', 'bin/expr',
                                                        'bin/ln', 'bin/ls', 'bin/mkdir', 'bin/rm'])
    base = query(args, args.baseline_pkgsrc, 'baseline-cross', 'USE_CROSS_COMPILE=yes')
    for tool in ['awk', 'echo', 'expr', 'ln', 'ls', 'openssl', 'rm', 'mkdir']:
        assert f'USE_TOOLS+={tool}:run not supported' in base['PKG_FAIL_REASON']
    print('PASS: unpatched consumer refuses the real compiler-only SDK')
    cross = query(args, args.pkgsrc, 'cross', 'USE_CROSS_COMPILE=yes')
    assert not cross['PKG_FAIL_REASON'], cross['PKG_FAIL_REASON']
    assert not any(t.endswith(':run') for t in cross['USE_TOOLS'].split())
    assert 'openssl>=3.6.5:../../security/openssl' in cross['TOOL_DEPENDS'].split()
    assert cross['USE_BUILTIN.openssl'] == 'yes'
    assert 'openssl>=3.6.5:../../security/openssl' not in cross['DEPENDS'].split()
    assert '-e \'s,@OPENSSL@,/usr/bin/openssl,g\'' in cross['SUBST_SED.paths']
    alternate = query(args, args.pkgsrc, 'pkgsrc-openssl', 'USE_CROSS_COMPILE=yes', 'USE_BUILTIN.openssl=no')
    assert not alternate['PKG_FAIL_REASON'], alternate['PKG_FAIL_REASON']
    assert 'openssl>=3.6.5:../../security/openssl' in alternate['DEPENDS'].split()
    assert '-e \'s,@OPENSSL@,/usr/pkg/bin/openssl,g\'' in alternate['SUBST_SED.paths']
    print('PASS: distinct native generator and target OpenSSL dependency/path')
    native = query(args, args.pkgsrc, 'native', 'USE_CROSS_COMPILE=no')
    original = query(args, args.baseline_pkgsrc, 'native-baseline', 'USE_CROSS_COMPILE=no')
    assert native == original, 'Native tool selection changed'
    print('PASS: native tool/dependency/substitution behavior is unchanged')
    for name, options in [
        ('arbitrary-tool', ['USE_TOOLS=sed:run']),
        ('unknown-version', ['OS_VERSION=12.0', 'OPSYS_VERSION=120000']),
    ]:
        values = query(args, args.pkgsrc, name, 'USE_CROSS_COMPILE=yes', *options)
        assert 'not supported in cross-compilation' in values['PKG_FAIL_REASON']
        print(f'PASS: refusal {name}')
    empty = args.work / 'empty-sysroot'
    empty.mkdir()
    for tool in ['bash', 'perl']:
        values = query(args, args.pkgsrc, 'missing-' + tool, 'USE_CROSS_COMPILE=yes',
                       f'EMBERBSD_CROSS_SYSROOT={empty}', f'USE_TOOLS={tool}:run')
        assert f'{tool}:run not supported' in values['PKG_FAIL_REASON']
        print(f'PASS: missing target {tool} remains refused')
    # Verify the source contract against the SDK's actual OS pin, not VM files.
    imported = json.loads((args.sysroot / '.prebuild-sdk-import.json').read_text())
    assert imported['manifest']['provenance']['sources']['os'] == args.os_commit
    def source(path):
        return subprocess.check_output(['git', '-C', str(args.os_source), 'show',
                                        args.os_commit + ':' + path], text=True)
    assert re.search(r'^BINDIR\?=\s*/bin$', source('bin/Makefile.inc'), re.M)
    for tool in ['sh', 'cat', 'echo', 'expr', 'ln', 'ls', 'mkdir', 'rm']:
        assert re.search(r'^PROG=\s*' + tool + r'$', source(f'bin/{tool}/Makefile'), re.M)
    for path, tool in [('external/historical/nawk/bin/Makefile', 'awk'),
                       ('crypto/external/apache2/openssl/bin/Makefile', 'openssl')]:
        text = source(path)
        assert re.search(r'^PROG=\s*' + tool + r'$', text, re.M)
        assert re.search(r'^BINDIR\??=\s*/usr/bin$', text, re.M)
    print('PASS: fixed runtime paths match the pinned EmberBSD full-base sources')
    distinfo = (args.pkgsrc / 'security/mozilla-rootcerts/distinfo').read_text()
    data = args.certdata.read_bytes()
    for label, value in [('SHA512', hashlib.sha512(data).hexdigest()),
                         ('BLAKE2s', hashlib.blake2s(data).hexdigest())]:
        assert f'{label} (certdata-20260715.txt) = {value}' in distinfo
    assert f'Size (certdata-20260715.txt) = {len(data)} bytes' in distinfo
    script = args.staged_script.read_text()
    assert script.startswith('#!/bin/sh\n')
    for variable, path in BASE.items():
        assert f': ${{{variable}={path}}}' in script
    assert ': ${OPENSSL=/usr/bin/openssl}' in script
    for forbidden in [str(args.sysroot), str(args.work), str(args.pkgsrc), '/Volumes/']:
        assert forbidden not in script
    env_command = shlex.split(cross['_CERT_BUILD_ENV'])
    assignments = dict(x.split('=', 1) for x in env_command[1:])
    assert set(assignments) == {'AWK', 'OPENSSL'}
    assert str(args.sysroot) not in assignments['OPENSSL']
    assert assignments['OPENSSL'].endswith('/bin/openssl')
    run = args.work / 'host-extract'
    run.mkdir()
    environment = dict(os.environ, **assignments)
    result = subprocess.run(shlex.split(cross['SH']) + [str(args.staged_script), '-f',
                            str(args.certdata), 'extract'], cwd=run, env=environment,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    (args.work / 'host-extract.log').write_bytes(result.stdout)
    count = len(list(run.glob('*.pem')))
    assert count > 100, count
    (args.work / 'host-cert-count.txt').write_text(str(count) + '\n')
    print(f'PASS: actual installed script extracts {count} certificates with native generators')


if __name__ == '__main__':
    main()
