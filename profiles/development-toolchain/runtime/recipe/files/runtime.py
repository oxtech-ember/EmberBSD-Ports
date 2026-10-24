#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted host packaging of audited GCC16 target libraries.
"""Verify and package GCC runtime DSOs without executing target code."""
import datetime
import hashlib
import os
from pathlib import Path
import re
import shutil
import sys
sys.dont_write_bytecode = True
import tarfile
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sdk_source

# Library callers select SDK source before importing this module.
if __name__ == '__main__':
    try:
        sdk_source.install_signal_handlers()
        _arguments = sdk_source.arguments(sys.argv[1:])
    except (RuntimeError, OSError, ImportError) as error:
        print('gcc16-runtime: ' + str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 1)
else:
    sdk_source.load()

from emberbsd_sdk.errors import SDKError, CommandError, ProcessOwnershipError
from emberbsd_sdk import elf as sdk_elf, inventory as sdk_inventory, jsonio, paths, process

VERSION = '16.2.0'
NAME = 'gcc16-runtime-16.2.0nb7'
SOURCE_SHA256 = 'e6738e29597f733270731aa90600f37ffdc045079dfc27ec7e8192cc81085c3e'
LICENSES = ('COPYING3', 'COPYING.RUNTIME')
CONFLICTS = ('gcc16<16.2.0nb5', 'gcc16-libs-[0-9]*')
LIBRARIES = {'libgcc': 'libgcc_s.so.1', 'libstdc++': 'libstdc++.so.7', 'libgomp': 'libgomp.so.1', 'libatomic': 'libatomic.so.3'}
SELECTIONS = ('libgcc,libstdc++', 'libgcc,libstdc++,libgomp', 'libgcc,libstdc++,libatomic', 'libgcc,libstdc++,libgomp,libatomic')
TARGETS = {'amd64': {'triplet': 'x86_64--netbsd', 'machine_arch': 'x86_64', 'elf_machine': 62},
           'aarch64': {'triplet': 'aarch64--netbsd', 'machine_arch': 'aarch64', 'elf_machine': 183}}
MATH_PATCHES = {'patch-libstdc++-v3_crossconfig.m4': 'e0efdd76a89b3b317ad9964156c6f6a47ebbf425067b763c0dc056b827910f71',
                'patch-libstdc++-v3_configure_math': '2957e7c72d37c95a8657f27a806bc1e731b21685b869a1dfc84cc38c1e6b0ea2'}
TLS_PATCHES = {'patch-libstdc++-v3_configure_tls': 'dc9b9b3507ce81859ad6aca40e955b719ab8a5c234842d6169a9373240e5dd1d',
               'patch-libstdc++-v3_crossconfig_tls': '21f6cbb1d1493920782117f923c540a498cb3e9350744b573af2445aa876e06c'}
MATH_FUNCTIONS = 'acosf acosl asinf asinl atan2f atan2l atanf atanl ceilf ceill cosf coshf coshl cosl expf expl fabsf fabsl floorf floorl fmodf fmodl frexpl ldexpf ldexpl log10f log10l logf logl modff modfl powf powl sinf sinhf sinhl sinl sqrtf sqrtl tanf tanhf tanhl tanl'.split()
Invalid = SDKError
hash_file = sdk_inventory.sha256_file


def require(condition, message):
    if not condition:
        raise Invalid(message)


def text(path):
    paths.regular_file(path)
    return Path(path).read_text(encoding='utf-8')


def rows(value):
    return value.splitlines(keepends=True)


def field(value, key):
    matches = [line for line in rows(value) if line.startswith(key + '=')]
    require(len(matches) == 1 and matches[0].endswith('\n'), 'Missing or duplicate provenance: ' + key)
    return matches[0][len(key) + 1:-1]


def hash_claims(value, path):
    return [match[1] for line in rows(value) if (match := re.fullmatch(r'([0-9a-f]{64})  (.+)\n?', line)) and match[2] == str(path)]


def relative(value):
    require(value.startswith('./usr/pkg/gcc16/') and '..' not in value.split('/') and re.fullmatch(r'[A-Za-z0-9_+./-]+', value), 'Unsafe stage path: ' + value)
    return value[2:]


class ELF:
    def __init__(self, path):
        self.path = path

    def verify(self, soname, target, runtime_sonames, require_relro=True):
        record = sdk_elf.read_elf_dynamic(self.path, machine=target['elf_machine'])
        require(record['type'] == 3, 'Expected target ELF64 little-endian DSO')
        require(not require_relro or record['relro'], 'Missing GNU_RELRO segment')
        require(record['soname'] == soname, 'Runtime SONAME mismatch')
        require(set(record['needed']) <= set(['libc.so.12', 'libm.so.0', 'libpthread.so.1'] + list(runtime_sonames)), 'Foreign runtime dependency')
        for key in ('rpath', 'runpath'):
            if record[key] is not None:
                require(set(record[key].split(':')) <= {'/usr/pkg/gcc16/lib', '/usr/lib', '/lib'}, 'Unsafe runtime library path')
        return {'soname': soname, 'needed': record['needed'], 'machine': target['machine_arch']}


class Stage:
    def __init__(self, work, pkgsrc, archive, expected_source=SOURCE_SHA256, receipt_paths=None, allow_rebuild=True, historical=False):
        self.work = Path(paths.canonical_existing(work))
        self.pkgsrc = Path(paths.canonical_existing(pkgsrc))
        paths.real_directory(self.work)
        paths.real_directory(self.pkgsrc)
        self.archive = Path(paths.canonical_existing(archive))
        self.stage = self.work / 'stage'
        self.expected_source = expected_source
        self.receipt_paths = receipt_paths
        self.allow_rebuild = allow_rebuild
        self.historical = historical

    def verify_capability_inputs(self, recipe, regular, architecture):
        if self.historical:
            return {}
        for name, expected in MATH_PATCHES.items():
            require(hash_file(recipe / 'patches' / name) == expected, 'Missing or changed GCC16 math source input')
        name = 'usr/pkg/gcc16/include/c++/' + architecture['triplet'] + '/bits/c++config.h'
        require(name in regular, 'Missing generated GCC16 math capability header')
        header = text(self.stage / name)
        for name_ in MATH_FUNCTIONS:
            require(len(re.findall(r'^#define _GLIBCXX_HAVE_' + name_.upper() + r' 1$', header, re.M)) == 1, 'Missing or ambiguous generated math capability: ' + name_)
        result = {'GCC_RUNTIME_CXX_MATH_INPUTS_SHA256': hashlib.sha256((''.join(MATH_PATCHES.values()) + regular[name]).encode()).hexdigest()}
        # Native NetBSD libstdc++ detects TLS. A cross runtime without it lacks
        # std::__once_call and std::__once_callable, which consumers import.
        for name_, expected in TLS_PATCHES.items():
            require(hash_file(recipe / 'patches' / name_) == expected, 'Missing or changed GCC16 TLS source input')
        require(len(re.findall(r'^#define _GLIBCXX_HAVE_TLS 1$', header, re.M)) == 1, 'Missing or ambiguous generated TLS capability')
        result['GCC_RUNTIME_CXX_TLS_INPUTS_SHA256'] = hashlib.sha256((''.join(TLS_PATCHES.values()) + regular[name]).encode()).hexdigest()
        return result

    def verify_support_parent(self, inputs, required):
        claims = [line for line in rows(inputs) if line.startswith('resume_support_prior_inputs_sha256=')]
        if not claims and not required:
            return
        require(required and len(claims) == 1 and re.fullmatch(r'resume_support_prior_inputs_sha256=[0-9a-f]{64}\n', claims[0]), 'Invalid support parent claim')
        parent = self.work / 'support-parent'
        paths.real_directory(parent)
        def verify_document(path, expected=None):
            actual = hash_file(path)
            receipts = hash_claims(inputs, path)
            require(receipts and all(value == actual for value in receipts) and (expected is None or expected == actual), 'Changed support parent receipt: ' + str(path))
        manifest = self.work / 'support-parent.sha256'
        verify_document(manifest)
        producer = 'checkpoint-producer.py' if (parent / 'checkpoint-producer.py').is_file() else 'checkpoint-producer.sh'
        expected_documents = ['inputs.txt', 'failure-exit.txt', 'phase', 'helper-prefix.txt', 'helpers.sha256', producer, 'checkpoint-producer.sha256', 'support-build.log', 'support-host.log', 'configure.log', 'patch.log'] + [tag + '.' + kind for tag in ('source', 'build', 'seed') for kind in ('inventory', 'sha256', 'symlinks')]
        names = []
        for line in rows(text(manifest)):
            match = re.fullmatch(r'([0-9a-f]{64})  (.+)\n', line)
            require(match and Path(match[2]).parent == parent, 'Unsafe support parent manifest')
            names.append(Path(match[2]).name)
            verify_document(match[2], match[1])
        if 'external-compiler.txt' in names:
            expected_documents.append('external-compiler.txt')
        require(sorted(names) == sorted(expected_documents), 'Incomplete support parent documents')
        verify_document(parent / 'external-compiler.txt')
        require(text(parent / 'checkpoint-producer.sha256').split()[0] == hash_file(parent / producer), 'Wrong support checkpoint producer')
        require(text(parent / 'external-compiler.txt').replace('support_target=libgcc-support\n', 'support_target=gcc-leaf-metadata-v1\n', 1) == text(self.work / 'external-compiler.txt'), 'Support resume changed compiler identity')
        require(hash_file(parent / 'inputs.txt') == claims[0].strip().split('=', 1)[1], 'Wrong support parent identity')
        require(text(parent / 'phase') == 'failed-external-support\n' and re.fullmatch(r'[1-9][0-9]*\n', text(parent / 'failure-exit.txt')), 'Wrong support failure phase')
        helpers = parent / 'helpers'
        paths.real_directory(helpers)
        for line in rows(text(parent / 'helpers.sha256')):
            match = re.fullmatch(r'([0-9a-f]{64})  (.+)\n', line)
            require(match and Path(match[2]).parent == helpers, 'Unsafe frozen helper manifest')
            verify_document(match[2], match[1])
        original = text(parent / 'inputs.txt')
        require(field(original, 'scope') == 'runtime-only-external-compiler', 'Wrong original support scope')
        require(hash_claims(original, self.work / 'external-compiler.txt') == [hash_file(parent / 'external-compiler.txt')], 'Original compiler identity hash mismatch')
        for key in 'target triplet seed_source compiler sysroot math jobs runtime_libraries host_cc host_cxx host_cflags host_cxxflags host_ar host_nm host_ranlib'.split():
            require(field(original, key) == field(inputs, key), 'Support parent input changed: ' + key)

    def verify_external_compiler(self, inputs, architecture, support_resumed=False):
        self.verify_support_parent(inputs, support_resumed)
        names = ['external-compiler.txt', 'external-runtime-plan.txt'] + ['external-support/' + name for name in 'libgcc.mvars specs tconfig.h version.h auto-host.h Makefile config.status'.split()]
        documents = {}
        for name in names:
            path = self.work / name
            require(hash_claims(inputs, path) == [hash_file(path)], 'External compiler receipt changed')
            documents[name] = text(path)
        compiler = documents['external-compiler.txt']
        for key, expected in {'compiler_mode': 'external-posix', 'version': VERSION, 'triplet': architecture['triplet'], 'thread_model': 'posix', 'support_target': 'gcc-leaf-metadata-v1', 'target_objects': 'external-compiler'}.items():
            require(field(compiler, key) == expected, 'Wrong external compiler contract: ' + key)
        prefix = field(compiler, 'compiler')
        require(re.fullmatch(r'/[A-Za-z0-9_./-]+', prefix) and '..' not in prefix.split('/'), 'Unsafe external compiler prefix')
        frontends = [field(compiler, key) for key in ('cc1', 'cc1plus')]
        require(all(path.startswith(prefix + '/') and '..' not in path.split('/') for path in frontends), 'External frontend escapes prefix')
        expected = [prefix + '/bin/' + architecture['triplet'] + '-' + name for name in ('gcc', 'g++')] + frontends
        actual = [match[1] for line in rows(compiler) if (match := re.fullmatch(r'[0-9a-f]{64}  (.+)\n', line))]
        require(sorted(actual) == sorted(expected) and len(set(expected)) == 4, 'Incomplete external compiler hash inventory')
        plan = documents['external-runtime-plan.txt']
        require(field(plan, 'support_target') == 'gcc-leaf-metadata-v1' and field(plan, 'target_objects') == 'external-compiler', 'Wrong external support target')
        command = field(plan, 'CC')
        expected_command = prefix + '/bin/' + architecture['triplet'] + '-gcc --sysroot=' + field(inputs, 'sysroot') + ' -B'
        support = command[len(expected_command):]
        require(command.startswith(expected_command) and re.fullmatch(r'/[A-Za-z0-9_./-]+/build/gcc/', support) and '..' not in support.split('/'), 'External runtime selected different compiler or seed')
        require(field(plan, 'CXX') == command + ' -shared-libgcc -nostdinc++', 'External C++ runtime selected different compiler')
        require(not re.search(r'(?:^|\s)(?:all-gcc|all-target-|install-gcc)', plan), 'External runtime selected compiler recursion')

    def verify(self):
        require(paths.entry(self.work / sdk_source.PRODUCER_QUARANTINE) is None, 'Producer shutdown is unproven. Recover this work explicitly before reuse')
        marker = text(self.work / 'build-success')
        scope = marker.rstrip('\n')
        support_resumed = scope == 'runtime-only-external-support-resume'
        external = scope == 'runtime-only-external-compiler' or support_resumed
        rebuild, relink = scope == 'runtime-libstdcxx-rebuild', scope == 'runtime-relro-relink'
        require(marker in ('runtime-only-bootstrap\n', 'runtime-only-external-compiler\n', 'runtime-only-external-support-resume\n') or (self.allow_rebuild and marker in ('runtime-libstdcxx-rebuild\n', 'runtime-relro-relink\n')), 'No completed runtime stage')
        inputs = text(self.work / 'inputs.txt')
        require(field(inputs, 'scope') == scope, 'Expected runtime-only bootstrap scope')
        target = field(inputs, 'target')
        require(target in TARGETS, 'Unsupported runtime target')
        architecture = TARGETS[target]
        require(field(inputs, 'triplet') == architecture['triplet'], 'Runtime target/triplet mismatch')
        choices = [line for line in rows(inputs) if line.startswith('runtime_libraries=')]
        require(len(choices) <= 1, 'Duplicate runtime library selection')
        require(not choices or choices[0].endswith('\n'), 'Unterminated runtime library selection')
        selection = field(inputs, 'runtime_libraries') if choices else SELECTIONS[0]
        require(selection in SELECTIONS, 'Unsupported runtime library selection')
        sonames = [LIBRARIES[name] for name in selection.split(',')]
        seed = field(inputs, 'seed_source')
        require(re.fullmatch(r'[0-9a-f]{40}', seed), 'Missing seed source commit')
        require(hash_file(self.archive) == self.expected_source, 'GCC source archive mismatch')
        recipe = self.pkgsrc / 'lang/gcc16'
        recipe_files = [recipe / name for name in ('distinfo', 'Makefile', 'Makefile.common')] + sorted(path for path in (recipe / 'patches').iterdir() if path.is_file())
        for path in [self.archive] + recipe_files:
            receipt_path = str(path)
            if self.receipt_paths:
                receipt_path = self.receipt_paths['archive'] if path == self.archive else self.receipt_paths['pkgsrc'] + str(path)[len(str(self.pkgsrc)):]
            require(hash_claims(inputs, receipt_path) == [hash_file(path)], 'Source/recipe receipt mismatch: ' + str(path))
        if external:
            self.verify_external_compiler(inputs, architecture, support_resumed)
        regular, links = {}, {}
        for line in rows(text(self.work / 'stage.sha256')):
            match = re.fullmatch(r'([0-9a-f]{64})  (.+)\n', line)
            require(match, 'Invalid stage hash manifest')
            path = relative(match[2])
            require(path not in regular, 'Duplicate stage path')
            regular[path] = match[1]
        for line in rows(text(self.work / 'stage.symlinks')):
            pair = line.rstrip('\n').split('\t')
            require(len(pair) == 2 and pair[1], 'Invalid symlink')
            path = relative(pair[0])
            require(path not in links, 'Duplicate symlink')
            links[path] = pair[1]
        tree = sdk_inventory.snapshot_tree(self.stage)
        actual_regular, actual_links = {}, {}
        for path, record in tree.items():
            if record['kind'] == 'file':
                actual_regular[path] = record['sha256']
            elif record['kind'] == 'link':
                actual_links[path] = record['target']
                require(paths.inside((self.stage / path).resolve(strict=True), self.stage / 'usr/pkg/gcc16'), 'Stage symlink escapes runtime prefix')
        require(actual_regular == regular and actual_links == links, 'Stage inventory or file hash mismatch')
        capability_inputs = self.verify_capability_inputs(recipe, regular, architecture)
        all_paths = list(regular) + list(links)
        for path in all_paths:
            if re.fullmatch(r'usr/pkg/gcc16/lib/(?:libgcc_s|libstdc\+\+|libgomp|libatomic)\.so\.[0-9]+(?:\.[0-9]+)*', path):
                require(any(re.fullmatch(re.escape(name) + r'(?:\.[0-9]+)*', Path(path).name) for name in sonames), 'Unselected or foreign runtime ABI in stage: ' + path)
        selected = sorted(path for path in all_paths if any(re.fullmatch('usr/pkg/gcc16/lib/' + re.escape(name) + r'(?:\.[0-9]+)*', path) for name in sonames))
        require(all('usr/pkg/gcc16/lib/' + name in selected for name in sonames), 'Required runtime DSOs missing')
        records = {}
        for path in selected:
            source = self.stage / path
            if source.is_symlink():
                immediate = os.path.normpath(os.path.join(os.path.dirname(path), os.readlink(source)))
                require(immediate in selected, 'Runtime alias requires unshipped intermediate link')
            resolved = source.resolve(strict=True)
            require(str(resolved.relative_to(self.stage)) in selected, 'Runtime alias points outside selected payload')
            soname = next(name for name in sonames if re.fullmatch(re.escape(name) + r'(?:\.[0-9]+)*', Path(path).name))
            records[path.removeprefix('usr/pkg/')] = ELF(resolved).verify(soname, architecture, sonames, require_relro=not self.historical)
        digest = hashlib.sha256(''.join(str(path.relative_to(recipe)) + ' ' + hash_file(path) + '\n' for path in sorted(recipe_files)).encode()).hexdigest()
        result = {'files': [path.removeprefix('usr/pkg/') for path in selected], 'metadata': {
            'OPSYS': 'NetBSD', 'OS_VERSION': '11.0', 'MACHINE_ARCH': architecture['machine_arch'], 'PKGPATH': 'lang/gcc16-runtime', 'PKGNAME': NAME, 'LICENSE': 'gnu-gpl-v3', 'GCC_VERSION': VERSION, 'GCC_RUNTIME_SONAME': 'libstdc++.so.7', 'GCC_RUNTIME_LIBRARIES': selection, 'GCC_RUNTIME_SONAMES': ','.join(sonames), 'GCC_RUNTIME_TARGET': target, 'GCC_RUNTIME_TRIPLET': architecture['triplet'], 'GCC_RUNTIME_MACHINE_ARCH': architecture['machine_arch'], 'GCC_SOURCE_SHA256': self.expected_source, 'GCC_RECIPE_SHA256': digest, 'GCC_RECIPE_DISTINFO_SHA256': hash_file(recipe / 'distinfo'), 'GCC_RUNTIME_INPUTS_SHA256': hash_file(self.work / 'inputs.txt'), 'GCC_RUNTIME_STAGE_SHA256': hash_file(self.work / 'stage.sha256'), 'GCC_RUNTIME_LINKS_SHA256': hash_file(self.work / 'stage.symlinks'), 'EMBERBSD_SEED_SOURCE': seed}, 'elf': records}
        result['metadata'].update(capability_inputs)
        if not self.historical:
            import tls_abi
            result['tls_abi'] = tls_abi.inspect(
                (self.stage / 'usr/pkg/gcc16/lib/libstdc++.so.7').resolve(strict=True),
                architecture['elf_machine'])
        if rebuild:
            import inheritance
            result['metadata'].update(inheritance.verify(self.work, self.pkgsrc, self.archive, result, expected_source=self.expected_source))
        if relink:
            import relro
            result['metadata'].update(relro.verify(self.work, self.pkgsrc, self.archive, result, expected_source=self.expected_source))
        return result

    def install(self, destination):
        require(not self.historical, 'Historical provenance cannot be installed or packaged')
        result = self.verify()
        prefix = Path(destination) / 'usr/pkg'
        for path in result['files']:
            source, target = self.stage / 'usr/pkg' / path, prefix / path
            require(paths.entry(target) is None, 'Refusing existing payload: ' + str(target))
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_symlink():
                target.symlink_to(os.readlink(source))
            else:
                shutil.copyfile(source, target)
                target.chmod(0o755)
                require(hash_file(target) == hash_file(source), 'Runtime changed while copying')
        with tarfile.open(self.archive) as archive:
            for name in LICENSES:
                member = archive.getmember('gcc-' + VERSION + '/' + name)
                require(member.isfile() and member.size > 0, 'Cannot read GCC license: ' + name)
                data = archive.extractfile(member).read()
                target = prefix / 'share/licenses/gcc16-runtime' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(data)
                target.chmod(0o644)
        require(hash_file(self.archive) == self.expected_source, 'Source archive changed during license extraction')
        require(self.verify() == result, 'Stage changed during packaging')
        return result


def plist(result):
    return '\n'.join(['@name ' + NAME] + ['@pkgcfl ' + name for name in CONFLICTS] + result['files'] + ['share/licenses/gcc16-runtime/' + name for name in LICENSES]) + '\n'


def validate_pkgtools_version(value):
    require(type(value) is str and re.fullmatch(r'[1-9][0-9]{7}', value), 'Invalid native pkgtools version')
    try:
        datetime.date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError as error:
        raise Invalid('Invalid native pkgtools version') from error
    return value


def native_pkgtools(executable):
    digest = hash_file(executable)
    result = process.capture([str(executable), '-V'])
    require(not result.stderr and re.fullmatch(rb'[0-9]{8}\n', result.stdout), 'Cannot query native pkg_create version')
    version = validate_pkgtools_version(result.stdout.decode().rstrip('\n'))
    require(hash_file(executable) == digest, 'Native pkg_create changed during version query')
    return {'PKGTOOLS_VERSION': version, 'EMBERBSD_PKG_CREATE_SHA256': digest}


def audit_package(package, payload, result):
    metadata = result['metadata']
    validate_pkgtools_version(metadata['PKGTOOLS_VERSION'])
    require(re.fullmatch(r'[0-9a-f]{64}', metadata['EMBERBSD_PKG_CREATE_SHA256']), 'Missing native pkg_create digest')
    files = result['files'] + ['share/licenses/gcc16-runtime/' + name for name in LICENSES]
    allowed = {'+CONTENTS', '+COMMENT', '+DESC', '+BUILD_INFO', '+BUILD_VERSION', '+SIZE_PKG', '+SIZE_ALL'}
    with tarfile.open(package) as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        require(len(set(names)) == len(names) and sorted(set(names) - allowed) == sorted(files), 'Unexpected runtime package payload')
        for name in files:
            expected, actual = Path(payload) / name, archive.getmember(name)
            if expected.is_symlink():
                require(actual.issym() and actual.linkname == os.readlink(expected), 'Package symlink changed')
            else:
                require(actual.isfile() and hashlib.sha256(archive.extractfile(actual).read()).hexdigest() == hash_file(expected), 'Package bytes changed')
        build_info = archive.extractfile('+BUILD_INFO').read().decode().splitlines()
        require(all([line for line in build_info if line.startswith(key + '=')] == [key + '=' + value] for key, value in metadata.items()), 'Target package metadata changed or duplicated')
        contents = archive.extractfile('+CONTENTS').read().decode().splitlines()
        require(all('@pkgcfl ' + name in contents for name in CONFLICTS), 'Missing runtime conflicts')
        require('@cwd /usr/pkg' in contents, 'Wrong installed prefix')


def create(stage, pkg_create, output):
    pkg_create, output = str(pkg_create), Path(output)
    require(os.path.isabs(pkg_create) and os.access(pkg_create, os.X_OK), 'Use absolute native pkg_create path')
    require(output.is_absolute() and paths.entry(output) is None, 'Output must be new absolute directory')
    packaging = native_pkgtools(pkg_create)
    output.mkdir()
    tmp = None
    producer_pending = False
    try:
        tmp = Path(tempfile.mkdtemp(prefix='gcc16-runtime-package-'))
        stage_result = stage.install(tmp / 'payload')
        result = dict(stage_result, metadata=dict(stage_result['metadata'], **packaging))
        (tmp / 'PLIST').write_text(plist(result))
        (tmp / 'BUILD_INFO').write_text(''.join(key + '=' + value + '\n' for key, value in result['metadata'].items()))
        (tmp / 'COMMENT').write_text('GCC16 target runtime libraries for EmberBSD\n')
        (tmp / 'DESCR').write_text('GCC 16.2 target shared libraries with the GCC Runtime Library Exception.\nNo compiler, headers, CRT objects or static libraries are installed.\n')
        package = output / (NAME + '.tgz')
        producer_pending = True
        try:
            process.run_logged([pkg_create, '-u', 'root', '-g', 'wheel', '-p', str(tmp / 'payload/usr/pkg'), '-I', '/usr/pkg', '-B', str(tmp / 'BUILD_INFO'), '-c', str(tmp / 'COMMENT'), '-d', str(tmp / 'DESCR'), '-f', str(tmp / 'PLIST'), str(package)], tmp / 'pkg-create.log', env=process.sanitized_environment())
        except CommandError:
            producer_pending = False
            raise
        except ProcessOwnershipError:
            # The shared process API could not prove a safe producer exit.
            # Retain every path that a live descendant could still access.
            raise
        except BaseException:
            # run_logged propagates an interruption only after it drains its group.
            producer_pending = False
            raise
        else:
            producer_pending = False
        audit_package(package, tmp / 'payload/usr/pkg', result)
        require(hash_file(pkg_create) == packaging['EMBERBSD_PKG_CREATE_SHA256'], 'Native pkg_create changed while creating package')
        require(stage.verify() == stage_result, 'Stage changed while creating package')
        (output / 'package.sha256').write_text(hash_file(package) + '  ' + NAME + '.tgz\n')
        jsonio.write_json(output / 'provenance.json', result)
    except BaseException as error:
        if producer_pending:
            raise Invalid('Package producer shutdown is unproven. Retained output ' + str(output) + ' and work ' + str(tmp) + ': ' + str(error)) from error
        shutil.rmtree(output)
        raise
    finally:
        if tmp is not None and not producer_pending:
            shutil.rmtree(tmp)


def main(arguments):
    require(arguments and arguments[0] in ('check', 'fields', 'plist', 'install', 'create'), 'Usage: runtime.py check|fields|plist|install|create WORK ARCHIVE PKGSRC [DESTDIR|PKG_CREATE NEW_OUTPUT] --sdk-source SOURCE')
    mode, *values = arguments
    require(len(values) == {'check': 3, 'fields': 3, 'plist': 3, 'install': 4, 'create': 5}[mode], 'Wrong argument count')
    work, archive, pkgsrc, *rest = values
    stage = Stage(work, pkgsrc, archive)
    if mode == 'install':
        stage.install(rest[0])
    elif mode == 'create':
        create(stage, *rest)
    else:
        result = stage.verify()
        if mode == 'check':
            import json
            print(json.dumps(result, indent=2))
        elif mode == 'fields':
            print(''.join(key + '=' + value + '\n' for key, value in result['metadata'].items() if key.startswith('GCC_') or key == 'EMBERBSD_SEED_SOURCE'), end='')
        else:
            print(''.join(line + '\n' for line in plist(result).splitlines() if not line.startswith('@')), end='')


if __name__ == '__main__':
    try:
        main(_arguments)
    except (Invalid, OSError, ValueError, KeyError, tarfile.TarError) as error:
        print('gcc16-runtime: ' + str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 1)
