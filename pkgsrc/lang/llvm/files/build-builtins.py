#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: LLVM compiler-rt standalone builtins CMake; AI-assisted Ports orchestration.
"""Compatibility entry point for the common compiler-rt builtins phase."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True


def _module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def _inputs(options):
    from emberbsd_sdk import host_prefix
    ports = Path(options.ports).resolve(strict=True)
    files = ports / 'pkgsrc/lang/compiler-rt/files'
    owner = _module(files / 'source.py', 'builtins_common_source')
    owner.load_sdk(['--sdk-source', options.sdk_source])
    producer = _module(files / 'build.py', 'builtins_common_build')
    source, _ = owner.recipe(options.git)
    archive = Path(owner.paths.canonical_existing(options.archive))
    owner.require(archive.name == source['source']['archive'], 'archive name differs from the common LLVM recipe')
    hashes = owner.sourceprep.archive_hashes(owner.read(archive))
    owner.require(all(hashes[key] == source['source'][key] for key in ('sha512', 'blake2s', 'size')),
                  'LLVM archive bytes differ from the common recipe')
    work = Path(owner.paths.build_path(owner.paths.canonical_new(options.work)))
    owner.require(not os.path.lexists(work), 'work directory already exists')
    owner.paths.real_directory(work.parent)
    for root in (ports, archive, options.base, options.os, options.host_prefix,
                 options.target_prefix or options.host_prefix):
        owner.paths.reject_overlap(str(work), str(root))
    args = SimpleNamespace(source=str(work / 'source'), work=str(work / 'build'), stage=str(work / 'stage'),
        sysroot=options.base, os_source=options.os, host_prefix=options.host_prefix,
        target_prefix=options.target_prefix or options.host_prefix,
        host_compiler_family=options.host_compiler_family, git=options.git,
        target=options.target, jobs=options.jobs, phase='builtins', bootstrap_stage=None)
    selected = producer.inspect_inputs(owner, args, source)
    patch = options.patch
    if patch is None:
        patch = host_prefix.load_host_prefix(options.host_prefix,
            compiler_family=options.host_compiler_family, required_roles=('patch',)).tool('patch')
    owner.require(os.path.isabs(patch), 'select an absolute patch executable')
    runtime = str(files / 'runtime.py')
    common = [selected.native.tool('python'), '-B', runtime, '--sdk-source', options.sdk_source]
    commands = [common + ['prepare', '--archive', str(archive), '--source', args.source,
                         '--patch', patch, '--git', options.git],
                common + ['build', '--source', args.source, '--target', args.target, '--phase', 'builtins',
                    '--sysroot', args.sysroot, '--os-source', args.os_source,
                    '--host-prefix', args.host_prefix, '--target-prefix', args.target_prefix,
                    '--host-compiler-family', args.host_compiler_family, '--work', args.work,
                    '--stage', args.stage, '--git', args.git, '--jobs', str(args.jobs)]]
    result = dict(format='emberbsd-builtins-build', version=1, target=args.target,
        work=str(work), source=source['source'], recipe=selected.recipe, base=selected.context,
        commands=commands, status='planned', target_execution='not-run',
        base_origin='caller-selected OS source; header producer origin is not verified')
    return result, owner, producer, args, patch


def plan(options):
    return _inputs(options)[0]


def build(options):
    result, owner, producer, args, patch = _inputs(options)
    if options.plan:
        return result
    work = Path(result['work'])
    work.mkdir()
    result['status'] = 'building'
    owner.jsonio.write_json(work / 'build.json', result)
    try:
        owner.prepare_source(options.archive, args.source, patch, options.git)
        result['runtime'] = producer.build(owner, args)
        result['status'] = 'built-and-inspected'
    except BaseException as error:
        result.update(status='failed', error=str(error))
        manifest = Path(args.stage) / 'runtime.json'
        if manifest.exists():
            manifest.unlink()
        raise
    finally:
        owner.jsonio.write_json(work / 'build.json', result, exclusive=False)
    return result


def main():
    from sdk_source import load_sdk, install_signal_handlers, exit_error
    sdk, arguments = load_sdk()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'base', 'os', 'host-prefix', 'work', 'target'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--ports', default=str(Path(__file__).resolve().parents[4]))
    parser.add_argument('--git', default=shutil.which('git'), help='Git is used only for source inspection')
    parser.add_argument('--patch', help='Defaults to the selected native prefix patch tool')
    parser.add_argument('--target-prefix', help='Defaults to the selected native LLVM prefix')
    parser.add_argument('--host-compiler-family', choices=('clang', 'gcc'), default='clang')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--plan', action='store_true')
    options = parser.parse_args(arguments)
    options.sdk_source = sdk
    install_signal_handlers()
    try:
        import json
        print(json.dumps(build(options), indent=2))
    except Exception as error:
        exit_error(error)


if __name__ == '__main__':
    main()
