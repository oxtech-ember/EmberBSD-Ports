#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual pkgsrc substitutions; private host fixtures.
"""Check pkg_alternatives native bytes and NetBSD cross runtime tool paths."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time
sys.dont_write_bytecode = True


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('ports-source', 'pkgsrc-source', 'sdk-source', 'bmake', 'native-conf',
                 'cross-conf', 'native-prefix', 'sysroot', 'lock-root'):
        cli.add_argument('--' + name, required=True, type=Path)
    cli.add_argument('new_output', type=Path)
    a = cli.parse_args()
    for value in vars(a).values():
        if not value.is_absolute():
            cli.error('Use absolute paths')
    sys.path.insert(0, str(a.sdk_source / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError, SDKError
    from emberbsd_sdk.process import ContextLocks, sanitized_environment
    from emberbsd_sdk.stream import capture_streamed
    if emberbsd_sdk.API_VERSION != 1 or Path(emberbsd_sdk.__file__).resolve().parent != (a.sdk_source / 'src/emberbsd_sdk').resolve():
        raise SDKError('Use the explicit SDK API1 source')
    out = a.new_output
    if out.exists() or out.is_symlink() or out.parent.resolve() != out.parent:
        raise SDKError('Use a new canonical output directory')
    recipe = a.pkgsrc_source / 'pkgtools/pkg_alternatives'
    patch = a.ports_source / 'profiles/common-build-tools/patches/pkgsrc-pkg-alternatives-target-runtime.patch'
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    env = sanitized_environment()
    for key in ('MAKECONF', 'MAKEFLAGS', 'MFLAGS', 'MAKELEVEL', 'PKG_DBDIR', 'PKG_PATH'):
        env.pop(key, None)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda number, frame: sys.exit(128 + number))
    with ContextLocks([str(out)], str(a.lock_root)):
        out.mkdir(); (out / 'tmp').mkdir()
        for key in ('TMPDIR', 'TMP', 'TEMP'):
            env[key] = str(out / 'tmp')
        commands = []

        def run(argv, data=None):
            argv = list(map(str, argv))
            try:
                r = capture_streamed(argv, env=env, input=data, timeout=30,
                                     stdout_limit=1048576, stderr_limit=1048576)
                code, stdout, stderr = 0, r.value, r.stderr
                if r.stderr_truncated:
                    raise SDKError('Truncated control output')
            except CommandError as error:
                code, stdout, stderr = error.returncode, error.stdout, error.stderr
                if error.stdout_truncated or error.stderr_truncated:
                    raise SDKError('Truncated failed control output')
            commands.append(dict(argv=argv, exit=code, stdout=stdout.decode(), stderr=stderr.decode()))
            (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
            if code != 0:
                raise SDKError('Control command failed: ' + str(code))
            return stdout

        shared = [a.ports_source, a.pkgsrc_source, a.sdk_source, a.native_prefix,
                  a.sysroot, a.native_conf, a.cross_conf]
        try:
            with ContextLocks(list(map(str, shared)), str(a.lock_root), shared=True):
                after = out / 'after/pkgtools/pkg_alternatives'
                shutil.copytree(recipe, after)
                run(['/usr/bin/patch', '-f', '-F', '0', '-p1', '-d', out / 'after', '-i', patch])
                runtime = out / 'runtime'; (runtime / 'data').mkdir(parents=True)
                shutil.copyfile(recipe / 'files/wrapper.sh', runtime / 'data/wrapper.sh')
                fields = ['PKGNAME', 'OPSYS', 'USE_CROSS_COMPILE', 'SH', 'ID', 'SUBST_VARS.vars',
                          'SUBST_SED.vars', 'SUBST_FILTER_CMD.vars', 'CHECK_INTERPRETER', 'CHECK_INTERPRETER_SKIP', 'PKG_FAIL_REASON']
                results = {}
                for mode, conf in [('native', a.native_conf), ('cross', a.cross_conf)]:
                    for phase, makefile in [('before', recipe / 'Makefile'), ('after', after / 'Makefile')]:
                        work = out / (mode + '-' + phase); work.mkdir()
                        argv = [a.bmake, '-C', recipe, '-I', recipe, '-f', makefile,
                                'MAKECONF=' + str(conf), 'WRKDIR=' + str(work), '_MAKEVARS_MK=defined', 'PKG_DEVELOPER=yes',
                                'DATADIR=' + str(runtime / 'data'), 'DBDIR=' + str(runtime / 'db'),
                                'PKG_SYSCONFDIR=' + str(runtime / 'etc')]
                        raw = run(argv + [x for key in fields for x in ('-v', key)])
                        lines = raw.decode().splitlines()
                        if len(lines) != len(fields):
                            raise SDKError('Unexpected metadata field count')
                        v = dict(zip(fields, lines))
                        if v['PKG_FAIL_REASON'] or v['CHECK_INTERPRETER'].lower() != 'yes':
                            raise SDKError('Package refused or interpreter check disabled')
                        if mode == 'cross' and (v['OPSYS'], v['USE_CROSS_COMPILE'].lower()) != ('NetBSD', 'yes'):
                            raise SDKError('Use a real NetBSD cross configuration')
                        text = run([v['SH'], '-c', v['SUBST_FILTER_CMD.vars']], (recipe / 'files/pkg_alternatives.sh').read_bytes())
                        (work / 'pkg_alternatives.sh').write_bytes(text)
                        run([v['SH'], '-n', work / 'pkg_alternatives.sh'])
                        run([v['SH'], work / 'pkg_alternatives.sh', '-s', '-w', '-p', runtime / 'prefix',
                             'register', 'bin/probe', '/usr/bin/true'])
                        wrapper = runtime / 'prefix/bin/probe'
                        generated = wrapper.read_bytes(); (work / 'generated-wrapper').write_bytes(generated)
                        wrapper.unlink()  # Exact private generated leaf; all bytes retained above.
                        results[mode + '-' + phase] = dict(metadata=v, main_sha256=sha(work / 'pkg_alternatives.sh'),
                                                          wrapper_sha256=sha(work / 'generated-wrapper'))
                        if mode == 'cross' and phase == 'after':
                            if not text.startswith(b'#!/bin/sh\n') or not generated.startswith(b'#!/bin/sh\n'):
                                raise SDKError('Cross runtime shebang differs')
                            if str(a.native_prefix).encode() in text + generated or b'@SH@' in text or b'@ID@' in text:
                                raise SDKError('Cross runtime keeps a native tool or placeholder')
                            if 'SH' in v['SUBST_VARS.vars'].split() or 'ID' in v['SUBST_VARS.vars'].split():
                                raise SDKError('Overlapping host substitutions remain')
                for key in ('main_sha256', 'wrapper_sha256'):
                    if results['native-before'][key] != results['native-after'][key]:
                        raise SDKError('Native runtime bytes changed')
                if results['cross-before']['main_sha256'] == results['cross-after']['main_sha256']:
                    raise SDKError('Baseline did not expose distinct host shell paths')
                (out / 'result.json').write_text(json.dumps(dict(status='PASS', cases=results, patch_sha256=sha(patch),
                    limits='Real recipe metadata and substitutions; private host wrapper creation only. '
                           'No package, compiler, target ELF execution or prefix/database mutation.'), indent=2) + '\n')
        except ProcessOwnershipError as error:
            # Commands can write only private fixtures. Release shared inputs, quarantine output.
            while True:
                try:
                    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                        signal.signal(sig, signal.SIG_IGN)
                except BaseException:
                    pass
                try:
                    (out / 'OWNERSHIP-HOLD.json').write_text(json.dumps(dict(sid=getattr(error, 'sid', None), reason=str(error), output_EX_retained=True)) + '\n')
                except BaseException:
                    pass
                try:
                    time.sleep(30)
                except BaseException:
                    pass
    print('PASS: native bytes unchanged; NetBSD cross script and wrappers use target tools')


if __name__ == '__main__':
    main()
