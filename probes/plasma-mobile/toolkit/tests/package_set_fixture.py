# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Shared native package fixtures, no installation.
import sys
sys.dont_write_bytecode = True
import contextlib
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
from unittest.mock import patch


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def metadata(arch):
    return f'OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH={arch}\nOBJECT_FMT=ELF\n'.encode()


def elf(machine, klass=2, endian=1):
    data = bytearray(64)
    data[:7] = b'\x7fELF' + bytes((klass, endian, 1))
    data[18:20] = machine.to_bytes(2, 'little')
    return bytes(data)


class Fixture:
    def __init__(self, arguments, *, llvm=False, optional_auditor=False, publication=False):
        self.ports = Path(__file__).resolve().parents[4]
        sys.path.insert(0, str(self.ports / 'profiles/development-toolchain/runtime/recipe/files'))
        import sdk_source
        args = sdk_source.arguments(arguments)
        self.sdk = sdk_source.load()
        sdk_source.install_signal_handlers()
        from emberbsd_sdk.stream import capture_streamed, PRODUCER_STREAM_API
        from emberbsd_sdk.tarstream import TAR_STREAM_API
        check(PRODUCER_STREAM_API == TAR_STREAM_API == 1, 'SDK stream/raw-tar API1 required')
        if publication:
            from emberbsd_sdk import publication as publisher, tarstream
            capabilities = ((publisher, 'DIRECTORY_PUBLICATION_API'), (tarstream, 'TAR_HEADER_FACTS_API'))
            check(all(type(getattr(module, name, None)) is int and getattr(module, name) == 1
                      for module, name in capabilities), 'SDK publication/raw-header facts API1 required')
            publisher.require_directory_publication()
        self.capture = capture_streamed
        required = 2 if llvm else 1
        check(required <= len(args) <= required + int(optional_auditor),
              'Use [--sdk-source SDK] ' + ('HOST_PREFIX ' if llvm else '') + 'NEW_OUTPUT' + (' [AUDITOR]' if optional_auditor else ''))
        host = Path(args.pop(0)).resolve(strict=True) if llvm else None
        self.work = Path(args.pop(0)).absolute()
        self.work.mkdir()
        self.create = str(host / 'sbin/pkg_create') if host else os.environ.get('PKG_CREATE', 'pkg_create')
        self.info = str(host / 'sbin/pkg_info') if host else os.environ.get('PKG_INFO', 'pkg_info')
        self.admin = os.environ.get('PKG_ADMIN', 'pkg_admin')
        self.tar = os.environ.get('BSDTAR', 'bsdtar')
        self.env = dict(os.environ, PKG_INFO=self.info, PKG_ADMIN=self.admin, BSDTAR=self.tar, COPYFILE_DISABLE='1')
        self.auditor = Path(args[0]).absolute() if args else Path(__file__).resolve().parents[1] / 'cross/prepare-package-set.py'
        spec = importlib.util.spec_from_file_location('package_set_under_test', self.auditor)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.installer = Path(__file__).resolve().parents[1] / 'cross/install-package-set.sh'
        self.count = 0

    def run(self, argv, *, env=None):
        return self.capture([str(a) for a in argv], stdout_limit=32*1024*1024,
                            timeout=300, env=self.env if env is None else env).value

    def status(self, argv, *, env=None):
        from emberbsd_sdk.errors import CommandError
        try:
            return SimpleNamespace(returncode=0, stdout=self.run(argv, env=env), stderr=b'')
        except CommandError as error:
            return SimpleNamespace(returncode=error.returncode, stdout=error.stdout, stderr=error.stderr)

    def package(self, directory, name, payload, files, *, arch='aarch64', prefix='/usr/pkg',
                build=None, dependencies=None, scripts=None):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'comment').write_text('Package-set regression\n')
        (directory / 'description').write_text('Native package fixture; no target execution.\n')
        (directory / 'build-info').write_bytes(metadata(arch) if build is None else build)
        (directory / 'plist').write_text('\n'.join(files) + '\n')
        argv = [self.create, '-p', payload, '-I', prefix, '-f', directory / 'plist',
                '-c', directory / 'comment', '-d', directory / 'description', '-B', directory / 'build-info']
        if dependencies:
            argv += ['-P', dependencies]
        for entry, data in (scripts or {}).items():
            (directory / entry).write_bytes(data)
            if entry in ('+INSTALL', '+DEINSTALL'):
                argv += ['-i' if entry == '+INSTALL' else '-k', directory / entry]
        archive = directory / (name + '.tgz')
        self.run(argv + [archive])
        return archive

    def database(self, archive, database):
        destination = database / archive.name.removesuffix('.tgz')
        destination.mkdir(parents=True)
        for entry in self.run([self.tar, '-tf', archive]).splitlines():
            if entry.startswith(b'+'):
                (destination / os.fsdecode(entry)).write_bytes(self.run([self.tar, '-xOf', archive, os.fsdecode(entry)]))

    def unpack(self, archive, directory):
        directory.mkdir(parents=True)
        self.run([self.tar, '-xf', archive, '-C', directory])

    def pack(self, tree, archive):
        names = sorted(str(p.relative_to(tree)) for p in tree.rglob('*') if not p.is_dir())
        names.remove('+CONTENTS')
        self.run([self.tar, '-czf', archive, '--format=pax', '-C', tree, '+CONTENTS', *names])

    def audit(self, database, index, destination, roots, *, target=None, copy_log=None, race=None):
        args = ['--sdk-source', self.sdk]
        if target is not None:
            args += ['--target', target]
        args += [str(database), str(index), str(destination), *roots]
        copied = shutil.copyfile
        def observe(source, dest, *args, **kwargs):
            if race and os.path.realpath(source) == str(race['source']):
                Path(source).write_bytes(race['bad'].read_bytes())
                race['events'].append('restore-a-before-copy')
            if copy_log:
                with copy_log.open('a') as log:
                    log.write(str(source) + '\n')
            return copied(source, dest, *args, **kwargs)
        # The import is explicit and performs the production capability checks.
        self.module.load_sdk(args)
        from emberbsd_sdk import inventory
        original_hash = inventory.sha256_file
        swapped = False
        def digest(path):
            nonlocal swapped
            value = original_hash(path)
            if race and os.path.realpath(path) == str(race['source']) and not swapped:
                swapped = True
                Path(path).write_bytes(race['good'].read_bytes())
                race['events'].append('hash-a-then-b')
            return value
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, self.env), patch.object(shutil, 'copyfile', observe), \
                patch.object(inventory, 'sha256_file', digest), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = self.module.main(args)
        return SimpleNamespace(returncode=code, stdout=out.getvalue().encode(), stderr=err.getvalue().encode())

    def result(self, name, result, expected=None, destination=None, *, log=None):
        data = result.stdout + result.stderr
        (log or self.work / (name + '.log')).write_bytes(data)
        if expected is None:
            check(result.returncode == 0, f'{name}: {data!r}')
        else:
            check(result.returncode != 0 and expected.encode() in data, f'{name}: did not reject {expected}: {data!r}')
            if destination:
                check(not destination.exists(), f'{name}: published a rejected set')
        if destination:
            check(not list(destination.parent.glob('.' + destination.name + '-*')), f'{name}: staging remains')
        self.count += 1
        print('PASS: ' + name)

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
