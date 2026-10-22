#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Ported from target-execute.rb.
"""Compile GCC target probes and verify real GI target streams and cleanup."""

import argparse
import os
import re
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_sdk(source):
    require(source and os.path.isabs(source),
            'set --sdk-source or EMBERBSD_SDK_SOURCE to an absolute SDK source')
    root = Path(source).resolve(strict=True)
    package = root / 'src/emberbsd_sdk'
    require((package / '__init__.py').is_file(), 'SDK source has no emberbsd_sdk API')
    sys.path.insert(0, str(root / 'src'))
    import emberbsd_sdk
    require(type(emberbsd_sdk.API_VERSION) is int and emberbsd_sdk.API_VERSION == 1
            and Path(emberbsd_sdk.__file__).resolve().parent == package.resolve(),
            'the selected SDK must provide API version 1')
    from emberbsd_sdk.errors import CommandError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import read_json
    from emberbsd_sdk.paths import canonical_existing, canonical_new
    from emberbsd_sdk.process import capture
    return SimpleNamespace(root=str(root), CommandError=CommandError,
                           sha256_file=sha256_file, read_json=read_json,
                           canonical_existing=canonical_existing,
                           canonical_new=canonical_new, capture=capture)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', default=os.environ.get('EMBERBSD_SDK_SOURCE'))
    parser.add_argument('--helper', default=str(Path(__file__).resolve().parent.parent /
                        'recipes/devel/gobject-introspection/files/target-query.py'))
    parser.add_argument('cc', metavar='CC')
    parser.add_argument('sysroot', metavar='SYSROOT')
    parser.add_argument('query_config', metavar='QUERY_CONFIG')
    parser.add_argument('new_work', metavar='NEW_WORK')
    options = parser.parse_args()
    require(sys.version_info[:2] == (3, 15), 'use the selected build-host Python 3.15')
    sdk = load_sdk(options.sdk_source)
    python = sdk.canonical_existing(sys.executable)
    cc, sysroot, config_path, helper = map(sdk.canonical_existing,
        (options.cc, options.sysroot, options.query_config, options.helper))
    work = Path(sdk.canonical_new(os.path.abspath(options.new_work)))
    require(not os.path.lexists(work), 'Work already exists')
    config = sdk.read_json(config_path)
    require(isinstance(config, dict), 'GI query configuration must be an object')
    cache = Path(sdk.canonical_existing(config['cache']))
    triplet = sdk.capture([cc, '-dumpmachine']).stdout.decode('ascii').strip()
    version = sdk.capture([cc, '-dumpfullversion']).stdout.decode('ascii').strip()
    require(triplet in ('aarch64--netbsd', 'x86_64--netbsd') and
            re.fullmatch(r'16\.[0-9]+\.[0-9]+', version),
            'select the common GCC16 target compiler')
    runtime = Path(sysroot) / 'usr/pkg/gcc16/lib'
    crt = runtime / 'gcc' / triplet / version
    require((crt / 'libgcc.a').is_file() and (runtime / 'libgcc_s.so').is_file(),
            'selected sysroot lacks the common GCC16 runtime')
    work.mkdir(parents=True)
    source = work / 'probe.c'
    source.write_text('''#include <stdio.h>
int main(void) {
    fputs("target stdout\\n", stdout);
    fputs("target stderr\\n", stderr);
    return RESULT;
}
''', encoding='utf-8')
    environment = dict(os.environ, EMBERBSD_SDK_SOURCE=sdk.root,
                       EMBERBSD_GI_QUERY_CONFIG=config_path,
                       EMBERBSD_GI_FAILURE_MARKER=str(work / 'failure'))
    for expected in (0, 7):
        binary = work / f'probe-{expected}'
        command = [cc, '--sysroot=' + sysroot, '-Wall', '-Wextra', '-Werror',
                   '-B' + str(crt) + '/', '-B' + str(runtime) + '/',
                   '-L' + str(runtime), '-Wl,-rpath,/usr/pkg/gcc16/lib',
                   f'-DRESULT={expected}', str(source), '-o', str(binary)]
        try:
            sdk.capture(command)
        except sdk.CommandError as error:
            raise RuntimeError((error.stdout + error.stderr).decode('utf-8', 'replace')) from error
        before = set(cache.glob('gi-query-*'))
        command = [python, '-E', '-S', helper, '--execute', str(binary)]
        try:
            result = sdk.capture(command, env=environment)
        except sdk.CommandError as error:
            result = subprocess.CompletedProcess(command, error.returncode,
                                                 error.stdout, error.stderr)
        (work / f'result-{expected}.log').write_text(
            f'exit={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}\n',
            encoding='utf-8')
        require(result.stdout == b'target stdout\n' and result.stderr == b'target stderr\n'
                and result.returncode == expected, f'Target result {expected} differs')
        # Other builds may use the cache. Select this binary's exact hash receipt.
        entry = f'{sdk.sha256_file(str(binary))}  {sdk.canonical_existing(str(binary))}'
        receipts = [directory for directory in set(cache.glob('gi-query-*')) - before
                    if (directory / 'sources.sha256').is_file()
                    and entry in (directory / 'sources.sha256').read_text(encoding='utf-8').splitlines()]
        require(len(receipts) == 1, 'Missing or ambiguous provenance')
        receipt = receipts[0]
        require((receipt / 'cleanup.log').read_bytes().startswith(b'0\n'),
                'Target cleanup failed')
        require(not os.path.lexists(receipt / 'stage') and
                not os.path.lexists(receipt / 'input.tar.gz'), 'Temporary bundle survived')
    require(not os.path.lexists(work / 'failure'), 'Unexpected failure marker')
    print('PASS: real target streams, success/failure status, provenance and cleanup')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f'error: {error}', file=sys.stderr)
        raise SystemExit(1)
