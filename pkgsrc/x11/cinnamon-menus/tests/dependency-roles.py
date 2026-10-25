#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check source export and finite bmake metadata without running build targets."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
RECIPE = ROOT / 'pkgsrc/x11/cinnamon-menus'
PKGPATH = 'x11/cinnamon-menus'
FIELDS = ('PKGREVISION', 'BUILD_DEPENDS', 'TOOL_DEPENDS', 'MAKE_ENV',
          'MESON_CROSS_VARS', 'MESON_BINARIES', 'PKG_FAIL_REASON',
          'BUILDLINK_API_DEPENDS.cinnamon-menus', 'GLIB_PUBLIC')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob('*')) if path.is_file()}


def export_recipe(args):
    adapter = load('export_fixture', ROOT / 'scripts/tests/export-fixture.py')
    exporter = adapter.load_exporter(ROOT)
    recipes, _, _, _ = exporter.configuration(ROOT)
    selected = [source for name, source in recipes if name == PKGPATH]
    require(selected == [RECIPE], 'the common export must select one canonical CMenu recipe')
    require(not (ROOT / 'probes/cinnamon/cinnamon-menus').exists(), 'the probe recipe remains')

    fixture = args.work / 'ports'
    source = fixture / 'pkgsrc' / PKGPATH
    source.parent.mkdir(parents=True)
    shutil.copytree(RECIPE, source)
    (fixture / 'pkgsrc/export.conf').write_text('')
    upstream = args.work / 'upstream'
    upstream.mkdir()
    # The upstream fixture has no CMenu recipe, as in the pinned pkgsrc tree.
    environment = {'FAKE_ARCHIVE': str(upstream), 'FAKE_MATCH': '1',
                   'EXPORT_TEST_GIT': str(args.git), 'EXPORT_TEST_PATCH': str(args.patch)}
    with mock.patch.dict(os.environ, environment):
        exporter.export_pkgsrc(fixture, args.work / 'export',
                              selection=adapter.TestSelection(), runner=adapter.test_runner,
                              scratch=args.work / 'export-scratch')
    exported = args.work / 'export' / PKGPATH
    require(inventory(RECIPE) == inventory(exported), 'export changed the recipe payload')

    (fixture / 'pkgsrc/export.conf').write_text(
        'recipe\tpkgsrc/' + PKGPATH + '\t' + PKGPATH + '\n')
    try:
        exporter.configuration(fixture)
    except exporter.ExportError as error:
        require('Two recipe sources' in str(error), 'duplicate failed for an unrelated reason')
    else:
        raise ValueError('a duplicate recipe provider was accepted')
    return exported


def metadata_tree(args, exported):
    tree = exported.parents[1]
    files = {
        'mk/bsd.prefs.mk': '',
        'mk/bsd.pkg.mk': '',
        'devel/meson/build.mk': '',
        'devel/gobject-introspection/buildlink3.mk': '',
        'devel/glib2/buildlink3.mk': 'GLIB_PUBLIC= yes\n',
    }
    for name, contents in files.items():
        path = tree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    # Evaluate the actual shared routing include, without executing its targets.
    shutil.copyfile(ROOT / 'pkgsrc/devel/gobject-introspection/cross.mk',
                    tree / 'devel/gobject-introspection/cross.mk')
    (args.work / 'sdk/src/emberbsd_sdk').mkdir(parents=True)
    (args.work / 'sdk/src/emberbsd_sdk/__init__.py').write_text('')
    for name in ('python', 'cc', 'query.json'):
        (args.work / name).write_text('finite metadata input; never executed\n')
    (args.work / 'empty-path').mkdir()
    (exported / 'consumer.mk').write_text('.include "buildlink3.mk"\n')
    return exported


def evaluate(args, package, mode, consumer=False):
    architecture, triplet = ('x86_64', 'x86_64--netbsd') if mode == 'amd64' else (
        'aarch64', 'aarch64--netbsd')
    command = [str(args.bmake), '-r', '-f', 'consumer.mk' if consumer else 'Makefile',
               'USE_CROSS_COMPILE=' + ('no' if mode == 'native' else 'yes'),
               'OPSYS=NetBSD', 'CROSS_OPSYS=NetBSD', 'CROSS_OS_VERSION=11.0',
               'MACHINE_ARCH=' + architecture, 'CROSS_MACHINE_ARCH=' + architecture,
               'MACHINE_GNU_PLATFORM=' + triplet,
               'EMBERBSD_CROSS_BUILD_PYTHON=' + str(args.work / 'python'),
               'EMBERBSD_CROSS_BUILD_CC=' + str(args.work / 'cc'),
               'EMBERBSD_GI_QUERY_CONFIG=' + str(args.work / 'query.json'),
               'EMBERBSD_SDK_SOURCE=' + str(args.work / 'sdk'),
               'TOOLBASE=/finite-host', 'CROSS_DESTDIR=/finite-target',
               'PREFIX=/usr/pkg', 'TOOLDIR=/finite-cross']
    for name in FIELDS:
        command += ['-V', name + '=${' + name + '}']
    result = subprocess.run(command, cwd=package, capture_output=True, text=True,
                            timeout=30, check=True,
                            env={'PATH': str(args.work / 'empty-path'), 'LC_ALL': 'C'})
    return dict(line.split('=', 1) for line in result.stdout.splitlines())


def check(args, package):
    output = {}
    for mode in ('native', 'aarch64', 'amd64'):
        values = evaluate(args, package, mode)
        output[mode] = values
        require(not values['PKG_FAIL_REASON'], mode + ': GI metadata refused')
        require(values['PKGREVISION'] == '4', 'dependency change needs package revision 4')
        require('gtk3' not in ' '.join(values.values()), mode + ': GTK3 dependency appeared')
        if mode == 'native':
            require('glib2-introspection-' in values['TOOL_DEPENDS'], 'native GIR dependency is absent')
            require('glib2-introspection' not in values['BUILD_DEPENDS'], 'native mode selects target GIR data')
            require('GI_CROSS_LAUNCHER=' not in values['MAKE_ENV'], 'native mode selects the target launcher')
            require('XDG_DATA_DIRS=' not in values['MAKE_ENV'], 'native mode overrides its GIR data path')
            require(not values['MESON_CROSS_VARS'] and not values['MESON_BINARIES'],
                    'native mode overrides cross generator metadata')
        else:
            require('glib2-introspection>=2.90.1nb1:' in values['BUILD_DEPENDS'],
                    mode + ': target GIR dependency is absent')
            require('glib2-introspection' not in values['TOOL_DEPENDS'], mode + ': native GIR data selected')
            require('gobject-introspection>=' in values['TOOL_DEPENDS'], mode + ': native GI tools absent')
            require('GI_CROSS_LAUNCHER=' in values['MAKE_ENV'], mode + ': real target launcher absent')
            require('XDG_DATA_DIRS=/finite-target/usr/pkg/share' in values['MAKE_ENV'],
                    mode + ': target GIR search path absent')
            require('emberbsd_gi_ldd_wrapper' in values['MESON_CROSS_VARS'], mode + ': ELF wrapper absent')
            require(all(name in values['MESON_BINARIES'] for name in ('g-ir-scanner', 'g-ir-compiler')),
                    mode + ': native GI generator selection absent')
        public = evaluate(args, package, mode, consumer=True)
        require(public['BUILDLINK_API_DEPENDS.cinnamon-menus'] == 'cinnamon-menus>=6.6.0',
                'public CMenu floor is stale')
        require(public['GLIB_PUBLIC'] == 'yes', 'public GIO header dependency is absent')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bmake', 'git', 'patch', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    require(all(value.is_absolute() for value in vars(args).values()), 'all paths must be absolute')
    args.work.mkdir(parents=True, exist_ok=False)
    package = metadata_tree(args, export_recipe(args))
    results = check(args, package)
    mutations = (
        ('target-gir', 'Makefile', 'BUILD_DEPENDS+= glib2-introspection>=2.90.1nb1:../../devel/glib2-introspection\n', ''),
        ('native-gir', 'Makefile', 'TOOL_DEPENDS+= glib2-introspection-[0-9]*:../../devel/glib2-introspection\n', ''),
        ('public-glib', 'buildlink3.mk', '.include "../../devel/glib2/buildlink3.mk"\n', ''),
        ('api-floor', 'buildlink3.mk', 'cinnamon-menus>=6.6.0', 'cinnamon-menus>=4.8'),
        ('native-cross-route', 'Makefile', '.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"', '.if 1'),
    )
    failures = {}
    for label, name, before, after in mutations:
        path = package / name
        original = path.read_text()
        require(original.count(before) == 1, 'mutation input changed: ' + label)
        path.write_text(original.replace(before, after))
        try:
            check(args, package)
        except ValueError as error:
            failures[label] = str(error)
        else:
            raise ValueError('deliberate fault passed: ' + label)
        finally:
            path.write_text(original)
    check(args, package)
    (args.work / 'results.json').write_text(json.dumps({
        'scope': 'source export and finite metadata; no SDK qualification or build',
        'metadata': results, 'rejected_mutations': failures,
        'source_files': inventory(RECIPE),
        'python': {'path': sys.executable, 'version': sys.version,
                   'sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()},
        'tools': {name: {'path': str(getattr(args, name)),
                         'sha256': hashlib.sha256(getattr(args, name).read_bytes()).hexdigest()}
                  for name in ('bmake', 'git', 'patch')},
    }, indent=2) + '\n')
    print('PASS: canonical export, duplicate refusal, three metadata modes, five causal controls')


if __name__ == '__main__':
    main()
