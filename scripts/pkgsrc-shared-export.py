#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Export pkgsrc once for the source owners of one run.

The new directory holds pkgsrc/ and pkgsrc-export.json.  Source owners accept
it with verify-source --pkgsrc-export DIR and refuse it unless the Ports
commit, the pinned pkgsrc commit, the overlay inputs and the patch tool still
match the receipt.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source


def main():
    sdk_source.install_signal_handlers()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', help='new absolute directory for the export and its receipt')
    parser.add_argument('--sdk-source', required=True)
    parser.add_argument('--git', required=True, help='absolute Git inspector')
    parser.add_argument('--patch', required=True, help='absolute patch tool')
    parser.add_argument('--update', action='store_true',
                        help='refresh selected packages and file outputs; unsupported changes fail closed')
    parser.add_argument('--resume', action='store_true', help='resume an interrupted selected update')
    parser.add_argument('--package', action='append', help='selected package to update (repeatable)')
    parser.add_argument('--file', action='append', default=[], help='selected file output to update')
    args = parser.parse_args()
    sdk_source.load_sdk(['--sdk-source', args.sdk_source])
    spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', PORTS / 'scripts/pkgsrc-source-identity.py')
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    if args.update:
        if not args.package:
            parser.error('--update requires --package')
        spec = importlib.util.spec_from_file_location('pkgsrc_shared_update', PORTS / 'scripts/pkgsrc-shared-update.py')
        updater = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(updater)
        receipt = updater.update(args.directory, PORTS, args.git, args.sdk_source, args.patch, args.package, args.file, resume=args.resume)
    else:
        if args.package or args.file or args.resume:
            parser.error('--package and --file require --update')
        receipt = selector.create_shared_export(Path(args.directory), PORTS, args.git, args.sdk_source, args.patch)
    if args.update:
        receipt = {key: receipt[key] for key in ('format', 'version', 'identity')}
    sys.stdout.write(json.dumps(receipt, sort_keys=True) + '\n')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sdk_source.exit_error(error, 'pkgsrc shared export: ')
