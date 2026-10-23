#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Ported from librsvg-mime-regression.rb.
"""Reproduce isolated SVG MIME omission through the real GI target launcher."""

import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_sdk(source):
    require(source and os.path.isabs(source),
            'set --sdk-source or EMBERBSD_SDK_SOURCE to an absolute SDK source')
    root = Path(source).resolve(strict=True)
    package = root / 'src/emberbsd_sdk'
    require((package / '__init__.py').is_file(), 'SDK source has no emberbsd_sdk API')
    sys.path.insert(0, str(root / 'src'))
    import emberbsd_sdk
    require(type(emberbsd_sdk.API_VERSION) is int and emberbsd_sdk.API_VERSION == 1
            and Path(emberbsd_sdk.__file__).resolve().parent == package.resolve(),
            'the selected SDK must provide API version 1')
    from emberbsd_sdk.errors import CommandError
    from emberbsd_sdk.paths import canonical_existing, canonical_new
    from emberbsd_sdk.process import capture
    return SimpleNamespace(root=str(root), CommandError=CommandError,
                           canonical_existing=canonical_existing,
                           canonical_new=canonical_new, capture=capture)


def main():
    tests = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', default=os.environ.get('EMBERBSD_SDK_SOURCE'))
    parser.add_argument('--source', default=str(tests / 'librsvg-package.c'))
    parser.add_argument('--helper', default=str(tests.parent /
                        '../../pkgsrc/devel/gobject-introspection/files/target-query.py'))
    parser.add_argument('prepared_consumer', metavar='PREPARED_CONSUMER')
    parser.add_argument('new_work', metavar='NEW_WORK')
    options = parser.parse_args()
    require(sys.version_info[:2] == (3, 15), 'use the selected build-host Python 3.15')
    sdk = load_sdk(options.sdk_source)
    python = sdk.canonical_existing(sys.executable)
    consumer, source, helper = map(sdk.canonical_existing,
        (options.prepared_consumer, options.source, options.helper))
    require(os.path.isabs(options.new_work), 'new absolute work required')
    work = Path(sdk.canonical_new(options.new_work))
    require(not os.path.lexists(work), 'new absolute work required')
    work.mkdir(parents=True)
    text = Path(source).read_text(encoding='utf-8')
    normal = 'char *mime_args[] = { "./update-mime-database", "mime", NULL };'
    require(text.count(normal) == 1, 'MIME command changed')
    # Keep both XDG directories private. System data must not mask this omission.
    text = text.replace(normal, 'char *mime_args[] = { "./update-mime-database", "-v", NULL };', 1)
    changed = work / 'missing-mime.c'
    changed.write_text(text, encoding='utf-8')
    command = shlex.split((Path(consumer) / 'compile.command').read_text(encoding='utf-8'))
    require(source in command, 'unexpected consumer compilation')
    require(len(command) >= 2 and command[-2] == '-o', 'unexpected output option')
    command[command.index(source)] = str(changed)
    command[-1] = str(work / 'missing-mime')

    def capture(argv, env=None):
        try:
            return sdk.capture(argv, env=env)
        except sdk.CommandError as error:
            return subprocess.CompletedProcess(argv, error.returncode,
                                               error.stdout, error.stderr)

    result = capture(command)
    (work / 'compile.log').write_bytes(result.stdout + result.stderr)
    require(result.returncode == 0, (result.stdout + result.stderr).decode('utf-8', 'replace'))
    environment = dict(os.environ, EMBERBSD_SDK_SOURCE=sdk.root)
    result = capture([python, '-E', '-S', helper, command[-1]], env=environment)
    output = result.stdout + result.stderr
    (work / 'target.log').write_bytes(output)
    receipt = re.search(rb'target query failed \(1\), (/[^\n]+)\n', output)
    require(result.returncode == 1 and receipt is not None and
            b'FAIL: dynamic GdkPixbuf SVG loader' in output and
            b'(gdk-pixbuf-error-quark:3)' in output,
            'wrong failure: ' + output.decode('utf-8', 'replace'))
    require((Path(os.fsdecode(receipt[1])) / 'cleanup.log').read_bytes().strip() == b'0',
            'remote cleanup failed')
    print('PASS: omitting only MIME generation reproduces the SVG format-detection failure; target cleanup succeeded')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f'error: {error}', file=sys.stderr)
        raise SystemExit(1)
