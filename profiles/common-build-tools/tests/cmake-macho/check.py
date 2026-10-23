#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check the real CMake Mach-O TU with a GCC16 bootstrap compilation entry."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import sys
import time

sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def thin(cpu, subtype, commands=b''):
    return struct.pack('<8I', 0xfeedfacf, cpu, subtype,
                       6 if commands else 1, bool(commands), len(commands), 0, 0) + commands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'compile-commands', 'baseline', 'candidate',
                 'cxx', 'sysroot', 'output', 'lock-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--read-root', type=Path, action='append', required=True)
    args = parser.parse_args()
    assert sys.platform == 'darwin' and not os.path.lexists(args.output)
    for path in (args.sdk_source, args.compile_commands, args.baseline,
                 args.candidate, args.cxx, args.sysroot, *args.read_root):
        assert path.is_absolute() and path.exists(), str(path)
    sys.path.insert(0, str(args.sdk_source / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk.process import ContextLocks
    from emberbsd_sdk.stream import capture_streamed
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
    assert emberbsd_sdk.API_VERSION == 1
    assert Path(emberbsd_sdk.__file__).resolve().parent == (args.sdk_source / 'src/emberbsd_sdk').resolve()

    def interrupted(number, frame):
        raise SystemExit(128 + number)
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, interrupted)

    with ContextLocks([str(args.output)], str(args.lock_root)):
        try:
            with ContextLocks([str(p) for p in args.read_root] +
                              [str(args.sdk_source)], str(args.lock_root), shared=True):
                args.output.mkdir()
                (args.output / 'tmp').mkdir()
                env = dict(os.environ, SDKROOT=str(args.sysroot),
                           TMPDIR=str(args.output / 'tmp'), TMP=str(args.output / 'tmp'),
                           TEMP=str(args.output / 'tmp'))
                entries = json.loads(args.compile_commands.read_text())
                assert len(entries) == 1
                entry = entries[0]
                argv = entry['arguments']
                assert all(isinstance(v, str) and v for v in argv)
                assert argv.count('-c') == argv.count('-o') == 1
                i = argv.index('-c')
                assert argv[i + 1] == entry['file'] and Path(entry['file']).name == 'cmMachO.cxx'
                j = argv.index('-o')
                flags = [v for k, v in enumerate(argv[1:], 1) if k not in (i, i + 1, j, j + 1)]
                driver = Path(__file__).with_name('driver.cxx')
                inputs = [Path(__file__), driver, args.baseline, args.candidate, args.compile_commands]
                pins = {str(p): sha(p) for p in inputs}
                save(args.output / 'inputs.json', {'sha256': pins, 'entry': entry,
                     'cxx': str(args.cxx), 'sysroot': str(args.sysroot),
                     'limits': 'Native module regression. No full CMake package or memory-safety claim.'})
                commands = []

                def run(label, command, expected=0):
                    start = time.monotonic()
                    try:
                        result = capture_streamed(command, cwd=entry['directory'], env=env,
                                                  stdout_limit=1024*1024, timeout=120)
                        code, out, err = 0, result.value, result.stderr
                        assert not result.stderr_truncated
                    except CommandError as error:
                        assert not error.stdout_truncated and not error.stderr_truncated
                        code, out, err = error.returncode, error.stdout, error.stderr
                    (args.output / (label + '.stdout')).write_bytes(out)
                    (args.output / (label + '.stderr')).write_bytes(err)
                    commands.append({'label': label, 'argv': command, 'exit': code,
                                     'seconds': time.monotonic()-start,
                                     'stdout_sha256': hashlib.sha256(out).hexdigest(),
                                     'stderr_sha256': hashlib.sha256(err).hexdigest()})
                    save(args.output / (label + '.json'), commands[-1])
                    assert (code != 0 if expected is None else code == expected), label
                    return out, err

                version, _ = run('compiler', [str(args.cxx), '-dumpfullversion'])
                assert version.strip().startswith(b'16.')
                _, error = run('before-modern', [str(args.cxx), *flags, '-fsyntax-only',
                                                str(args.baseline)], None)
                assert b'__builtin_available' in error
                arm = thin(0x0100000c, 0)
                x86 = thin(0x01000007, 3)
                fat = struct.pack('>2I10I', 0xcafebabe, 2,
                                  0x0100000c, 0, 4096, len(arm), 12,
                                  0x01000007, 3, 8192, len(x86), 12)
                fat += bytes(4096-len(fat)) + arm
                fat += bytes(8192-len(fat)) + x86
                name = b'libprobe.dylib\0'
                command = struct.pack('<6I', 0xd, 40, 24, 0, 0, 0) + name
                command += bytes(40-len(command))
                fixtures = {
                    'arm64': (arm, b'arm64\n', 0),
                    'arm64e': (thin(0x0100000c, 2), b'arm64e\n', 0),
                    'x86_64': (x86, b'x86_64\n', 0),
                    'fat': (fat, b'arm64\nx86_64\n', 0),
                    'unknown': (thin(0x010000ff, 0), b'unknown\n', 0),
                    'dylib': (thin(0x0100000c, 0, command), b'arm64\ninstall=libprobe.dylib\n', 0),
                    'invalid': (b'bad!', b'invalid\n', 2),
                    'truncated': (arm[:12], b'invalid\n', 2),
                }
                for name, (data, expected, code) in fixtures.items():
                    (args.output / (name + '.macho')).write_bytes(data)
                for name in ('arm64', 'arm64e', 'x86_64', 'fat'):
                    out, _ = run('lipo-' + name, ['/usr/bin/lipo', '-archs', str(args.output / (name+'.macho'))])
                    assert out.split() == fixtures[name][1].split()
                for label, source, extra in (
                        ('after-modern', args.candidate, []),
                        ('before-pre13', args.baseline, ['-mmacosx-version-min=12.0']),
                        ('after-pre13', args.candidate, ['-mmacosx-version-min=12.0'])):
                    binary = args.output / label
                    run(label, [str(args.cxx), *flags, *extra, str(source), str(driver), '-o', str(binary)])
                    for name, (data, expected, code) in fixtures.items():
                        out, _ = run(label+'-'+name, [str(binary), str(args.output/(name+'.macho'))], code)
                        assert out == expected, (label, name, out, expected)
                assert all(sha(p) == digest for p, digest in pins.items())
                save(args.output / 'result.json', {'status': 'PASS', 'commands': commands,
                     'fixture_cases': len(fixtures), 'module_variants': 3, 'pins': pins,
                     'limits': 'The pre-13 path executes on the current host. No old-OS execution, full CMake suite, Valgrind or memory-safety acceptance.'})
        except ProcessOwnershipError as error:
            for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                try:
                    signal.signal(number, signal.SIG_IGN)
                except BaseException:
                    pass
            try:
                save(args.output / 'QUARANTINED.json', {'sid': error.sid, 'reason': str(error)})
            except BaseException:
                pass
            # Release input SH before retaining only this private output EX.
            while True:
                try:
                    time.sleep(30)
                except BaseException:
                    pass


if __name__ == '__main__':
    main()
