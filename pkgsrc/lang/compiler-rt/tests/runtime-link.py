#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Link the runtime consumers with real staged headers and libraries."""
import argparse
import importlib.util
from pathlib import Path
import sys

sys.dont_write_bytecode = True
FILES = Path(__file__).resolve().parents[1] / 'files'


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


owner = module(FILES / 'source.py', 'runtime_link_source')
arguments = owner.load_sdk(sys.argv[1:])
producer = module(FILES / 'build.py', 'runtime_link_builder')
from emberbsd_sdk import host_prefix, target_toolchain, targets

cli = argparse.ArgumentParser(description=__doc__)
for name in ('host-prefix', 'target-prefix', 'base', 'stage', 'work'):
    cli.add_argument('--' + name, type=Path, required=True)
cli.add_argument('--target', choices=('aarch64', 'amd64'), required=True)
args = cli.parse_args(arguments)
for path in (args.host_prefix, args.target_prefix, args.base, args.stage, args.work):
    owner.require(path.is_absolute(), 'use absolute input and output paths')
native = host_prefix.load_host_prefix(str(args.host_prefix), compiler_family='clang',
    required_roles=('cc', 'cxx', 'python', 'sh'))
environment = owner.process.sanitized_environment()
environment['PATH'] = native.path
definition = targets.target_definition(args.target)
compiler = target_toolchain.clang_compiler(str(args.target_prefix), definition['triplet'],
    host=dict(native.host), env=environment)
args.work.mkdir()
producer.link_checks(owner, args.work, args.stage, args.base, native, compiler,
    definition, environment)
print('PASS: C and C++ static, dynamic and DSO consumers linked with staged headers')
