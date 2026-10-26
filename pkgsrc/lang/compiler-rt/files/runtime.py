#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Prepare, build and verify the canonical common LLVM runtime stages."""
import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import source as owner


def main(arguments):
    arguments = owner.load_sdk(arguments)
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('--archive', required=True)
    prepare.add_argument('--patch', required=True)
    verify_source = commands.add_parser('verify-source')
    build = commands.add_parser('build')
    for name in ('sysroot', 'os-source', 'host-prefix', 'target-prefix', 'work', 'stage'):
        build.add_argument('--' + name, required=True)
    build.add_argument('--host-compiler-family', choices=('clang', 'gcc'), default='clang')
    build.add_argument('--bootstrap-stage')
    build.add_argument('--jobs', type=int, default=1)
    verify = commands.add_parser('verify')
    verify.add_argument('--stage', required=True)
    verify.add_argument('--base')
    for parser in (build, verify):
        parser.add_argument('--target', choices=('aarch64', 'amd64'), required=True)
        parser.add_argument('--phase', choices=('builtins', 'bootstrap', 'full'), default='full')
    for parser in (prepare, verify_source, build):
        parser.add_argument('--source', required=True)
    for parser in (prepare, verify_source, build, verify):
        parser.add_argument('--git', required=True)
    args = cli.parse_args(arguments)
    if args.command == 'prepare':
        record = owner.prepare_source(args.archive, args.source, args.patch, args.git)
    elif args.command == 'verify-source':
        record = owner.verify_source(args.source, args.git)
    elif args.command == 'build':
        import build as producer
        record = producer.build(owner, args)
    else:
        from emberbsd_sdk import llvm_runtime
        import build as producer
        record = llvm_runtime.validate_stage(args.stage, target=args.target,
            required_components=producer.PROFILES[args.phase], base=args.base)
        # Compare the complete owner contract, not just a caller-provided
        # subset of input hashes. Unrelated commits do not change these inputs.
        current, _ = owner.recipe(args.git)
        expected = producer.effective_recipe(owner, current, args.git)
        owner.require(record['llvm_version'] == current['llvm_version'] and
                      record['source'] == {k: current['source'][k] for k in ('archive', 'sha512')},
                      'runtime source selection changed')
        owner.require(record['recipe']['files'] == expected['files'],
                      'runtime recipe inputs changed')
    print(owner.jsonio.json_bytes(record).decode(), end='')


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as error:
        print('llvm-runtimes: ' + str(error), file=sys.stderr)
        status = getattr(error, 'returncode', 1)
        sys.exit(status if status >= 0 else 128 - status)
