#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), ported from the EmberBSD Ruby regression.
"""Check real target streams, exit status, provider receipts and cleanup."""
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    if len(sys.argv) != 5:
        raise ValueError('Usage: target-execute.py CC SYSROOT QUERY_CONFIG NEW_WORK')
    cc, sysroot, config_path = (Path(p).resolve(strict=True) for p in sys.argv[1:4])
    original = Path(sys.argv[4])
    if not original.is_absolute() or original.exists() or original.is_symlink():
        raise ValueError('new absolute work required')
    original.mkdir()
    work = original.resolve(strict=True)
    config = json.loads(config_path.read_text())
    helper = Path(__file__).resolve().parent.parent / 'recipes/devel/gobject-introspection/files/target-query.py'
    source = work / 'probe.c'
    source.write_text('#include <stdio.h>\nint main(void) {\n'
                      ' fputs("target stdout\\n", stdout);\n'
                      ' fputs("target stderr\\n", stderr);\n return RESULT;\n}\n')
    for code in (0, 7):
        binary = work / ('probe-' + str(code))
        command = [str(cc), '--sysroot=' + str(sysroot), '-Wall', '-Wextra', '-Werror',
                   '-DRESULT=' + str(code), str(source), '-o', str(binary)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        (work / ('compile-' + str(code) + '.log')).write_bytes(result.stdout)
        if result.returncode:
            raise ValueError('compilation failed; use a configured GCC16 target wrapper: ' + str(work))
        cache = Path(config['cache'])
        before = set(cache.glob('gi-query-*'))
        result = subprocess.run([sys.executable, str(helper), '--execute', str(binary)],
                                env={**os.environ, 'EMBERBSD_GI_QUERY_CONFIG': str(config_path),
                                     'EMBERBSD_GI_FAILURE_MARKER': str(work / 'failure')},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=210, check=False)
        (work / ('result-' + str(code) + '.log')).write_text(
            f'exit={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}\n')
        if (result.stdout, result.stderr, result.returncode) != (b'target stdout\n', b'target stderr\n', code):
            raise ValueError('Target result differs: ' + str(code))
        receipts = [p for p in set(cache.glob('gi-query-*')) - before
                    if (p / 'sources.sha256').is_file() and str(binary) in (p / 'sources.sha256').read_text()]
        if len(receipts) != 1:
            raise ValueError('Missing or ambiguous provenance')
        receipt = receipts[0]
        if not (receipt / 'cleanup.log').read_text().startswith('0\n'):
            raise ValueError('Target cleanup failed')
        if (receipt / 'stage').exists() or (receipt / 'input.tar.gz').exists():
            raise ValueError('Temporary bundle survived')
    if (work / 'failure').exists():
        raise ValueError('Unexpected failure marker')
    print('PASS: real target streams, success/failure status, provenance and cleanup')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        sys.exit(str(error))
