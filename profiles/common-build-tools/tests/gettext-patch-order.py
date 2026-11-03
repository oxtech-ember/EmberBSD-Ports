#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Apply the effective gettext patch series to the checked release archive."""
import argparse
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile

ports = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', required=True)
parser.add_argument('--pkgsrc', type=Path, required=True, help='current shared pkgsrc export')
parser.add_argument('--archive', type=Path, required=True)
parser.add_argument('--patch', required=True)
args = parser.parse_args()
sys.path.insert(0, str(Path(args.sdk_source) / 'src'))
from emberbsd_sdk import sourceprep
spec = importlib.util.spec_from_file_location('gettext_source', ports / 'scripts/source-inputs/gettext/source.py')
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
owner.load_sdk(['--sdk-source', args.sdk_source])
rows = [line.split('\t') for line in (ports / 'pkgsrc/export.conf').read_text().splitlines()]
selected = [row for row in rows if len(row) == 4 and row[0] == 'recipe-patch' and
            row[1] == 'profiles/common-build-tools/patches/gettext-external-tree-sitter.patch' and
            row[2] == 'devel/gettext']
if len(selected) != 1:
    raise SystemExit('expected one selected gettext runtime patch')
name = selected[0][3]
with tempfile.TemporaryDirectory(prefix='gettext-patch-order-') as directory:
    temp = Path(directory)
    export = temp / 'pkgsrc'
    (export / 'devel/gettext').parent.mkdir(parents=True)
    shutil.copytree(args.pkgsrc / 'devel/gettext', export / 'devel/gettext')
    (export / 'devel/gettext-tools').mkdir(parents=True)
    shutil.copy2(args.pkgsrc / 'devel/gettext-tools/Makefile', export / 'devel/gettext-tools/Makefile')
    recipe = export / 'devel/gettext'
    matches = list((recipe / 'patches').glob('patch-*ember_external_tree_sitter'))
    if len(matches) != 1:
        raise SystemExit('expected one exported tree-sitter patch')
    if matches[0].read_bytes() != (ports / selected[0][1]).read_bytes():
        raise SystemExit('exported tree-sitter patch differs from selected source')
    old = matches[0].name
    if old != name:
        matches[0].rename(recipe / 'patches' / name)
        distinfo = recipe / 'distinfo'
        distinfo.write_text(distinfo.read_text().replace('(' + old + ')', '(' + name + ')'))
    metadata, patches = owner.recipe(export)
    data = args.archive.read_bytes()
    hashes = sourceprep.archive_hashes(data)
    if args.archive.name != metadata['archive'] or any(hashes[key] != metadata[key] for key in ('sha512', 'blake2s', 'size')):
        raise SystemExit('archive differs from common gettext recipe')
    sourceprep.extract_archive(args.archive, temp, metadata['distname'], 'gettext')
    source = temp / metadata['distname']
    for index, patch in enumerate(patches):
        sourceprep.apply_patch(args.patch, patch, patch.read_bytes(), source, 'gettext',
            patch_args=('-p0', '-f', '-N', '-F0', '-V', 'none'),
            backup_directory=temp / ('patch-backups-' + str(index)))
    configure = (source / 'gettext-tools/configure').read_text()
    if 'TREE_SITTER_LIBS' not in configure or 'EMBER_GETTEXT_PLAIN_STYLE_FALSE' not in configure:
        raise SystemExit('gettext generated configure is incomplete')
    order = [patch.name for patch in patches]
    if order.index('patch-zz_ember_tools_plain_output') >= order.index(name):
        raise SystemExit('tree-sitter patch precedes its plain-output prerequisite')
print('PASS: checksum-verified gettext archive accepts complete ordered patch series')
