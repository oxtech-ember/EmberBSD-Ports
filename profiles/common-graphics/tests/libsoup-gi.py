#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the release Soup GIR build description.
"""Inspect real Meson scanner/compiler commands. Do not build or execute Soup."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

sys.dont_write_bytecode = True


def check_commands(run, meson, module, work, native_file, cross_file, env, native_env=None):
    source = module.read_text()
    start = source.index('if enable_introspection or enable_vapi\n')
    end = source.index('  soup_gir_gen_dep =', start)
    block = source[start:end] + 'endif\n'
    work.mkdir()
    project = work / 'project'
    project.mkdir()
    (project / 'probe.c').write_text('int soup_command_probe;\n')
    (project / 'meson.build').write_text(
        "project('libsoup', 'c', version: '3.6.6')\n"
        "gnome = import('gnome')\n"
        "gir = find_program('g-ir-scanner')\n"
        "enable_introspection = true\nenable_vapi = false\n"
        "libsoup = shared_library('soup-3.0', 'probe.c')\n"
        "soup_sources = ['probe.c']\nsoup_introspection_headers = []\n"
        "soup_enum_h = []\nsoup_version_h = []\n"
        "libsoup_dep = dependency('gio-2.0')\n"
        "libsoup_c_args = []\napiversion = '3.0'\nlibsoup_api_name = 'libsoup-3.0'\n" + block)
    commands = {}
    for mode in ('native', 'cross'):
        build = work / mode
        argv = [str(meson), 'setup', str(build), str(project),
                '--native-file', str(native_file), '--wrap-mode=nodownload']
        if mode == 'cross':
            argv += ['--cross-file', str(cross_file)]
        run('meson-' + mode, argv, native_env if mode == 'native' and native_env is not None else env)
        ninja = (build / 'build.ninja').read_text()
        scanner = next(line for line in ninja.splitlines()
                       if 'COMMAND =' in line and '--namespace=Soup' in line)
        compiler = next(line for line in ninja.splitlines()
                        if 'COMMAND =' in line and 'g-ir-compiler' in line)
        assert '--warn-all' in scanner
        assert '--namespace=Soup' in scanner and '--nsversion=3.0' in scanner
        assert 'Soup-3.0.gir' in scanner and 'Soup-3.0.typelib' in compiler
        if mode == 'cross':
            assert '--use-ldd-wrapper=' in scanner
            assert 'LD_LIBRARY_PATH=' in scanner
        else:
            assert '--use-ldd-wrapper=' not in scanner
            assert 'LD_LIBRARY_PATH=' not in scanner
        commands[mode] = {'scanner': scanner, 'compiler': compiler}
    return commands


def ownership_hold(error, output):
    # An unknown session may still write the private output. Retain all leases.
    while True:
        try:
            for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                signal.signal(number, signal.SIG_IGN)
            marker = output / 'QUARANTINED.json'
            if not marker.exists():
                with marker.open('x') as stream:
                    json.dump({'sid': error.sid, 'reason': str(error)}, stream)
                    stream.write('\n')
                    stream.flush()
                    os.fsync(stream.fileno())
        except BaseException:
            pass
        try:
            time.sleep(30)
        except BaseException:
            pass


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for key in ('sdk-source', 'meson', 'module', 'native-file', 'cross-file', 'output'):
        cli.add_argument('--' + key, type=Path, required=True)
    cli.add_argument('--lock-root', type=Path, action='append', required=True)
    cli.add_argument('--read-root', type=Path, action='append', required=True)
    a = cli.parse_args()
    assert not os.path.lexists(a.output)
    inputs = [Path(__file__).resolve(), a.module, a.native_file, a.cross_file]
    for p in [*inputs, a.sdk_source, a.meson, *a.read_root, *a.lock_root]:
        assert p.is_absolute() and p.exists(), str(p)
    sys.path.insert(0, str(a.sdk_source / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk.process import ContextLocks
    from emberbsd_sdk.stream import capture_streamed
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
    assert emberbsd_sdk.API_VERSION == 1
    assert Path(emberbsd_sdk.__file__).resolve().parent == a.sdk_source / 'src/emberbsd_sdk'
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, lambda n, f: sys.exit(128 + n))
    with ExitStack() as stack:
        stack.enter_context(ContextLocks([str(a.output)], str(a.lock_root[0])))
        for root in a.lock_root:
            stack.enter_context(ContextLocks([str(p) for p in [a.sdk_source, *a.read_root]],
                                            str(root), shared=True))
        a.output.mkdir()
        (a.output / 'tmp').mkdir()
        env = dict(os.environ, TMPDIR=str(a.output / 'tmp'), TMP=str(a.output / 'tmp'),
                   TEMP=str(a.output / 'tmp'))
        pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
        commands = []

        def run(name, argv, environment):
            try:
                r = capture_streamed(argv, cwd=str(a.output), env=environment,
                                     stdout_limit=1024 * 1024, timeout=180)
                code, out, err = 0, r.value, r.stderr
                assert not r.stderr_truncated
            except ProcessOwnershipError as error:
                ownership_hold(error, a.output)
            except CommandError as error:
                code, out, err = error.returncode, error.stdout, error.stderr
                assert not error.stdout_truncated and not error.stderr_truncated
            (a.output / (name + '.stdout')).write_bytes(out)
            (a.output / (name + '.stderr')).write_bytes(err)
            commands.append(dict(name=name, argv=argv, exit=code))
            (a.output / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
            assert code == 0, name
            return out, err

        emitted = check_commands(run, a.meson, a.module, a.output / 'commands',
                                 a.native_file, a.cross_file, env)
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in pins.items())
        (a.output / 'result.json').write_text(json.dumps(dict(status='PASS',
            source_sha256=pins, commands=commands, emitted=emitted,
            limits='Release-derived Meson GIR command generation only. Compiler sanity checks run; '
                   'Soup, target queries, TLS and upstream runtime tests do not run.'), indent=2) + '\n')


if __name__ == '__main__':
    main()
