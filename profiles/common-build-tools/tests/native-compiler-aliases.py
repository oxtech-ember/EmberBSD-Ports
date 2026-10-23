#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check actual native compiler alias policy.
"""Check cwrappers alias metadata with BSD make. Do not bootstrap packages."""
import argparse
import json
from pathlib import Path
import signal
import sys
sys.dont_write_bytecode = True


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--ports-source', required=True, type=Path)
    cli.add_argument('--sdk-source', required=True, type=Path)
    cli.add_argument('--bmake', required=True, type=Path)
    cli.add_argument('--pkgsrc-source', required=True, type=Path)
    cli.add_argument('new_result', type=Path)
    args = cli.parse_args()
    sys.path.insert(0, str(args.sdk_source/'src'))
    import emberbsd_sdk
    from emberbsd_sdk import inventory, paths
    from emberbsd_sdk.errors import CommandError, SDKError
    from emberbsd_sdk.process import sanitized_environment
    from emberbsd_sdk.stream import capture_streamed
    if (type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1 or
            Path(emberbsd_sdk.__file__).resolve().parent != (args.sdk_source/'src/emberbsd_sdk').resolve()):
        raise SDKError('Use the explicit SDK API1 source')
    result = Path(paths.canonical_new(args.new_result))
    result.mkdir()
    patch = args.ports_source/'profiles/common-build-tools/patches/pkgsrc-native-compiler-aliases.patch'
    patch_hash = inventory.sha256_file(patch)
    for phase in ('before', 'after'):
        target = result/phase/'mk/cwrappers.mk'
        target.parent.mkdir(parents=True)
        target.write_bytes((args.pkgsrc_source/'mk/cwrappers.mk').read_bytes())
    environment = sanitized_environment()
    for key in ('MAKECONF', 'MAKEFLAGS', 'MFLAGS', 'MAKELEVEL'):
        environment.pop(key, None)
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, lambda number, frame: sys.exit(128+number))
    commands = []

    def run(argv, cwd, expected=0):
        try:
            captured = capture_streamed(list(map(str, argv)), cwd=str(cwd), env=environment,
                                        stdout_limit=1024*1024, stderr_limit=1024*1024, timeout=30)
            code, stdout, stderr = 0, captured.value, captured.stderr
            if captured.stderr_truncated:
                raise SDKError('Truncated command stderr')
        except CommandError as error:
            if error.stdout_truncated or error.stderr_truncated:
                raise SDKError('Truncated command output')
            code, stdout, stderr = error.returncode, error.stdout, error.stderr
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), exit=code,
                   stdout=stdout.decode(), stderr=stderr.decode())
        commands.append(row)
        with (result/'commands.jsonl').open('a') as out:
            out.write(json.dumps(row)+'\n')
        if code != expected:
            raise SDKError('Unexpected command exit: '+str(code))
        return row['stdout'].splitlines()

    run(['/usr/bin/patch', '-N', '-f', '-F', '0', '-p1', '-i', patch], result/'after')
    fields = ('CWRAPPERS_ALIASES.cc', 'CWRAPPERS_ALIASES.cxx', 'CWRAPPERS_ALIASES.ld')
    blocks = {}
    for phase in ('before', 'after'):
        text = (result/phase/'mk/cwrappers.mk').read_text()
        start = text.index('CWRAPPERS_ALIASES.as=')
        stop = text.index('CWRAPPERS_WRAPPEE.as=')
        blocks[phase] = text[start:stop]
    cases = []
    for cross, cc, cxx, ld in (
            ('no', '/compiler/bin/gcc-16', '/compiler/bin/g++-16', 'ld'),
            ('no', 'gcc-16', 'g++-16', 'ld'),
            ('no', 'gcc', 'g++', 'ld'),
            ('no', 'cc', 'c++', 'ld'),
            ('no', 'clang', 'clang++', 'ld'),
            ('no', '/compiler/bin/gcc-16 -pipe', '/compiler/bin/g++-16 -pipe', 'ld'),
            ('yes', 'x86_64--netbsd-gcc', 'x86_64--netbsd-g++', 'x86_64--netbsd-ld'),
            ('yes', 'aarch64--netbsd-gcc', 'aarch64--netbsd-g++', 'aarch64--netbsd-ld')):
        values = {}
        for phase in ('before', 'after'):
            source = result/phase/'case.mk'
            source.write_text(f'TOOLS_USE_CROSS_COMPILE={cross}\nCC={cc}\nCXX={cxx}\nLD={ld}\n'+blocks[phase])
            output = run([args.bmake, '-r', '-f', source]+[part for key in fields for part in ('-v', key)], result)
            if len(output) != len(fields):
                raise SDKError('Unexpected alias metadata count')
            values[phase] = {key:value.split() for key,value in zip(fields, output)}
        expected = {key:list(value) for key,value in values['before'].items()}
        if cross == 'no':
            for key, command in zip(fields, (cc, cxx)):
                name = Path(command.split()[0]).name
                if name not in expected[key]:
                    expected[key].append(name)
        if values['after'] != expected or any(len(v) != len(set(v)) for v in values['after'].values()):
            raise SDKError('Compiler aliases differ from the contract')
        cases.append(dict(cross=cross, cc=cc, cxx=cxx, ld=ld, **values))
    changed = result/'after/mk/cwrappers.mk'
    digest = inventory.sha256_file(changed)
    run(['/usr/bin/patch', '-N', '-f', '-F', '0', '-p1', '-i', patch], result/'after', expected=1)
    if inventory.sha256_file(changed) != digest or inventory.sha256_file(patch) != patch_hash:
        raise SDKError('Repeated patch or input change modified the accepted source')
    value = dict(status='PASS', alias_cases=len(cases), cases=cases, patch_sha256=patch_hash,
                 before_cwrappers_sha256=inventory.sha256_file(result/'before/mk/cwrappers.mk'),
                 after_cwrappers_sha256=digest, command_count=len(commands), repeated_patch_refused=True,
                 limits='Real BSD make evaluation of the actual cwrappers alias block only. '
                        'No package bootstrap, compiler, object, link, database or program execution. '
                        'Normal native package and target acceptance are separate.')
    with (result/'result.json').open('x') as out:
        json.dump(value, out, indent=2)
        out.write('\n')
    print(json.dumps({key:value[key] for key in ('status', 'alias_cases', 'command_count', 'repeated_patch_refused')}))


if __name__ == '__main__':
    main()
