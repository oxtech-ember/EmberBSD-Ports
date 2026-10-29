#!/usr/bin/env python3
"""Query real pkgsrc metadata for both QtQuick3D importer selections."""
import argparse
import pathlib
import subprocess

p = argparse.ArgumentParser()
p.add_argument('pkgsrc', type=pathlib.Path)
p.add_argument('--make', default='/usr/bin/make')
p.add_argument('--makeconf', default='/etc/mk.conf')
a = p.parse_args()
recipe = a.pkgsrc / 'graphics/qt6-qtquick3d'
variables = ['PKG_OPTIONS', 'DEPENDS', 'CONFIGURE_ARGS', 'PLIST.assimp']
for selection, enabled in [('', True), ('assimp', True), ('-assimp', False)]:
    command = [a.make, f'MAKECONF={a.makeconf}', f'PKG_OPTIONS.qt6-qtquick3d={selection}']
    for variable in variables:
        command += ['-V', '${' + variable + '}']
    result = subprocess.run(command, cwd=recipe, capture_output=True, text=True, check=True)
    values = result.stdout.splitlines()
    assert len(values) == 4, result.stdout
    options, dependencies, configure, plist = values
    assert ('assimp' in options.split()) == enabled, (selection, options)
    has_assimp = any(dependency.endswith(':../../multimedia/assimp') for dependency in dependencies.split())
    assert has_assimp == enabled, (selection, dependencies)
    assert ('-DFEATURE_quick3d_assimp:BOOL=OFF' in configure.split()) == (not enabled), (selection, configure)
    for flag in ('-DINPUT_quick3d_assimp:STRING=system', '-DFEATURE_system_assimp:BOOL=ON'):
        assert (flag in configure.split()) == enabled, (selection, configure)
    assert '-no-feature-quick3d-assimp' not in configure.split(), configure
    assert (plist == 'yes') == enabled, (selection, plist)
    print(f'PASS: {selection or "default"} selects the expected dependency, feature and package manifest')
plist = (recipe / 'PLIST').read_text().splitlines()
plugin_files = [line for line in plist if 'Qt6AssimpImporterPlugin' in line or 'plugins/assetimporters/libassimp.so' in line]
assert len(plugin_files) == 8 and all(line.startswith('${PLIST.assimp}') for line in plugin_files), plugin_files
for library in ['qt6/lib/libQt6Quick3D.so', 'qt6/lib/libQt6Quick3DRuntimeRender.so']:
    assert library in plist, library
print('PASS: 8 importer files are conditional; core library manifest entries stay unconditional')
