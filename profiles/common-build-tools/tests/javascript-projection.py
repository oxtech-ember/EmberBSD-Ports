#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Test installed JS projection with real Node and the selected semver source."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

if len(sys.argv) != 4:
    sys.exit('Usage: javascript-projection.py NODE SEMVER_MODULE PKG_ADMIN')
source = Path(__file__).resolve().parents[1] / 'javascript-projection.py'
spec = importlib.util.spec_from_file_location('js_projection', source)
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)

with tempfile.TemporaryDirectory(prefix='js-projection-') as temp:
    root = Path(temp).resolve()
    (root / 'bin').mkdir()
    (root / 'sbin').mkdir()
    shutil.copy2(sys.argv[3], root / 'sbin/pkg_admin')
    shutil.copy2(sys.argv[1], root / 'bin/node')
    modules = root / 'lib/node_modules'
    modules.mkdir(parents=True)
    shutil.copytree(sys.argv[2], modules / 'semver')
    database = root / 'pkgdb'
    database.mkdir()

    def owner(name, metadata, package, external='', dependencies=(), pkgpath=None):
        directory = modules / name
        directory.mkdir(parents=True, exist_ok=True)
        if metadata is not None:
            (directory / 'package.json').write_text(json.dumps(metadata))
        db = database / package
        db.mkdir()
        files = sorted(path.relative_to(root).as_posix() for path in directory.rglob('*') if path.is_file())
        (db / '+CONTENTS').write_text(f'@cwd {root}\n@name {package}\n' + ''.join(f'@pkgdep {dep}\n' for dep in dependencies) + ''.join(path + '\n' for path in files))
        pkgpath = pkgpath or f'devel/{package.rsplit("-", 1)[0]}'
        (db / '+BUILD_INFO').write_text(f'PKGPATH={pkgpath}\n' + (f'JS_MODULE_EXTERNAL_PEERS={external}\n' if external else ''))
        (db / '+BUILD_VERSION').write_text(f'{pkgpath}/distinfo: ' + 'a' * 64 + '\n')
        return directory

    owner('semver', None, 'node-semver-7.8.5')
    owner('@test/root', {'name': '@test/root', 'version': '1.0.0',
                         'dependencies': {'child': '^1.0.0'},
                         'peerDependencies': {'electron': '>11'}}, 'node-root-1.0.0', 'electron', ('node-child>=1.0.0',))
    child = owner('child', {'name': 'child', 'version': '1.1.0'}, 'node-child-1.1.0', pkgpath='devel/child-provider')
    args = (root, root / 'bin/node', root / 'sbin/pkg_admin', {'@test/root': 'devel/node-root'})
    result = projection.project(*args, {'electron': '45.2.1'})
    assert [row['name'] for row in result] == ['@test/root', 'child']
    assert all(row['pkgpath'].startswith('devel/') and row['buildVersionSha256'] for row in result)

    def fails(runtime, message):
        try:
            projection.project(*args, runtime)
        except (ValueError, OSError) as error:
            assert message in str(error), str(error)
        else:
            raise AssertionError('expected failure: ' + message)

    fails({}, 'unknown or missing mandatory peer')
    fails({'electron': '10.0.0'}, 'semver rejected')
    stray = child / 'unowned.js'
    stray.write_text('not owned')
    fails({'electron': '45.2.1'}, 'module files differ from package ownership')
    stray.unlink()
    child_manifest = child / 'package.json'
    child_bytes = child_manifest.read_bytes()
    child_manifest.unlink()
    fails({'electron': '45.2.1'}, 'No such file')
    child_manifest.write_bytes(child_bytes)
    root_info = database / 'node-root-1.0.0/+BUILD_INFO'
    original_info = root_info.read_text()
    root_info.write_text(original_info.replace('JS_MODULE_EXTERNAL_PEERS=electron\n', ''))
    fails({'electron': '45.2.1'}, 'undeclared external runtime peer')
    root_info.write_text(original_info)
    try:
        projection.project(root, root / 'bin/node', root / 'sbin/pkg_admin',
                           {'@test/root': 'devel/wrong-owner'}, {'electron': '45.2.1'})
    except ValueError as error:
        assert 'root package owner differs' in str(error)
    else:
        raise AssertionError('wrong root owner was accepted')
    root_contents = database / 'node-root-1.0.0/+CONTENTS'
    original_contents = root_contents.read_text()
    root_manifest = modules / '@test/root/package.json'
    original_manifest = root_manifest.read_text()
    owner('peer', {'name': 'peer', 'version': '1.2.0'}, 'node-peer-1.2.0')
    peer_manifest = json.loads(original_manifest)
    peer_manifest['peerDependencies']['peer'] = '^1.0.0'
    root_manifest.write_text(json.dumps(peer_manifest))
    root_contents.write_text(original_contents.replace('@pkgdep node-child>=1.0.0\n',
                                                       '@pkgdep node-child>=1.0.0\n@pkgdep node-peer>=1.0.0\n'))
    result = projection.project(*args, {'electron': '45.2.1'})
    assert [row['name'] for row in result] == ['@test/root', 'child', 'peer']
    root_manifest.write_text(original_manifest)
    root_contents.write_text(original_contents)
    root_contents.write_text(original_contents.replace('@pkgdep node-child>=1.0.0\n', ''))
    fails({'electron': '45.2.1'}, 'missing pkgsrc dependency')
    root_contents.write_text(original_contents.replace('node-child>=1.0.0', 'node-child>=3.0.0'))
    fails({'electron': '45.2.1'}, 'pkgsrc dependency does not match')
    root_contents.write_text(original_contents)
    root_manifest = modules / '@test/root/package.json'
    original = root_manifest.read_text()
    invalid = json.loads(original)
    invalid['peerDependencies']['electron'] = 'not-a-range'
    root_manifest.write_text(json.dumps(invalid))
    fails({'electron': '45.2.1'}, 'semver rejected')
    root_manifest.write_text(original)
    (database / 'node-child-1.1.0/+CONTENTS').unlink()
    fails({'electron': '45.2.1'}, 'no installed package owns module')
    (database / 'node-child-1.1.0/+CONTENTS').write_text(f'@cwd {root}\n@name node-child-1.1.0\nlib/node_modules/child/package.json\n')
    (child / 'package.json').write_text(json.dumps({'name': 'child', 'version': '2.0.0'}))
    fails({'electron': '45.2.1'}, 'semver rejected')
    (child / 'package.json').write_text(json.dumps({'name': 'child', 'version': '1.1.0',
                                                     'peerDependencies': {'unknown': '^1'}}))
    fails({'electron': '45.2.1'}, 'unknown or missing mandatory peer')
print('PASS: installed JS projection, missing owner/dependency/peer and incompatible runtime')
