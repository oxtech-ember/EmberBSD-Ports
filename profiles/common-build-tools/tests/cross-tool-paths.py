#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the actual cross-installed tool mapping rule and count tree scans."""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-prefix', type=Path, required=True)
    parser.add_argument('--patch', type=Path, default=Path(__file__).resolve().parents[1]
                        / 'patches/pkgsrc-cross-runtime-tool-values.patch')
    args = parser.parse_args()
    host = args.host_prefix.resolve()
    patch = args.patch.read_text()
    rule = patch.split('+ember-cross-tool-paths:\n', 1)[1].split('+.  endif', 1)[0]
    rule = 'ember-cross-tool-paths:\n' + ''.join(line[1:] + '\n' for line in rule.splitlines())

    with tempfile.TemporaryDirectory(prefix='cross-tool-paths-') as tmp:
        work = Path(tmp)
        stage = work / 'stage'
        stage.mkdir()
        script = stage / 'script with spaces'
        script.write_text('#!/build/native/bin/sh\n/build/native/bin/awk; /build/native/bin/grep\n'
                          '/build/native/bin/sh-long /build/native/bin/sh/subdir\n'
                          '/build/a.b[1]/sed\n/build/first\n')
        script.chmod(0o755)
        binary = stage / 'binary'
        binary.write_bytes(b'\0/build/native/bin/sh\n')
        data = stage / 'models.step'
        data.write_text('model data\n' * 10000)
        data_stat = data.stat()
        (stage / 'alias').symlink_to(script.name)
        counter = work / 'scans'
        finder = work / 'find'
        finder.write_text(f'#!{host}/bin/mksh\nprintf "scan\\n" >> "{counter}"\n'
                          f'exec "{host}/bin/gfind" "$@"\n')
        finder.chmod(0o755)
        makefile = work / 'Makefile'
        makefile.write_text(
            f'RUN= @set -e;\nWRKDIR= {work}\nDESTDIR= {stage}\nPREFIX=\n'
            f'FIND= {finder}\nGREP= {host}/bin/ggrep\nSED= {host}/bin/gsed\n'
            f'CAT= {host}/bin/gcat\nRM= {host}/bin/grm\n'
            'EMBER_CROSS_TOOL_MAP= /build/native/bin/sh=/bin/sh '
            '/build/native/bin/awk=/usr/bin/awk /build/native/bin/grep=/usr/bin/grep '
            '/build/a.b[1]/sed=/usr/bin/sed /build/first=/build/second '
            '/build/second=/usr/bin/final /build/native/bin/sh=/bin/sh '
            '=/empty /empty= relative=/bin/ignored /same=/same\n' + rule
        )
        command = [str(host / 'bin/bmake'), '-r', '-f', str(makefile), 'ember-cross-tool-paths']
        env = dict(os.environ, PATH=f'{host}/bin:{host}/gnu/bin')
        subprocess.run(command, cwd=work, env=env, check=True, capture_output=True, text=True)
        assert script.read_text() == ('#!/bin/sh\n/usr/bin/awk; /usr/bin/grep\n'
                                      '/build/native/bin/sh-long /build/native/bin/sh/subdir\n'
                                      '/usr/bin/sed\n/usr/bin/final\n')
        assert script.stat().st_mode & 0o777 == 0o755
        assert binary.read_bytes() == b'\0/build/native/bin/sh\n'
        assert (stage / 'alias').is_symlink()
        assert data.stat().st_mtime_ns == data_stat.st_mtime_ns
        assert not list(stage.glob('*.ember-tool'))
        assert not (work / '.ember-cross-tool-paths.sed').exists()
        scans = counter.read_text().splitlines()
        assert len(scans) == 1, f'expected one traversal, got {len(scans)}'
        subprocess.run(command + ['EMBER_CROSS_TOOL_MAP==/empty /empty= /same=/same'],
                       cwd=work, env=env, check=True, capture_output=True, text=True)
        assert counter.read_text().splitlines() == scans, 'empty map traversed the data tree'

    print('PASS: one scan preserves ordered mappings, boundaries, modes, binaries and untouched data')


if __name__ == '__main__':
    main()
