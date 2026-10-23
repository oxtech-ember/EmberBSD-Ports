#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); real cross Libtool post-build hook regression.
"""Test the recipe hook. No compiler, configure, package or target program runs."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import sys

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True)
    parser.add_argument('--pkgsrc', required=True, help='Prepared pkgsrc source for the dispatcher template')
    parser.add_argument('--recipe', required=True, help='cross-libtool-fortran Makefile to test')
    parser.add_argument('--baseline-recipe', help='Optional original recipe with the duplicate hook')
    parser.add_argument('--bmake', required=True, help='Absolute native-prefix/bin/bmake path')
    parser.add_argument('--lock-root', required=True, help='Common SDK context-lock directory')
    parser.add_argument('new_output')
    args = parser.parse_args()
    sdk = Path(args.sdk_source).resolve(strict=True)
    sys.path.insert(0, str(sdk / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk import inventory, paths
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError, SDKError
    from emberbsd_sdk.process import ContextLocks, sanitized_environment
    from emberbsd_sdk.stream import capture_streamed

    def require(value, message):
        if not value:
            raise SDKError(message)

    require(emberbsd_sdk.API_VERSION == 1 and
            Path(emberbsd_sdk.__file__).parent == sdk / 'src/emberbsd_sdk', 'Explicit SDK API1 required')
    root = Path(args.pkgsrc).resolve(strict=True)
    recipe = Path(args.recipe).resolve(strict=True)
    bmake = Path(args.bmake)
    require(bmake.is_absolute() and bmake.parent.name == 'bin', 'Use native-prefix/bin/bmake')
    native = bmake.parent.parent.resolve(strict=True)
    require(bmake.resolve(strict=True) == bmake and os.access(bmake, os.X_OK), 'Use a regular native bmake')
    template = root / 'devel/libtool-base/files/shlibtool-fortran.in'
    baseline = Path(args.baseline_recipe).resolve(strict=True) if args.baseline_recipe else None
    sources = [recipe, template, bmake] + ([baseline] if baseline else [])
    require(all(path.is_file() and not path.is_symlink() for path in sources), 'Regular source inputs required')
    output = Path(paths.build_path(args.new_output))
    lock_root = Path(args.lock_root).resolve(strict=True)
    require(lock_root.is_dir(), 'Existing common lock directory required')
    require(paths.entry(output) is None, 'New output directory required')
    fingerprints = {str(path): inventory.sha256_file(path) for path in sources}
    env = sanitized_environment()
    env.update(MAKECONF='/dev/null', TMPDIR=str(output), TMP=str(output), TEMP=str(output))
    tools = {name: shutil.which(name, path='/usr/bin:/bin') for name in ('sed', 'grep', 'chmod', 'mv', 'sh')}
    require(all(tools.values()), 'POSIX sed, grep, chmod, mv and sh are required')
    records = []

    def save(name, value):
        with (output / name).open('x') as handle:
            json.dump(value, handle, indent=2)
            handle.write('\n')

    def interrupt(number, frame):
        raise SystemExit(128 + number)

    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, interrupt)
    readers = sorted(set(map(str, (sdk, root, recipe.parent, native) + ((baseline.parent,) if baseline else ()))))
    try:
        with ContextLocks(readers, str(lock_root), shared=True), ContextLocks([str(output)], str(lock_root)):
            require(paths.entry(output) is None, 'Output appeared before admission')
            output.mkdir()
            cases = [('fixed', recipe, None, 0, True), ('missing-FC', recipe, 'FC', 1, False),
                     ('missing-F77', recipe, 'F77', 1, False)]
            if baseline:
                cases.insert(0, ('original', baseline, None, 0, False))
            for name, source, missing, expected, dispatcher_expected in cases:
                work = output / name
                work.mkdir()
                text = source.read_text()
                start = text.index('.PHONY: fix-libtool')
                stop = text.index('# Do not install the C/C++', start)
                fixture = work / 'libtool'
                fixture.write_text('CC="/target/bin/gcc"\nCC="/target/bin/g++"\n'
                                   'LTCC="/target/bin/gcc"\nCC="/target/bin/gfortran"\n'
                                   '-L/private/buildlink/lib /private/buildlink/lib \n' + ''.join(
                                       '# ### BEGIN LIBTOOL TAG CONFIG: ' + tag + '\n'
                                       for tag in ('FC', 'F77') if tag != missing))
                fixture.chmod(0o755)
                values = dict(WRKSRC=shlex.quote(str(work)), BUILDLINK_DIR='/private/buildlink',
                              CC='/target/bin/gcc', CXX='/target/bin/g++', FC='/target/bin/gfortran',
                              RUN='set -e;', SH=tools['sh'], GNU_CONFIGURE_PREFIX='/accepted/cross-target',
                              FILESDIR=shlex.quote(str(template.parent)))
                values.update({name.upper(): shlex.quote(path) for name, path in tools.items() if name != 'sh'})
                makefile = work / 'hook.mk'
                makefile.write_text(''.join(key + '=' + value + '\n' for key, value in values.items()) + text[start:stop])
                argv = [str(bmake), '-f', str(makefile), 'MAKECONF=/dev/null', 'post-build']
                try:
                    result = capture_streamed(argv, cwd=str(work), env=env, stdout_limit=1024 * 1024,
                                              stderr_limit=1024 * 1024, timeout=60)
                    row = dict(case=name, argv=argv, exit=0, stdout=result.value.decode(), stderr=result.stderr.decode())
                    require(not result.stderr_truncated, 'stderr limit exceeded')
                except CommandError as error:
                    row = dict(case=name, argv=argv, exit=error.returncode,
                               stdout=error.stdout.decode(), stderr=error.stderr.decode())
                    require(not error.stdout_truncated and not error.stderr_truncated, 'Capture limit exceeded')
                records.append(row)
                save(name + '.json', row)
                require(row['exit'] == expected, 'Unexpected hook status: ' + name)
                dispatcher = work / 'shlibtool-fortran'
                require(dispatcher.exists() == dispatcher_expected, 'Wrong dispatcher result: ' + name)
                fixed = fixture.read_text()
                require(all(value in fixed for value in ('CC="gcc"', 'CC="g++"', 'CC="f77"')) and
                        '/private/buildlink' not in fixed, 'fix-libtool prerequisite did not run')
                if dispatcher_expected:
                    require(dispatcher.read_text() == template.read_text().replace('@PREFIX@', '/accepted/cross-target').replace('@SH@', tools['sh']),
                            'Dispatcher differs from the source template')
            require(fingerprints == {str(path): inventory.sha256_file(path) for path in sources}, 'Source changed during checks')
            save('results.json', dict(status='PASS', cases=[row['case'] for row in records], source_sha256=fingerprints,
                                     tools=tools, scope='Extracted real recipe hook and synthetic text inputs only. No configured tags, package, compiler, link or runtime acceptance.'))
    except ProcessOwnershipError:
        # A read-only hook writes only its private output. Release shared readers.
        if output.is_dir():
            save('UNACCEPTED.json', dict(status='Unproven process shutdown. Do not accept this output.'))
        raise


if __name__ == '__main__':
    main()
