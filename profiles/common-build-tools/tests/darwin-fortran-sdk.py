#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); real platform metadata, no package bootstrap.
"""Check selected Darwin SDK transport to Fortran wrappers with BSD make."""
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
    sys.path.insert(0, str(args.sdk_source / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk import inventory, paths
    from emberbsd_sdk.errors import CommandError, SDKError
    from emberbsd_sdk.process import sanitized_environment
    from emberbsd_sdk.stream import capture_streamed
    if (type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1 or
            Path(emberbsd_sdk.__file__).resolve().parent != (args.sdk_source / 'src/emberbsd_sdk').resolve()):
        raise SDKError('Use the explicit SDK API1 source')
    result = Path(paths.canonical_new(args.new_result))
    result.mkdir()
    patch = args.ports_source / 'profiles/common-build-tools/patches/pkgsrc-darwin-fortran-sdk.patch'
    patch_hash = inventory.sha256_file(patch)
    for phase in ('before', 'after'):
        directory = result / phase / 'mk/platform'
        directory.mkdir(parents=True)
        for name in ('Darwin.mk', 'NetBSD.mk'):
            (directory / name).write_bytes((args.pkgsrc_source / 'mk/platform' / name).read_bytes())
    sdk = result / 'selected-sdk'
    (sdk / 'usr/include').mkdir(parents=True)
    (sdk / 'usr/include/stdio.h').write_text('/* Metadata fixture only. */\n')
    environment = sanitized_environment()
    for key in ('MAKECONF', 'MAKEFLAGS', 'MFLAGS', 'MAKELEVEL', 'SDKROOT', 'MACOSX_DEPLOYMENT_TARGET'):
        environment.pop(key, None)
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, lambda number, frame: sys.exit(128 + number))
    commands = []
    log = (result / 'commands.jsonl').open('x')

    def run(argv, cwd, expected=0):
        try:
            captured = capture_streamed(list(map(str, argv)), cwd=str(cwd), env=environment,
                                        stdout_limit=1024*1024, stderr_limit=1024*1024, timeout=30)
            code, stdout, stderr = 0, captured.value, captured.stderr
            if captured.stderr_truncated:
                raise SDKError('Truncated metadata stderr')
        except CommandError as error:
            if error.stdout_truncated or error.stderr_truncated:
                raise SDKError('Truncated control output')
            code, stdout, stderr = error.returncode, error.stdout, error.stderr
        row = dict(argv=list(map(str, argv)), cwd=str(cwd), exit=code,
                   stdout=stdout.decode('utf-8'), stderr=stderr.decode('utf-8'))
        commands.append(row)
        log.write(json.dumps(row) + '\n')
        log.flush()
        if code != expected:
            raise SDKError('Unexpected command exit: ' + str(code))
        return row['stdout'].splitlines()

    run(['/usr/bin/patch', '-N', '-f', '-F', '0', '-p1', '-i', patch], result / 'after')
    fields = ('CWRAPPERS_APPEND.cc', 'CWRAPPERS_APPEND.cxx', 'CWRAPPERS_APPEND.f77',
              '_WRAP_EXTRA_ARGS.CC', '_WRAP_EXTRA_ARGS.CXX', '_WRAP_EXTRA_ARGS.FC', 'PKG_FAIL_REASON')
    cases = []

    def metadata(phase, system, architecture, cross, selected, missing=False):
        root = result / phase
        target_sdk = result / 'missing-sdk' if missing else sdk
        text = (f'OPSYS={system}\nOPSYS_VERSION={270000 if system == "Darwin" else 110000}\n'
                f'OS_VERSION={"27.0" if system == "Darwin" else "11.0"}\nOSX_VERSION=27.0\n'
                f'MACHINE_ARCH={architecture}\nHOST_MACHINE_ARCH=arm64\n'
                f'USE_CROSS_COMPILE={cross}\nTOOLS_USE_CROSS_COMPILE={cross}\n'
                f'PKGSRC_COMPILER=gcc\nCC=gcc-16\nOBJECT_FMT={"Mach-O" if system == "Darwin" else "ELF"}\n'
                f'LOCALBASE={result}/prefix\nTOOLBASE={result}/prefix\n'
                f'OSX_SDK_PATH={target_sdk}\n_CROSS_DESTDIR={result}/empty-target\n'
                'CWRAPPERS_APPEND.cc=-keep-cc\nCWRAPPERS_APPEND.cxx=-keep-cxx\n'
                'CWRAPPERS_APPEND.f77=-keep-fc\n_WRAP_EXTRA_ARGS.CC=-keep-cc\n'
                '_WRAP_EXTRA_ARGS.CXX=-keep-cxx\n_WRAP_EXTRA_ARGS.FC=-keep-fc\n')
        if selected:
            text += 'MACOSX_DEPLOYMENT_TARGET=27.0\n'
        text += f'.include "{root}/mk/platform/${{OPSYS}}.mk"\n'
        makefile = root / 'case.mk'
        makefile.write_text(text)
        output = run([args.bmake, '-r', '-f', makefile] +
                     [item for name in fields for item in ('-v', name)], result)
        if len(output) != len(fields):
            raise SDKError('Unexpected metadata field count')
        return dict(zip(fields, output))

    for system, architecture, cross, selected, missing in (
            ('Darwin', 'arm64', 'no', True, False),
            ('Darwin', 'arm64', 'no', False, False),
            ('Darwin', 'arm64', 'no', True, True),
            ('NetBSD', 'x86_64', 'yes', True, False),
            ('NetBSD', 'aarch64', 'yes', True, False),
            ('NetBSD', 'x86_64', 'no', True, False),
            ('NetBSD', 'aarch64', 'no', True, False)):
        old = metadata('before', system, architecture, cross, selected, missing)
        new = metadata('after', system, architecture, cross, selected, missing)
        expected = dict(old)
        if system == 'Darwin' and selected:
            target_sdk = result / 'missing-sdk' if missing else sdk
            for name in ('CWRAPPERS_APPEND.f77', '_WRAP_EXTRA_ARGS.FC'):
                expected[name] = old[name] + ' -isysroot ' + str(target_sdk)
            if missing != bool(new['PKG_FAIL_REASON']):
                raise SDKError('Darwin missing-SDK refusal changed')
        if new != expected:
            raise SDKError('Platform flags differ from the contract')
        cases.append(dict(system=system, architecture=architecture, cross=cross,
                          selected_sdk=selected, missing_sdk=missing, before=old, after=new))
    changed = result / 'after/mk/platform/Darwin.mk'
    digest = inventory.sha256_file(changed)
    run(['/usr/bin/patch', '-N', '-f', '-F', '0', '-p1', '-i', patch], result / 'after', expected=1)
    if inventory.sha256_file(changed) != digest or inventory.sha256_file(patch) != patch_hash:
        raise SDKError('Repeated patch or input change modified the accepted source')
    log.close()
    value = dict(status='PASS', platform_cases=len(cases), cases=cases,
                 patch_sha256=patch_hash, patched_Darwin_sha256=digest,
                 command_count=len(commands), repeated_patch_refused=True,
                 limits='Real BSD make platform metadata and patch controls only. SDK directories are fixtures. '
                        'No package bootstrap, compiler, target/native object, link, database or execution.')
    with (result / 'result.json').open('x') as output:
        json.dump(value, output, indent=2)
        output.write('\n')
    print(json.dumps({key:value[key] for key in ('status', 'platform_cases', 'command_count', 'repeated_patch_refused')}))


if __name__ == '__main__':
    main()
