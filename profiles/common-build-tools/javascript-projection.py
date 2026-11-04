#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD contributors (AI-assisted).
"""Project installed common JS providers without selecting package versions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

NAME = re.compile(r'^(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*$')
MODULE = re.compile(r'^lib/node_modules/((?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*)/package\.json$')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def regular(path, prefix):
    require(stat.S_ISREG(path.lstat().st_mode), f'not a regular file: {path}')
    require(path.resolve(strict=True).is_relative_to(prefix), f'file escapes prefix: {path}')
    return path


def project(prefix, node, pkg_admin, roots, runtimes):
    prefix = Path(prefix).resolve(strict=True)
    node = Path(node).resolve(strict=True)
    require(node.is_relative_to(prefix) and node.is_file(), 'Node must be inside the selected prefix')
    pkg_admin = Path(pkg_admin).resolve(strict=True)
    require(pkg_admin.is_relative_to(prefix) and pkg_admin.is_file(), 'pkg_admin must be inside the selected prefix')
    database = prefix / 'pkgdb'
    require(database.is_dir() and database.resolve(strict=True).is_relative_to(prefix), 'missing selected package database')
    owners = {}
    for package in sorted(database.iterdir()):
        if not package.is_dir() or package.is_symlink():
            continue
        contents, build = package / '+CONTENTS', package / '+BUILD_INFO'
        if not contents.is_file() or not build.is_file():
            continue
        lines = regular(contents, prefix).read_text().splitlines()
        paths = [MODULE.fullmatch(line) for line in lines]
        paths = [match.group(1) for match in paths if match]
        if not paths:
            continue
        cwd_lines = [line for line in lines if line.startswith('@cwd ')]
        require('@name ' + package.name in lines and cwd_lines and
                all(line == '@cwd ' + str(prefix) for line in cwd_lines),
                f'package identity or prefix differs: {package.name}')
        info = regular(build, prefix).read_text().splitlines()
        pkgpaths = [line[8:] for line in info if line.startswith('PKGPATH=')]
        require(len(pkgpaths) == 1 and re.fullmatch(r'[a-z0-9+_.-]+/[a-z0-9+_.-]+', pkgpaths[0]),
                f'invalid package origin: {package.name}')
        external_lines = [line.partition('=')[2] for line in info if line.startswith('JS_MODULE_EXTERNAL_PEERS=')]
        require(len(external_lines) <= 1, f'duplicate external peer metadata: {package.name}')
        external = external_lines[0].split() if external_lines else []
        require(len(external) == len(set(external)), f'duplicate external peers: {package.name}')
        version_file = regular(package / '+BUILD_VERSION', prefix)
        version_bytes = version_file.read_bytes()
        distinfo_key = pkgpaths[0] + '/distinfo: '
        distinfos = [line[len(distinfo_key):] for line in version_bytes.decode('utf8').splitlines()
                     if line.startswith(distinfo_key)]
        require(len(distinfos) == 1 and re.fullmatch(r'[0-9a-f]{64}', distinfos[0]),
                f'missing distinfo source identity: {package.name}')
        patterns = [line[8:] for line in lines if line.startswith('@pkgdep ')]
        record = {'pkgname': package.name, 'pkgpath': pkgpaths[0], 'externalPeers': external,
                  'pkgdepPatterns': patterns, 'distinfoSha256': distinfos[0],
                  'buildVersionSha256': hashlib.sha256(version_bytes).hexdigest()}
        for name in paths:
            require(name not in owners, f'multiple installed owners: {name}')
            module_prefix = 'lib/node_modules/' + name + '/'
            owned = {line for line in lines if line.startswith(module_prefix)}
            require(module_prefix + 'package.json' in owned, f'missing owned manifest: {name}')
            owners[name] = {**record, '_ownedFiles': owned}
    def check_tree(name, directory):
        actual_files = set()
        for current, dirs, files in os.walk(directory, followlinks=False):
            for item in dirs + files:
                path = Path(current) / item
                mode = path.lstat().st_mode
                require(stat.S_ISDIR(mode) or stat.S_ISREG(mode), f'link or special file in {name}: {item}')
                require(not (stat.S_ISREG(mode) and path.suffix in ('.node', '.so', '.dylib', '.dll')),
                        f'native payload in source module: {name}/{item}')
                if stat.S_ISREG(mode):
                    actual_files.add(path.relative_to(prefix).as_posix())
        require(actual_files == owners[name]['_ownedFiles'], f'module files differ from package ownership: {name}')

    require('semver' in owners, 'common semver provider is not installed')
    semver_root = (prefix / 'lib/node_modules/semver').resolve(strict=True)
    require(semver_root.is_relative_to(prefix), 'semver escapes prefix')
    check_tree('semver', semver_root)
    require(isinstance(roots, dict) and roots, 'missing module roots')
    for name, pkgpath in roots.items():
        require(NAME.fullmatch(name) and re.fullmatch(r'[a-z0-9+_.-]+/[a-z0-9+_.-]+', pkgpath), 'invalid module root owner')
        require(name in owners and owners[name]['pkgpath'] == pkgpath, f'root package owner differs: {name}')
    projected, pending = {}, list(roots)
    while pending:
        name = pending.pop()
        require(NAME.fullmatch(name) is not None, f'invalid module name: {name}')
        if name in projected:
            continue
        require(name in owners, f'no installed package owns module: {name}')
        module_dir = prefix / 'lib/node_modules' / name
        require(module_dir.is_dir() and not module_dir.is_symlink() and module_dir.resolve(strict=True).is_relative_to(prefix),
                f'module directory escapes prefix: {name}')
        metadata = json.loads(regular(module_dir / 'package.json', prefix).read_text())
        require(metadata.get('name') == name and isinstance(metadata.get('version'), str), f'invalid module metadata: {name}')
        require(not metadata.get('os') and not metadata.get('cpu'), f'platform-specific module: {name}')
        scripts = metadata.get('scripts', {})
        require(isinstance(scripts, dict) and not any(key in scripts for key in ('install', 'preinstall', 'postinstall')),
                f'unsupported install lifecycle: {name}')
        deps, optional = metadata.get('dependencies', {}), metadata.get('optionalDependencies', {})
        peers, peer_meta = metadata.get('peerDependencies', {}), metadata.get('peerDependenciesMeta', {})
        require(all(isinstance(value, dict) for value in (deps, optional, peers, peer_meta)), f'invalid dependencies: {name}')
        require(all(isinstance(v, dict) for v in peer_meta.values()), f'invalid peer metadata: {name}')
        require(not set(deps) & set(optional), f'duplicate dependency declarations: {name}')
        dependencies = {**deps, **optional}
        mandatory = {key: value for key, value in peers.items() if not peer_meta.get(key, {}).get('optional', False)}
        require(not set(mandatory) & set(dependencies), f'peer overlaps dependency: {name}')
        require(set(owners[name]['externalPeers']).issubset(mandatory), f'invalid external peer metadata: {name}')
        for dep, wanted in list(dependencies.items()) + list(mandatory.items()):
            require(NAME.fullmatch(dep) is not None and isinstance(wanted, str) and wanted, f'invalid range: {name}/{dep}')
        check_tree(name, module_dir)
        projected[name] = {**owners[name], 'name': name, 'version': metadata['version'],
                           'modulePath': 'lib/node_modules/' + name,
                           'dependencies': dependencies, 'peers': mandatory,
                           'license': metadata.get('license', 'NOASSERTION')}
        pending.extend(dependencies)
        for peer in mandatory:
            if peer not in runtimes and peer not in owners[name]['externalPeers']:
                require(peer in owners, f'unknown or missing mandatory peer: {name}/{peer}')
                pending.append(peer)
    checks = []
    checked_patterns = {}

    def package_edge(name, dependency):
        owner = projected[dependency]
        patterns = projected[name]['pkgdepPatterns']
        require(patterns, f'missing pkgsrc dependency: {name}/{dependency}')
        for pattern in patterns:
            key = (pattern, owner['pkgname'])
            if key not in checked_patterns:
                result = subprocess.run([str(pkg_admin), 'pmatch', *key], capture_output=True,
                                        env={'PATH': str(prefix / 'bin'), 'LC_ALL': 'C'}, timeout=30)
                require(result.returncode in (0, 1), f'pkg_admin pmatch failed: {pattern}')
                checked_patterns[key] = result.returncode == 0
            if checked_patterns[key]:
                return
        raise ValueError(f'pkgsrc dependency does not match installed provider: {name}/{dependency}')

    for name, row in projected.items():
        for dep, wanted in row['dependencies'].items():
            require(dep in projected, f'missing dependency: {name}/{dep}')
            package_edge(name, dep)
            checks.append([name, dep, projected[dep]['version'], wanted])
        for dep, wanted in row['peers'].items():
            require(dep in runtimes or dep in projected, f'unknown or missing mandatory peer: {name}/{dep}')
            require(dep not in runtimes or dep in row['externalPeers'], f'undeclared external runtime peer: {name}/{dep}')
            if dep not in runtimes and dep not in row['externalPeers']:
                package_edge(name, dep)
            checks.append([name, dep, runtimes.get(dep, projected.get(dep, {}).get('version')), wanted])
    js = "const s=require(process.argv[1]);const c=JSON.parse(require('fs').readFileSync(0,'utf8'));for(const [a,b,v,r] of c){if(!s.validRange(r)||!s.valid(v)||!s.satisfies(v,r))throw Error(`${a}: ${b}@${v} does not satisfy ${r}`)}"
    run = subprocess.run([str(node), '-e', js, str(semver_root)], input=json.dumps(checks), text=True,
                         capture_output=True, env={'PATH': str(prefix / 'bin')}, timeout=60)
    require(run.returncode == 0, 'common semver rejected selected provider graph: ' + run.stderr.strip()[:1000])
    return [{key: value for key, value in projected[name].items() if key != '_ownedFiles'}
            for name in sorted(projected)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--node', required=True)
    parser.add_argument('--pkg-admin', required=True)
    parser.add_argument('--root', action='append', default=[])
    parser.add_argument('--runtime', action='append', default=[])
    args = parser.parse_args()
    try:
        roots = {}
        for item in args.root:
            name, separator, pkgpath = item.partition('=')
            require(separator and name not in roots, 'invalid or duplicate root')
            roots[name] = pkgpath
        runtimes = {}
        for item in args.runtime:
            name, separator, version = item.partition('=')
            require(separator and NAME.fullmatch(name) and version and name not in runtimes, 'invalid or duplicate runtime')
            runtimes[name] = version
        print(json.dumps({'schemaVersion': 1, 'modules': project(args.prefix, args.node, args.pkg_admin, roots, runtimes)}, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print('javascript-projection: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
