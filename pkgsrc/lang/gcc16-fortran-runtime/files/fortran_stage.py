# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); verified GCC16 Fortran runtime and SDK roles.
"""Inspect or stage host-built target data. Never run a target executable."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import tarfile

from emberbsd_sdk import elf, inventory, jsonio, paths
from emberbsd_sdk.errors import SDKError
from runtime import Stage as BaseStage, SOURCE_SHA256, TARGETS, VERSION

NAMES = {'runtime': 'gcc16-fortran-runtime-16.2.0',
         'devel': 'gcc16-fortran-devel-16.2.0'}
BASE = 'gcc16-runtime-16.2.0nb6'
SONAMES = ('libgfortran.so.5', 'libquadmath.so.0')
LICENSES = {'COPYING3': 'COPYING3', 'COPYING.RUNTIME': 'COPYING.RUNTIME',
            'libquadmath/COPYING.LIB': 'libquadmath-COPYING.LIB',
            'libbacktrace/backtrace.h': 'libbacktrace-notice.h'}


def require(condition, message):
    if not condition:
        raise SDKError(message)


def digest(path):
    return inventory.sha256_file(path)


def inspect_stage(stage, target):
    require(target in TARGETS, 'Unsupported Fortran target')
    architecture = TARGETS[target]
    stage = Path(paths.canonical_existing(stage))
    tree = inventory.snapshot_tree(stage, machine=architecture['elf_machine'])
    runtime, development, records, generated = [], [], {}, []
    prefix = 'usr/pkg/gcc16/'
    triplet = re.escape(architecture['triplet'])
    development_pattern = re.compile(
        r'lib/lib(?:gfortran|quadmath)[.](?:a|la|so)$|lib/libgfortran[.]spec$|'
        r'lib/gcc/' + triplet + r'/16[.]2[.]0/(?:'
        r'include/(?:ISO_Fortran_binding|quadmath|quadmath_weak)[.]h|'
        r'finclude/ieee_(?:arithmetic|exceptions|features)[.]mod|libcaf_[A-Za-z0-9_]+[.](?:a|la))$|'
        r'share/info/(?:libquadmath[.]info(?:-[0-9]+)?|dir)$')
    for name, row in tree.items():
        if row['kind'] == 'directory':
            require(name in ('usr', 'usr/pkg') or name == prefix.rstrip('/') or name.startswith(prefix),
                    'Fortran stage directory escaped its prefix')
            continue
        require(name.startswith(prefix), 'Fortran payload escaped its prefix')
        relative = name[len(prefix):]
        if relative == 'share/info/dir':
            require(row['kind'] == 'file', 'Info index must be a regular generated file')
            generated.append(name)
            continue
        family = next((soname for soname in SONAMES
                       if re.fullmatch('lib/' + re.escape(soname) + r'(?:[.][0-9]+)*', relative)), None)
        if family:
            actual = (stage / name).resolve(strict=True)
            record = elf.read_elf_dynamic(actual, machine=architecture['elf_machine'])
            require(record['type'] == 3 and record['relro'], 'Fortran runtime needs a target RELRO DSO')
            require(record['soname'] == family, 'Fortran runtime SONAME mismatch')
            require(set(record['needed']) <= set(SONAMES) | {
                'libgcc_s.so.1', 'libatomic.so.3', 'libc.so.12', 'libm.so.0', 'libpthread.so.1'},
                'Foreign Fortran runtime dependency')
            for key in ('rpath', 'runpath'):
                require(record[key] is None or set(record[key].split(':')) <= {
                    '/usr/pkg/gcc16/lib', '/usr/lib', '/lib'}, 'Unsafe Fortran runtime path')
            require(row['kind'] == 'link' or row['mode'] == 0o755, 'Unexpected DSO mode')
            runtime.append(name)
            records[name] = record
        else:
            require(development_pattern.fullmatch(relative), 'Unexpected Fortran stage payload: ' + name)
            # Upstream Libtool uses INSTALL, not INSTALL_DATA, for .la metadata.
            expected_mode = 0o755 if relative.endswith('.la') else 0o644
            require(row['kind'] == 'link' or row['mode'] == expected_mode, 'Unexpected SDK data mode')
            if row['kind'] == 'link' or relative in ('lib/libgfortran.so', 'lib/libquadmath.so'):
                family_name = {'lib/libgfortran.so': 'libgfortran.so.5', 'lib/libquadmath.so': 'libquadmath.so.0'}.get(relative)
                require(row['kind'] == 'link' and family_name is not None and (stage / name).resolve(strict=True) ==
                        (stage / prefix / 'lib' / family_name).resolve(strict=True),
                        'SDK alias does not select its matching runtime family')
            if relative.endswith(('.la', '.spec')):
                require(row['kind'] == 'file', 'Link metadata must be regular')
                text = (stage / name).read_text(encoding='utf-8')
                if relative.endswith('.la'):
                    values = []
                    for line in text.splitlines():
                        if not line.strip() or line.lstrip().startswith('#'): continue
                        require('$' not in line and '`' not in line, 'Nonliteral Libtool metadata')
                        try:
                            lexer = shlex.shlex(line, posix=True, punctuation_chars=';&|<>()')
                            lexer.whitespace_split = True
                            lexer.commenters = ''
                            fields = list(lexer)
                        except ValueError as error:
                            raise SDKError('Invalid Libtool metadata quoting') from error
                        require(len(fields) == 1 and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*=.*', fields[0]),
                                'Invalid Libtool metadata assignment')
                        values.append(fields[0].partition('=')[2])
                    text = '\n'.join(values)
                for absolute in re.findall(r'/[A-Za-z0-9_+./-]+', text):
                    require('..' not in absolute.split('/') and any(absolute == allowed or absolute.startswith(allowed + '/')
                            for allowed in ('/usr/pkg/gcc16', '/usr/lib', '/lib')),
                            'Build-host path leaked into Fortran link metadata')
            if relative.endswith('.a'):
                require(row['kind'] == 'file' and row['archive']['elf_members'] > 0, 'Empty SDK static archive')
            development.append(name)
    require(all(prefix + 'lib/' + soname in runtime for soname in SONAMES),
            'Incomplete Fortran runtime families')
    require(not (set(runtime) & set(development)), 'Runtime and SDK payloads overlap')
    for name in runtime:
        source = stage / name
        if source.is_symlink():
            require(os.path.normpath(os.path.join(os.path.dirname(name), os.readlink(source))) in runtime,
                    'Unshipped Fortran runtime alias target')
            require(str(source.resolve(strict=True).relative_to(stage)) in runtime,
                    'Fortran runtime alias escaped its role')
    mandatory = [prefix + 'lib/libgfortran.spec', prefix + 'lib/libgfortran.so',
                 prefix + 'lib/libquadmath.so', prefix + 'lib/libgfortran.a',
                 prefix + 'lib/libquadmath.a', prefix + 'lib/gcc/' + architecture['triplet'] +
                 '/16.2.0/include/ISO_Fortran_binding.h']
    versioned = prefix + 'lib/gcc/' + architecture['triplet'] + '/16.2.0/'
    mandatory += [versioned + 'include/' + name for name in ('quadmath.h', 'quadmath_weak.h')]
    mandatory += [versioned + 'finclude/' + name for name in ('ieee_arithmetic.mod', 'ieee_exceptions.mod', 'ieee_features.mod')]
    mandatory += [versioned + name for name in ('libcaf_single.a', 'libcaf_single.la')]
    require(set(mandatory) <= set(development), 'Fortran SDK data is incomplete')
    return {'stage': tree, 'runtime': sorted(runtime), 'devel': sorted(development), 'elf': records, 'generated': generated}


class Stage:
    def __init__(self, work, archive, pkgsrc):
        self.work, self.archive, self.pkgsrc = map(
            lambda x: Path(paths.canonical_existing(x)), (work, archive, pkgsrc))
        self.stage = self.work / 'stage'

    def verify(self):
        paths.real_directory(self.work)
        require(paths.entry(self.work / '.producer-ownership-unproven.json') is None,
                'Producer shutdown is unproven')
        require(digest(self.archive) == SOURCE_SHA256, 'Fortran GCC archive changed')
        receipt = self.work / 'fortran-stage.json'
        paths.regular_file(receipt)
        value = jsonio.read_json(receipt)
        require(value['format'] == 'emberbsd-gcc16-fortran-stage' and type(value['version']) is int
                and value['version'] == 1 and value['status'] == 'BUILT_AND_INSPECTED',
                'No completed Fortran stage')
        target = value['target']
        require(target in TARGETS and value['triplet'] == TARGETS[target]['triplet'],
                'Fortran stage target/triplet mismatch')
        require(value['source_archive_sha256'] == SOURCE_SHA256 and value['base_runtime_name'] == BASE,
                'Fortran stage source or runtime version differs')
        inputs = value['inputs']
        require(type(inputs) is dict and inputs, 'Missing Fortran input hashes')
        for name, expected in inputs.items():
            path = Path(name)
            require(path.is_absolute() and re.fullmatch(r'[0-9a-f]{64}', expected), 'Invalid Fortran input claim')
            require(paths.canonical_existing(path) == str(path), 'Noncanonical Fortran input claim')
            paths.regular_file(path)
            require(digest(path) == expected, 'Changed Fortran input: ' + name)
        commands = self.work / 'commands.json'
        require(inputs.get(str(commands)) == value['commands_sha256'] == digest(commands),
                'Standalone command input binding differs')
        capability = Path(value['compiler_capability'])
        require(str(capability) in inputs, 'Missing frontend capability hash')
        cap = jsonio.read_json(capability)
        require(cap['format'] == 'emberbsd-gcc16-fortran-capability' and type(cap['version']) is int and cap['version'] == 1
                and cap['status'] == 'PASS' and cap['target'] == target,
                'Missing matching real frontend capability')
        require(cap['archive_sha256'] == SOURCE_SHA256 and cap['sources']['recipe'] ==
                inventory.snapshot_tree(self.pkgsrc / 'lang/gcc16'), 'Frontend recipe differs')
        parent = BaseStage(value['base_runtime_work'], self.pkgsrc, self.archive).verify()
        require(parent['metadata'] == value['base_runtime_metadata'] and
                parent['metadata']['PKGNAME'] == BASE and parent['metadata']['GCC_RUNTIME_TARGET'] == target,
                'The exact compatible GCC16 runtime changed')
        for tool in cap['compiler']['tools'].values():
            require(inputs.get(tool['path']) == tool['sha256'], 'Missing frontend tool input binding')
        require(cap['compiler']['version'] == VERSION and cap['compiler']['triplet'] == value['triplet']
                and cap['compiler']['threads'] == 'posix', 'Frontend identity differs')
        result = inspect_stage(self.stage, target)
        allowed = set(parent['metadata']['GCC_RUNTIME_SONAMES'].split(',')) | set(SONAMES) | {
            'libc.so.12', 'libm.so.0', 'libpthread.so.1'}
        require(all(set(row['needed']) <= allowed for row in result['elf'].values()),
                'Fortran needs an unselected base runtime component')
        old_stage = inventory.snapshot_tree(Path(value['base_runtime_work']) / 'stage')
        require(not (set(old_stage) & (set(result['runtime']) | set(result['devel']))),
                'Fortran SDK data overlaps the existing runtime development stage')
        require(result['stage'] == value['stage'], 'Fortran stage bytes, modes or links changed')
        old_paths = {'usr/pkg/' + name for name in parent['files']}
        old_paths.update('usr/pkg/share/licenses/gcc16-runtime/' + name for name in ('COPYING3', 'COPYING.RUNTIME'))
        require(not (old_paths & (set(result['runtime']) | set(result['devel']))),
                'Fortran package overlaps the existing GCC16 runtime')
        result['metadata'] = {'GCC_FORTRAN_TARGET': target, 'GCC_FORTRAN_TRIPLET': value['triplet'],
            'GCC_FORTRAN_MACHINE_ARCH': TARGETS[target]['machine_arch'],
            'GCC_FORTRAN_STAGE_SHA256': digest(receipt), 'GCC_SOURCE_SHA256': SOURCE_SHA256,
            'GCC_FORTRAN_BASE_RUNTIME': BASE}
        return result

    def payload(self, role):
        require(role in NAMES, 'Unknown Fortran package role')
        result = self.verify()
        files = [name.removeprefix('usr/pkg/') for name in result[role]]
        if role == 'runtime':
            files += ['share/licenses/gcc16-fortran-runtime/' + name for name in LICENSES.values()]
        return result, sorted(files)

    def install(self, role, destination):
        result, files = self.payload(role)
        destination = Path(paths.canonical_existing(destination))
        for source in (self.work, self.archive, self.pkgsrc): paths.reject_overlap(source, destination)
        root = destination / 'usr/pkg'
        require(paths.canonical_new(root) == str(root), 'Destination prefix has a symlink ancestor')
        for name in result[role]:
            source, output = self.stage / name, root / name.removeprefix('usr/pkg/')
            require(paths.canonical_new(output) == str(output), 'Destination payload escapes its prefix')
            require(paths.entry(output) is None, 'Refusing existing Fortran payload')
            output.parent.mkdir(parents=True, exist_ok=True)
            if source.is_symlink():
                output.symlink_to(os.readlink(source))
            else:
                shutil.copyfile(source, output)
                output.chmod(result['stage'][name]['mode'])
                require(digest(output) == result['stage'][name]['sha256'], 'Fortran payload changed while copying')
        if role == 'runtime':
            with tarfile.open(self.archive) as archive:
                for source, name in LICENSES.items():
                    member = archive.getmember('gcc-' + VERSION + '/' + source)
                    require(member.isfile() and 0 < member.size < 1024 * 1024, 'Missing component license')
                    output = root / 'share/licenses/gcc16-fortran-runtime' / name
                    require(paths.canonical_new(output) == str(output), 'License destination escaped its prefix')
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with output.open('xb') as stream:
                        stream.write(archive.extractfile(member).read())
                    output.chmod(0o644)
        require(self.verify() == result, 'Fortran stage changed during packaging')
        return files
