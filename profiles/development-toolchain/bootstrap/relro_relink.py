# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; reproduce real archived GCC16 links before RELRO hardening.
from pathlib import Path
import re
import shlex
import shutil
import tarfile
from emberbsd_sdk import inventory, jsonio, paths
from host import *
from runtime import Stage, ELF, LIBRARIES, SELECTIONS, TARGETS as RUNTIME_TARGETS
from libstdcxx import LibstdcxxRebuild
import relro


class RelroRelink:
    def __init__(self, args):
        require(len(args) == 11, 'Usage: relink-relro.py TARGET NEW_PKGSRC OLD_PKGSRC ARCHIVE COMPILER SYSROOT OLD_WORK LOCALE_WORK BACKUP BACKUP_SHA256 NEW_WORK --sdk-source SOURCE')
        self.target, pkgsrc, old_pkgsrc, archive, compiler, sysroot, old, parent, backup, self.backup_sha, work = args
        require(re.fullmatch(r'[0-9a-f]{64}', self.backup_sha), 'Expected archive SHA256')
        self.pkgsrc, self.archive, self.old, self.parent, self.backup, self.work = [build_path(value) for value in (pkgsrc, archive, old, parent, backup, work)]
        self.preflight = LibstdcxxRebuild(['--check', self.target, pkgsrc, old_pkgsrc, archive, compiler, sysroot, old, work])
        self.readelf = Path(compiler) / 'bin' / (TARGETS[self.target][0] + '-readelf')
        self.stock = Path(old_pkgsrc) / 'mk/check/check-relro-elf.awk'
        self.inputs, self.commands = {}, []

    def record(self, path):
        path = Path(path).resolve(strict=True)
        self.inputs[str(path)] = sha(path)

    def abi(self, path):
        data = capture([self.readelf, '--dyn-syms', '--wide', path])
        rows = []
        for line in data.splitlines():
            fields = line.split()
            if len(fields) >= 8 and re.fullmatch(r'[0-9]+:', fields[0]) and fields[6] != 'UND':
                rows.append([fields[2], fields[3], fields[4], fields[5], fields[7]])
        require(rows, 'No dynamic symbols')
        return sorted(rows)

    def run(self):
        self.preflight.preflight()
        require(sha(self.backup) == self.backup_sha, 'Archived bootstrap hash mismatch')
        require((self.parent / 'build-success').read_text() == 'runtime-libstdcxx-rebuild\n', 'Expected completed locale rebuild')
        parent = Stage(self.parent, self.pkgsrc, self.archive, historical=True).verify()
        require(parent['metadata']['GCC_RUNTIME_LIBRARIES'] == SELECTIONS[-1], 'All four runtime libraries required')
        require(parent['metadata']['GCC_RUNTIME_TARGET'] == self.target, 'Locale target differs')
        work = self.work
        work.mkdir(); (work / 'proof').mkdir()
        root, triplet = self.old.name, TARGETS[self.target][0]
        driver = 'xgcc collect2 collect-ld specs libgcc_s.so libgcc_s.so.1 libgcc_s_asneeded.so crtbeginS.o crtendS.o libgcc.a liblto_plugin.so'.split()
        rules = 'libatomic/libatomic.map libgcc/config/t-slibgcc libgcc/config/t-slibgcc-gld libgcc/Makefile.in libgomp/Makefile.in libatomic/Makefile.in'.split()
        receipts = [name for name in relro.PARENT if name != 'inheritance.json'] + ['runtime-build.log']
        with tarfile.open(self.backup, 'r:gz') as archive:
            listing = archive.getnames()
            members = [name for name in listing if re.match(re.escape(root + '/build/' + triplet) + r'/(?:libgcc|libgomp|libatomic)/', name) and not archive.getmember(name).isdir()]
            members += [root + '/build/gcc/' + name for name in driver] + [root + '/' + name for name in receipts] + [root + '/src/' + name for name in rules]
            require(len(members) == len(set(members)) and all(re.fullmatch(r'[A-Za-z0-9_+./-]+', name) and '..' not in name.split('/') and listing.count(name) == 1 for name in members), 'Unsafe or missing archive members')
            (work / 'members.txt').write_text(''.join(name + '\n' for name in members))
            archive.extractall(work, members=[archive.getmember(name) for name in members], filter='data')
        restored = work / root
        for name in receipts:
            require(sha(restored / name) == sha(self.old / name), 'Archived original receipt mismatch')
        for name, record in inventory.snapshot_tree(restored).items():
            if record['kind'] == 'file':
                self.record(restored / name)
        for path in [self.readelf, work / 'members.txt'] + policy_sources() + sorted((PROFILE / 'bootstrap').glob('*.py')) + sorted((PROFILE / 'runtime/recipe/files').glob('*.py')):
            self.record(path)
        match = re.search(r'^ORIGINAL_LD_FOR_TARGET=[\'\"]?([^\'\"\n]+)[\'\"]?$', (restored / 'build/gcc/collect-ld').read_text(), re.M)
        require(match and Path(match[1]).is_absolute() and os.access(match[1], os.X_OK), 'Missing absolute original linker')
        linker = match[1]
        lines = (restored / 'inputs.txt').read_text().splitlines(keepends=True)
        require(sha(linker) + '  ' + linker + '\n' in lines, 'Original linker differs from authenticated bootstrap')
        self.record(linker)
        seeds = [line.strip().removeprefix('sysroot=') for line in lines if line.startswith('sysroot=')]
        require(len(seeds) == 1, 'Expected one original seed')
        for name in ('libc.so.12', 'libpthread.so.1', 'libm.so.0', 'crt0.o'):
            path = Path(seeds[0]) / 'usr/lib' / name
            require(sha(path.resolve(strict=True)) + '  ' + str(path) + '\n' in lines, 'Original seed differs from bootstrap')
            self.record(path)
        require(capture([restored / 'build/gcc/xgcc', '-dumpfullversion']).strip() == VERSION and capture([restored / 'build/gcc/xgcc', '-dumpmachine']).strip() == triplet, 'Wrong archived compiler version/target')
        log = (restored / 'runtime-build.log').read_text().splitlines()
        components = {}
        for library, basename in relro.COMPONENTS.items():
            selected = [line for line in log if (line.startswith(str(self.old) + '/build/./gcc/xgcc') and '-o ./libgcc_s.so.1.tmp' in line if library == 'libgcc' else line.startswith('libtool: link: ') and '-o .libs/' + basename in line)]
            require(len(selected) == 1, 'Expected one original link command')
            original = shlex.split(selected[0].removeprefix('libtool: link: ').split(' && ', 1)[0])
            argv = [word.replace(str(self.old), str(restored)) for word in original]
            require(argv[0] == str(restored) + '/build/./gcc/xgcc' and argv.count('-o') == 1 and '-shared' in argv and '-c' not in argv, 'Unexpected original link driver/output')
            index = argv.index('-o')
            outputs = []
            for harden in (False, True):
                output = work / 'proof' / (basename + ('.relro' if harden else '.baseline'))
                command = list(argv)
                command[index + 1] = str(output)
                if harden:
                    command.append('-Wl,-z,relro')
                name = library + ('-relro' if harden else '-baseline')
                try:
                    logged(command, work / (name + '.stdout'), cwd=restored / 'build' / triplet / library)
                    (work / (name + '.stderr')).write_bytes(b'')
                    status = 0
                except Exception as error:
                    (work / (name + '.stderr')).write_text(str(error) + '\n')
                    status = getattr(error, 'returncode', None)
                    self.commands.append({'component': library, 'argv': command, 'status': status})
                    jsonio.write_json(work / 'commands.json', self.commands, exclusive=not (work / 'commands.json').exists())
                    raise
                self.commands.append({'component': library, 'argv': command, 'status': status})
                jsonio.write_json(work / 'commands.json', self.commands, exclusive=not (work / 'commands.json').exists())
                outputs.append(output)
            relative = 'usr/pkg/gcc16/lib/' + basename
            require(sha(outputs[0]) == sha(self.parent / 'stage' / relative), 'Baseline does not reproduce original bytes')
            old_abi = self.abi(outputs[0])
            require(old_abi == self.abi(outputs[1]), 'Runtime symbol identity or size changed')
            jsonio.write_json(work / (library + '-abi.json'), old_abi)
            before = ELF(outputs[0]).verify(LIBRARIES[library], RUNTIME_TARGETS[self.target], list(LIBRARIES.values()), require_relro=False)
            after = ELF(outputs[1]).verify(LIBRARIES[library], RUNTIME_TARGETS[self.target], list(LIBRARIES.values()))
            require(before == after, 'Runtime dependency changed')
            components[library] = {'path': relative, 'before': sha(outputs[0]), 'after': sha(outputs[1])}
        for mode in ('baseline', 'relro'):
            files = [str(work / 'proof' / (name + '.' + mode)) for name in relro.COMPONENTS.values()]
            result = process.capture(['awk', '-f', str(self.stock)], env=environment({'READELF': str(self.readelf)}), input=('\n'.join(files) + '\n').encode())
            (work / ('stock-' + mode + '.stdout')).write_bytes(result.stdout)
            (work / ('stock-' + mode + '.stderr')).write_bytes(result.stderr)
            expected = ''.join(path + ': missing RELRO\n' for path in files) if mode == 'baseline' else ''
            require(not result.stderr and result.stdout.decode() == expected, 'Stock pkgsrc RELRO check differs')
        for path in [self.stock, work / 'commands.json'] + [path for path in work.iterdir() if path.suffix in ('.stdout', '.stderr', '.json')]:
            self.record(path)
        for path, digest in self.inputs.items():
            require(sha(path) == digest, 'Relink input changed')
        shutil.copytree(self.parent / 'stage', work / 'stage', symlinks=True)
        for record in components.values():
            shutil.copyfile(work / 'proof' / (Path(record['path']).name + '.relro'), work / 'stage' / record['path'])
        receipt = {'format': 1, 'parent_work': str(self.parent.resolve(strict=True)), 'parent_receipts': {name: sha(self.parent / name) for name in relro.PARENT}, 'backup': {'path': str(self.backup.resolve(strict=True)), 'sha256': self.backup_sha}, 'inputs': self.inputs, 'components': components}
        jsonio.write_json(work / 'relink.json', receipt)
        inputs = (self.parent / 'inputs.txt').read_text().replace('scope=runtime-libstdcxx-rebuild\n', 'scope=runtime-relro-relink\n', 1)
        (work / 'inputs.txt').write_text(inputs + digest_rows([work / 'relink.json']))
        manifests(work / 'stage', work)
        (work / 'build-success').write_text('runtime-relro-relink\n')
        try:
            jsonio.write_json(work / 'stage-check.json', Stage(work, self.pkgsrc, self.archive).verify())
        except BaseException:
            (work / 'build-success').rename(work / 'failed-stage-marker')
            raise
        print('PASS: exact original baseline DSOs, three real RELRO relinks, unchanged ABI and ordinary stage gates; target runtime pending')
