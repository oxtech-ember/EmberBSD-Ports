#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Query the actual ordinary pkgsrc recipe.
"""Check NNG host formatter selection for native and cross builds."""
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--makeconf', type=Path, required=True)
    parser.add_argument('--bmake', type=Path, required=True)
    parser.add_argument('--asciidoctor', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    config = args.work / 'mk.conf'
    config.write_text(f'.include "{args.makeconf.resolve()}"\n'
                      '.undef EMBERBSD_BUILD_ASCIIDOCTOR\n.undef PKG_OPTIONS.nng\n')

    def query(name, mode, override=None, options=None):
        command = [str(args.bmake), '-C', str(args.pkgsrc / 'net/nng'),
                   f'MAKECONF={config}', f'USE_CROSS_COMPILE={mode}']
        if override is not None:
            command.append(f'EMBERBSD_BUILD_ASCIIDOCTOR={override}')
        if options is not None:
            command.append(f'PKG_OPTIONS.nng={options}')
        for variable in ['PKG_FAIL_REASON', 'TOOL_DEPENDS', 'CMAKE_CONFIGURE_ARGS', 'PKG_OPTIONS']:
            command += ['-v', variable]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, check=True)
        (args.work / f'{name}.txt').write_text(result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        assert len(lines) == 4, result.stdout
        return lines

    for mode in ['yes', 'no']:
        failures, depends, flags, options = query(f'default-{mode}', mode)
        assert not failures, failures
        assert '-asciidoctor>=2.0.26<3:../../textproc/ruby-asciidoctor' in depends
        assert '-DNNG_ENABLE_DOC:BOOL=ON' in flags and 'doc' in options.split()
        failures, depends, flags, options = query(f'explicit-{mode}', mode, args.asciidoctor.resolve())
        assert not failures, failures
        assert ':../../textproc/ruby-asciidoctor' not in depends
        assert f'-DASCIIDOCTOR:FILEPATH={args.asciidoctor.resolve()}' in flags
        print(f'PASS: default and real explicit formatter; cross={mode}')

    linked = args.work / 'linked-asciidoctor'
    linked.symlink_to(args.asciidoctor.resolve())
    failures, depends, flags, _ = query('valid-symlink', 'yes', linked)
    assert not failures, failures
    assert f'-DASCIIDOCTOR:FILEPATH={linked}' in flags
    assert ':../../textproc/ruby-asciidoctor' not in depends
    print('PASS: real executable formatter symlink')
    nonexec = args.work / 'non-executable'
    nonexec.write_text('#!/bin/sh\nprintf "Asciidoctor 2.0.26\\n"\n')
    failures, _, _, _ = query('non-executable', 'yes', nonexec)
    assert 'must successfully report' in failures
    print('PASS: refusal non-executable')
    for name, version, status in [('old', '2.0.25', 0), ('future', '3.0.0', 0),
                                  ('failed-command', '2.0.26', 1), ('wrong-banner', 'unknown', 0)]:
        fake = args.work / name
        fake.write_text(f'#!/bin/sh\nprintf "Asciidoctor {version}\\n"\nexit {status}\n')
        fake.chmod(0o755)
        failures, _, _, _ = query(name, 'yes', fake)
        assert 'EMBERBSD_BUILD_ASCIIDOCTOR must successfully report' in failures
        print(f'PASS: refusal {name}')
    for name, path in [('relative', 'formatter'), ('missing', args.work / 'absent')]:
        failures, _, _, _ = query(name, 'yes', path)
        assert 'existing absolute host executable' in failures
        print(f'PASS: refusal {name}')
    failures, depends, flags, options = query('doc-disabled', 'yes', args.work / 'absent', '-doc')
    assert not failures, failures
    assert ':../../textproc/ruby-asciidoctor' not in depends
    assert '-DNNG_ENABLE_DOC:BOOL=OFF' in flags and 'doc' not in options.split()
    print('PASS: explicit doc-disabled package option')


if __name__ == '__main__':
    main()
