# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); standalone GCC16 Fortran target runtime.
"""Build only target library components in a new work directory."""
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys

from emberbsd_sdk import elf, inventory, jsonio, paths, process
from emberbsd_sdk.errors import ProcessOwnershipError
import sdk_source
from host import (PROFILE, VERSION, TARGETS, TOOLS, capture, check_compilers,
                  environment, jobs, new_path, policy_sources, prepare_source, require, sha)
sys.path.insert(0, str(PROFILE / 'cross'))
from fortran_support import inspect, quarantine_work, source_state, lease_hold as ownership_hold
from fortran_commands import component_plan
sys.path.insert(0, str(PROFILE.parents[1] / 'pkgsrc/lang/gcc16-fortran-runtime/files'))
import fortran_stage
import fortran_target


class FortranRuntime:
    def __init__(self, argv):
        args = list(argv)
        self.check = args[:1] == ['--check']
        if self.check: args.pop(0)
        require(len(args) == 8 and args[0] == '--target',
                'Usage: build-fortran-runtime.py [--check] --target TARGET PKGSRC ARCHIVE COMPILER SYSROOT BASE_RUNTIME_WORK NEW_WORK --sdk-source SOURCE')
        self.target = args[1]
        require(self.target in TARGETS, 'Unsupported Fortran target')
        self.pkgsrc, self.archive, self.compiler, self.sysroot, self.base = map(
            lambda x: Path(paths.canonical_existing(x)), args[2:-1])
        self.work = new_path(args[-1])
        for path in (self.pkgsrc, self.archive, self.compiler, self.sysroot, self.base):
            paths.reject_overlap(path, self.work)
        self.triplet, self.machine, _, self.flags = TARGETS[self.target]
        self.count = int(jobs(4))
        self.inputs = {}

    def record(self, value):
        path = Path(paths.canonical_existing(value))
        paths.regular_file(path)
        self.inputs[str(path)] = sha(path)
        return path

    def unchanged_inputs(self):
        for path, digest in self.inputs.items():
            require(sha(path) == digest, 'Fortran input changed: ' + path)

    def support_flags(self):
        prefix = self.sysroot / 'usr/pkg/gcc16'
        return ['--sysroot=' + str(self.sysroot), '-B' + str(prefix / 'lib/gcc' / self.triplet / VERSION) + '/',
                '-B' + str(prefix / 'lib') + '/']

    def inspect_build_context(self):
        """Inspect real generated header providers without hashing GCC objects."""
        providers = {'gcc': (self.compiler.parent / 'build/gcc', self.compiler.parent,
                             ('auto-host.h', 'config.h', 'tconfig.h', 'tm.h', 'version.h')),
                     'libgcc': (self.base / 'build' / self.triplet / 'libgcc', self.base,
                                ('auto-target.h', 'gthr-default.h'))}
        result = {}
        for role, (directory, owner, required) in providers.items():
            paths.real_directory(directory)
            require(paths.canonical_existing(directory) == str(directory), 'Generated provider is not canonical')
            source_version, makefile = owner / 'src/gcc/BASE-VER', directory / 'Makefile'
            selected = [source_version, makefile] + sorted(p for p in directory.iterdir()
                if p.suffix in ('.h', '.def', '.inc'))
            require(all((directory / name) in selected for name in required), 'Required generated header missing')
            files = {}
            for path in selected:
                actual = Path(paths.canonical_existing(path))
                require(paths.inside(actual, owner), 'Generated provider header escapes its owner')
                paths.regular_file(actual)
                files[str(path)] = {'path': str(actual), 'sha256': sha(actual)}
            require(source_version.read_text().strip() == VERSION, 'Generated provider GCC source version differs')
            field = 'target' if role == 'gcc' else 'target_noncanonical'
            require(re.findall(r'^' + field + r'[ \t]*=[ \t]*(\S+)[ \t]*$', makefile.read_text(), re.M)
                    == [self.triplet], 'Generated provider target differs')
            if role == 'gcc':
                require(re.findall(r'^#define version_string "([^"]+)"$',
                                   (directory / 'version.h').read_text(), re.M) == [VERSION],
                        'Generated compiler header version differs')
            else:
                require(re.findall(r'^thread_header[ \t]*=[ \t]*(\S+)[ \t]*$', makefile.read_text(), re.M)
                        == ['gthr-posix.h'], 'Generated runtime did not select the POSIX thread header')
                expected = self.base / 'src/libgcc/gthr-posix.h'
                peer = self.compiler.parent / 'src/libgcc/gthr-posix.h'
                for path, root in ((expected, self.base), (peer, self.compiler.parent)):
                    require(paths.canonical_existing(path) == str(path) and paths.inside(path, root),
                            'Raw thread source escapes its owner')
                    paths.regular_file(path)
                    files[str(path)] = {'path': str(path), 'sha256': sha(path)}
                require(paths.canonical_existing(directory / 'gthr-default.h') == str(expected) and
                        sha(expected) == sha(peer), 'Generated raw thread header differs from the matching frontend source')
            result[role] = {'path': str(directory), 'owner': str(owner), 'files': files}
        return result

    def bind_build_context(self):
        """Restore only two upstream build-directory roles in this new work."""
        require(self.inspect_build_context() == self.context, 'Generated provider changed before binding')
        aliases = {self.work / 'build/gcc': Path(self.context['gcc']['path']),
                   self.work / 'build' / self.triplet / 'libgcc': Path(self.context['libgcc']['path'])}
        for link in aliases:
            require(paths.entry(link) is None and paths.canonical_new(link) == str(link),
                    'Build context path exists or escapes the new work')
        for link, provider in aliases.items():
            link.parent.mkdir(parents=True, exist_ok=True)
            paths.real_directory(link.parent)
            require(paths.canonical_existing(link.parent) == str(link.parent), 'Build context parent is not canonical')
            link.symlink_to(provider, target_is_directory=True)
        self.verify_build_context()
        jsonio.write_json(self.work / 'build-context.json', self.context, exclusive=True)
        self.record(self.work / 'build-context.json')

    def verify_build_context(self):
        require(self.inspect_build_context() == self.context, 'Generated provider headers changed')
        for role, relative in (('gcc', 'build/gcc'), ('libgcc', 'build/' + self.triplet + '/libgcc')):
            link, provider = self.work / relative, self.context[role]['path']
            require(link.is_symlink() and os.readlink(link) == provider and
                    paths.canonical_existing(link) == provider, 'Build context link changed')

    def preflight(self):
        self.sources = source_state(self.pkgsrc, self.archive)
        self.parent = fortran_stage.BaseStage(self.base, self.pkgsrc, self.archive).verify()
        require(self.parent['metadata']['PKGNAME'] == fortran_stage.BASE and
                self.parent['metadata']['GCC_RUNTIME_TARGET'] == self.target, 'Exact compatible base runtime required')
        self.capability = self.record(self.compiler.parent / 'fortran-check/capability.json')
        cap = jsonio.read_json(self.capability)
        require(cap['format'] == 'emberbsd-gcc16-fortran-capability' and type(cap['version']) is int and cap['version'] == 1
                and cap['status'] == 'PASS' and cap['target'] == self.target, 'Matching real frontend capability required')
        self.frontend = inspect(self.compiler, self.target)
        require(cap['compiler'] == self.frontend and cap['archive_sha256'] == self.sources['archive_sha256']
                and cap['sources']['recipe'] == self.sources['recipe'], 'Frontend source or executable differs')
        self.tools = check_compilers(self.compiler, self.target)
        for tool in list(self.tools.values()) + [Path(row['path']) for row in self.frontend['tools'].values()]:
            self.record(tool)
        for compiler, frontend in (('gcc', 'cc1'), ('g++', 'cc1plus')):
            path = Path(capture([self.tools[compiler], '-print-prog-name=' + frontend]).strip()).resolve(strict=True)
            require(paths.inside(path, self.compiler), 'Compiler frontend escaped its generation')
            self.record(path)
        self.record(self.compiler.parent / 'inputs.txt')
        self.context = self.inspect_build_context()
        for provider in self.context.values():
            for row in provider['files'].values(): self.record(row['path'])
        self.record(self.archive)
        self.record(self.sysroot / '.prebuild-sdk-build.json')
        # Keep the authenticated SDK thread header inputs. The upstream build
        # include order selects the raw C form from the real libgcc provider.
        for name in ('gthr.h', 'gthr-default.h', 'gthr-posix.h', 'gthr-single.h'):
            relative = Path('include/c++') / self.triplet / 'bits' / name
            actual = self.sysroot / 'usr/pkg/gcc16' / relative
            expected = self.base / 'stage/usr/pkg/gcc16' / relative
            require(sha(actual) == sha(expected), 'Target thread header differs from authenticated stage')
            self.record(actual)
        for name in ('inputs.txt', 'stage.sha256', 'stage.symlinks', 'build-success'):
            self.record(self.base / name)
        self.base_tree = inventory.snapshot_tree(self.sysroot, exclude=('usr/pkg', '.prebuild-sdk-build.json', '.prebuild-sdk-build.log'))
        self.headers = inventory.snapshot_tree(self.sysroot / 'usr/include')
        for name in ('crtbegin.o', 'crtbeginS.o', 'crtend.o', 'crtendS.o', 'libgcc.a', 'libgcc_s.so'):
            path = Path(capture([self.tools['gcc']] + self.support_flags() + ['-print-file-name=' + name]).strip())
            require(path.is_absolute() and paths.inside(path.resolve(strict=True), self.sysroot / 'usr/pkg/gcc16'),
                    'Target support escaped the selected SDK')
            relative = ('lib/' if name == 'libgcc_s.so' else 'lib/gcc/' + self.triplet + '/' + VERSION + '/') + name
            expected = self.base / 'stage/usr/pkg/gcc16' / relative
            require(sha(path.resolve(strict=True)) == sha(expected.resolve(strict=True)), 'Target support differs from authenticated stage')
            if name.endswith('.o'):
                require(elf.read_elf_header(path.resolve(strict=True), self.machine, 1), 'Wrong target support object')
            elif name.endswith('.a'):
                require(elf.read_archive(path.resolve(strict=True), self.machine)['elf_members'] > 0, 'Empty target support archive')
            self.record(path)
        self.make = Path(os.environ.get('GNU_MAKE') or shutil.which('gmake') or shutil.which('make') or '')
        require(self.make.is_absolute() and capture([self.make, '--version']).startswith('GNU Make '), 'Explicit GNU make required')
        self.record(self.make)
        cc = os.environ.get('HOST_CC', 'gcc-16')
        self.native_cc = Path(shutil.which(cc) or '')
        require(self.native_cc.is_absolute() and capture([self.native_cc, '-dumpfullversion']).strip() == VERSION,
                'Native GCC16.2 build compiler required')
        self.build_triplet = capture([self.native_cc, '-dumpmachine']).strip()
        host = platform.system(), platform.machine()
        native = ((host == ('Darwin', 'arm64') and re.fullmatch(r'(?:aarch64|arm64)-apple-darwin[0-9.]+', self.build_triplet)) or
                  (host == ('Darwin', 'x86_64') and re.fullmatch(r'x86_64-apple-darwin[0-9.]+', self.build_triplet)) or
                  (host[0] == 'Linux' and host[1] in ('aarch64', 'x86_64') and
                   re.fullmatch(re.escape(host[1]) + r'-[A-Za-z0-9_-]*linux-gnu', self.build_triplet)))
        require(native, 'CC_FOR_BUILD is not the native host compiler')
        self.record(self.native_cc)
        self.host_tools = {}
        for variable, name in {'M4': 'm4', 'AWK': 'awk', 'SED': 'sed', 'SHELL': 'sh',
                               'MAKEINFO': 'makeinfo', 'INSTALL': 'install', 'PERL': 'perl',
                               'GREP': 'grep', 'EGREP': 'egrep', 'FGREP': 'fgrep',
                               'TAR': 'tar', 'PATCH': 'patch', 'SORT': 'sort'}.items():
            found = shutil.which(name)
            require(found is not None, 'Required native tool missing: ' + name)
            self.host_tools[variable] = str(self.record(Path(found).resolve(strict=True)))
        for path in policy_sources() + [Path(__file__), Path(fortran_stage.__file__), Path(inspect.__code__.co_filename),
                                         Path(component_plan.__code__.co_filename), Path(fortran_target.__file__)]:
            self.record(path)
        self.plan = component_plan(self.target, self.build_triplet, self.work / 'src', self.work,
                                   self.compiler, self.sysroot, self.make, self.count, self.native_cc)
        self.host_tools['CONFIG_SHELL'] = self.host_tools['SHELL']
        for row in self.plan: row['env'].update(self.host_tools)
        print(json.dumps({'scope': 'Fortran runtime plan only', 'target': self.target, 'commands': self.plan,
                          'inputs': self.inputs, 'limits': 'No runtime producer or target execution in --check mode.'}, indent=2))

    def run(self, row, number):
        directory = Path(row['cwd'])
        directory.mkdir(parents=True, exist_ok=True)
        log = self.work / (str(number) + '-' + row['component'] + '-' + row['phase'] + '.log')
        require(paths.entry(log) is None, 'Fortran producer log already exists')
        process.run_logged(row['argv'], log, cwd=directory, env=environment(row['env']))
        self.record(log)
        if row['phase'] == 'configure':
            makefile = directory / 'Makefile'
            text = makefile.read_text().splitlines()
            require('CC = ' + row['env']['CC'] in text, 'Component lost the selected target C compiler')
            if row['component'] == 'libgfortran':
                require('FC = ' + row['env']['FC'] in text, 'Component lost the selected Fortran compiler')
            if row['component'] == 'libbacktrace':
                require('PIC_FLAG = -fPIC' in text, 'Target backtrace convenience objects are not PIC')
            for name in ('Makefile', 'config.status', 'config.log', 'config.h', 'libtool'):
                self.record(directory / name)

    def build(self):
        self.preflight()
        if self.check: return
        self.work.mkdir()
        info = self.work.stat()
        owned = {'path': str(self.work), 'device': info.st_dev, 'inode': info.st_ino}
        try:
            self.build_owned()
        except ProcessOwnershipError as error:
            quarantine_work(owned, error)
            raise

    def build_owned(self):
        with (self.work / 'patch.log').open('xb') as output:
            prepare_source(self.pkgsrc, self.archive, self.work / 'src', runtime=False, output=output)
        self.bind_build_context()
        self.prepared = {name: inventory.snapshot_tree(self.work / 'src' / name)
                         for name in ('libbacktrace', 'libquadmath', 'libgfortran')}
        jsonio.write_json(self.work / 'source-inventory.json', self.prepared, exclusive=True)
        self.record(self.work / 'source-inventory.json')
        jsonio.write_json(self.work / 'commands.json', self.plan, exclusive=True)
        self.record(self.work / 'commands.json')
        jsonio.write_json(self.work / 'base-inventory.json', self.base_tree, exclusive=True)
        self.record(self.work / 'base-inventory.json')
        jsonio.write_json(self.work / 'headers-inventory.json', self.headers, exclusive=True)
        self.record(self.work / 'headers-inventory.json')
        for number, row in enumerate(self.plan): self.run(row, number)
        require({name: inventory.snapshot_tree(self.work / 'src' / name) for name in self.prepared} == self.prepared,
                'Prepared component source changed during the build')
        require(inventory.snapshot_tree(self.sysroot, exclude=('usr/pkg', '.prebuild-sdk-build.json', '.prebuild-sdk-build.log')) == self.base_tree,
                'Source-built target base changed during the build')
        require(inventory.snapshot_tree(self.sysroot / 'usr/include') == self.headers, 'Target headers changed during the build')
        require(inspect(self.compiler, self.target) == self.frontend and source_state(self.pkgsrc, self.archive) == self.sources,
                'Compiler or clean producer source changed')
        require(fortran_stage.BaseStage(self.base, self.pkgsrc, self.archive).verify() == self.parent,
                'Compatible base runtime changed during the build')
        self.verify_build_context()
        self.unchanged_inputs()
        result = fortran_stage.inspect_stage(self.work / 'stage', self.target)
        receipt = self.work / 'fortran-stage.json'
        jsonio.write_json(receipt, {'format': 'emberbsd-gcc16-fortran-stage', 'version': 1,
            'status': 'BUILT_AND_INSPECTED', 'target': self.target, 'triplet': self.triplet,
            'source_archive_sha256': self.sources['archive_sha256'], 'sources': self.sources,
            'base_runtime_name': fortran_stage.BASE, 'base_runtime_work': str(self.base),
            'base_runtime_metadata': self.parent['metadata'], 'compiler_capability': str(self.capability),
            'commands_sha256': sha(self.work / 'commands.json'), 'inputs': self.inputs,
            'stage': result['stage'], 'limits': 'No target execution, package install, FFTW or compiler promotion.'}, exclusive=True)
        try:
            fortran_stage.Stage(self.work, self.archive, self.pkgsrc).verify()
        except BaseException:
            receipt.rename(self.work / 'failed-fortran-stage.json')
            raise


def locked_main(argv):
    """One process owns the producer, SDK shared lease and exact new-work lease."""
    import argparse
    import inspect as python_inspect
    from emberbsd_sdk.process import ContextLocks
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock-root', required=True, type=Path, action='append')
    parser.add_argument('--host-prefix', required=True, type=Path, action='append')
    options, remaining = parser.parse_known_args(argv)
    require(len(options.lock_root) == len(options.host_prefix) == 1, 'Use each lease option once')
    lock_root = Path(paths.canonical_existing(options.lock_root[0]))
    host_prefix = Path(paths.canonical_existing(options.host_prefix[0]))
    paths.real_directory(lock_root)
    paths.real_directory(host_prefix)
    require('shared' in python_inspect.signature(ContextLocks).parameters,
            'SDK API1 ContextLocks shared mode is required')
    producer = FortranRuntime(remaining)
    require(producer.work.parent == lock_root, 'NEW_WORK must be a direct child of LOCK_ROOT')
    inputs = [producer.pkgsrc, producer.archive, producer.compiler, producer.compiler.parent, producer.sysroot,
              producer.base, PROFILE.parents[1], Path(sdk_source.load()), host_prefix]
    for path in inputs: paths.reject_overlap(path, producer.work)
    with ContextLocks(sorted(set(map(str, inputs))), str(lock_root), shared=True), \
            ContextLocks([str(producer.work)], str(lock_root)):
        require(paths.entry(producer.work) is None, 'NEW_WORK appeared before its exclusive lease')
        try:
            producer.build()
        except ProcessOwnershipError as error:
            ownership_hold(error)
