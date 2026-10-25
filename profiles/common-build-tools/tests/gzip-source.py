#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check the common gzip source update. Do not execute upstream programs."""
import argparse
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
RECIPE = None
XZ_SHA256 = '9aa0cc780dec156b8282844833b342ab7cb08c25d2cd9a1869cdd0df31deff48'
TAR_SHA256 = 'db2d827bc811f348a11da04484bd2c5971ff729a83c5d9f7a3ad6df206b94e92'
ARGS = None


def checked_archive(raw, expected):
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('The pinned source archive differs.')
    return raw


def metadata_inputs(value, pkgsrc):
    """Check an explicit fixture equivalent of SDK seed_commands()['make']."""
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    def path(text, *, directory=False, executable=False):
        require(isinstance(text, str) and Path(text).is_absolute() and
                re.fullmatch(r'[A-Za-z0-9_./+@%=-]+', text), 'Metadata paths need absolute SDK-safe spelling.')
        result = Path(text)
        require(result.exists() and result.resolve() == result and
                (result.is_dir() if directory else result.is_file()), 'Metadata input is absent or indirect.')
        require(not executable or os.access(result, os.X_OK), 'Metadata tool is not executable.')
        return result
    require(pkgsrc.is_absolute() and pkgsrc.resolve(strict=True) == pkgsrc,
            'Metadata needs an absolute prepared export path.')
    require(isinstance(value, dict) and set(value) == {'make', 'work', 'environment', 'record'},
            'Metadata selection needs the complete make tuple, private work, environment and record.')
    make = value['make']
    require(isinstance(make, list) and len(make) == 5 and all(isinstance(word, str) for word in make),
            'Metadata requires the complete five-word SDK make tuple.')
    require(make[1] == '-m' and make[3].startswith('SHELL=') and make[4].startswith('MAKECONF='),
            'Metadata make tuple must bind system rules, shell and MAKECONF.')
    program = path(make[0], executable=True)
    mk = path(make[2], directory=True)
    path(str(mk / 'sys.mk'))
    shell = path(make[3].removeprefix('SHELL='), executable=True)
    conf = path(make[4].removeprefix('MAKECONF='))
    work = path(value['work'], directory=True)
    require(conf.is_relative_to(work), 'Metadata MAKECONF must be in its private work directory.')
    env = value['environment']
    private = {'HOME', 'TMPDIR', 'XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME'}
    require(isinstance(env, dict) and set(env) == private | {'PATH', 'LC_ALL', 'TZ', 'MAKECONF'} and
            all(isinstance(text, str) for text in env.values()), 'Metadata environment must be complete and finite.')
    require(env['MAKECONF'] == str(conf) and env['LC_ALL'] == 'C' and env['TZ'] == 'UTC',
            'Metadata environment differs from its explicit make context.')
    for name in private:
        require(path(env[name], directory=True).is_relative_to(work), 'Metadata environment escapes its private work.')
    directories = [path(name, directory=True) for name in env['PATH'].split(os.pathsep)]
    require(program.parent in directories and shell.parent in directories, 'Selected metadata tools are absent from PATH.')
    record = Path(value['record']) if isinstance(value['record'], str) else Path()
    require(record.is_absolute() and record.parent.resolve(strict=True) == record.parent and
            record.is_relative_to(pkgsrc.resolve(strict=True)) and not record.exists(),
            'Metadata record must be new and inside the prepared export.')
    return list(make), dict(env), work, record


def native_metadata(value, pkgsrc):
    make, env, work, record = metadata_inputs(value, pkgsrc)
    shell, mk = make[3].removeprefix('SHELL='), make[2]
    fixture = work / 'metadata.mk'
    fixture_text = (f'.if "${{.SHELL}}" != "{shell}" || "${{SHELL}}" != "{shell}"\n'
        '.error metadata shell selection changed\n.endif\n'
        f'.if "${{.SYSPATH}}" != "{mk}"\n.error metadata system rules changed\n.endif\n'
        '_GZIP_ASSIGN != print -r -- "$${KSH_VERSION-}"\n'
        '_GZIP_COMMAND = print -r -- "$${KSH_VERSION-}"\n'
        '_GZIP_MODIFIER := ${_GZIP_COMMAND:sh}\n'
        '.if empty(_GZIP_ASSIGN:M*MIRBSD*) || empty(_GZIP_MODIFIER:M*MIRBSD*)\n'
        '.error metadata parse-time shell changed\n.endif\n'
        '.include "${.CURDIR}/Makefile"\n'
        f'.if "${{PKG_DBDIR}}" != "{work}/pkgdb" || "${{WRKOBJDIR}}" != "{work}/objects" || "${{LOCALBASE}}" != "{work}/prefix"\n'
        '.error metadata package paths escape their fixture\n.endif\n')
    with fixture.open('x') as output:
        output.write(fixture_text)
    package = pkgsrc / 'archivers/gzip'
    argv = [*make, '-C', str(package), '-f', str(fixture)]
    for variable in ('PKGNAME', 'INFO_FILES', 'CONFIGURE_ENV', 'PKG_FAIL_REASON',
                     '.SHELL', '.SYSPATH', '_GZIP_ASSIGN', '_GZIP_MODIFIER'):
        argv.extend(['-V', '${' + variable + '}'])
    result = subprocess.run(argv, cwd=work, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, timeout=30)
    with record.open('x') as output:
        json.dump(dict(scope='source-metadata-fixture', ordinary_provider_qualified=False,
            argv=argv, environment=env, cwd=str(work), returncode=result.returncode,
            inputs=[dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                    for path in (Path(make[0]), Path(shell), Path(mk) / 'sys.mk',
                                 Path(env['MAKECONF']), fixture)],
            stdout=result.stdout, stderr=result.stderr), output, indent=2)
        output.write('\n')
    return result


class GzipSourceTests(unittest.TestCase):
    def test_single_current_recipe_and_export_registration(self):
        recipe = (RECIPE / 'Makefile').read_text()
        self.assertRegex(recipe, r'(?m)^DISTNAME=\s*gzip-1\.15$')
        self.assertNotRegex(recipe, r'(?m)^PKGREVISION=')
        replaces = (ROOT / 'pkgsrc/replaces').read_text().splitlines()
        self.assertNotIn('archivers/gzip', replaces)
        self.assertFalse((ROOT / 'pkgsrc/archivers/gzip').exists())
        export = (ROOT / 'pkgsrc/export.conf').read_text().splitlines()
        self.assertEqual(sum('pkgsrc-gzip-1.15.patch' in row for row in export), 1)
        self.assertEqual(sum('pkgsrc-gzip-zless-runtime.patch' in row for row in export), 1)

    def test_existing_interfaces_and_bootstrap_archive_are_preserved(self):
        recipe = (RECIPE / 'Makefile').read_text()
        for pattern in (r'EXTRACT_SUFX=\s*\.tar', r'MASTER_SITES=\s*\$\{MASTER_SITE_LOCAL\}',
                        r'GNU_CONFIGURE=\s*yes', r'CONFIGURE_ENV\+=\s*LESS=less',
                        r'MAKE_FLAGS\+=\s*manlinks=so', r'INFO_FILES=\s*yes',
                        r'LICENSE=\s*gnu-gpl-v3', r'CHECK_PERMS=\s*no'):
            self.assertRegex(recipe, pattern)
        for name in ('DESCR', 'PLIST'):
            self.assertEqual((RECIPE / name).read_bytes(),
                (ROOT / 'upstream/pkgsrc/archivers/gzip' / name).read_bytes())
        self.assertFalse((RECIPE / 'patches').exists())

    def test_official_archive_and_distinfo(self):
        packed = checked_archive(ARGS.archive.read_bytes(), XZ_SHA256)
        raw = checked_archive(lzma.decompress(packed), TAR_SHA256)
        self.assertEqual(raw, ARGS.tar.read_bytes())
        info = (RECIPE / 'distinfo').read_text()
        for label, constructor in [('BLAKE2s', hashlib.blake2s), ('SHA512', hashlib.sha512)]:
            self.assertEqual(re.findall(r'^' + label + r' \(gzip-1\.15.tar\) = ([0-9a-f]+)$', info, re.M),
                             [constructor(raw).hexdigest()])
        self.assertEqual(re.findall(r'^Size \(gzip-1\.15.tar\) = (\d+) bytes$', info, re.M), [str(len(raw))])
        self.assertNotIn('patch-', info)
        with self.assertRaises(ValueError):
            checked_archive(packed[:-1] + bytes([packed[-1] ^ 1]), XZ_SHA256)

    def test_upstream_contains_both_retired_patch_repairs(self):
        raw = checked_archive(ARGS.tar.read_bytes(), TAR_SHA256)
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            def source(name):
                return archive.extractfile('gzip-1.15/' + name).read().decode()
            self.assertIn('# include <sys/stat.h>', source('lib/utimens.h'))
            unlzh = source('unlzh.c')
            self.assertIn('memzero (left, (2 * NC - 1) * sizeof *left);', unlzh)
            self.assertIn('memzero (right, (2 * NC - 1) * sizeof *right);', unlzh)
            self.assertIn('memzero (c_table, 4096 * sizeof *c_table);', unlzh)
            self.assertIn('unlinkat (remove_ofname_dfd, fname, 0);', source('gzip.c'))
            self.assertIn('Noteworthy changes in release 1.15 (2026-09-20) [stable]', source('NEWS'))

    def test_complete_export_keeps_the_common_recipe(self):
        manifest = (ROOT / 'profiles/common-build-tools/sources.tsv').read_text().splitlines()
        rows = [row.split('\t') for row in manifest if row.startswith('pkgsrc-gzip-1.15.patch\t')]
        self.assertEqual(len(rows), 1)
        name, digest, url = rows[0]
        patch = ROOT / 'profiles/common-build-tools/patches' / name
        self.assertEqual(hashlib.sha256(patch.read_bytes()).hexdigest(), digest)
        self.assertEqual(url, 'https://github.com/NetBSD/pkgsrc/commit/171d7b4ad9cf6d880db6340df4e239157725afd9.patch')
        self.assertFalse((ARGS.pkgsrc / 'archivers/gzip/patches').exists())

    def test_real_native_package_metadata(self):
        if ARGS.metadata_selection is None:
            self.skipTest('Pass --metadata-selection for isolated native metadata.')
        self.assertIsNotNone(ARGS.pkgsrc)
        value = json.loads(ARGS.metadata_selection.read_bytes())
        result = native_metadata(value, ARGS.pkgsrc)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '', 'Metadata diagnostics must not hide failed parse-time commands.')
        rows = result.stdout.splitlines()
        self.assertEqual(rows[:2], ['gzip-1.15', 'yes'])
        self.assertIn('LESS=less', shlex.split(rows[2]))
        self.assertEqual(rows[3], '')
        self.assertEqual(rows[4:6], [value['make'][3].removeprefix('SHELL='), value['make'][2]])
        self.assertTrue(all('MIRBSD' in row for row in rows[6:8]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True, help='Official gzip-1.15.tar.xz')
    parser.add_argument('--tar', type=Path, required=True, help='Uncompressed archive used by pkgsrc')
    parser.add_argument('--pkgsrc', type=Path, required=True, help='Complete prepared export')
    parser.add_argument('--metadata-selection', type=Path,
                        help='Explicit complete SDK make tuple, private work, environment and new record')
    ARGS, remainder = parser.parse_known_args()
    if ARGS.metadata_selection is not None and not ARGS.metadata_selection.is_absolute():
        parser.error('--metadata-selection must be absolute')
    RECIPE = ARGS.pkgsrc / 'archivers/gzip'
    unittest.main(argv=[__file__, *remainder])
