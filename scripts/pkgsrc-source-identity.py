# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Fingerprint the inputs to the canonical pkgsrc export.

The deliberately conservative identity includes every configured overlay.  A
change to an unrelated overlay may require re-preparing a source tree, while
an unrelated commit which leaves these inputs unchanged does not.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True


def effective_package_identity(exported, package, upstream):
    """Describe the effective exported recipe; retain upstream as provenance.

    Callers must supply an export produced by the canonical exporter.  The
    compatibility digest covers the effective recipe, distinfo, patches and
    auxiliary files after all overlays.  The upstream
    revision identifies where it came from but is not part of the digest.
    """
    from emberbsd_sdk import inventory

    root = Path(exported).resolve(strict=True)
    if not isinstance(package, str) or re.fullmatch(
            r'[a-z0-9][a-z0-9+_.-]*/[a-z0-9][a-z0-9+_.-]*', package) is None:
        raise ValueError('invalid package path')
    parts = package.split('/')
    if not isinstance(upstream, str) or len(upstream) != 40 or any(c not in '0123456789abcdef' for c in upstream):
        raise ValueError('invalid upstream revision')
    directory = root.joinpath(*parts)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError('effective package is not a directory')
    # The preparation owners consume recipe files and the complete patch and
    # files trees.  Descriptions, package manifests, tests and bootstrap
    # metadata are not inputs to those owners' source preparation.
    inputs = ('Makefile', 'Makefile.common', 'distinfo', 'patches', 'files')
    exclude = [child.name for child in directory.iterdir()
               if child.name not in inputs and not child.name.endswith('.mk')]
    rows = inventory.snapshot_tree(str(directory), exclude=exclude)
    payload = {'api': 1, 'package': package, 'tree': rows}
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return {'api': 1, 'package': package,
            'effective_package_sha256': hashlib.sha256(encoded).hexdigest(),
            'upstream': upstream}


# A recipe file is an input to source preparation when it is one of these
# top-level entries of the package directory or a top-level *.mk file.
RECIPE_INPUTS = ('Makefile', 'Makefile.common', 'distinfo', 'patches', 'files')
GIT_PACKAGE_API = 2


def recipe_input(relative):
    top = relative.split('/', 1)[0]
    return top in RECIPE_INPUTS or ('/' not in relative and top.endswith('.mk'))


def _exporter(root):
    path = Path(root) / 'scripts/prepare-pkgsrc.py'
    spec = importlib.util.spec_from_file_location('emberbsd_pkgsrc_export_identity', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_environment():
    # Only the explicit Git executable and its own object store are used;
    # no index, alternate index or lazy fetch from a promisor remote.
    return {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'GIT_OPTIONAL_LOCKS': '0',
            'GIT_NO_LAZY_FETCH': '1', 'GIT_CONFIG_NOSYSTEM': '1', 'HOME': '/nonexistent'}


def _file_mode(path):
    # The exporter copies files with umask 022, so only the execute bit of
    # the owner survives as a distinction; Git records exactly that.
    return '100755' if os.stat(path).st_mode & 0o100 else '100644'


def _hash_objects(git, root, paths):
    """Return Git blob ids of the given files (no filters, no writes)."""
    if not paths:
        return []
    data = ''.join(str(path) + '\n' for path in paths).encode()
    out = subprocess.run([str(git), '-C', str(root), 'hash-object', '--no-filters', '--stdin-paths'],
                         input=data, stdout=subprocess.PIPE, check=True,
                         env=_git_environment()).stdout.split()
    if len(out) != len(paths):
        raise ValueError('git hash-object returned an unexpected number of ids')
    return [oid.decode('ascii') for oid in out]


def _hash_bytes(git, root, data):
    return subprocess.run([str(git), '-C', str(root), 'hash-object', '--no-filters', '--stdin'],
                          input=data, stdout=subprocess.PIPE, check=True,
                          env=_git_environment()).stdout.strip().decode('ascii')


def _directory_rows(git, root, directory):
    """Rows of a materialised recipe directory as the exporter copies it.

    shutil.copytree follows the (checked, in-tree, regular-file) links of a
    Ports overlay, so a link contributes its target's content.
    """
    directory = Path(directory)
    names, paths = [], []
    for current, dirs, files in os.walk(directory):
        dirs.sort()
        for name in sorted(files):
            path = Path(current) / name
            relative = path.relative_to(directory).as_posix()
            if recipe_input(relative):
                names.append(relative)
                paths.append(path.resolve(strict=True))
    oids = _hash_objects(git, root, paths)
    return {name: [_file_mode(path), oid] for name, path, oid in zip(names, paths, oids)}


def _tree_rows(git, repository, revision, package):
    """Rows of one package directory of a pinned commit, from Git's tree."""
    out = subprocess.run([str(git), '-C', str(repository), 'ls-tree', '-r', '-z', '--full-tree',
                          revision, '--', package + '/'],
                         stdout=subprocess.PIPE, check=True, env=_git_environment()).stdout
    rows = {}
    for entry in out.split(b'\0'):
        if not entry:
            continue
        meta, _, name = entry.partition(b'\t')
        mode, kind, oid = meta.decode('ascii').split()
        relative = name.decode('utf-8', 'surrogateescape')[len(package) + 1:]
        if kind == 'commit':
            raise ValueError('effective package contains a gitlink: ' + package + '/' + relative)
        if recipe_input(relative):
            # git archive gives regular files mode 644/755 after umask 022.
            rows[relative] = [mode, oid]
    return rows


def _patch_targets(source):
    """Paths (after -p1) named by a patch, or None when they are unknown."""
    names = []
    for line in Path(source).read_bytes().split(b'\n'):
        if line.startswith((b'--- ', b'+++ ', b'diff --git ')):
            if line.startswith(b'diff --git '):
                fields = line[11:].split(b' ')
            else:
                fields = [line[4:].split(b'\t')[0].strip()]
            for field in fields:
                if field == b'/dev/null':
                    continue
                parts = field.decode('utf-8', 'surrogateescape').split('/')[1:]
                if not parts or any(part in ('', '.', '..') for part in parts):
                    return None
                names.append('/'.join(parts))
    return names or None


def git_package_inputs(ports_root, package, git):
    """Identify one effective recipe from Git object ids, without an export.

    The identity covers the same recipe inputs as effective_package_identity
    (Makefile, Makefile.common, distinfo, *.mk, patches/ and files/ of the
    package after all overlays): the blob ids of the pinned pkgsrc tree or of
    the Ports overlay that replaces it, the recipe patches and exported files
    placed into it, and the blob ids of every infrastructure patch that names
    a path in it (or whose paths are unknown).  Git already stores these ids
    for the pinned tree; overlay files are hashed with git hash-object, so
    uncommitted overlay edits count.  The upstream revision is provenance.
    """
    root = Path(ports_root).resolve(strict=True)
    if not os.path.isabs(str(git)) or not os.path.isfile(git) or not os.access(git, os.X_OK):
        raise ValueError('git must be an absolute executable')
    if not isinstance(package, str) or re.fullmatch(
            r'[a-z0-9][a-z0-9+_.-]*/[a-z0-9][a-z0-9+_.-]*', package) is None:
        raise ValueError('invalid package path')
    exporter = _exporter(root)
    recipes, patches, files, _ = exporter.configuration(root)
    if exporter.version_pruned(package, exporter.version_families(root)):
        raise ValueError('pkgsrc/versions.mk removes ' + package)

    def run(directory, *args):
        return subprocess.run([str(git), '-C', str(directory), *args], stdout=subprocess.PIPE,
                              check=True, env=_git_environment()).stdout.strip()

    pin = run(root, 'ls-files', '--stage', '--', 'upstream/pkgsrc').split()
    if len(pin) != 4 or pin[0] != b'160000' or pin[2] != b'0':
        raise ValueError('Expected one pinned pkgsrc gitlink')
    upstream = pin[1].decode('ascii')
    if run(root / 'upstream/pkgsrc', 'rev-parse', 'HEAD').decode('ascii') != upstream:
        raise ValueError('pkgsrc checkout differs from its gitlink')
    overlay = dict(recipes).get(package)
    if overlay is not None:
        origin = 'ports'
        rows = _directory_rows(git, root, overlay)
    else:
        origin = 'pkgsrc'
        rows = _tree_rows(git, root / 'upstream/pkgsrc', upstream, package)
    if 'Makefile' not in rows:
        raise ValueError('effective package has no Makefile: ' + package)
    appended = []
    for method, source, recipe, name in patches:
        if method == 'recipe-patch' and recipe == package:
            rows['patches/' + name] = [_file_mode(source), _hash_objects(git, root, [source])[0]]
            appended.append(f'SHA1 ({name}) = {exporter.patch_sha1(source)}\n')
    if appended:
        if 'distinfo' not in rows:
            raise ValueError('recipe patch for a package without distinfo: ' + package)
        if origin == 'ports':
            base = (Path(overlay) / 'distinfo').read_bytes()
        else:
            base = subprocess.run([str(git), '-C', str(root / 'upstream/pkgsrc'), 'cat-file', 'blob',
                                   rows['distinfo'][1]], stdout=subprocess.PIPE, check=True,
                                  env=_git_environment()).stdout
        rows['distinfo'] = [rows['distinfo'][0],
                            _hash_bytes(git, root, base + ''.join(appended).encode('utf-8'))]
    for source, destination in files:
        if destination.startswith(package + '/'):
            relative = destination[len(package) + 1:]
            if recipe_input(relative):
                rows[relative] = [_file_mode(source), _hash_objects(git, root, [source])[0]]
    infrastructure = []
    for method, source, _, _ in patches:
        if method not in ('patch', 'git-apply'):
            continue
        targets = _patch_targets(source)
        if targets is None or any(target.startswith(package + '/') and
                                  recipe_input(target[len(package) + 1:]) for target in targets):
            infrastructure.append([method, source.relative_to(root).as_posix(),
                                   _hash_objects(git, root, [source])[0]])
    return {'api': GIT_PACKAGE_API, 'package': package, 'origin': origin,
            'tree': dict(sorted(rows.items())), 'infrastructure_patches': infrastructure,
            'upstream': upstream}


def git_package_identity(ports_root, package, git):
    """Return the API 2 effective package identity of git_package_inputs."""
    payload = git_package_inputs(ports_root, package, git)
    upstream = payload.pop('upstream')
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return {'api': GIT_PACKAGE_API, 'package': package,
            'effective_package_sha256': hashlib.sha256(encoded).hexdigest(),
            'upstream': upstream}


def exported_package_rows(exported, package, git):
    """Rows of an exported package directory, for comparison with the Git rows.

    Used to show that the Git-derived identity describes the files that the
    canonical export materialises.
    """
    root = Path(exported).resolve(strict=True)
    return _directory_rows(git, root, root.joinpath(*package.split('/')))


def current_git_package(old, owner_sha256, current):
    """Whether a scoped receipt still names the current Git recipe objects.

    Only API 2 receipts qualify; `current` computes the owner's present
    identity lazily, so API 1 receipts keep using the export comparison.
    """
    if not isinstance(old, dict) or set(old) != {'effective', 'owner_sha256'}:
        return False
    effective = old['effective']
    if (not isinstance(effective, dict) or effective.get('api') != GIT_PACKAGE_API or
            old['owner_sha256'] != owner_sha256):
        return False
    return equivalent_effective_package(effective, current())


def equivalent_effective_package(left, right):
    """Compare effective inputs while leaving the recorded origin untouched."""
    keys = {'api', 'package', 'effective_package_sha256', 'upstream'}
    def valid(value):
        return (isinstance(value, dict) and set(value) == keys and
                type(value['api']) is int and value['api'] in (1, GIT_PACKAGE_API) and
                isinstance(value['package'], str) and
                re.fullmatch(r'[a-z0-9][a-z0-9+_.-]*/[a-z0-9][a-z0-9+_.-]*', value['package']) is not None and
                isinstance(value['effective_package_sha256'], str) and
                re.fullmatch(r'[0-9a-f]{64}', value['effective_package_sha256']) is not None and
                isinstance(value['upstream'], str) and
                re.fullmatch(r'[0-9a-f]{40}', value['upstream']) is not None)
    return (valid(left) and valid(right) and left['api'] == right['api'] and
            left['package'] == right['package'] and
            left['effective_package_sha256'] == right['effective_package_sha256'])


def identity(ports_root, package, git, sdk_source):
    root, package, payload, _ = export_inputs(ports_root, git, sdk_source, package)
    payload['package'] = package
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return {'api': 1, 'package': package,
            'export_inputs_sha256': hashlib.sha256(encoded).hexdigest(),
            'upstream': payload['upstream']}


def export_inputs(ports_root, git, sdk_source, package=None):
    """Return the package-independent inputs of the canonical export."""
    root = Path(ports_root).resolve(strict=True)
    if not os.path.isabs(str(git)) or not os.path.isfile(git) or not os.access(git, os.X_OK):
        raise ValueError('git must be an absolute executable')
    loader_path = root / 'pkgsrc/lang/llvm/files/sdk_source.py'
    loader_spec = importlib.util.spec_from_file_location('selected_sdk_source', loader_path)
    loader = importlib.util.module_from_spec(loader_spec)
    loader_spec.loader.exec_module(loader)
    loader.load_sdk(['--sdk-source', str(sdk_source)])
    from emberbsd_sdk import inventory, process, sourceprep

    if sourceprep.PREPARED_TREE_API != 1:
        raise ValueError('SDK prepared-tree API 1 is required')
    path = root / 'scripts/prepare-pkgsrc.py'
    spec = importlib.util.spec_from_file_location('emberbsd_pkgsrc_export', path)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    if package is not None:
        package = exporter.package_path(package, 'package')
    recipes, patches, files, _, manifests = exporter.configuration(root, include_manifests=True)

    def run(directory, *args):
        return subprocess.check_output([str(git), '-C', str(directory), *args],
                                       env=process.sanitized_environment()).strip()

    pin = run(root, 'ls-files', '--stage', '--', 'upstream/pkgsrc').split()
    if len(pin) != 4 or pin[0] != b'160000' or pin[2] != b'0':
        raise ValueError('Expected one pinned pkgsrc gitlink')
    if run(root / 'upstream/pkgsrc', 'rev-parse', 'HEAD') != pin[1]:
        raise ValueError('pkgsrc checkout differs from its gitlink')

    inputs = {path, root / 'pkgsrc/export.conf', root / 'pkgsrc/replaces'}
    inputs.update(source for _, source, _, _ in patches)
    inputs.update(source for source, _ in files)
    inputs.update(manifests)
    inputs = {str(p.relative_to(root)): inventory.sha256_file(str(p))
              for p in sorted(inputs) if p.exists()}
    def tree(source):
        rows = inventory.snapshot_installed_tree(str(source))
        for relative, row in rows.items():
            if row['kind'] == 'link':
                target = (source / relative).resolve(strict=True)
                if not target.is_relative_to(root) or not target.is_file():
                    raise ValueError(f'unsupported export source link: {source / relative}')
                row['target_sha256'] = inventory.sha256_file(str(target))
        return rows

    trees = {str(source.relative_to(root)): tree(source) for _, source in recipes}
    # Include overlay category metadata and replacement-list state as well.
    trees['pkgsrc'] = tree(root / 'pkgsrc')
    payload = {'api': 1, 'upstream': pin[1].decode('ascii'),
               'files': inputs, 'trees': trees}
    return root, package, payload, run


SHARED_EXPORT_RECEIPT = 'pkgsrc-export.json'
SHARED_EXPORT_FORMAT = 'emberbsd-pkgsrc-shared-export'
# These small source directories are consumed directly from the shared export.
SHARED_EXPORT_MATERIAL = ('net/libfetch/files',)


def material_snapshot(root):
    """Snapshot regular files by relative path, execute mode and SHA256."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('missing shared export material directory')
    rows = {}
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('symlink in shared export material')
        if path.is_file():
            rows[path.relative_to(root).as_posix()] = [
                bool(path.stat().st_mode & 0o111), hashlib.sha256(path.read_bytes()).hexdigest()]
        elif path.is_dir():
            rows[path.relative_to(root).as_posix()] = ['directory']
        else:
            raise ValueError('non-regular shared export material')
    return rows


def shared_export_material(directory, relative):
    """Return a stored snapshot, or None for a legacy v1 export."""
    receipt = json.loads((Path(directory) / SHARED_EXPORT_RECEIPT).read_text(encoding='ascii'))
    if receipt['version'] == 1:
        return None
    return receipt['material'][relative]



def export_identity(ports_root, git, sdk_source, patch):
    """Identify one canonical export for every package of a run.

    The export depends on the Ports commit, the pinned pkgsrc commit, the
    overlay inputs (which also cover uncommitted overlay edits) and the patch
    tool that applied the infrastructure patches.
    """
    if not os.path.isabs(str(patch)) or not os.path.isfile(patch) or not os.access(patch, os.X_OK):
        raise ValueError('patch must be an absolute executable')
    root, _, payload, run = export_inputs(ports_root, git, sdk_source)
    from emberbsd_sdk import inventory
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return {'api': 1, 'ports_commit': run(root, 'rev-parse', 'HEAD').decode('ascii'),
            'upstream': payload['upstream'],
            'export_inputs_sha256': hashlib.sha256(encoded).hexdigest(),
            'patch': {'path': str(patch), 'sha256': inventory.sha256_file(str(patch))}}


def create_shared_export(directory, ports_root, git, sdk_source, patch):
    """Export pkgsrc once into a new directory and record its identity."""
    directory = Path(directory)
    if not directory.is_absolute():
        raise ValueError('shared export directory must be absolute')
    before = export_identity(ports_root, git, sdk_source, patch)
    directory.mkdir(mode=0o700)
    from emberbsd_sdk import process
    subprocess.run([sys.executable, '-B', str(Path(ports_root) / 'scripts/prepare-pkgsrc.py'),
                    str(directory / 'pkgsrc'), '--git', str(git), '--patch', str(patch)],
                   check=True, env=process.sanitized_environment(), stdout=sys.stderr)
    if export_identity(ports_root, git, sdk_source, patch) != before:
        raise ValueError('pkgsrc export inputs changed during the shared export')
    receipt = {'format': SHARED_EXPORT_FORMAT, 'version': 2, 'identity': before,
               'material': {name: material_snapshot(directory / 'pkgsrc' / name)
                            for name in SHARED_EXPORT_MATERIAL}}
    with open(directory / SHARED_EXPORT_RECEIPT, 'x', encoding='ascii') as output:
        output.write(json.dumps(receipt, sort_keys=True) + '\n')
    return receipt


def shared_export(directory, ports_root, git, sdk_source, patch):
    """Return the pkgsrc tree of a shared export made from current inputs.

    The caller owns the directory for the duration of its run; this check
    binds the export to the Ports commit, pkgsrc commit, overlay inputs and
    patch tool selected now, and refuses an export made from other ones.
    """
    directory = Path(directory)
    if not directory.is_absolute() or directory.is_symlink() or not directory.is_dir():
        raise ValueError('shared pkgsrc export must be an absolute real directory')
    path = directory / SHARED_EXPORT_RECEIPT
    if path.is_symlink() or not path.is_file():
        raise ValueError('shared pkgsrc export has no receipt')
    receipt = json.loads(path.read_text(encoding='ascii'))
    if (not isinstance(receipt, dict) or receipt.get('format') != SHARED_EXPORT_FORMAT or
            type(receipt.get('version')) is not int or receipt['version'] not in (1, 2) or
            set(receipt) != ({'format', 'version', 'identity'} if receipt['version'] == 1 else
                             {'format', 'version', 'identity', 'material'}) or
            (receipt['version'] == 2 and
             (not isinstance(receipt['material'], dict) or
              set(receipt['material']) != set(SHARED_EXPORT_MATERIAL)))):
        raise ValueError('invalid shared pkgsrc export receipt')
    if receipt['identity'] != export_identity(ports_root, git, sdk_source, patch):
        raise ValueError('shared pkgsrc export was made from different inputs')
    exported = directory / 'pkgsrc'
    revision = exported / 'EMBERBSD-PKGSRC-REVISION'
    if (exported.is_symlink() or not exported.is_dir() or revision.is_symlink() or not revision.is_file() or
            revision.read_text(encoding='ascii') != receipt['identity']['upstream'] + '\n'):
        raise ValueError('shared pkgsrc export tree differs from its receipt')
    return exported
