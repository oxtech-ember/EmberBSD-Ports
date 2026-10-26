#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Inspect real NetBSD driver commands; no linker or target program executes."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--clang', type=Path, required=True)
    cli.add_argument('--work', type=Path, required=True)
    args = cli.parse_args()
    assert args.clang.is_absolute()
    args.work.mkdir()
    resource = args.work / 'resource'
    libraries = resource / 'lib/netbsd'
    libraries.mkdir(parents=True)
    source = args.work / 'input.c'
    source.write_text('int main(void) { return 0; }\n')
    count = 0
    for arch in ('aarch64', 'x86_64'):
        builtins = libraries / ('libclang_rt.builtins-' + arch + '.a')
        builtins.touch()
        for language in ('c', 'c++'):
            for mode in ('dynamic', 'bootstrap', 'static', 'shared', 'nostdlib', 'nodefaultlibs', 'relocatable', 'gcc'):
                options = {'dynamic': [], 'bootstrap': ['--unwindlib=none'], 'static': ['-static'], 'shared': ['-shared'],
                           'nostdlib': ['-nostdlib'], 'nodefaultlibs': ['-nodefaultlibs'],
                           'relocatable': ['-r'], 'gcc': ['--rtlib=libgcc']}[mode]
                driver = args.clang if language == 'c' else args.clang.with_name('clang++')
                argv = [str(driver), '--target=' + arch + '--netbsd',
                        '--rtlib=compiler-rt', '--unwindlib=libunwind',
                        '-resource-dir=' + str(resource), '-###', '-x', language,
                        *options, str(source)]
                result = subprocess.run(argv, capture_output=True, text=True)
                label = arch + '-' + language.replace('+', 'x') + '-' + mode
                (args.work / (label + '.log')).write_text(result.stdout + result.stderr)
                assert result.returncode == 0, label + ': driver failed'
                commands = [shlex.split(line.strip()) for line in result.stderr.splitlines()
                            if line.strip().startswith('"')]
                assert commands and '-o' in commands[-1], label + ': no link command'
                link = commands[-1]
                if mode in ('nostdlib', 'nodefaultlibs', 'relocatable', 'gcc'):
                    assert str(builtins) not in link and not any('unwind' in item for item in link), label
                    assert '--start-group' not in link and '--end-group' not in link, label
                else:
                    assert link.count(str(builtins)) == 1, label + ': compiler-rt omitted or duplicated'
                    unwind = '-l:libunwind.a' if mode == 'static' else '-lunwind'
                    assert link.index('-lc') < link.index(str(builtins)), label
                    if mode == 'bootstrap':
                        assert not any('unwind' in item for item in link), label + ': bootstrap added an unwinder'
                    else:
                        assert unwind in link, label + ': selected unwind omitted'
                        assert link.index(str(builtins)) < link.index(unwind), label
                    assert not any(item in ('-lgcc', '-lgcc_eh', '-lgcc_s', '-lstdc++') for item in link), label
                    if language == 'c++':
                        assert '-lc++' in link and link.index('-lc++') < link.index('-lc'), label
                    if mode == 'static':
                        assert link.count('--start-group') == link.count('--end-group') == 1, label
                        assert link.index('--start-group') < link.index('-lc') < link.index(unwind) < link.index('--end-group'), label
                    else:
                        assert '--start-group' not in link and '--end-group' not in link, label
                count += 1
    nostartfiles_count = 0
    for arch in ('aarch64', 'x86_64'):
        builtins = libraries / ('libclang_rt.builtins-' + arch + '.a')
        for language in ('c', 'c++'):
            driver = args.clang if language == 'c' else args.clang.with_name('clang++')
            argv = [str(driver), '--target=' + arch + '--netbsd',
                    '--rtlib=compiler-rt', '--unwindlib=libunwind',
                    '-resource-dir=' + str(resource), '-###', '-x', language,
                    '-nostartfiles', str(source)]
            result = subprocess.run(argv, capture_output=True, text=True)
            label = arch + '-' + language.replace('+', 'x') + '-nostartfiles'
            (args.work / (label + '.log')).write_text(result.stdout + result.stderr)
            assert result.returncode == 0, label + ': driver failed'
            commands = [shlex.split(line.strip()) for line in result.stderr.splitlines()
                        if line.strip().startswith('"')]
            assert commands and '-o' in commands[-1], label + ': no link command'
            link = commands[-1]
            assert link.count(str(builtins)) == 1 and '-lc' in link and '-lunwind' in link, label
            assert link.index('-lc') < link.index(str(builtins)) < link.index('-lunwind'), label
            assert not any(item in ('-lgcc', '-lgcc_eh', '-lgcc_s', '-lstdc++') for item in link), label
            assert not any(any(name in item for name in
                               ('crt0.o', 'crt1.o', 'crti.o', 'crtbegin', 'crtend', 'crtn.o'))
                           for item in link), label + ': -nostartfiles retained a CRT object'
            if language == 'c++':
                assert '-lc++' in link and link.index('-lc++') < link.index('-lc'), label
            nostartfiles_count += 1
    (args.work / 'result.json').write_text(json.dumps(dict(status='PASS', driver_cases=count,
        nostartfiles_cases=nostartfiles_count,
        scope='Driver command construction only; no runtime link or execution')) + '\n')
    print('PASS: ' + str(count) + ' NetBSD runtime routes plus ' + str(nostartfiles_count) +
          ' -nostartfiles routes')


if __name__ == '__main__':
    main()
