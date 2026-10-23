#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check actual MIT metadata generation and GCC16 consumer linking."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import tarfile
import tempfile
sys.dont_write_bytecode = True
from sdk_source import load_sdk, install_signal_handlers, exit_error

ARCHIVE_SHA256 = '3243ffbc8ea4d4ac22ddc7dd2a1dc54c57874c40648b60ff97009763554eaf13'
BASELINE_PATCH_SHA1 = 'ffd76099bc4882502835ca40ec9c78e6ec15043c'
FILES = ('aclocal.m4', 'patchlevel.h', 'config/config.guess', 'config/config.sub',
         'config/install-sh', 'config/shlib.conf', 'config/pkg.m4',
         'config/ac-archive/ax_pthread.m4', 'config/ac-archive/ax_recursive_eval.m4',
         'build-tools/krb5-config.in')


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    sdk, args = load_sdk()
    from emberbsd_sdk import stream
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
    from emberbsd_sdk.elf import read_elf_dynamic
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json
    from emberbsd_sdk.paths import canonical_existing, canonical_new, reject_overlap
    require(stream.PRODUCER_STREAM_API == 1 and stream.PRODUCER_INSPECTION_API == 1,
            'SDK producer stream and inspection API 1 are required')
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'pkgsrc', 'bmake', 'autoconf', 'cc', 'native-cc', 'sysroot', 'work'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--native-sysroot', type=Path, help='Native GCC SDK override, when required')
    p.add_argument('--rpath-flag', required=True, help='Expanded target COMPILER_RPATH_FLAG')
    a = p.parse_args(args)
    require(sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 15),
            'Use build-host CPython 3.15')
    require(all(x.is_absolute() for x in vars(a).values() if isinstance(x, Path)),
            'All paths must be absolute')
    require(not os.path.lexists(a.work), 'Work must be unused')
    require(a.rpath_flag and not any(c in a.rpath_flag for c in '\n\r$@#'),
            'Use the expanded target compiler flag')
    a.work = Path(canonical_new(a.work))
    for name in ('archive', 'pkgsrc', 'bmake', 'autoconf', 'cc', 'native_cc', 'sysroot', 'native_sysroot'):
        path = getattr(a, name)
        if path is not None:
            path = Path(canonical_existing(path))
            reject_overlap(path, a.work)
            setattr(a, name, path)
    reject_overlap(sdk, a.work)
    reject_overlap(Path(__file__).resolve().parents[4], a.work)
    require(sha256_file(a.archive) == ARCHIVE_SHA256, 'MIT archive SHA256 differs')
    here = Path(__file__).resolve().parent
    recipe = here.parents[1] / '../../pkgsrc/security/mit-krb5'
    a.work.mkdir(mode=0o700)
    (a.work / 'incomplete').write_text('Metadata/link qualification is incomplete.\n')
    tempfile.tempdir = str(a.work)
    env = dict(os.environ, TMPDIR=str(a.work), TMP=str(a.work), TEMP=str(a.work),
               PYTHONDONTWRITEBYTECODE='1', CONFIG_SITE='/dev/null')
    commands = []

    def run(name, argv, cwd=None, environment=None, failure=False):
        status = 0
        try:
            r = stream.capture_streamed(list(map(str, argv)), cwd=str(cwd or a.work),
                env=environment or env, timeout=90, empty_snapshot_timeout=10,
                stdout_limit=2 * 1024 * 1024)
            out, err = r.value, r.stderr
            require(not r.stderr_truncated, 'Producer stderr was truncated')
        except CommandError as error:
            status, out, err = error.returncode, error.stdout, error.stderr
        (a.work / (name + '.stdout')).write_bytes(out)
        (a.work / (name + '.stderr')).write_bytes(err)
        commands.append(dict(name=name, argv=list(map(str, argv)), cwd=str(cwd or a.work), status=status))
        with (a.work / 'commands.jsonl').open('a') as log:
            log.write(json.dumps(commands[-1]) + '\n')
        require((status == 1) if failure else (status == 0), name + ': unexpected producer status')
        return out.decode('utf-8', 'strict').strip()

    try:
        for name, compiler in (('cross', a.cc), ('native', a.native_cc)):
            require(re.fullmatch(r'16\.[0-9]+\.[0-9]+', run(name + '-version', [compiler, '-dumpfullversion'])),
                    'Both compilers must be GCC16')
        triplet = run('cross-triplet', [a.cc, '-dumpmachine'])
        native = run('native-triplet', [a.native_cc, '-dumpmachine'])
        require(triplet in ('aarch64--netbsd', 'x86_64--netbsd'), 'Select a common target compiler')
        runtime = a.sysroot / 'usr/pkg/gcc16/lib'
        version = run('runtime-version', [a.cc, '-dumpfullversion'])
        support = runtime / 'gcc' / triplet / version
        require((support / 'libgcc.a').is_file(), 'The common target runtime is absent')
        inputs = [a.archive, a.cc, a.native_cc, a.bmake, a.autoconf, Path(__file__),
                  recipe/'Makefile', recipe/'patches/patch-config_shlib.conf',
                  recipe/'patches/patch-build-tools_krb5-config.in', a.pkgsrc/'mk/subst.mk', here/'client.c',
                  *(recipe/'patches'/n for n in ('patch-aclocal.m4', 'patch-z-cross-aclocal_m4',
                                                 'patch-zz-libtool-nodelete')),
                  *(a.sysroot/'usr/pkg/lib'/n for n in ('libkrb5.so.3', 'libgssapi_krb5.so.2',
                       'libk5crypto.so.3', 'libcom_err.so.3', 'libkrb5support.so.0'))]
        initial = {str(x):sha256_file(x.resolve(strict=True)) for x in inputs}
        run('autoconf-version', [a.autoconf, '--version'])
        run('bmake-version', [a.bmake, '-V', 'MAKE_VERSION'])
        baseline_patch = (recipe / 'patches/patch-config_shlib.conf').read_bytes()
        require(baseline_patch.count(b'@COMPILER_RPATH_FLAG@') == 3, 'Compiler markers changed')
        baseline_patch = baseline_patch.replace(b'@COMPILER_RPATH_FLAG@', b'${COMPILER_RPATH_FLAG}')
        require(hashlib.sha1(b''.join(x for x in baseline_patch.splitlines(keepends=True)
                    if b'$NetBSD' not in x)).hexdigest() == BASELINE_PATCH_SHA1,
                'The inverse baseline differs from the historical inherited patch')
        (a.work / 'baseline-shlib.patch').write_bytes(baseline_patch)
        selected = a.work / 'selected-upstream'
        with tarfile.open(a.archive) as archive:
            for rel in FILES:
                member = archive.getmember('krb5-1.22.2/src/' + rel)
                require(member.isfile(), 'Selected upstream input must be a regular file')
                target = selected / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as src, target.open('xb') as dst:
                    shutil.copyfileobj(src, dst)
                target.chmod(0o755 if rel.endswith(('config.guess', 'config.sub', 'install-sh')) else 0o644)
        variables = ('KRB5_VERSION', 'KDB5_DB_LIB', 'PTHREAD_CFLAGS', 'DL_LIB',
                     'DEFCCNAME', 'DEFKTNAME', 'DEFCKTNAME', 'LIBS')
        configure = ('AC_INIT([mit-rpath-contract], [1.22.2])\n'
                     'AC_PREFIX_DEFAULT([/usr/pkg])\nKRB5_AC_CHOOSE_ET\nKRB5_BUILD_PROGRAM\n' +
                     '\n'.join('AC_SUBST([' + x + '])' for x in variables) +
                     '\nAC_CONFIG_FILES([build-tools/krb5-config])\nAC_OUTPUT\n')
        outputs = {}
        for label, host, compiler in (('target', triplet, a.cc), ('native', native, a.native_cc)):
            for state in ('before', 'after'):
                name = label + '-' + state
                src = a.work / name
                shutil.copytree(selected, src)
                patch = a.work / 'baseline-shlib.patch' if state == 'before' else recipe / 'patches/patch-config_shlib.conf'
                run(name + '-patch', ['patch', '-f', '-F', '0', '-p0', '-d', src, '-i', patch])
                run(name + '-template-patch', ['patch', '-f', '-F', '0', '-p0', '-d', src, '-i',
                    recipe / 'patches/patch-build-tools_krb5-config.in'])
                for number, filename in enumerate(('patch-aclocal.m4', 'patch-z-cross-aclocal_m4',
                                                   'patch-zz-libtool-nodelete')):
                    run(name + '-normal-patch-' + str(number),
                        ['patch', '-f', '-F', '0', '-p0', '-d', src, '-i', recipe/'patches'/filename])
                if state == 'after':
                    declarations = '\n'.join(line for line in (recipe / 'Makefile').read_text().splitlines()
                        if re.match(r'SUBST_(?:CLASSES|STAGE\.krb5-rpath|FILES\.krb5-rpath|VARS\.krb5-rpath)', line))
                    require('SUBST_STAGE.krb5-rpath=\tpre-configure' in declarations,
                            'The ordinary recipe must substitute before configure')
                    tools = dict(CMP='/usr/bin/cmp', AWK='/usr/bin/awk', SED='/usr/bin/sed',
                        MV='/bin/mv', RM='/bin/rm -f', TOUCH='/usr/bin/touch', TR='/usr/bin/tr',
                        CHMOD='/bin/chmod', TRUE='/usr/bin/true', FAIL_MSG='/usr/bin/false',
                        INFO_MSG='/bin/echo', WARNING_MSG='/bin/echo', ECHO='/bin/echo', ECHO_SUBST_MSG='/bin/echo')
                    make = src / 'subst-contract.mk'
                    make.write_text('WRKSRC=' + str(src) + '\nWRKDIR=' + str(src) +
                        '\nPKGSRCDIR=' + str(a.pkgsrc) + '\nCOMPILER_RPATH_FLAG=' + a.rpath_flag +
                        '\nRUN=\n' + '\n'.join(k + '=' + v for k,v in tools.items()) + '\n' +
                        declarations + '\n.include "' + str(a.pkgsrc / 'mk/subst.mk') + '"\n')
                    run(name + '-actual-subst', [a.bmake, '-f', make, 'subst-krb5-rpath'])
                    require(b'@COMPILER_RPATH_FLAG@' not in (src / 'config/shlib.conf').read_bytes(),
                            'The compiler marker was not expanded')
                (src / 'configure.ac').write_text(configure)
                run(name + '-autoconf', [a.autoconf], cwd=src)
                flags = ('--sysroot=' + str(a.sysroot) + ' -B' + str(support) + '/') if label == 'target' else (
                    '--sysroot=' + str(a.native_sysroot.resolve(strict=True)) if a.native_sysroot else '')
                local = dict(env, CC=str(compiler), CFLAGS=flags, CPPFLAGS='', LDFLAGS=('-L' + str(runtime)) if label == 'target' else '', LIBS='')
                run(name + '-configure', ['sh', './configure', '--build=' + native, '--host=' + host,
                    '--prefix=/usr/pkg', '--libdir=/usr/pkg/lib', '--enable-pkgsrc-libtool'], cwd=src, environment=local)
                script = src / 'build-tools/krb5-config'
                outputs[name] = run(name + '-libs', ['sh', script, '--libs', 'gssapi'])
        require('${COMPILER_RPATH_FLAG}/usr/pkg/lib' in outputs['target-before'], 'Missing original metadata failure')
        require(outputs['native-before'] == outputs['native-after'], 'Native platform output changed')
        require(a.rpath_flag + '/usr/pkg/lib' in outputs['target-after'] and
                not re.search(r'[$@]', outputs['target-after']), 'Target output contains unresolved metadata')
        flags = ['--sysroot=' + str(a.sysroot), '-B' + str(support) + '/', '-O2', '-g', '-Wall', '-Wextra',
            '-Werror', '-pthread', '-L' + str(runtime), '-I' + str(a.sysroot / 'usr/pkg/include'), '-L' + str(a.sysroot / 'usr/pkg/lib'),
            '-Wl,-rpath-link,' + str(a.sysroot / 'usr/pkg/lib'), '-Wl,-rpath-link,' + str(runtime), '-Wl,-rpath-link,' + str(a.sysroot/'lib'),
            '-Wl,-rpath-link,' + str(a.sysroot/'usr/lib')]
        for state in ('before', 'after'):
            binary = a.work / ('client-' + state)
            run('link-' + state, [a.cc, *flags, here / 'client.c', *shlex.split(outputs['target-' + state]),
                '-o', binary], failure=state == 'before')
        require('${COMPILER_RPATH_FLAG}/usr/pkg/lib' in (a.work/'link-before.stderr').read_text(),
                'Baseline link did not reject the original literal metadata')
        elf = read_elf_dynamic(a.work / 'client-after', machine=183 if triplet.startswith('aarch64') else 62)
        require('libgssapi_krb5.so.2' in elf['needed'], 'Consumer lacks the real GSS provider')
        require(elf['rpath'] == '/usr/pkg/lib' or elf['runpath'] == '/usr/pkg/lib', 'Consumer runtime path differs')
        require(initial == {str(x):sha256_file(x.resolve(strict=True)) for x in inputs},
                'An input changed during qualification')
        write_json(a.work/'receipt.json', dict(sdk_source=sdk, outputs=outputs, commands=commands,
            input_sha256=initial,
            generated_sha256={str(x.relative_to(a.work)):sha256_file(x)
                for label in ('target', 'native') for state in ('before', 'after')
                for rel in ('configure', 'config/shlib.conf', 'aclocal.m4', 'build-tools/krb5-config')
                for x in [a.work/(label+'-'+state)/rel]},
            client_sha256=sha256_file(a.work/'client-after'), client_elf=elf,
            boundary='Actual library-policy macros and full krb5-config template; metadata generation and cross link only. Native output equality, no native package or new target runtime acceptance. Unchanged previously analysed client.c.'))
        (a.work/'incomplete').unlink()
        print('PASS: target metadata repair, native output equality, baseline link refusal, repaired consumer link')
    except ProcessOwnershipError:
        (a.work/'producer-ownership-unconfirmed').write_text('Retain this work. Producer exit is not proven.\n')
        raise


if __name__ == '__main__':
    install_signal_handlers()
    try:
        main()
    except Exception as error:
        exit_error(error)
