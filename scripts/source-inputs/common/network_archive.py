#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Recipe adapters for common mDNSResponder and dhcpcd sources."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import sys

PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source
sys.path.append(str(PORTS / 'scripts'))
import prepared_receipt
import tar_archive


class NetworkOwner:
    def __init__(self, owner, package, version_name, project, suffix, root_prefix):
        self.owner = Path(owner).resolve()
        self.PACKAGE = package
        self.LABEL = project
        self.version_name = version_name
        self.project = project
        self.suffix = suffix
        self.root_prefix = root_prefix
        self.PORTS = PORTS
        self.prepared_receipt = prepared_receipt

    def load_sdk(self, argv):
        self.SDK_SOURCE, argv = sdk_source.load_sdk(argv)
        from emberbsd_sdk import jsonio, paths, process, sourceprep
        from emberbsd_sdk.errors import SDKError
        from emberbsd_sdk.publication import publish_directory_noreplace
        self.jsonio, self.paths, self.process, self.sourceprep = jsonio, paths, process, sourceprep
        self.SDKError = SDKError
        self.publish_directory_noreplace = publish_directory_noreplace
        if getattr(sourceprep, 'PREPARED_TREE_API', None) != 1:
            raise SDKError('selected SDK lacks the prepared source tree API')
        return argv

    def require(self, condition, message):
        if not condition:
            raise self.SDKError(message)

    def read(self, path):
        handle, before = self.paths.open_regular(path)
        with handle:
            data = handle.read()
        self.paths.verify_stable(path, before)
        return data

    @staticmethod
    def digest(data):
        return hashlib.sha256(data).hexdigest()

    def owner_digest(self):
        return self.digest(b''.join(hashlib.sha256(path.read_bytes()).digest() for path in
            (self.owner, Path(__file__).resolve(), Path(tar_archive.__file__).resolve())))

    def identity_module(self):
        path = PORTS / 'scripts/pkgsrc-source-identity.py'
        spec = importlib.util.spec_from_file_location('pkgsrc_source_identity', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def git_effective_identity(self, git):
        return self.identity_module().git_package_identity(PORTS, self.PACKAGE, git)

    def source_identity(self, git):
        return {'export': self.identity_module().identity(PORTS, self.PACKAGE, git, self.SDK_SOURCE),
                'owner_sha256': self.owner_digest()}

    def recipe(self, exported):
        root = Path(exported) / self.PACKAGE
        makefile = self.read(root / 'Makefile')
        common = self.read(root / 'Makefile.common')
        include = ('.include "../../' + self.PACKAGE + '/Makefile.common"').encode()
        self.require(sum(line.strip() == include for line in makefile.splitlines()) == 1,
                       self.PACKAGE + ': missing or duplicate common recipe include')
        combined = makefile + b'\n' + common
        def assignments(name):
            return re.findall(rb'^[ \t]*' + name + rb'[ \t]*([?:+!]?=)[ \t]*([^\n#]*?)[ \t]*$', combined, re.M)

        matches = assignments(self.version_name.encode())
        self.require(len(matches) == 1 and matches[0][0] == b'=' and
                     re.fullmatch(rb'[0-9]+(?:\.[0-9]+)+', matches[0][1]) is not None,
                     self.PACKAGE + ': ambiguous version')
        version = matches[0][1].decode('ascii')
        if self.project == 'mDNSResponder':
            required = {b'GITHUB_PROJECT': b'mDNSResponder', b'DISTNAME': b'${GITHUB_PROJECT}-${PKGVER}',
                        b'GITHUB_TAG': b'refs/tags/${GITHUB_PROJECT}-${PKGVER}',
                        b'WRKSRC': b'${WRKDIR}/${GITHUB_PROJECT}-${GITHUB_PROJECT}-${PKGVER}'}
            absent = (b'GITHUB_RELEASE', b'EXTRACT_SUFX', b'DISTFILES')
        else:
            required = {b'GITHUB_PROJECT': b'dhcpcd', b'DISTNAME': b'dhcpcd-${DHCPCD_VERSION}',
                        b'GITHUB_RELEASE': b'v${DHCPCD_VERSION}', b'EXTRACT_SUFX': b'.tar.xz'}
            absent = (b'GITHUB_TAG', b'WRKSRC', b'DISTFILES')
        self.require(all(assignments(key) == [(b'=', value)] for key, value in required.items()) and
                     all(not assignments(key) for key in absent),
                       self.PACKAGE + ': unexpected common source selection')
        distname = self.project + '-' + version
        archive = distname + self.suffix
        info = self.read(root / 'distinfo').decode('utf-8')
        hashes = {}
        for label, key in (('SHA512', 'sha512'), ('BLAKE2s', 'blake2s'), ('Size', 'size')):
            values = re.findall(r'^' + label + r' \(' + re.escape(archive) + r'\) = (\S+)(?: bytes)?$', info, re.M)
            self.require(len(values) == 1, self.PACKAGE + ': ambiguous archive ' + label)
            hashes[key] = int(values[0]) if key == 'size' else values[0]
        declared = re.findall(r'^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$', info, re.M)
        patches = sorted((root / 'patches').glob('patch-*'))
        self.require([p.name for p in patches] == sorted(name for name, _ in declared),
                       self.PACKAGE + ': patch inventory differs from distinfo')
        for name, expected in declared:
            data = self.read(root / 'patches' / name)
            filtered = b''.join(line for line in data.splitlines(keepends=True) if b'$NetBSD' not in line)
            self.require(hashlib.sha1(filtered).hexdigest() == expected,
                           self.PACKAGE + ': patch checksum differs: ' + name)
        inputs = [root / 'Makefile', root / 'Makefile.common', root / 'distinfo', *patches]
        return (dict(distname=distname, archive=archive, archive_root=self.root_prefix + distname,
                     **hashes, recipe={str(p.relative_to(root)): self.digest(self.read(p)) for p in inputs}), patches)

    def verify(self, source, git, archive=None, patch=None, pkgsrc_export=None):
        return tar_archive.verify(self, source, git, archive, patch, pkgsrc_export)

    def prepare(self, archive, output, patch, git, scoped_identity=False, exported=None):
        return tar_archive.prepare(self, archive, output, patch, git, scoped_identity, exported)

    def shared_tree(self, selected):
        return tar_archive.shared_tree(self, selected)

    def main(self):
        sdk_source.install_signal_handlers()
        args = self.load_sdk(sys.argv[1:])
        parser = argparse.ArgumentParser(description='Prepare and verify ' + self.PACKAGE + ' source')
        parser.add_argument('--git', required=True, help='absolute Git inspector')
        sub = parser.add_subparsers(dest='action', required=True)
        produce = sub.add_parser('prepare')
        produce.add_argument('--archive', required=True)
        produce.add_argument('--output', required=True)
        produce.add_argument('--patch', required=True)
        produce.add_argument('--scoped-identity', action='store_true')
        produce.add_argument('--pkgsrc-export')
        check = sub.add_parser('verify-source')
        check.add_argument('--source', required=True)
        check.add_argument('--archive')
        check.add_argument('--patch')
        check.add_argument('--pkgsrc-export')
        selected = parser.parse_args(args)
        try:
            if selected.action == 'prepare':
                record = self.prepare(selected.archive, selected.output, selected.patch, selected.git,
                                      selected.scoped_identity, exported=self.shared_tree(selected))
            else:
                record = self.verify(selected.source, selected.git, selected.archive, selected.patch,
                                     pkgsrc_export=selected.pkgsrc_export)
            sys.stdout.buffer.write(self.jsonio.json_bytes(record))
        except (self.SDKError, OSError, ValueError) as exc:
            sdk_source.exit_error(exc, self.LABEL + ' source: ')
