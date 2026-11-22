#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the CA exporter in a private store and evaluate finite make metadata.

The fixture evaluates the real recipe with synthetic OpenSSL selection and
configuration data. It does not qualify the complete dependency graph.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import sys
import types
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
UPSTREAM = ROOT / 'upstream/pkgsrc'
PATCH = ROOT / 'profiles/common-build-tools/patches/mozilla-rootcerts-prefix.patch'
RECIPE = 'security/mozilla-rootcerts-openssl/Makefile'
PLIST = 'security/mozilla-rootcerts-openssl/PLIST'
HELPER = ROOT / 'profiles/common-build-tools/tests/bsdinstall-source.py'
model = types.ModuleType('source_patch_model')
model.__file__ = str(HELPER)
exec(compile(HELPER.read_bytes(), str(HELPER), 'exec'), model.__dict__)
ARGS = None


def sources():
    originals = {RECIPE: (UPSTREAM / RECIPE).read_text()}
    return originals, model.replay(originals, PATCH.read_text())


def octets(record, name):
    match = re.search(r'^' + name + r' MULTILINE_OCTAL\n((?:[\\0-7]+\n)+)END$', record, re.M)
    if not match:
        raise ValueError('Missing ' + name)
    return bytes(int(n, 8) for n in re.findall(r'\\([0-7]{3})', match[1]))


def nss_records(source):
    records = re.split(r'(?=^CKA_CLASS CK_OBJECT_CLASS )', source.read_text(), flags=re.M)
    certs = [s for s in records if s.startswith('CKA_CLASS CK_OBJECT_CLASS CKO_CERTIFICATE\n')]
    trusts = {octets(s, 'CKA_CERT_SHA1_HASH'): s for s in records
              if s.startswith('CKA_CLASS CK_OBJECT_CLASS CKO_NSS_TRUST\n')}
    return certs, trusts


def pem_ders(contents):
    blocks = re.findall(rb'-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----',
                        contents, re.S)
    return [base64.b64decode(b''.join(block.split()), validate=True) for block in blocks]


class ExportTests(unittest.TestCase):
    """Run the distributed shell helper against real certificates in a private store."""

    def setUp(self):
        if not all((ARGS.certdata, ARGS.openssl, ARGS.awk)):
            self.skipTest('Supply --certdata, --openssl and --awk for the real export')
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.input = self.directory / 'certdata.txt'
        self.store = self.directory / 'certs'
        self.store.mkdir()
        self.script = ROOT / 'pkgsrc/security/mozilla-rootcerts/files/mozilla-rootcerts.sh'
        self.env = dict(PATH='/bin:/usr/bin', LC_ALL='C', AWK=str(ARGS.awk),
                        OPENSSL=str(ARGS.openssl), ECHO='echo', EXPR='expr', LN='ln',
                        LS='ls', MKDIR='mkdir', RM='rm', PREFIX=str(self.directory),
                        SSLDIR=str(self.directory), DATADIR=str(self.directory))
        self.retired = self.directory / 'retired-tls-sha256'
        self.retired.write_text('# No retired roots in this private fixture.\n\n')
        self.certs, self.trust = nss_records(ARGS.certdata)
        self.anchors = []
        for cert in self.certs:
            der = octets(cert, 'CKA_VALUE')
            trust = self.trust.get(hashlib.sha1(der).digest(), '')
            if ('CKA_TRUST_SERVER_AUTH CK_TRUST CKT_NSS_TRUSTED_DELEGATOR\n' in trust
                    and 'CKA_NSS_SERVER_DISTRUST_AFTER MULTILINE_OCTAL' not in cert):
                self.anchors.append((cert, trust, der))
        self.assertGreaterEqual(len(self.anchors), 3)

    def invoke(self, action, *, success=True):
        result = subprocess.run(['/bin/sh', self.script, '-f', self.input, action],
                                cwd=self.store, env=self.env, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stderr.decode())

    def write_records(self, *records):
        self.input.write_text('\n'.join(records))

    def with_cutoff(self, cert, purpose):
        attribute = 'CKA_NSS_' + purpose + '_DISTRUST_AFTER'
        date = ''.join(f'\\{byte:03o}' for byte in b'260914235959Z')
        original = attribute + ' CK_BBOOL CK_FALSE'
        self.assertIn(original, cert)
        return cert.replace(original, attribute + ' MULTILINE_OCTAL\n' + date + '\nEND')

    def trusted_pem(self, der, *settings):
        result = subprocess.check_output([ARGS.openssl, 'x509', '-inform', 'DER',
                                          '-trustout', *settings], input=der)
        blocks = re.findall(rb'-----BEGIN TRUSTED CERTIFICATE-----.*?'
                            rb'-----END TRUSTED CERTIFICATE-----\n', result, re.S)
        self.assertEqual(len(blocks), 1)
        return blocks[0]

    def numbered(self):
        return [der for f in self.store.glob('mozilla-rootcert-*.pem')
                for der in pem_ders(f.read_bytes())]

    def test_pinned_certdata_matches_all_unconditional_server_delegators(self):
        self.input.write_bytes(ARGS.certdata.read_bytes())
        self.invoke('extract')
        self.assertCountEqual(self.numbered(), [der for cert, trust, der in self.anchors])
        self.assertEqual(len(self.anchors), 109)

    def test_server_trust_uses_identity_and_purpose(self):
        a, b, c = self.anchors[:3]
        def same_label(record):
            return re.sub(r'^CKA_LABEL UTF8 .*$', 'CKA_LABEL UTF8 "Shared label"', record,
                          flags=re.M)
        # Reordering the trust records and sharing labels must not change identity.
        denied = b[1].replace('CKA_TRUST_SERVER_AUTH CK_TRUST CKT_NSS_TRUSTED_DELEGATOR',
                              'CKA_TRUST_SERVER_AUTH CK_TRUST CKT_NSS_MUST_VERIFY_TRUST')
        # An email-only cutoff does not restrict server authentication.
        email_only = self.with_cutoff(c[0], 'EMAIL')
        self.write_records(*(same_label(r) for r in (a[0], b[0], email_only, denied, c[1], a[1])))
        self.invoke('extract')
        self.assertCountEqual(self.numbered(), [a[2], c[2]])

    def test_malformed_input_preserves_existing_store(self):
        cert, trust, _ = self.anchors[0]
        self.write_records(cert, trust)
        self.invoke('extract')
        original = {p.name: p.read_bytes() for p in self.store.iterdir()}
        for label, records in (('duplicate identity', (cert, cert, trust)),
                               ('duplicate trust', (cert, trust, trust)),
                               ('truncated DER', (cert.split('CKA_VALUE MULTILINE_OCTAL')[0]
                                                  + 'CKA_VALUE MULTILINE_OCTAL\n',))):
            with self.subTest(label=label):
                self.write_records(*records)
                self.invoke('extract', success=False)
                self.assertEqual({p.name: p.read_bytes() for p in self.store.iterdir()}, original)

    def test_reextract_removes_conditional_anchor_from_existing_store(self):
        restricted, normal, local = self.anchors[:3]
        self.write_records(restricted[0], normal[0], normal[1], restricted[1])
        self.invoke('extract')
        self.invoke('rehash')
        self.assertCountEqual(self.numbered(), [restricted[2], normal[2]])
        def pem(der):
            return (b'-----BEGIN CERTIFICATE-----\n' + base64.encodebytes(der)
                    + b'-----END CERTIFICATE-----\n')
        combined = self.store / 'ca-certificates.crt'
        combined.write_bytes(b''.join(pem(row[2]) for row in (normal, local, restricted)))
        neighbor = self.store / 'operator-note'
        neighbor.write_text('Local configuration\n')
        alias = self.store / 'operator-link'
        alias.symlink_to(neighbor.name)
        conditional = self.with_cutoff(restricted[0], 'SERVER')
        # Reordering also reuses the old numbered filenames for different certificates.
        self.write_records(normal[0], conditional, restricted[1], normal[1])
        self.invoke('extract')
        self.invoke('rehash')
        self.assertEqual(self.numbered(), [normal[2]])
        self.assertCountEqual(pem_ders(combined.read_bytes()), [normal[2], local[2]])
        self.assertTrue(alias.is_symlink())
        self.assertEqual(alias.read_text(), 'Local configuration\n')
        for row in (restricted, normal):
            subject_hash = subprocess.check_output([ARGS.openssl, 'x509', '-inform', 'DER',
                                                    '-noout', '-subject_hash'], input=row[2]).decode().strip()
            links = list(self.store.glob(subject_hash + '.[0-9]*'))
            if row is restricted:
                self.assertEqual(links, [])
            else:
                self.assertEqual(len(links), 1)
                self.assertEqual(pem_ders(links[0].read_bytes()), [normal[2]])

    def test_bundle_only_update_preserves_local_trust_settings(self):
        restricted, normal, local = self.anchors[:3]
        conditional = self.with_cutoff(restricted[0], 'SERVER')
        self.write_records(conditional, normal[0], normal[1], restricted[1])
        # A copied or restored previous bundle can contain the only copies of
        # these anchors. OpenSSL's TRUSTED form also holds auxiliary policy.
        settings = ('-addtrust', 'serverAuth', '-addreject', 'emailProtection')
        old = self.trusted_pem(restricted[2], *settings)
        local_aux = self.trusted_pem(local[2], *settings)
        combined = self.store / 'ca-certificates.crt'
        combined.write_bytes(old + local_aux)
        self.invoke('extract')
        output = combined.read_bytes()
        self.assertEqual(pem_ders(output), [normal[2]])
        trusted_blocks = re.findall(rb'-----BEGIN TRUSTED CERTIFICATE-----.*?'
                                    rb'-----END TRUSTED CERTIFICATE-----\n', output, re.S)
        self.assertEqual(trusted_blocks, [local_aux])
        self.assertEqual(self.numbered(), [normal[2]])


    def test_retained_anchor_keeps_explicit_restrictions_in_both_stores(self):
        cert, trust, der = self.anchors[0]
        self.write_records(cert, trust)
        combined = self.store / 'ca-certificates.crt'
        aux = self.trusted_pem(der, '-addreject', 'serverAuth')
        combined.write_bytes(aux)
        self.invoke('extract')
        self.invoke('rehash')
        self.assertEqual(combined.read_bytes(), aux)
        named, = list(self.store.glob('mozilla-rootcert-*.pem'))
        self.assertEqual(named.read_bytes(), aux)
        subject_hash = subprocess.check_output([ARGS.openssl, 'x509', '-inform', 'DER',
                                                '-subject_hash', '-noout'], input=der).decode().strip()
        self.assertEqual((self.store / (subject_hash + '.0')).read_bytes(), aux)

        different = self.trusted_pem(der, '-addreject', 'emailProtection')
        combined.write_bytes(aux + different)
        self.invoke('extract', success=False)
        self.assertEqual(combined.read_bytes(), aux + different)
        self.assertEqual(named.read_bytes(), aux)


    def test_rehash_preserves_local_pem_and_indexes_a_crl(self):
        openssl = ARGS.openssl
        directory = self.directory
        def create(*args):
            subprocess.run([openssl, *args], cwd=directory, check=True, capture_output=True)
        (directory / 'db').touch()
        (directory / 'ca.conf').write_text(
            '[ca]\ndefault_ca=test\n[test]\ncertificate=ca.pem\nprivate_key=ca.key\n'
            'database=db\ndefault_md=sha256\ndefault_crl_days=1\n')
        create('req', '-new', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256',
               '-noenc', '-x509', '-days', '1', '-subj', '/CN=CRL fixture',
               '-keyout', 'ca.key', '-out', 'ca.pem')
        pem = self.store / 'local-crl.pem'
        create('ca', '-config', 'ca.conf', '-gencrl', '-out', pem)
        self.invoke('rehash')
        subject_hash = subprocess.check_output([openssl, 'x509', '-in', directory / 'ca.pem',
                                                '-subject_hash', '-noout']).decode().strip()
        self.assertEqual((self.store / (subject_hash + '.r0')).readlink(), Path(pem.name))
        self.assertTrue(pem.is_file())


    def test_missing_or_invalid_retired_list_preserves_existing_bundle(self):
        cert, trust, der = self.anchors[0]
        self.write_records(cert, trust)
        combined = self.store / 'ca-certificates.crt'
        original = self.trusted_pem(der, '-addreject', 'emailProtection')
        combined.write_bytes(original)
        self.retired.unlink()
        for invalid in (None, 'not-a-sha256\n'):
            with self.subTest(invalid=invalid):
                if invalid is not None:
                    self.retired.write_text(invalid)
                self.invoke('extract', success=False)
                self.assertEqual(combined.read_bytes(), original)
                self.assertEqual(self.numbered(), [])

    def test_bundle_restored_from_previous_release_uses_current_server_trust(self):
        if not ARGS.previous_certdata:
            self.skipTest('Supply --previous-certdata to check removed upstream roots')
        previous_certs, previous_trust = nss_records(ARGS.previous_certdata)
        current_by_der = {octets(record, 'CKA_VALUE'): record for record in self.certs}
        retired, revoked = [], []
        records = []
        for cert in previous_certs:
            der = octets(cert, 'CKA_VALUE')
            identity = hashlib.sha1(der).digest()
            if 'CKA_TRUST_SERVER_AUTH CK_TRUST CKT_NSS_TRUSTED_DELEGATOR\n' not in previous_trust[identity]:
                continue
            if der not in current_by_der:
                retired.append(der)
            elif 'CKA_TRUST_SERVER_AUTH CK_TRUST CKT_NSS_MUST_VERIFY_TRUST\n' in self.trust[identity]:
                revoked.append(der)
                records.extend([current_by_der[der], self.trust[identity]])
        self.assertEqual(len(retired), 2)
        self.assertEqual(len(revoked), 3)
        installed = ROOT / 'pkgsrc/security/mozilla-rootcerts/files/retired-tls-sha256'
        self.retired.write_bytes(installed.read_bytes())
        listed = set(s.strip().lower() for s in installed.read_text().splitlines()
                     if s.strip() and not s.lstrip().startswith('#'))
        self.assertTrue({hashlib.sha256(der).hexdigest() for der in retired} <= listed)
        anchor, local = self.anchors[:2]
        self.write_records(anchor[0], anchor[1], *records)
        combined = self.store / 'ca-certificates.crt'
        combined.write_bytes(b''.join(self.trusted_pem(der, '-addtrust', 'serverAuth')
                                      for der in [*retired, *revoked, local[2]]))
        self.invoke('extract')
        output = combined.read_bytes()
        self.assertEqual(pem_ders(output), [anchor[2]])
        local_aux = self.trusted_pem(local[2], '-addtrust', 'serverAuth')
        self.assertEqual(re.findall(rb'-----BEGIN TRUSTED CERTIFICATE-----.*?'
                                    rb'-----END TRUSTED CERTIFICATE-----\n', output, re.S),
                         [local_aux])
        self.assertEqual(self.numbered(), [anchor[2]])


class PrefixTests(unittest.TestCase):
    def test_install_and_updated_store_packing_list(self):
        originals, result = sources()
        def install(text):
            return text.split('do-install:\n')[1].split('.include ')[0]
        self.assertEqual(install(result[RECIPE]), install(originals[RECIPE]))
        self.assertNotIn('cert.pem', result[RECIPE])
        self.assertIn('${DESTDIR}${OPENSSLDIR}', install(result[RECIPE]))
        self.assertIn('${SCRIPT} -d ${DESTDIR} install', install(result[RECIPE]))
        # Existing CA payloads remain under the ordinary package packing list.
        store_patch = PATCH.with_name('mozilla-rootcerts-store-files.patch')
        plist = model.replay({PLIST: (UPSTREAM / PLIST).read_text()},
                             store_patch.read_text())[PLIST].splitlines()
        self.assertIn('${MYETCDIR}/openssl/certs/ca-certificates.crt', plist)
        self.assertEqual(sum(line.endswith('.pem') for line in plist), 109)
        self.assertEqual(sum(bool(re.search(r'/[0-9a-f]{8}\.[0-9]+$', line)) for line in plist), 109)
        self.assertFalse(any(line.endswith('/cert.pem') for line in plist))

    def test_one_owner_preserves_certificate_data(self):
        originals, result = sources()
        self.assertEqual(set(result), {RECIPE})
        record = 'patch\t' + PATCH.relative_to(ROOT).as_posix() + '\n'
        self.assertEqual((ROOT / 'pkgsrc/export.conf').read_text().count(record), 1)
        replaces = (ROOT / 'pkgsrc/replaces').read_text().splitlines()
        self.assertTrue((ROOT / 'pkgsrc/security/mozilla-rootcerts').is_dir())
        self.assertIn('security/mozilla-rootcerts', replaces)
        self.assertTrue((UPSTREAM / RECIPE).is_file())
        self.assertNotIn('security/mozilla-rootcerts-openssl', replaces)
        self.assertIn('mozilla-rootcerts>=1.1.20261113nb1:', result[RECIPE])

    def test_foundation_selects_trust_in_final_prefix(self):
        policy = (ROOT / 'profiles/development-toolchain/darwin-bootstrap.mk.conf').read_text()
        self.assertIn('BOOTSTRAP_DEPENDS+= mozilla-rootcerts-openssl>=2.29:../../security/mozilla-rootcerts-openssl', policy)
        self.assertRegex(policy, r'(?m)^PREFER.openssl= pkgsrc$')
        self.assertRegex(policy, r'(?m)^PKG_SYSCONFBASEDIR= \$\{LOCALBASE\}/etc$')

    def test_real_metadata_and_former_failure(self):
        if not ARGS.make_arg:
            self.skipTest("Supply an explicit SDK make tuple for finite metadata")
        originals, result = sources()
        work = ARGS.work.resolve()
        work.mkdir(parents=True, exist_ok=False)
        for directory in ('security/mozilla-rootcerts-openssl', 'security/openssl', 'mk'):
            (work / directory).mkdir(parents=True, exist_ok=True)
        (work / 'security/openssl/builtin.mk').write_text('# Explicit fixture selection; no discovery.\n')
        (work / 'mk/bsd.pkg.mk').write_text('PKG_SYSCONFDIR= ${PKG_SYSCONFBASEDIR}\n')
        variables = ['PREFIX', 'OPENSSLDIR', 'PLIST_SUBST', 'NOT_FOR_UNPRIVILEGED', 'SCRIPT']
        receipts = {}

        def query(text, builtin, config):
            path = work / RECIPE
            path.write_text('PREFIX= /sdk/final\n' + text)
            command = [*ARGS.make_arg, '-r', '-C', str(path.parent),
                'LOCALBASE=/sdk/final', 'PKG_SYSCONFBASEDIR=' + config,
                'USE_BUILTIN.openssl=' + builtin]
            for variable in variables:
                command += ['-v', variable]
            run = subprocess.run(command, check=True, capture_output=True, text=True)
            lines = run.stdout.splitlines()
            self.assertEqual(len(lines), len(variables), run.stdout)
            return dict(zip(variables, lines))

        old = query(originals[RECIPE], 'no', '/sdk/final/etc')
        self.assertEqual(old['PREFIX'], '/')
        for name, builtin, config, prefix, certdir, relative in (
            ('contained', 'no', '/sdk/final/etc', '/sdk/final', '/sdk/final/etc/openssl/certs', 'etc'),
            ('external', 'no', '/separate/config', '/', '/separate/config/openssl/certs', 'separate/config'),
            ('neighbor', 'no', '/sdk/final-other/etc', '/', '/sdk/final-other/etc/openssl/certs', 'sdk/final-other/etc'),
            ('builtin', 'yes', '/sdk/final/etc', '/', '/etc/openssl/certs', 'etc'),
        ):
            data = query(result[RECIPE], builtin, config)
            self.assertEqual(data['PREFIX'], prefix, name)
            self.assertEqual(data['OPENSSLDIR'], certdir, name)
            self.assertIn('MYETCDIR=' + relative, data['PLIST_SUBST'].split(), name)
            self.assertEqual(data['NOT_FOR_UNPRIVILEGED'], 'yes' if builtin == 'yes' else '', name)
            self.assertEqual(data['SCRIPT'], '/sdk/final/sbin/mozilla-rootcerts', name)
            receipts[name] = data
        for name, mutant in (
            ('lost-containment', result[RECIPE].replace('SET_PREFIX=\t\tno', 'SET_PREFIX=\t\tyes')),
            ('absolute-plist', result[RECIPE].replace(':S/^\\///', '')),
        ):
            data = query(mutant, 'no', '/sdk/final/etc')
            self.assertFalse(data['PREFIX'] == '/sdk/final' and
                             'MYETCDIR=etc' in data['PLIST_SUBST'].split(), name)
            receipts[name] = data
        receipts['before'] = old
        (work / 'metadata.json').write_text(json.dumps(receipts, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make-arg', action='append', default=[])
    parser.add_argument('--work', type=Path)
    parser.add_argument('--certdata', type=Path)
    parser.add_argument('--previous-certdata', type=Path)
    parser.add_argument('--openssl', type=Path)
    parser.add_argument('--awk', type=Path)
    ARGS, remaining = parser.parse_known_args()
    export_inputs = (ARGS.certdata, ARGS.openssl, ARGS.awk)
    if any(export_inputs) and not all(export_inputs):
        parser.error('--certdata, --openssl and --awk must be supplied together')
    if ARGS.make_arg and (ARGS.work is None or not ARGS.work.is_absolute()):
        parser.error('--make-arg requires a new absolute --work directory')
    unittest.main(argv=[__file__, *remaining])
