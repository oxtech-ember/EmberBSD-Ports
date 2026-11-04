#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Test relocated stdbuf with the producer prefix inaccessible on Darwin.

Arguments: staged gstdbuf, staged libstdbuf.so, native prefix, SDKROOT.
The selected native Clang builds a small child whose first line must be flushed
before it exits.  The test uses an isolated temporary prefix and sandbox-exec.
"""
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile

stdbuf, library, producer, sdkroot = (Path(x).resolve(strict=True) for x in sys.argv[1:])
if sys.platform != 'darwin':
    raise SystemExit('This producer-denial regression currently requires Darwin sandbox-exec')
cc = producer / 'bin/clang'
sandbox = Path('/usr/bin/sandbox-exec')
if not cc.is_file() or not sandbox.is_file():
    raise SystemExit('select the native Ports compiler and Darwin sandbox-exec')
with tempfile.TemporaryDirectory(prefix='ember-stdbuf-', dir='/private/tmp') as tmp:
    work = Path(tmp)
    prefix = work / 'sdk'
    for path in ('bin', 'lib', 'libexec/coreutils', 'gnu/bin'):
        (prefix / path).mkdir(parents=True, exist_ok=True)
    shutil.copy2(stdbuf, prefix / 'bin/gstdbuf')
    shutil.copy2(library, prefix / 'libexec/coreutils/libstdbuf.so')
    shutil.copy2((producer / 'lib/libintl.8.dylib').resolve(strict=True), prefix / 'lib/libintl.8.dylib')
    (prefix / 'gnu/bin/stdbuf').symlink_to('../../bin/gstdbuf')
    (work / 'external-stdbuf').symlink_to(prefix / 'bin/gstdbuf')
    child_source = work / 'child.c'
    child = work / 'child'
    child_source.write_text('#include <stdio.h>\n#include <unistd.h>\nint main(void) { puts("ready"); sleep(2); puts("done"); return 0; }\n')
    subprocess.run([str(cc), '--ld-path=' + str(producer / 'bin/ld64.lld'), '-isysroot',
                    str(sdkroot), str(child_source), '-o', str(child)], check=True,
                   env={'PATH': str(producer / 'bin'), 'LC_ALL': 'C', 'TMPDIR': str(work)})
    # Prove that the sandbox really denies access to the producer prefix.
    escaped = str(producer).replace('\\', '\\\\').replace('"', '\\"')
    profile = '(version 1)(allow default)(deny file-read* (subpath "' + escaped + '"))'
    check = subprocess.run([str(sandbox), '-p', profile, '/bin/cat', str(producer / 'bin/gstdbuf')],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if check.returncode == 0:
        raise AssertionError('producer prefix was not denied')

    def command(executable, *, deny=True, cwd=work, path=None):
        args = [str(sandbox), '-p', profile] if deny else []
        args += ['/usr/bin/env', 'LC_ALL=C', 'DYLD_LIBRARY_PATH=' + str(prefix / 'lib'),
                 'PATH=' + (path if path is not None else str(prefix / 'bin') + ':/usr/bin:/bin'),
                 str(executable), '-oL', str(child)]
        return args, cwd

    def flushed(executable, *, cwd=work, path=None):
        args, directory = command(executable, cwd=cwd, path=path)
        process = subprocess.Popen(args, cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            ready, _, _ = select.select([process.stdout], [], [], 1.5)
            if not ready or process.stdout.readline() != b'ready\n':
                if process.poll() is not None:
                    raise AssertionError(f'child exited {process.returncode}: {process.stderr.read()!r}')
                raise AssertionError(f'line was not flushed before child exit: {args}')
            rest, err = process.communicate(timeout=5)
            if process.returncode or rest != b'done\n':
                raise AssertionError(f'child failed: {process.returncode} {rest!r} {err!r}')
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

    cases = [('absolute', prefix / 'bin/gstdbuf', work, None),
             ('relative', Path('sdk/bin/gstdbuf'), work, None),
             ('path', 'gstdbuf', work, str(prefix / 'bin') + ':/usr/bin:/bin'),
             ('empty-path', 'gstdbuf', prefix / 'bin', ':/usr/bin:/bin'),
             ('gnu-symlink', prefix / 'gnu/bin/stdbuf', work, None),
             ('external-symlink', work / 'external-stdbuf', work, None)]
    for name, executable, cwd, path in cases:
        flushed(executable, cwd=cwd, path=path)
        print(name, 'PASS', flush=True)

    # No fallback to a producer that actually exists and is accessible.
    shared = prefix / 'libexec/coreutils/libstdbuf.so'
    shared.rename(prefix / 'libexec/coreutils/hidden')
    args, cwd = command(prefix / 'bin/gstdbuf', deny=False)
    result = subprocess.run(args, cwd=cwd, capture_output=True)
    if result.returncode == 0 or b'failed to find' not in result.stderr:
        raise AssertionError(f'missing library unexpectedly accepted: {result.stderr!r}')
    print('missing library with producer present PASS', flush=True)

    # Upstream's build-tree layout keeps its support library beside stdbuf.
    shutil.copy2(prefix / 'libexec/coreutils/hidden', prefix / 'bin/libstdbuf.so')
    flushed(prefix / 'bin/gstdbuf')
    print('uninstalled sibling library PASS', flush=True)
