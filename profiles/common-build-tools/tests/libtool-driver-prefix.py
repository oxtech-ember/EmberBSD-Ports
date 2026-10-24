#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), GCC driver-prefix transport regression.
"""Check native Darwin Libtool link routes without installing a provider."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prefix_in_link(output, prefix):
    for line in output.splitlines():
        if ' link: ' not in line:
            continue
        args = shlex.split(line.split(' link: ', 1)[1])
        if '-dynamiclib' not in args and '-shared' not in args:
            continue
        if '-B' + prefix in args:
            return True
        if any(arg == '-B' and following == prefix for arg, following in zip(args, args[1:])):
            return True
    return False


def check_override(pkgsrc, bmake, shell, candidate, cc, host_abi, prefix, work, run):
    fixture = work / 'override'
    projects = ('libiconv/libtool', 'libiconv/libcharset/libtool', 'libunistring/libtool')
    for name in projects:
        path = fixture / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/sh\n# Labelled project fixture before pkgsrc override.\nexit 77\n')
        path.chmod(0o755)
    makefile = work / 'override.mk'
    makefile.write_text(f'WRKSRC= {fixture}\nLIBTOOL= {candidate}\nTOOLS_SH= {shell}\n'
                        'OVERRIDE_DIRDEPTH= 2\nRUN= set -e;\nSTEP_MSG= :\n'
                        'RM= /bin/rm\nECHO= echo\nCHMOD= /bin/chmod\nEXPR= /bin/expr\n'
                        f'.include "{pkgsrc}/mk/configure/libtool-override.mk"\n')
    run('override-generation', [bmake, '-r', '-f', makefile, 'libtool-override'])
    for name in projects:
        wrapper = fixture / name
        require(wrapper.read_text().splitlines() == ['#!' + str(shell), 'exec ' + str(candidate) + ' "$@"'],
                'Project did not select the common provider: ' + name)
        command = [wrapper, '--dry-run', '--tag=CC', '--mode=link', cc, '-B' + prefix,
                   '-isysroot', host_abi, '-mmacosx-version-min=26.0', '-o', 'libcontrol.la',
                   '-rpath', work / '.libs', '-version-info', '1:0:0', '-no-undefined', 'probe.lo']
        _, output = run('override-' + name.replace('/', '-'), command)
        require(prefix_in_link(output, prefix), 'Common driver prefix was lost through project override')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'cc', 'driver-prefix', 'host-abi', 'sandbox-profile', 'pkgsrc', 'bmake', 'shell', 'work'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    require(sys.platform == 'darwin', 'This runtime check requires native Darwin')
    for path in vars(args).values():
        require(path.is_absolute(), 'Use absolute paths')
    args.work.mkdir()
    work = args.work
    for name in ('home', 'tmp', 'cache', 'config', 'data'):
        (work / name).mkdir()
    prefix = str(args.driver_prefix) + '/'
    env = dict(HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'),
               XDG_CACHE_HOME=str(work / 'cache'), XDG_CONFIG_HOME=str(work / 'config'),
               XDG_DATA_HOME=str(work / 'data'), LC_ALL='C', xcrun_log='1',
               PATH=f'{args.cc.parent}:{args.baseline.parent}:/usr/bin:/bin:/usr/sbin:/sbin')
    for tool in ('as', 'ld', 'ar', 'ranlib', 'nm', 'strip'):
        env[tool.upper()] = str(args.driver_prefix / tool)
    records = []

    def run(name, command, success=True):
        full = ['/usr/bin/sandbox-exec', '-f', str(args.sandbox_profile), *map(str, command)]
        result = subprocess.run(full, cwd=work, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=30)
        output = result.stdout.decode(errors='replace')
        (work / (name + '.log')).write_text(output)
        records.append(dict(name=name, argv=full, exit=result.returncode))
        (work / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
        if success:
            require(result.returncode == 0, f'{name} failed; see {work / (name + ".log")}')
        return result.returncode, output

    _, version = run('compiler', [args.cc, '-dumpfullversion'])
    require(version.strip().startswith('16.'), 'Select native GCC16')
    providers = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in (args.baseline, args.candidate)}
    (work / 'probe.c').write_text('int\nroute_probe(void)\n{\n\treturn 42;\n}\n')
    (work / 'main.c').write_text('int route_probe(void);\n\nint\nmain(void)\n{\n\treturn (route_probe() != 42);\n}\n')
    flags = ['-B' + prefix, '-isysroot', str(args.host_abi), '-mmacosx-version-min=26.0']
    run('compile', [args.baseline, '--tag=CC', '--mode=compile', args.cc,
                    *flags, '-c', 'probe.c', '-o', 'probe.lo'])

    def link(tool, selectors, output, dry=False, tag='CC'):
        return [tool, *(['--dry-run'] if dry else []), '--tag=' + tag, '--mode=link',
                args.cc if tag == 'CC' else args.cc.parent / 'g++', *selectors,
                '-isysroot', args.host_abi, '-mmacosx-version-min=26.0',
                '-o', output, '-rpath', work / '.libs', '-version-info', '1:0:0',
                '-no-undefined', 'probe.lo']

    for name, selectors in (('joined', ['-B' + prefix]), ('separate', ['-B', prefix])):
        _, output = run('link-' + name, link(args.candidate, selectors, 'lib' + name + '.la'))
        require(prefix_in_link(output, prefix), name + ': shared link lost the GCC driver prefix')
        require("couldn't create cache file" not in output, name + ': external xcrun cache route remains')
        run('consumer-' + name, [args.cc, *flags, 'main.c', work / '.libs' / ('lib' + name + '.dylib'),
                                '-o', name + '-consumer'])
        run('run-' + name, [work / (name + '-consumer')])

    # C++ uses the same parser. Dry runs avoid a second native runtime build.
    for tag in ('CC', 'CXX'):
        for name, selectors in (('joined', ['-B' + prefix]), ('separate', ['-B', prefix])):
            _, output = run('dry-' + tag + '-' + name,
                            link(args.candidate, selectors, 'libcontrol.la', dry=True, tag=tag))
            require(prefix_in_link(output, prefix), tag + ': driver prefix transport differs')
    spaced = str(work / 'driver prefix') + '/'
    for name, selectors in (('joined', ['-B' + spaced]), ('separate', ['-B', spaced])):
        _, output = run('quoted-' + name, link(args.candidate, selectors, 'libcontrol.la', dry=True))
        require(prefix_in_link(output, spaced), 'quoted driver prefix changed')

    # Keep the inherited Libtool meanings. These are not GCC search prefixes.
    for flag in ('-Bstatic', '-Bdynamic', '-Bsymbolic'):
        _, before = run('special-baseline-' + flag[1:], link(args.baseline, [flag], 'libcontrol.la', dry=True))
        _, after = run('special-candidate-' + flag[1:], link(args.candidate, [flag], 'libcontrol.la', dry=True))
        require(before == after, 'special Libtool flag changed: ' + flag)
    # Non-GCC configurations must keep their existing argument routing.
    for name, tool in (('baseline', args.baseline), ('candidate', args.candidate)):
        directory = work / (name + '-non-gcc')
        directory.mkdir()
        content, count = re.subn(r'^with_gcc=yes$', 'with_gcc=no', tool.read_text(), count=1, flags=re.M)
        require(count == 1, 'Fixture requires a configured GCC Libtool')
        fixture = directory / 'libtool'
        fixture.write_text(content)
        fixture.chmod(0o755)
        _, output = run('non-gcc-' + name, link(fixture, ['-B' + prefix], 'libcontrol.la', dry=True))
        if name == 'baseline':
            unchanged = output
        else:
            require(output == unchanged, 'non-GCC compiler flag routing changed')
    command = link(args.candidate, [], 'libcontrol.la', dry=True) + ['-B']
    status, output = run('missing-prefix', command, success=False)
    require(status != 0 and 'requires an argument' in output, 'missing separate prefix was accepted')
    require(all(hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
                for name, digest in providers.items()), 'Selected provider was modified')
    check_override(args.pkgsrc, args.bmake, args.shell, args.candidate, args.cc, args.host_abi,
                   prefix, work, run)
    (work / 'providers.json').write_text(json.dumps(providers, indent=2) + '\n')
    print('PASS: joined/separate GCC16 shared links and consumers run without external cache diagnostics')
    print('PASS: C/C++ and quoted prefixes, unchanged special/non-GCC controls, missing prefix refusal')
    print('PASS: real pkgsrc override selects one shared provider for libiconv/libcharset/libunistring layouts')
    print('SCOPE: native Darwin link transport only; no package build, install or target acceptance')


if __name__ == '__main__':
    main()
