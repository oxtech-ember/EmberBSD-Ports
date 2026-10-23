#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the actual WebKit pre-project SDK gate and Apple SDK module."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'cmake', 'patch', 'apple-sdk', 'sdk-source', 'output'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--lock-root', type=Path, action='append', required=True)
    cli.add_argument('--read-root', type=Path, action='append', required=True)
    a = cli.parse_args()
    assert sys.platform == 'darwin' and not os.path.lexists(a.output)
    for p in (a.source, a.cmake, a.patch, a.apple_sdk, a.sdk_source,
              *a.lock_root, *a.read_root):
        assert p.is_absolute() and p.exists(), str(p)
    repo = Path(__file__).resolve().parents[3]
    patch = repo / 'pkgsrc/www/webkit-gtk41/patches/patch-CMakeLists.txt'
    inputs = [a.source / 'CMakeLists.txt',
              a.source / 'Source/cmake/WebKitXcodeSDK.cmake', patch, Path(__file__)]
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    pins = {str(p): sha(p) for p in inputs}
    sys.path.insert(0, str(a.sdk_source / 'src'))
    import emberbsd_sdk
    from contextlib import ExitStack
    from emberbsd_sdk.process import ContextLocks
    from emberbsd_sdk.stream import capture_streamed
    from emberbsd_sdk.errors import CommandError
    assert emberbsd_sdk.API_VERSION == 1
    assert Path(emberbsd_sdk.__file__).resolve().parent == a.sdk_source / 'src/emberbsd_sdk'
    commands = []
    with ExitStack() as stack:
        for root in a.lock_root:
            stack.enter_context(ContextLocks([str(p) for p in
                [a.sdk_source, a.source, repo, *a.read_root]], str(root), shared=True))
        stack.enter_context(ContextLocks([str(a.output)], str(a.lock_root[0])))
        a.output.mkdir()
        (a.output / 'tmp').mkdir()
        env = dict(os.environ, PATH='/usr/bin:/bin', TMPDIR=str(a.output / 'tmp'),
                   TMP=str(a.output / 'tmp'), TEMP=str(a.output / 'tmp'))

        def run(name, argv, cwd, expected):
            try:
                r = capture_streamed(argv, cwd=str(cwd), env=env,
                                     stdout_limit=1048576, timeout=60)
                code, out, err = 0, r.value, r.stderr
                assert not r.stderr_truncated
            except CommandError as e:
                code, out, err = e.returncode, e.stdout, e.stderr
                assert not e.stdout_truncated and not e.stderr_truncated
            (a.output / (name + '.stdout')).write_bytes(out)
            (a.output / (name + '.stderr')).write_bytes(err)
            commands.append(dict(name=name, argv=argv, exit=code,
                                 stdout_sha256=hashlib.sha256(out).hexdigest(),
                                 stderr_sha256=hashlib.sha256(err).hexdigest()))
            assert code == expected, (name, code)
            return out, err

        native_results = {}
        for label in ('before', 'after'):
            source = a.output / label
            (source / 'Source/cmake').mkdir(parents=True)
            for p in inputs[:2]:
                q = source / p.relative_to(a.source)
                q.write_bytes(p.read_bytes())
            if label == 'after':
                out, err = run('patch', [str(a.patch), '-f', '-F', '0', '-p1',
                                       '-i', str(patch)], source, 0)
                assert b'offset' not in out + err and b'fuzz' not in out + err
            top = (source / 'CMakeLists.txt').read_text()
            prefix, sep, _ = top.partition('project(WebKit LANGUAGES C CXX)')
            assert sep and prefix.count('include(WebKitXcodeSDK)') == 1
            script = source / 'probe.cmake'
            script.write_text(prefix + '\nif(COMMAND WEBKIT_RESOLVE_SDK)\n'
                '  message(STATUS "EMBER-SDK-GATE=selected")\nelse()\n'
                '  message(STATUS "EMBER-SDK-GATE=skipped")\nendif()\n')
            for name, port, target in (
                    ('GTK-NetBSD', 'GTK', 'NetBSD'), ('WPE-NetBSD', 'WPE', 'NetBSD'),
                    ('GTK-Darwin', 'GTK', 'Darwin'), ('WPE-Darwin', 'WPE', 'Darwin'),
                    ('Mac', 'Mac', ''), ('JSCOnly', 'JSCOnly', ''), ('default', '', '')):
                args = [str(a.cmake), '-DPORT=' + port]
                if target:
                    args += ['-DCMAKE_SYSTEM_NAME=' + target]
                if target != 'NetBSD':
                    args += ['-DCMAKE_OSX_SYSROOT=' + str(a.apple_sdk)]
                expected = 1 if label == 'before' and target == 'NetBSD' else 0
                out, err = run(label + '-' + name,
                               args + ['-P', str(script)], source, expected)
                if expected:
                    assert b'Building for an Apple platform without an SDK' in err
                else:
                    marker = b'skipped' if target == 'NetBSD' else b'selected'
                    assert b'EMBER-SDK-GATE=' + marker in out
                    if marker == b'selected':
                        assert str(a.apple_sdk).encode() in out
                        if label == 'before':
                            native_results[name] = (out, err)
                        else:
                            assert native_results[name] == (out, err)
        assert all(sha(Path(p)) == h for p, h in pins.items())
        (a.output / 'result.json').write_text(json.dumps(dict(status='PASS',
            source_sha256=pins, commands=commands,
            limits='Fourteen real pre-project CMake script executions on Darwin. '
            'The actual Apple SDK module and output are retained for native GTK/WPE, '
            'Mac, JSCOnly and default. '
            'No compiler, full WebKit configuration, package or target execution.'), indent=2) + '\n')


if __name__ == '__main__':
    main()
