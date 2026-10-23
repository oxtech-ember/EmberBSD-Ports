#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; ordinary pkgsrc Fortran runtime and SDK staging.
import argparse
from pathlib import Path
import sys
sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=('runtime', 'devel'))
    parser.add_argument('action', choices=('check', 'fields', 'plist', 'install'))
    parser.add_argument('work')
    parser.add_argument('archive')
    parser.add_argument('pkgsrc', type=Path)
    parser.add_argument('destination', nargs='?')
    parser.add_argument('--runtime-files', action='append', required=True, type=Path)
    parser.add_argument('--sdk-source', action='append', required=True)
    args = parser.parse_args()
    if len(args.runtime_files) != 1 or len(args.sdk_source) != 1:
        parser.error('Use each explicit source option once')
    shared = args.runtime_files[0]
    if not shared.is_absolute() or shared.resolve(strict=True) != (args.pkgsrc / 'lang/gcc16-runtime/files').resolve(strict=True):
        parser.error('Use the prepared common GCC16 runtime files')
    if (args.action == 'install') != (args.destination is not None):
        parser.error('Only install requires a destination')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(shared))
    import sdk_source
    sdk_source.load(args.sdk_source[0])
    from fortran_stage import Stage
    stage = Stage(args.work, args.archive, args.pkgsrc)
    if args.action == 'install':
        stage.install(args.role, args.destination)
        return
    result, files = stage.payload(args.role)
    if args.action == 'fields':
        for key, value in result['metadata'].items(): print(key + '=' + value)
        print('GCC_FORTRAN_ROLE=' + args.role)
    elif args.action == 'plist':
        print(''.join(name + '\n' for name in files), end='')
    else:
        import json
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('gcc16-fortran: ' + str(error), file=sys.stderr)
        sys.exit(1)
