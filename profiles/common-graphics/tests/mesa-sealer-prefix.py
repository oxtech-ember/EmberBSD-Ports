#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the real sealer's prefix and runtime policy without running generators."""
import argparse
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from unittest.mock import patch
from contextlib import redirect_stderr

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source


def require(value, message):
    if not value:
        raise ValueError(message)


def metadata(path, loads=(), rpaths=(), identity=None, extra=()):
    names = list(loads) + ([identity] if identity else [])
    listing = str(path) + ':\n' + ''.join(
        '\t' + name + ' (compatibility version 1.0.0, current version 1.0.0)\n' for name in names)
    commands = [('LC_SEGMENT_64', None)]
    commands += [('LC_LOAD_DYLIB', name) for name in loads]
    commands += [('LC_RPATH', name) for name in rpaths]
    commands += [('LC_ID_DYLIB', identity)] if identity else []
    commands += list(extra)
    text = str(path) + ':\n'
    for index, (kind, name) in enumerate(commands):
        text += 'Load command ' + str(index) + '\n      cmd ' + kind + '\n  cmdsize 48\n'
        if name:
            text += '     ' + ('path' if kind == 'LC_RPATH' else 'name') + ' ' + name + ' (offset 24)\n'
    return listing, text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', type=Path, required=True)
    parser.add_argument('--work-parent', type=Path, required=True)
    parser.add_argument('--host-prefix', type=Path)
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    require(args.sdk_source.is_absolute() and args.work_parent.is_absolute(), 'Use absolute inputs')
    require((args.host_prefix is None) == (args.archive is None), 'Use --host-prefix and --archive together')
    sdk_source.load_sdk(['--sdk-source', str(args.sdk_source)])
    source = PORTS / 'profiles/common-graphics/cross/seal-mesa-generators.py'
    spec = importlib.util.spec_from_file_location('_mesa_sealer_prefix', source)
    sealer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sealer)
    print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True), end='')
    work = Path(tempfile.mkdtemp(prefix='mesa-sealer-prefix-test-', dir=args.work_parent))
    checks = 0

    def success(name, function):
        nonlocal checks
        value = function()
        checks += 1
        print('PASS: ' + name)
        return value

    def refusal(name, function, error):
        nonlocal checks
        try:
            function()
        except Exception as failure:
            require(error in str(failure), name + ': ' + str(failure))
        else:
            raise ValueError(name + ': refused input was accepted')
        checks += 1
        print('PASS: ' + name)

    try:
        diagnostics = io.StringIO()
        with redirect_stderr(diagnostics):
            try:
                sealer.seal(['/abs/archive', '/abs/source', '/abs/build', '/abs/validator', '/abs/new-work'])
            except SystemExit as error:
                require(error.code == 2 and '--host-prefix' in diagnostics.getvalue(), 'Wrong missing-prefix refusal')
            else:
                raise ValueError('Sealer accepted a missing --host-prefix')
        checks += 1
        prefix = work / 'prefix'
        (prefix / 'bin').mkdir(parents=True)
        # Native-byte fixtures only. The SDK selector checks them; no fixture
        # executable, compiler query, or generator is ever invoked.
        for name in ('bsdtar', 'patch', 'otool', 'spirv-val'):
            path = prefix / 'bin' / name
            path.write_bytes(struct.pack('<8I', 0xfeedfacf, 0x100000c, 0, 2, 0, 0, 0, 0))
            path.chmod(0o755)
        with patch('emberbsd_sdk.host_prefix.process.capture', side_effect=AssertionError('Unexpected compiler query')):
            native = success('real SDK prefix selection without compiler queries', lambda: sealer.select_host(prefix))
        require(set(native.tools) == {'bsdtar', 'patch', 'otool', 'spirv-val'} and not native.compiler,
                'Sealer requested unrelated compiler roles')
        from emberbsd_sdk.process import ContextLocks
        pkgdb, lockdir = work / 'pkgdb', work / 'shared-locks'
        pkgdb.mkdir()
        lockdir.mkdir()
        lease_args = ['--host-prefix', str(prefix), '--pkgdb', str(pkgdb),
                      '--lock-directory', str(lockdir), '/abs/archive', '/abs/source',
                      '/abs/build', '/abs/validator', '/abs/new-work']

        def locked_body(arguments):
            for resource in (prefix, pkgdb):
                refusal('writer excluded during seal: ' + resource.name,
                        lambda: ContextLocks([str(resource)], str(lockdir)).acquire(), 'busy')
            with ContextLocks([str(prefix), str(pkgdb)], str(lockdir), shared=True):
                sealer.select_host(arguments.host_prefix)
            raise ValueError('fixture seal failure')

        with patch.object(sealer, 'seal_locked', side_effect=locked_body):
            refusal('shared input lease spans selection and failed seal',
                    lambda: sealer.seal(lease_args), 'fixture seal failure')
        with ContextLocks([str(prefix), str(pkgdb)], str(lockdir)):
            checks += 1
        with ContextLocks([str(prefix)], str(lockdir)):
            with patch.object(sealer, 'seal_locked', side_effect=AssertionError('ran before lease')):
                refusal('busy input refuses before sealer body', lambda: sealer.seal(lease_args), 'busy')
        source_tree, build_tree = work / 'source', work / 'build-input'
        source_tree.mkdir()
        build_tree.mkdir()
        alias = work / 'prefix-alias'
        alias.symlink_to(prefix, target_is_directory=True)
        overlap_args = lease_args.copy()
        overlap_args[-4], overlap_args[-3] = str(source_tree), str(build_tree)
        for name, candidate in (('prefix child', prefix / 'output'),
                                ('pkgdb child', pkgdb / 'output'),
                                ('source child', source_tree / 'output'),
                                ('build child', build_tree / 'output'),
                                ('symlink prefix child', alias / 'output'),
                                ('protected ancestor', work)):
            trial = overlap_args.copy()
            trial[-1] = str(candidate)
            with patch.object(sealer, 'seal_locked', side_effect=AssertionError('ran before overlap refusal')):
                refusal('output overlaps ' + name, lambda: sealer.seal(trial), 'overlapping input/output')
            require(not (candidate / 'reference').exists(), 'Overlap refusal created work output')
        with patch.dict(os.environ, {'PATH': '/ambient/tools', 'DYLD_LIBRARY_PATH': '/unrelated'}):
            env = sealer.sealing_environment(native, work / 'tmp', {'PCO_DEBUG': 'no_pred_cf'})
        require(env['PATH'] == native.path and all(Path(p).is_relative_to(prefix) for p in env['PATH'].split(':')) and
                'DYLD_LIBRARY_PATH' not in env and env['PCO_DEBUG'] == 'no_pred_cf',
                'Sealer inherited ambient tools or loader overrides')
        checks += 1
        (prefix / 'bin/patch').unlink()
        refusal('missing prefix tool has no ambient fallback', lambda: sealer.select_host(prefix), 'missing native tool')
        (prefix / 'bin/patch').symlink_to('/bin/sh')
        refusal('external tool symlink', lambda: sealer.select_host(prefix), 'escapes host prefix')

        paths = {name: prefix / relative for name, relative in {
            'LLVM': 'lib/libLLVM.dylib', 'Translator': 'lib/libLLVMSPIRVLib.dylib',
            'SPIRV': 'lib/libSPIRV-Tools.dylib', 'GCC': 'gcc16/lib/libstdc++.6.dylib'}.items()}
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(path.name.encode())
        executable = work / 'build/mesa_clc'
        executable.parent.mkdir()
        executable.write_bytes(b'output-byte fixture, never executed')
        copied = work / 'copied/bin/mesa_clc'
        copied.parent.mkdir(parents=True)
        shutil.copyfile(executable, copied)
        graph = {
            paths['LLVM']: (['@rpath/libLLVMSPIRVLib.dylib', str(paths['SPIRV'])], ['@loader_path']),
            paths['Translator']: ([str(paths['GCC'])], []),
            paths['SPIRV']: ([str(paths['LLVM'])], []),
            paths['GCC']: (['/usr/lib/libSystem.B.dylib'], []),
            executable: (['@rpath/libLLVM.dylib'], [str(prefix / 'lib')]),
            copied: (['@rpath/libLLVM.dylib'], [str(prefix / 'lib')]),
        }

        def inspect(path):
            loads, rpaths = graph[path]
            identity = str(path) if path in paths.values() else None
            result = sealer.dependency_metadata(*metadata(path, loads, rpaths, identity))
            result['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            return result

        expected = {str(p) for p in paths.values()} | {str(executable)}
        found = success('shared GCC/LLVM/Translator/SPIRV closure and cycle',
                        lambda: sealer.native_dependencies(executable, prefix, inspect))
        require(set(found) == expected, 'Missing common native dependency')
        found = success('copied output keeps common prefix dependencies',
                        lambda: sealer.native_dependencies(copied, prefix, inspect))
        require(set(found) == {str(p) for p in paths.values()} | {str(copied)}, 'Copied closure differs')

        graph[paths['LLVM']] = (['@rpath/libLLVMSPIRVLib.dylib'], [])
        success('inherited rpath resolves inside common prefix', lambda: sealer.native_dependencies(executable, prefix, inspect))
        graph[paths['LLVM']] = (['@rpath/libLLVMSPIRVLib.dylib'], ['@loader_path'])
        graph[executable] = (['@loader_path/../prefix/lib/libLLVM.dylib'], [])
        success('loader-relative direct dependency', lambda: sealer.native_dependencies(executable, prefix, inspect))
        graph[copied] = graph[executable]
        refusal('copied output cannot reuse source-relative lookup',
                lambda: sealer.native_dependencies(copied, prefix, inspect), 'No such file')
        outside = work / 'outside.dylib'
        outside.write_bytes(b'outside fixture')
        graph[executable] = ([str(outside)], [])
        graph[outside] = (['/usr/lib/libSystem.B.dylib'], [])
        refusal('external absolute dependency', lambda: sealer.native_dependencies(executable, prefix, inspect), 'escapes host prefix')
        original_require = sealer.require

        def weakened(condition, message):
            if not message.startswith('Native shared dependency escapes host prefix:'):
                original_require(condition, message)

        with patch.object(sealer, 'require', side_effect=weakened):
            admitted = sealer.native_dependencies(executable, prefix, inspect)
        require(str(outside) in admitted, 'Removing containment did not admit the same outside fixture')
        checks += 1
        (prefix / 'lib/escaped.dylib').symlink_to(outside)
        graph[executable] = (['@rpath/escaped.dylib'], [str(prefix / 'lib')])
        refusal('rpath symlink escape', lambda: sealer.native_dependencies(executable, prefix, inspect), 'escapes host prefix')
        graph[executable] = (['@rpath/outside.dylib'], [str(work)])
        refusal('external rpath target', lambda: sealer.native_dependencies(executable, prefix, inspect), 'escapes host prefix')
        graph[executable] = (['@rpath/missing.dylib'], [str(prefix / 'lib')])
        refusal('unresolved rpath', lambda: sealer.native_dependencies(executable, prefix, inspect), 'Unresolved')
        graph[executable] = (['/usr/lib/libSystem.B.dylib', '/System/Library/Frameworks/A.framework/A'], [])
        require(set(sealer.native_dependencies(executable, prefix, inspect)) == {str(executable)}, 'OS ABI was not terminal')
        checks += 1

        listing, commands = metadata(executable, [str(paths['LLVM'])])
        refusal('otool interfaces disagree', lambda: sealer.dependency_metadata(listing, commands.replace(str(paths['LLVM']), str(outside))), 'disagree')
        refusal('dyld environment load command', lambda: sealer.dependency_metadata(
            *metadata(executable, extra=[('LC_DYLD_ENVIRONMENT', None)])), 'Unsupported')
        refusal('undecoded lazy metadata', lambda: sealer.dependency_metadata(
            *metadata(executable, extra=[('LC_LAZY_DYLIB_INFO', None)])), 'Unsupported')
        refusal('unknown loader command', lambda: sealer.dependency_metadata(
            *metadata(executable, extra=[('LC_LOAD_UNKNOWN', None)])), 'Unrecognized')
        if args.host_prefix is not None:
            from emberbsd_sdk.native_toolset import load_host_prefix
            require(args.host_prefix.is_absolute() and args.archive.is_absolute(), 'Use absolute source-check inputs')
            require(sealer.sha(args.archive) == sealer.MESA_SHA256, 'Wrong original Mesa archive')
            selected = load_host_prefix(args.host_prefix, required_roles=('bsdtar', 'patch'))
            reference, temporary = work / 'real-source', work / 'real-tmp'
            reference.mkdir()
            temporary.mkdir()
            env = sealer.sealing_environment(selected, temporary, {})
            files = ['meson.build', 'src/imagination/common/pvr_device_info.c',
                     'src/imagination/common/pvr_device_info.h', 'src/imagination/pco/uscgen/pco_clc.c',
                     'src/imagination/common/pvr_iface.h']
            command = [selected.tool('bsdtar'), '-xf', str(args.archive), '--strip-components=1',
                       '-C', str(reference), *['mesa-26.2.5/' + name for name in files]]
            subprocess.run(command, check=True, capture_output=True, env=env, timeout=60)
            original = {name: sealer.sha(reference / name) for name in files}
            patches = [(PORTS / 'probes/a733-accelerators/host-tools/mesa-26.2.4-pco-bvnc.patch', 1, []),
                       (PORTS / 'pkgsrc/graphics/MesaLib/patches/patch-meson.build-host-objc', 0, []),
                       (PORTS / 'pkgsrc/graphics/MesaLib/patches/patch-src_imagination_common_pvr__iface.h', 0, ['84'])]
            for source_patch, strip, offsets in patches:
                command = list(map(str, sealer.patch_command(selected, reference, source_patch, strip)))
                result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=30)
                output = result.stdout + result.stderr
                require(result.returncode == 0 and not re.search(r'\bfuzz\b', output, re.I) and
                        re.findall(r'offset ([+-]?[0-9]+) lines?', output) == offsets, output)
                checks += 1
                print('PASS: real prefix patch with production argv: ' + source_patch.name)
            actual = {str(path.relative_to(reference)) for path in reference.rglob('*') if path.is_file()}
            require(actual == set(files), 'Unexpected source files after patch: ' + str(sorted(actual - set(files))))
            unchanged = [name for name in files if sealer.sha(reference / name) == original[name]]
            require(not unchanged, 'Canonical source patch made no change: ' + str(unchanged))
        print('PASS: ' + str(checks) + ' source/fixture policy checks; no generator or compiler execution')
    finally:
        print(subprocess.check_output(['df', '-k', str(work)], text=True), end='')
        shutil.rmtree(work)
        require(not work.exists(), 'Owned fixture remains')
        print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True), end='')
        print('Removed owned fixture: ' + str(work))


if __name__ == '__main__':
    main()
