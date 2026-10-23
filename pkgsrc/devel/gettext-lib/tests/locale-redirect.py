#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check GCC16 locale redirection with matching generated Darwin headers."""
import argparse
import hashlib
import json
import os
import signal
import time
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def ownership_hold(error, work):
    """Keep both context leases until the owner reviews an unproven drain."""
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, signal.SIG_IGN)
    try:
        (work / 'OWNERSHIP-HOLD.json').write_text(json.dumps(dict(
            status='OWNERSHIP-HOLD', type=type(error).__name__, sid=error.sid,
            error=str(error), action='Preserve work and both context leases.')) + '\n')
    except BaseException:
        pass
    while True:
        try:
            time.sleep(30)
        except BaseException:
            pass

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('before-header', 'fixed-header', 'prefix', 'apple-sdk',
                 'sdk-root', 'obj-root', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--compiler', default='gcc-16')
    parser.add_argument('--cxx-compiler', default='g++-16')
    args = parser.parse_args()
    if sys.platform != 'darwin' or sys.version_info[:2] != (3, 15):
        parser.error('This native test requires Darwin and Python 3.15')
    for name in ('before_header', 'fixed_header', 'prefix', 'apple_sdk',
                 'sdk_root', 'obj_root'):
        path = getattr(args, name)
        assert path.is_absolute() and path.resolve(strict=True) == path, name
    work = args.work
    assert work.is_absolute() and work.resolve() == work
    assert work.is_relative_to(args.obj_root) and not os.path.lexists(work)
    source = Path(__file__).with_name('locale-redirect.c')
    pins = {str(p): sha(p) for p in (args.before_header, args.fixed_header, source)}
    compilers = [shutil.which(args.compiler), shutil.which(args.cxx_compiler)]
    assert all(compilers), 'Both GCC16 drivers are required'
    sys.path.insert(0, str(args.sdk_root / 'src'))
    import emberbsd_sdk
    assert emberbsd_sdk.API_VERSION == 1
    assert Path(emberbsd_sdk.__file__).resolve().parent == args.sdk_root / 'src/emberbsd_sdk'
    from emberbsd_sdk import provenance
    sdk_source = provenance.git_source(args.sdk_root)
    from emberbsd_sdk.process import ContextLocks, sanitized_environment
    from emberbsd_sdk.stream import capture_streamed
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
    work.mkdir()
    rows = []
    env = sanitized_environment()
    env.update(SDKROOT=str(args.apple_sdk), TMPDIR=str(work), TMP=str(work), TEMP=str(work))
    def run(label, argv, expected=True):
        argv = list(map(str, argv))
        try:
            result = capture_streamed(argv, env=env, timeout=60,
                                      stdout_limit=1048576, stderr_limit=1048576)
            status, output, errors = 0, result.value, result.stderr
            assert not result.stderr_truncated
        except ProcessOwnershipError as error:
            ownership_hold(error, work)
        except CommandError as error:
            status, output, errors = error.returncode, error.stdout, error.stderr
        output = output if isinstance(output, bytes) else str(output).encode()
        errors = errors if isinstance(errors, bytes) else str(errors).encode()
        for suffix, raw in (('stdout', output), ('stderr', errors)):
            (work / (label + '.' + suffix)).write_bytes(raw)
        rows.append(dict(label=label, argv=argv, exit=status,
                         stdout_sha256=sha(work / (label + '.stdout')),
                         stderr_sha256=sha(work / (label + '.stderr'))))
        assert (status == 0) == expected, (label, status, errors.decode(errors='replace'))
        return output, errors
    with ContextLocks([str(args.prefix)], str(args.obj_root), shared=True):
        with ContextLocks([str(work)], str(args.obj_root)):
            provider = (args.prefix / 'lib/libintl.dylib').resolve(strict=True)
            assert provider.is_relative_to(args.prefix)
            pins[str(provider)] = sha(provider)
            for label, compiler in zip(('cc', 'cxx'), compilers):
                version, _ = run(label + '-version', [compiler, '-dumpfullversion'])
                assert version.decode().strip().startswith('16.'), 'GCC16 is required'
            for tag, header in (('before', args.before_header), ('after', args.fixed_header)):
                (work / tag).mkdir()
                (work / tag / 'libintl.h').write_bytes(header.read_bytes())
            common = [compilers[0], '-isysroot', args.apple_sdk, '-O0',
                      '-Wall', '-Wextra', '-Wredundant-decls']
            _, errors = run('before-strict', common + ['-Werror=redundant-decls',
                '-I' + str(work / 'before'), '-c', source, '-o', work / 'before-strict.o'], False)
            assert b'redundant redeclaration' in errors and b'setlocale' in errors and b'newlocale' in errors
            run('before-normal', common + ['-I' + str(work / 'before'), '-c', source, '-o', work / 'before.o'])
            run('after-strict', common + ['-Werror=redundant-decls',
                '-I' + str(work / 'after'), '-c', source, '-o', work / 'after.o'])
            symbols, calls, cpp = [], [], []
            for tag in ('before', 'after'):
                output, _ = run(tag + '-nm', ['/usr/bin/nm', '-u', '-j', work / (tag + '.o')])
                names = set(output.decode().splitlines())
                assert {'_libintl_setlocale', '_libintl_newlocale'} <= names
                symbols.append(names)
                run(tag + '-link', [compilers[0], '-isysroot', args.apple_sdk,
                    work / (tag + '.o'), '-L' + str(args.prefix / 'lib'), '-lintl', '-o', work / (tag + '-program')])
                output, _ = run(tag + '-call', [work / (tag + '-program')])
                calls.append(output)
                output, _ = run(tag + '-cplusplus', [compilers[1], '-isysroot', args.apple_sdk,
                    '-x', 'c++', '-E', '-P', '-I' + str(work / tag), source])
                cpp.append(output)
            assert symbols[0] == symbols[1]
            assert calls[0] == calls[1] == b'locale=C; newlocale=C; address-and-call=OK\n'
            assert cpp[0] == cpp[1], 'Native C++ tokens changed'
            assert all(sha(path) == digest for path, digest in pins.items())
            assert provenance.git_source(args.sdk_root) == sdk_source
            result = dict(status='PASS', commands=rows, input_sha256=pins, sdk_source=sdk_source,
                symbols=sorted(symbols[0]), actual_calls_equal=True,
                native_CXX_tokens_equal=True, all_owned_captures_drained=True,
                limits='Native Darwin header/call regression. No prefix installation or target execution.')
            (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', result=str(work / 'result.json'))))

if __name__ == '__main__':
    main()
