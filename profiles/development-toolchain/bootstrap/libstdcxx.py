# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; fresh libstdc++ with authenticated component inheritance.
import json
import os
from pathlib import Path
import re
import shutil
import sys
from emberbsd_sdk import elf, jsonio, paths
import sdk_source
from host import *
from runtime import Stage, TARGETS as RUNTIME_TARGETS, field
import inheritance

HERE = PROFILE / 'bootstrap'


class LibstdcxxRebuild:
    def __init__(self, args):
        args = list(args)
        self.check = args[:1] == ['--check']
        if self.check:
            args.pop(0)
        require(len(args) == 8, 'Usage: rebuild-libstdcxx.py [--check] TARGET NEW_PKGSRC OLD_PKGSRC ARCHIVE COMPILER SYSROOT OLD_WORK NEW_WORK --sdk-source SOURCE')
        self.target = args[0]
        require(self.target in TARGETS, 'Unsupported target')
        self.pkgsrc, self.old_pkgsrc, self.archive, self.compiler, self.sysroot, self.old_work, self.work = [build_path(value) for value in args[1:]]
        new_path(self.work)
        self.triplet, self.machine, _, self.target_flags = TARGETS[self.target]
        self.count = jobs(2)
        self.make = os.environ.get('GNU_MAKE', '/usr/bin/make')
        require(Path(self.make).is_absolute() and os.access(self.make, os.X_OK), 'GNU_MAKE must be absolute executable')
        self.env = {'PATH': str(self.compiler / 'bin') + ':' + os.environ.get('PATH', '')}
        self.inputs = {}

    def record(self, path):
        self.inputs[str(path)] = sha(Path(path).resolve(strict=True))

    def check_elf(self, path, root):
        resolved = Path(path).resolve(strict=True)
        require(paths.inside(resolved, Path(root).resolve(strict=True)), 'Target ELF escapes prefix')
        require(elf.read_elf_header(resolved, machine=self.machine) is not None, 'Wrong target ELF')
        self.record(resolved)

    def compiler_receipt(self):
        self.receipt = self.compiler.parent / 'inputs.txt'
        receipt = self.receipt.read_text()
        modes = [line for line in receipt.splitlines(keepends=True) if line.startswith('mode=')]
        triplets = [line for line in receipt.splitlines(keepends=True) if line.startswith('triplet=')]
        require(modes == ['mode=applications\n'] and triplets and all(line == 'triplet=' + self.triplet + '\n' for line in triplets), 'Missing application compiler provenance')
        for digest in (sha(self.archive), sha(self.old_pkgsrc / 'lang/gcc16/distinfo')):
            require(any(line.startswith(digest + '  ') for line in receipt.splitlines()), 'Application compiler source identity differs')
        self.record(self.receipt)

    def preflight(self):
        self.parent = Stage(self.old_work, self.old_pkgsrc, self.archive, allow_rebuild=False, historical=True).verify()
        require(self.parent['metadata']['GCC_RUNTIME_TARGET'] == self.target, 'Parent architecture mismatch')
        inheritance.check_delta(self.old_pkgsrc / 'lang/gcc16', self.pkgsrc / 'lang/gcc16')
        self.record(self.archive)
        for prefix in (self.pkgsrc, self.old_pkgsrc):
            recipe = prefix / 'lang/gcc16'
            for path in [recipe / name for name in ('Makefile', 'Makefile.common', 'distinfo')] + sorted((recipe / 'patches').iterdir()):
                self.record(path)
        self.compiler_receipt()
        self.tools = check_compilers(self.compiler, self.target)
        self.env.update(target_tools(self.compiler, self.target))
        for name, path in self.tools.items():
            self.record(path.resolve(strict=True))
        for name in ('gcc', 'g++'):
            result = process.capture([str(self.tools[name]), '-v'], env=environment(self.env))
            require('Thread model: posix' in (result.stdout + result.stderr).decode().splitlines(), 'POSIX-thread compiler required')
        require(capture([self.make, '--version']).startswith('GNU Make '), 'GNU make required')
        self.record(Path(self.make).resolve(strict=True))
        for name in ('cc1', 'cc1plus'):
            path = Path(capture([self.tools['gcc'], '-print-prog-name=' + name]).strip()).resolve(strict=True)
            require(paths.inside(path, self.compiler.resolve(strict=True)), 'Frontend escapes compiler prefix')
            self.record(path)
        self.flags = ['--sysroot=' + str(self.sysroot), '-B' + str(self.sysroot / 'usr/pkg/gcc16/lib/gcc' / self.triplet / VERSION) + '/', '-B' + str(self.sysroot / 'usr/pkg/gcc16/lib') + '/']
        for name in ('crtbegin.o', 'crtbeginS.o', 'crtend.o', 'crtendS.o', 'libgcc.a', 'libgcc_s.so'):
            path = Path(capture([self.tools['gcc']] + self.flags + ['-print-file-name=' + name]).strip())
            if name not in ('libgcc.a', 'libgcc_s.so'):
                self.check_elf(path, self.sysroot / 'usr/pkg/gcc16')
            relative = ('lib/' if name == 'libgcc_s.so' else 'lib/gcc/' + self.triplet + '/' + VERSION + '/') + name
            expected = self.old_work / 'stage/usr/pkg/gcc16' / relative
            require(paths.inside(path.resolve(strict=True), self.sysroot / 'usr/pkg/gcc16') and sha(path.resolve(strict=True)) == sha(expected.resolve(strict=True)), 'SDK support input differs from parent stage')
            self.record(path)
        for relative in self.parent['files']:
            path = self.sysroot / 'usr/pkg' / relative
            self.check_elf(path, self.sysroot / 'usr/pkg/gcc16')
            require(sha(path.resolve(strict=True)) == sha((self.old_work / 'stage/usr/pkg' / relative).resolve(strict=True)), 'SDK runtime differs from parent stage')
            self.record(path)
        seed_inputs = (self.old_work / 'inputs.txt').read_text()
        old_seed = field(seed_inputs, 'sysroot')
        for relative in ['usr/lib/' + name for name in ('libc.so.12', 'libpthread.so.1', 'libm.so.0', 'crt0.o')] + ['usr/include/' + name for name in ('stddef.h', 'stdio.h', 'pthread.h', 'math.h')]:
            path = self.sysroot / relative
            if relative.startswith('usr/lib/'):
                self.check_elf(path, self.sysroot)
            self.record(path)
            require(seed_inputs.splitlines(keepends=True).count(sha(path.resolve(strict=True)) + '  ' + old_seed + '/' + relative + '\n') == 1, 'EmberBSD seed differs from authenticated parent')
        for name in inheritance.PARENT_FILES:
            self.record(self.old_work / name)
        for path in sorted(HERE.glob('*.py')) + sorted((PROFILE / 'runtime/recipe/files').glob('*.py')) + [PROFILE / 'host.py'] + sorted((Path(sdk_source.load()) / 'src/emberbsd_sdk').glob('*.py')):
            self.record(path)
        print(json.dumps({'scope': 'fresh-libstdcxx-preflight', 'target': self.target, 'stage': str(self.work / 'stage'), 'compiler': str(self.tools['gcc']), 'flags': self.flags, 'inherited': inheritance.inherited_paths(self.parent), 'inputs': self.inputs}, indent=2))

    def unchanged_inputs(self):
        for path, digest in self.inputs.items():
            require(sha(Path(path).resolve(strict=True)) == digest, 'Input changed: ' + path)

    def compiler_commands(self):
        command = ' '.join([str(self.tools['gcc'])] + self.flags)
        return {'CC': command, 'CXX': command + ' -shared-libgcc -nostdinc++'}

    def prepare_gthreads(self, source):
        source = Path(source)
        mapping, makefile = source / 'config/gthr.m4', source / 'libgcc/Makefile.in'
        headers = re.findall(r'^\s+posix\)\s+thread_header=([A-Za-z0-9_.-]+) ;;', mapping.read_text(), re.M)
        require(headers == ['gthr-posix.h'], 'Unexpected upstream POSIX thread header')
        rule = re.search(r'^gthr-default\.h: \$\(srcdir\)/\$\(thread_header\)\n\t-\$\(LN_S\) \$< \$@\n', makefile.read_text(), re.M)
        require(rule, 'Unexpected upstream gthr-default rule')
        directory = self.work / 'build' / self.triplet / 'libgcc'
        directory.mkdir(parents=True, exist_ok=True)
        rulefile = self.work / 'gthreads.mk'
        rulefile.write_text(rule[0])
        logged([self.make, '-f', rulefile, 'srcdir=' + str(source / 'libgcc'), 'thread_header=' + headers[0], 'LN_S=ln -s', 'gthr-default.h'], self.work / 'gthreads.log', self.env, directory)
        generated, expected = directory / 'gthr-default.h', source / 'libgcc' / headers[0]
        require(generated.is_symlink() and generated.resolve(strict=True) == expected.resolve(strict=True), 'Incorrect generated thread header')
        for path in (mapping, makefile, expected, rulefile, generated, self.work / 'gthreads.log'):
            self.record(path)

    def build(self):
        self.preflight()
        if self.check:
            return
        work = self.work
        work.mkdir()
        (work / 'parent-recipe/lang').mkdir(parents=True)
        shutil.copytree(self.old_pkgsrc / 'lang/gcc16', work / 'parent-recipe/lang/gcc16', symlinks=True)
        (work / 'parent').mkdir()
        for name in inheritance.PARENT_FILES:
            shutil.copy2(self.old_work / name, work / 'parent' / name)
        shutil.copytree(self.old_work / 'stage', work / 'parent/stage', symlinks=True)
        parent_paths = {'archive': str(self.archive), 'pkgsrc': str(self.old_pkgsrc)}
        Stage(work / 'parent', work / 'parent-recipe', self.archive, receipt_paths=parent_paths, allow_rebuild=False, historical=True).verify()
        with (work / 'patch.log').open('xb') as output:
            prepare_source(self.pkgsrc, self.archive, work / 'src', output=output)
        self.prepare_gthreads(work / 'src')
        build = work / 'build' / self.triplet / 'libstdc++-v3'
        build.mkdir(parents=True)
        env = dict(self.env, **self.compiler_commands(), CFLAGS=self.target_flags, CXXFLAGS=self.target_flags, CPPFLAGS='', LDFLAGS='-L' + str(self.sysroot / 'usr/pkg/gcc16/lib') + ' -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-z,relro', **CACHE)
        for name in TOOLS:
            env[name.upper()] = str(self.tools[name])
        build_triplet = capture(['sh', work / 'src/config.guess']).strip()
        args = ['--build=' + build_triplet, '--host=' + self.triplet, '--target=' + self.triplet, '--with-cross-host=' + build_triplet, '--with-target-subdir=' + self.triplet, '--prefix=/usr/pkg/gcc16', '--libdir=/usr/pkg/gcc16/lib', '--with-toolexeclibdir=/usr/pkg/gcc16/lib', '--with-local-prefix=/usr/pkg/gcc16', '--with-gxx-include-dir=/usr/pkg/gcc16/include/c++', '--with-sysroot=' + str(self.sysroot), '--with-native-system-header-dir=/usr/include', '--with-gnu-as', '--with-gnu-ld', '--with-as=' + str(self.tools['as']), '--with-ld=' + str(self.tools['ld']), '--disable-multilib', '--enable-shared', '--enable-threads=posix', '--enable-long-long', '--disable-libssp', '--disable-libstdcxx-pch', '--disable-nls', '--program-transform-name=s&^&' + self.triplet + '-&', '--disable-year2038']
        jsonio.write_json(work / 'commands.json', {'environment': env, 'configure': args})
        logged([work / 'src/libstdc++-v3/configure'] + args, work / 'configure.log', env, build)
        require('config/locale/generic/c_locale.cc' in (build / 'config.status').read_text(), 'Expected generic locale backend')
        require(re.search(r'^#define _GLIBCXX_HAS_GTHREADS 1$', (build / 'config.h').read_text(), re.M), 'C++ threads unavailable')
        logged([self.make, '-j' + self.count, 'all'], work / 'runtime-build.log', env, build)
        logged([self.make, 'DESTDIR=' + str(work / 'stage'), 'install'], work / 'runtime-install.log', env, build)
        require(sha(work / 'stage/usr/pkg/gcc16/include/c++' / self.triplet / 'bits/c++locale.h') == sha(work / 'src/libstdc++-v3/config/locale/generic/c_locale.h'), 'Installed locale header differs from prepared source')
        fresh = inheritance.inventory(work / 'stage')
        old = inheritance.inventory(work / 'parent/stage')
        inherited = {path: old[path] for path in inheritance.inherited_paths(self.parent)}
        for path, record in inherited.items():
            target = work / 'stage' / path
            require(paths.entry(target) is None, 'Overlapping installation ownership')
            target.parent.mkdir(parents=True, exist_ok=True)
            if 'link' in record:
                target.symlink_to(record['link'])
            else:
                shutil.copy2(work / 'parent/stage' / path, target)
        self.unchanged_inputs()
        receipts = {name: sha(work / 'parent' / name) for name in inheritance.PARENT_FILES}
        logs = {name: sha(work / name) for name in ('configure.log', 'runtime-build.log', 'runtime-install.log')}
        (work / 'configuration').mkdir()
        for name in ('config.status', 'config.h'):
            shutil.copy2(build / name, work / 'configuration' / name)
        configuration = {name: sha(work / name) for name in inheritance.CONFIG_FILES}
        jsonio.write_json(work / 'inheritance.json', {'format': 1, 'parent_paths': parent_paths, 'parent_receipts': receipts, 'inherited': inherited, 'rebuilt': fresh, 'build_logs': logs, 'configuration': configuration})
        for path in [work / 'inheritance.json', work / 'src/libstdc++-v3/configure'] + [work / name for name in inheritance.CONFIG_FILES]:
            self.record(path)
        metadata = self.parent['metadata']
        receipt = 'scope=runtime-libstdcxx-rebuild\ntarget=' + self.target + '\ntriplet=' + self.triplet + '\nseed_source=' + metadata['EMBERBSD_SEED_SOURCE'] + '\nruntime_libraries=' + metadata['GCC_RUNTIME_LIBRARIES'] + '\n' + ''.join(digest + '  ' + path + '\n' for path, digest in self.inputs.items())
        (work / 'inputs.txt').write_text(receipt)
        manifests(work / 'stage', work)
        (work / 'build-success').write_text('runtime-libstdcxx-rebuild\n')
        try:
            jsonio.write_json(work / 'stage-check.json', Stage(work, self.pkgsrc, self.archive, historical=True).verify())
        except BaseException:
            (work / 'build-success').rename(work / 'failed-stage-marker')
            raise
        print('Verified libstdc++ provenance: ' + str(work / 'stage') + '; inherited hardening and target acceptance remain separate')
