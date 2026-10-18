#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise partition selection and refusal using the real complete MIT stage."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
from sdk_source import load_sdk


def main():
    sdk, args = load_sdk()
    from emberbsd_sdk.inventory import snapshot_tree
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('stage', 'full', 'runtime', 'devel', 'selector', 'work'):
        parser.add_argument('--' + name, required=True, type=Path)
    arg = parser.parse_args(args)
    if any(not p.is_absolute() for p in vars(arg).values()) or arg.work.exists():
        raise ValueError('Use absolute paths and unused work')
    arg.work.mkdir()
    for case in ('runtime', 'devel', 'unlisted', 'missing', 'overlap', 'incomplete-union',
                 'runtime-sdk-link', 'absolute-link', 'cyclic-link', 'parent-symlink'):
        work = arg.work / case
        stage = work / 'stage'
        work.mkdir()
        shutil.copytree(arg.stage, stage, symlinks=True)
        lists = []
        for name in ('full', 'runtime', 'devel'):
            path = work / (name + '.plist')
            shutil.copyfile(getattr(arg, name), path)
            lists.append(path)
        if case == 'devel':
            for name in ('kadmind', 'kdc'):
                (stage / 'share/examples/rc.d' / name).unlink()
        if case == 'unlisted':
            (stage / 'unexpected').write_text('must refuse before deletion')
        elif case == 'missing':
            (stage / 'bin/kinit').unlink()
        elif case == 'overlap':
            with lists[2].open('a') as output:
                output.write('bin/kinit\n')
        elif case == 'incomplete-union':
            lists[1].write_text(lists[1].read_text().replace('bin/kinit\n', ''))
        elif case in ('runtime-sdk-link', 'absolute-link', 'cyclic-link'):
            link = stage / 'lib/libkrb5.so'
            link.unlink()
            link.symlink_to({'runtime-sdk-link':'libkrb5.a', 'absolute-link':'/etc/passwd',
                             'cyclic-link':'libkrb5.so'}[case])
        selected_stage = stage
        if case == 'parent-symlink':
            (work / 'alias').symlink_to(work, target_is_directory=True)
            selected_stage = work / 'alias/stage'
        # A stable snapshot also proves no partial deletion on each refusal.
        # Invalid links cannot use snapshot_tree, so retain their full tar bytes.
        def identity():
            rows = {}
            for path in sorted(stage.rglob('*')):
                rel = str(path.relative_to(stage))
                rows[rel] = ('link', path.readlink().as_posix()) if path.is_symlink() else (
                    ('file', path.read_bytes()) if path.is_file() else ('dir',))
            return rows
        before = identity()
        command = [sys.executable, str(arg.selector), '--sdk-source', sdk,
                   'devel' if case == 'devel' else 'runtime', str(selected_stage), *map(str, lists)]
        with (work / 'result.log').open('wb') as output:
            result = subprocess.run(command, stdout=output, stderr=output, timeout=60)
        if case in ('runtime', 'devel'):
            if result.returncode != 0:
                raise ValueError('Real-stage acceptance failed: ' + case)
            snapshot_tree(stage)
        elif result.returncode == 0 or identity() != before:
            raise ValueError('Refusal changed the stage or succeeded: ' + case)
        print('PASS: ' + case, flush=True)


if __name__ == '__main__':
    main()
