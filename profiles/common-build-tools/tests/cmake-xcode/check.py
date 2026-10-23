#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Compile the complete CMake Xcode TU with its actual native GCC16 arguments."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('sdk-source', 'compile-commands', 'baseline', 'candidate',
                'cxx', 'output', 'lock-root'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--read-root', type=Path, action='append', required=True)
    args = parser.parse_args()
    assert sys.platform == 'darwin' and not os.path.lexists(args.output)
    inputs = [Path(__file__), args.compile_commands, args.baseline, args.candidate]
    for path in [*inputs, args.cxx, args.sdk_source, *args.read_root]:
        assert path.is_absolute() and path.exists(), str(path)
    sys.path.insert(0, str(args.sdk_source / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk.process import ContextLocks
    from emberbsd_sdk.stream import capture_streamed
    from emberbsd_sdk.errors import CommandError
    assert emberbsd_sdk.API_VERSION == 1
    assert Path(emberbsd_sdk.__file__).resolve().parent == (args.sdk_source / 'src/emberbsd_sdk').resolve()

    def interrupt(number, frame):
        raise SystemExit(128 + number)
    for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(number, interrupt)
    with ContextLocks([str(args.output)], str(args.lock_root)), ContextLocks(
            [str(p) for p in [args.sdk_source, *args.read_root]],
            str(args.lock_root), shared=True):
        args.output.mkdir()
        (args.output / 'tmp').mkdir()
        env = dict(os.environ, TMPDIR=str(args.output / 'tmp'),
                   TMP=str(args.output / 'tmp'), TEMP=str(args.output / 'tmp'))
        pins = {str(p): sha(p) for p in inputs}
        before, after = args.baseline.read_bytes(), args.candidate.read_bytes()
        old = b'#    include <ApplicationServices/ApplicationServices.h>'
        new = b'#    include <CoreServices/../Frameworks/LaunchServices.framework/Headers/LSOpen.h>'
        assert before.count(old) == 1 and after == before.replace(old, new)
        entries = json.loads(args.compile_commands.read_text())
        assert len(entries) == 1
        entry = entries[0]
        argv = entry['arguments']
        assert argv[0] == str(args.cxx) and argv.count('-c') == argv.count('-o') == 1
        i, j = argv.index('-c'), argv.index('-o')
        assert Path(entry['file']).name == 'cmGlobalXCodeGenerator.cxx'
        assert argv[i + 1] == entry['file'] and '-DCMAKE_BOOTSTRAP' not in argv
        flags = [v for k, v in enumerate(argv[1:], 1) if k not in (i, i + 1, j, j + 1)]
        commands = []

        def run(name, command, expected=0):
            try:
                result = capture_streamed(command, cwd=entry['directory'], env=env,
                                          stdout_limit=1024 * 1024, timeout=180)
                code, out, err = 0, result.value, result.stderr
                assert not result.stderr_truncated
            except CommandError as error:
                code, out, err = error.returncode, error.stdout, error.stderr
                assert not error.stdout_truncated and not error.stderr_truncated
            (args.output / (name + '.stdout')).write_bytes(out)
            (args.output / (name + '.stderr')).write_bytes(err)
            commands.append({'name': name, 'argv': command, 'exit': code,
                             'stdout_sha256': hashlib.sha256(out).hexdigest(),
                             'stderr_sha256': hashlib.sha256(err).hexdigest()})
            save(args.output / (name + '.json'), commands[-1])
            assert (code != 0 if expected is None else code == expected), name
            return out, err

        version, _ = run('compiler', [str(args.cxx), '-dumpfullversion'])
        assert version.strip().startswith(b'16.')
        _, error = run('before', [str(args.cxx), *flags, '-fsyntax-only', str(args.baseline)], None)
        assert any(v in error for v in (b'xpc.h:', b'MDItem.h:', b'CGPath.h:'))
        obj = args.output / 'xcode.o'
        run('after', [str(args.cxx), *flags, '-c', str(args.candidate), '-o', str(obj)])
        out, _ = run('retained-api', ['/usr/bin/nm', '-u', str(obj)])
        assert b'_LSOpenCFURLRef' in out
        assert all(sha(p) == digest for p, digest in pins.items())
        save(args.output / 'result.json', {'status': 'PASS', 'commands': commands,
             'source_sha256': pins, 'object_sha256': sha(obj),
             'limits': 'Native full-module compile and API reference only. No GUI, full CMake suite, old SDK or memory-safety acceptance.'})


if __name__ == '__main__':
    main()
