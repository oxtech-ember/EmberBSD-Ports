#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compose an Electron GN source view using selected common sources."""
import os
import re
import ast
import stat
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def entries(source, omit):
    return {item.name: item for item in source.iterdir() if item.name not in omit}



def chromium_replacements(source):
    script = source / 'build/linux/unbundle/replace_gn_files.py'
    tree = ast.parse(script.read_text(), filename=str(script))
    assignments = [node for node in tree.body if isinstance(node, ast.Assign) and
                   any(isinstance(target, ast.Name) and target.id == 'REPLACEMENTS'
                       for target in node.targets)]
    require(len(assignments) == 1, 'invalid Chromium replacement inventory')
    mapping = ast.literal_eval(assignments[0].value)
    require(isinstance(mapping, dict), 'invalid Chromium replacement mapping')
    return mapping


def abseil_replacements(source):
    mapping = chromium_replacements(source)
    prefix = Path('third_party/abseil-cpp')
    result = {}
    for name, destination in mapping.items():
        if not name.startswith('absl_'):
            continue
        dest = Path(destination)
        require(not dest.is_absolute() and '..' not in dest.parts and dest.is_relative_to(prefix),
                'invalid Chromium Abseil mapping')
        shim = source / 'build/linux/unbundle' / (name + '.gn')
        require(shim.is_file(), 'missing Chromium Abseil shim: ' + name)
        rel = dest.relative_to(prefix)
        require(rel not in result and (source / dest).is_file(), 'invalid Abseil replacement target')
        result[rel] = shim
    require(result, 'Chromium Abseil replacements are missing')
    return result


def shim_masks(replacements):
    """Read the literal shim header lists selected from Chromium's GN files."""
    masks = set()
    for destination, shim in replacements.items():
        text = re.sub(r'(?m)#.*$', '', shim.read_text())
        blocks = re.findall(r'\b(?:absl_)?shim_headers\("[^"\n]+"\)\s*\{([^{}]*)\}', text, re.S)
        require(len(blocks) == len(re.findall(r'\b(?:absl_)?shim_headers\s*\(', text)),
                'unsupported Chromium shim_headers block: ' + str(shim))
        for block in blocks:
            roots = re.findall(r'\broot_path\s*=\s*"([^"\n]+)"', block)
            headers = re.findall(r'\bheaders\s*=\s*\[([^\]]*)\]', block, re.S)
            assignments = re.findall(r'\b(root_path|headers|prefix)\s*(?:\+=|=)', block)
            require(assignments.count('root_path') == 1 and assignments.count('headers') == 1 and
                    assignments.count('prefix') <= 1 and len(roots) == len(headers) == 1,
                    'non-literal or multiple Chromium shim header assignments')
            if 'prefix' in assignments:
                require(re.search(r'\bprefix\s*=\s*"[^"\n]*"', block) is not None,
                        'non-literal Chromium shim prefix')
            remainder = re.sub(r'\broot_path\s*=\s*"[^"\n]+"', '', block)
            remainder = re.sub(r'\bheaders\s*=\s*\[[^\]]*\]', '', remainder, flags=re.S)
            remainder = re.sub(r'\bprefix\s*=\s*"[^"\n]*"', '', remainder)
            require(not remainder.strip(), 'unsupported Chromium shim expression: ' + str(shim))
            names = re.findall(r'"([^"\n]+)"', headers[0])
            residue = re.sub(r'"[^"\n]+"|[,\s]', '', headers[0])
            require(names and not residue, 'unsupported Chromium shim header expression')
            prefixes = re.findall(r'\bprefix\s*=\s*"([^"\n]*)"', block)
            require(all('$' not in value and '\\' not in value
                        for value in roots + names + prefixes),
                    'interpolated or escaped Chromium shim string')
            base = destination.parent / roots[0]
            require(not base.is_absolute() and '..' not in base.parts,
                    'unsafe Chromium shim root')
            for name in names:
                path = Path(name)
                require(not path.is_absolute() and '..' not in path.parts and ';' not in name,
                        'unsafe Chromium shim header')
                masks.add(base / path)
    return masks


def abseil_masks(source, replacements):
    """Remove every bundled Abseil non-GN file from the selected view."""
    root = source / 'third_party/abseil-cpp'
    masks = shim_masks(replacements)
    for path in (root / 'absl').rglob('*'):
        require(not path.is_symlink(), 'Abseil source contains a symlink: ' + str(path))
        if path.is_file() and path.suffix not in ('.gn', '.gni'):
            masks.add(path.relative_to(root))
    return masks


def dependency_view(origin, dest, replacements, masks, *, verify=False, current=Path()):
    expected = {p.name for p in origin.iterdir() if current / p.name not in masks}
    if verify:
        require(dest.is_dir() and not dest.is_symlink(), 'dependency view component must be local')
        require({p.name for p in dest.iterdir()} == expected, 'dependency view entries changed')
    else:
        dest.mkdir()
    for item in origin.iterdir():
        rel = current / item.name
        if rel in masks:
            continue
        output = dest / item.name
        descend = any(path != rel and rel in path.parents for path in set(replacements) | masks)
        if descend:
            require(item.is_dir() and not item.is_symlink(), 'invalid dependency view parent')
            dependency_view(item, output, replacements, masks, verify=verify, current=rel)
        else:
            target = replacements.get(rel, item)
            if verify:
                require(output.is_symlink() and os.readlink(output) == str(target),
                        'dependency view link changed: ' + str(output))
            else:
                output.symlink_to(target, target_is_directory=target.is_dir())


# Script interpreters resolve symlinks (Python sys.path[0], esbuild entry
# points), so generators under a linked directory report or import paths from
# the prepared workspace instead of the view.  These third_party trees are
# mirrored as local directories of hard links (copies across devices).  The
# Chromium root outside third_party is mirrored as a whole because its build
# scripts locate the source root from their own module paths.
MATERIALIZED_THIRD_PARTY = ('blink', 'dawn', 'devtools-frontend', 'node')


def _directory_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _scan_directory(directory, omit):
    """Enumerate one real directory and retain its identity for final check."""
    before = os.lstat(directory)
    require(stat.S_ISDIR(before.st_mode),
            'mirrored view component must be a real directory: ' + str(directory))
    with os.scandir(directory) as scan:
        entries = {item.name: item for item in scan if item.name not in omit}
    return entries, _directory_identity(before)


def _require_directory_unchanged(directory, identity):
    current = os.lstat(directory)
    require(stat.S_ISDIR(current.st_mode) and _directory_identity(current) == identity,
            'mirrored view directory changed during verification: ' + str(directory))


def _same_file_bytes(left, right):
    with open(left, 'rb') as a, open(right, 'rb') as b:
        while True:
            left_chunk = a.read(1024 * 1024)
            right_chunk = b.read(1024 * 1024)
            if left_chunk != right_chunk:
                return False
            if not left_chunk:
                return True


def mirror(origin, dest, *, verify=False, omit=frozenset()):
    origin = Path(origin)
    dest = Path(dest)
    excluded = set(omit)
    source_entries, source_identity = _scan_directory(origin, excluded)
    names = set(source_entries)
    if verify:
        local_entries, local_identity = _scan_directory(dest, excluded)
        # Interpreter byte-code caches written into the local mirror are build
        # products of the view, not source entries.
        cache = local_entries.get('__pycache__')
        if cache is not None and cache.name not in names:
            cache_info = cache.stat(follow_symlinks=False)
            if stat.S_ISDIR(cache_info.st_mode):
                local_entries.pop('__pycache__')
        require(set(local_entries) == names,
                'mirrored view entries changed: ' + str(dest))
    else:
        dest.mkdir()

    for name, item in source_entries.items():
        output = dest / name
        source_info = item.stat(follow_symlinks=False)
        if stat.S_ISLNK(source_info.st_mode):
            source_link = os.readlink(item.path)
            if verify:
                output_entry = local_entries[name]
                output_info = output_entry.stat(follow_symlinks=False)
                require(stat.S_ISLNK(output_info.st_mode) and
                        os.readlink(output_entry.path) == source_link,
                        'mirrored view link changed: ' + str(output))
            else:
                output.symlink_to(source_link)
        elif stat.S_ISDIR(source_info.st_mode):
            if verify:
                output_info = local_entries[name].stat(follow_symlinks=False)
                require(stat.S_ISDIR(output_info.st_mode),
                        'mirrored view directory changed: ' + str(output))
            mirror(item.path, output, verify=verify)
        else:
            require(stat.S_ISREG(source_info.st_mode),
                    'unsupported mirrored view file type: ' + str(item.path))
            if not verify:
                try:
                    os.link(item.path, output)
                except OSError:
                    import shutil
                    shutil.copy2(item.path, output)
                continue
            output_entry = local_entries[name]
            output_info = output_entry.stat(follow_symlinks=False)
            same_inode = ((source_info.st_ino, source_info.st_dev) ==
                          (output_info.st_ino, output_info.st_dev))
            require(stat.S_ISREG(output_info.st_mode) and
                    (same_inode or
                     (source_info.st_size == output_info.st_size and
                      _same_file_bytes(item.path, output_entry.path))),
                    'mirrored view file changed: ' + str(output))

    _require_directory_unchanged(origin, source_identity)
    if verify:
        _require_directory_unchanged(dest, local_identity)


def mirrored(third_party):
    return {name for name in MATERIALIZED_THIRD_PARTY if (third_party / name).is_dir()}


def icu_replacements(source):
    require(chromium_replacements(source).get('icu') == 'third_party/icu/BUILD.gn',
            'invalid Chromium ICU replacement mapping')
    shim = source / 'build/linux/unbundle/icu.gn'
    require(shim.is_file(), 'missing Chromium ICU shim')
    return {Path('BUILD.gn'): shim}


def re2_replacements(source):
    require(chromium_replacements(source).get('re2') == 'third_party/re2/BUILD.gn',
            'invalid Chromium RE2 replacement mapping')
    shim = source / 'build/linux/unbundle/re2.gn'
    require(shim.is_file(), 'missing Chromium RE2 shim')
    return {Path('BUILD.gn'): shim}


# Electron's GN npm actions resolve these modules from electron/node_modules;
# expose only this build set from the common Ports module prefix so CI-only
# devDependencies stay out of the build and typeRoots sees only @types/node.
ELECTRON_BUILD_MODULES = ('@electron/asar', '@electron/docs-parser',
                          '@electron/typescript-definitions', '@types/node',
                          'pre-flight', 'rolldown', 'semver', 'typescript')


def electron_module_view(modules, dest, *, verify=False):
    import json
    expected, bins = {}, {}
    for name in ELECTRON_BUILD_MODULES:
        target = modules / name
        manifest = target / 'package.json'
        require(manifest.is_file() and not target.is_symlink(), 'missing common JS module: ' + name)
        data = json.loads(manifest.read_text())
        require(data.get('name') == name, 'common JS module name differs: ' + name)
        expected[name] = str(target)
        declared = data.get('bin') or {}
        if isinstance(declared, str):
            declared = {name.rsplit('/', 1)[-1]: declared}
        for command, relative in declared.items():
            require('/' not in command and command not in bins, 'invalid module command: ' + command)
            path = (target / relative).resolve(strict=True)
            require(path.is_relative_to(target), 'module command escapes its module: ' + command)
            bins[command] = str(path)
    links = {**expected, **{'.bin/' + c: t for c, t in bins.items()}}
    dirs = {str(Path(n).parent) for n in links if '/' in n}
    if not verify:
        dest.mkdir()
        for d in sorted(dirs):
            (dest / d).mkdir(parents=True, exist_ok=True)
        for name, target in links.items():
            (dest / name).symlink_to(target, target_is_directory=not name.startswith('.bin/'))
        return
    require(dest.is_dir() and not dest.is_symlink(), 'electron/node_modules must be a local view')
    found = {}
    for root, subdirs, files in os.walk(dest):
        for item in subdirs + files:
            path = Path(root) / item
            rel = str(path.relative_to(dest))
            if path.is_symlink():
                found[rel] = os.readlink(path)
                if item in subdirs:
                    subdirs.remove(item)
            else:
                require(path.is_dir() and rel in dirs, 'unexpected electron/node_modules entry: ' + rel)
    require(found == links, 'electron/node_modules view changed')


def python_edition_defaults(protobuf, protoc):
    """Render python_edition_defaults.py from the common source, as Bazel does."""
    import subprocess, tempfile
    template = protobuf / 'python/google/protobuf/internal/python_edition_defaults.py.template'
    text = template.read_text()
    require(text.count('DEFAULTS_VALUE') == 1, 'unexpected python edition defaults template')
    with tempfile.TemporaryDirectory(prefix='protobuf-edition-defaults-') as work:
        output = Path(work) / 'defaults.bin'
        subprocess.run([str(protoc), '-I' + str(protobuf / 'src'), '--edition_defaults_out=' + str(output),
                        '--edition_defaults_minimum=PROTO2', '--edition_defaults_maximum=2026',
                        str(protobuf / 'src/google/protobuf/descriptor.proto')], check=True)
        data = output.read_bytes()
    escaped = ''.join('\\%03o' % byte for byte in data)
    return text.replace('DEFAULTS_VALUE', escaped)


DESCRIPTOR_PB2 = 'descriptor_pb2.py'
PYTHON_PROTO_INPUTS = {
    DESCRIPTOR_PB2: 'google/protobuf/descriptor.proto',
    'compiler/plugin_pb2.py': 'google/protobuf/compiler/plugin.proto',
}


def python_protobuf_modules(protobuf, protoc):
    """Generate Chromium's required pyproto modules together with selected protoc."""
    import subprocess, tempfile
    source = protobuf / 'src'
    package = protobuf / 'python/google/protobuf'
    for relative in PYTHON_PROTO_INPUTS:
        require(not (package / relative).exists(),
                'common protobuf Python tree already ships generated module: ' + relative)
    with tempfile.TemporaryDirectory(prefix='protobuf-python-modules-') as work:
        subprocess.run([str(protoc), '-I' + str(source), '--python_out=' + work,
                        *(str(source / relative) for relative in PYTHON_PROTO_INPUTS.values())], check=True)
        return {relative: (Path(work) / 'google/protobuf' / relative).read_bytes()
                for relative in PYTHON_PROTO_INPUTS}


def mirror_generated_python(origin, dest, generated, *, verify=False):
    """Mirror one runtime subtree while writing or verifying generated leaves."""
    groups = {}
    files = {}
    for relative, data in generated.items():
        parts = Path(relative).parts
        if len(parts) == 1:
            files[parts[0]] = data
        else:
            groups.setdefault(parts[0], {})[Path(*parts[1:]).as_posix()] = data
    mirror(origin, dest, verify=verify, omit=set(groups) | set(files))
    for name, children in groups.items():
        mirror_generated_python(origin / name, dest / name, children, verify=verify)
    for name, data in files.items():
        output = dest / name
        if verify:
            require(output.is_file() and not output.is_symlink() and output.read_bytes() == data,
                    'generated Python module changed: ' + str(output))
        else:
            output.write_bytes(data)


def python_view(protobuf, dest, protoc, *, verify=False):
    """Mirror the common pyproto runtime and add Chromium's generated Python inputs."""
    generated = {
        'google/protobuf/' + relative: data
        for relative, data in python_protobuf_modules(protobuf, protoc).items()
    }
    generated['google/protobuf/internal/python_edition_defaults.py'] = (
        python_edition_defaults(protobuf, protoc).encode())
    mirror_generated_python(protobuf / 'python', dest, generated, verify=verify)


def create(source, protobuf, destination, *, node=None, perfetto=None, v8=None, system_abseil=False, system_icu=False, system_re2=False, node_modules=None, protobuf_protoc=None):
    source = Path(source).resolve(strict=True)
    protobuf = Path(protobuf).resolve(strict=True) if protobuf is not None else None
    v8 = Path(v8).resolve(strict=True) if v8 is not None else None
    if v8:
        require((v8 / 'BUILD.gn').is_file() and (v8 / 'include/v8-version.h').is_file(),
                'incomplete common V8 source')
    destination = Path(destination)
    require(destination.is_absolute() and not os.path.lexists(destination),
            'source view destination must be a new absolute path')
    destination = destination.resolve()
    providers = {name: Path(value).resolve(strict=True) for name, value in
                 (('electron_node', node), ('perfetto', perfetto)) if value is not None}
    for name, marker in (('electron_node', 'node.gni'), ('perfetto', 'gn/perfetto.gni')):
        if name in providers:
            require((providers[name] / marker).is_file(), 'incomplete common source: ' + name)
    for parent in (source, *([protobuf] if protobuf else []), *([v8] if v8 else []), *providers.values()):
        require(not destination.is_relative_to(parent) and not parent.is_relative_to(destination),
                'source view overlaps an input')
    third_party = source / 'third_party'
    original = third_party / 'protobuf'
    require((source / '.gn').is_file(), 'incomplete Electron source')
    if protobuf:
        require(original.is_dir() and (protobuf / 'src').is_dir() and
                (protobuf / 'third_party').is_dir(), 'incomplete common Protobuf source')
    destination.mkdir(parents=True)
    def links(origin, dest, omit):
        dest.mkdir()
        for name, item in entries(origin, omit).items():
            (dest / name).symlink_to(item, target_is_directory=item.is_dir())
    mirror(source, destination / 'src', omit={'third_party', 'out'} | ({'v8'} if v8 else set()))
    if v8:
        (destination / 'src/v8').symlink_to(v8, target_is_directory=True)
    (destination / 'src/out').mkdir()
    links(third_party, destination / 'src/third_party', ({'protobuf'} if protobuf else set()) | set(providers) | ({'abseil-cpp'} if system_abseil else set()) | ({'icu'} if system_icu else set()) | ({'re2'} if system_re2 else set()) | mirrored(third_party))
    for name in mirrored(third_party):
        mirror(third_party / name, destination / 'src/third_party' / name)
    if node_modules is not None:
        # WebUI scripts import third_party/node/node_modules statically; bind
        # it to the selected common Ports module prefix.
        modules = Path(node_modules).resolve(strict=True)
        require((third_party / 'node').is_dir() and not (third_party / 'node/node_modules').exists(),
                'Chromium third_party/node must not carry node_modules')
        node_view = destination / 'src/third_party/node'
        require(node_view.is_dir() and not node_view.is_symlink(), 'third_party/node must be mirrored')
        (node_view / 'node_modules').symlink_to(modules, target_is_directory=True)
        electron = destination / 'src/electron'
        require(electron.is_dir() and not electron.is_symlink() and
                not os.path.lexists(source / 'electron/node_modules'),
                'Electron source must be mirrored without node_modules')
        electron_module_view(modules, electron / 'node_modules')
    if system_abseil:
        replacements = abseil_replacements(source)
        dependency_view(third_party / 'abseil-cpp', destination / 'src/third_party/abseil-cpp',
                        replacements, abseil_masks(source, replacements))
    if system_icu:
        replacements = icu_replacements(source)
        dependency_view(third_party / 'icu', destination / 'src/third_party/icu',
                        replacements, shim_masks(replacements))
    if system_re2:
        replacements = re2_replacements(source)
        dependency_view(third_party / 're2', destination / 'src/third_party/re2',
                        replacements, shim_masks(replacements))
    for name, path in providers.items():
        (destination / 'src/third_party' / name).symlink_to(path, target_is_directory=True)
    if protobuf:
        common = ('src', 'third_party') + (('python',) if protobuf_protoc else ())
        links(original, destination / 'src/third_party/protobuf', set(common))
        for name in ('src', 'third_party'):
            (destination / 'src/third_party/protobuf' / name).symlink_to(protobuf / name,
                                                                         target_is_directory=True)
        if protobuf_protoc:
            # The pyproto runtime must match the selected protoc gencode.
            python_view(protobuf, destination / 'src/third_party/protobuf/python', protobuf_protoc)
    return destination / 'src'


def verify(source, protobuf, destination, *, node=None, perfetto=None, v8=None, system_abseil=False, system_icu=False, system_re2=False, node_modules=None, protobuf_protoc=None):
    source = Path(source).resolve(strict=True)
    protobuf = Path(protobuf).resolve(strict=True) if protobuf is not None else None
    providers = {name: Path(value).resolve(strict=True) for name, value in
                 (('electron_node', node), ('perfetto', perfetto)) if value is not None}
    v8 = Path(v8).resolve(strict=True) if v8 is not None else None
    destination = Path(destination)
    require(destination.is_dir() and not destination.is_symlink(), 'source view must be a local directory')
    destination = destination.resolve(strict=True)
    def check(origin, dest, omit, extra):
        require(dest.is_dir() and not dest.is_symlink(), 'source view component must be a local directory: ' + str(dest))
        expected = entries(origin, omit)
        require(set(item.name for item in dest.iterdir()) == set(expected) | set(extra),
                'source view entries changed: ' + str(dest))
        for name, item in expected.items():
            link = dest / name
            require(link.is_symlink() and os.readlink(link) == str(item),
                    'source view link changed: ' + str(link))
    root = destination / 'src'
    root_special = {'third_party', 'out'} | ({'v8'} if v8 else set())
    mirror(source, root, verify=True, omit=root_special | ({'electron'} if node_modules is not None else set()))
    if node_modules is not None:
        mirror(source / 'electron', root / 'electron', verify=True, omit={'node_modules'})
    require({item.name for item in root.iterdir()} >= root_special, 'source view root entries changed')
    if v8:
        require((root / 'v8').is_symlink() and os.readlink(root / 'v8') == str(v8),
                'common V8 source link changed')
    require((root / 'out').is_dir() and not (root / 'out').is_symlink(),
            'source view out must be local')
    replaced = ({'protobuf'} if protobuf else set()) | set(providers) | ({'abseil-cpp'} if system_abseil else set()) | ({'icu'} if system_icu else set()) | ({'re2'} if system_re2 else set()) | mirrored(source / 'third_party')
    check(source / 'third_party', root / 'third_party', replaced, replaced)
    for name in mirrored(source / 'third_party'):
        mirror(source / 'third_party' / name, root / 'third_party' / name, verify=True,
               omit={'node_modules'} if name == 'node' and node_modules is not None else frozenset())
    if node_modules is not None:
        link = root / 'third_party/node/node_modules'
        require(link.is_symlink() and os.readlink(link) == str(Path(node_modules).resolve(strict=True)),
                'common node_modules link changed')
        electron_module_view(Path(node_modules).resolve(strict=True), root / 'electron/node_modules', verify=True)
    if system_abseil:
        replacements = abseil_replacements(source)
        dependency_view(source / 'third_party/abseil-cpp', root / 'third_party/abseil-cpp',
                        replacements, abseil_masks(source, replacements), verify=True)
    if system_icu:
        replacements = icu_replacements(source)
        dependency_view(source / 'third_party/icu', root / 'third_party/icu',
                        replacements, shim_masks(replacements), verify=True)
    if system_re2:
        replacements = re2_replacements(source)
        dependency_view(source / 'third_party/re2', root / 'third_party/re2',
                        replacements, shim_masks(replacements), verify=True)
    for name, path in providers.items():
        link = root / 'third_party' / name
        require(link.is_symlink() and os.readlink(link) == str(path),
                'common source link changed: ' + str(link))
    if protobuf:
        path = root / 'third_party/protobuf'
        common = {'src', 'third_party'} | ({'python'} if protobuf_protoc else set())
        check(source / 'third_party/protobuf', path, common, common)
        if protobuf_protoc:
            python_view(protobuf, path / 'python', protobuf_protoc, verify=True)
        for name in ('src', 'third_party'):
            link = path / name
            require(link.is_symlink() and os.readlink(link) == str(protobuf / name),
                    'common Protobuf source link changed: ' + str(link))
    return root


def refresh(source, protobuf, destination, **sources):
    """Recompose generated inputs while keeping the sibling Ninja output intact.

    The caller must hold the workspace/output locks and verify prepared sources
    and compiler/provider identity before requesting this operation.
    """
    import tempfile

    destination = Path(destination)
    require(destination.is_absolute(), 'source view destination must be absolute')
    resolved = destination.resolve()
    for value in (source, protobuf, *(sources.get(name) for name in
                  ('node', 'perfetto', 'v8', 'node_modules'))):
        if value is not None:
            origin = Path(value).resolve(strict=True)
            require(not resolved.is_relative_to(origin) and
                    not origin.is_relative_to(resolved), 'source view overlaps an input')
    existing = os.path.lexists(destination)
    if existing:
        require(destination.is_dir() and not destination.is_symlink(),
                'source view must be a local directory')
        require({p.name for p in destination.iterdir()} == {'src'},
                'unexpected entries outside generated source view')
        require((destination / 'src').is_dir() and not (destination / 'src').is_symlink(),
                'source view src must be a local directory')
        local_out = destination / 'src/out'
        require(local_out.is_dir() and not local_out.is_symlink() and
                not any(local_out.iterdir()),
                'source view contains build outputs; use the sibling work/out directory')
    with tempfile.TemporaryDirectory(prefix='.source-view-refresh-',
                                     dir=destination.parent) as temporary:
        scratch = Path(temporary)
        candidate = scratch / 'candidate'
        create(source, protobuf, candidate, **sources)
        verify(source, protobuf, candidate, **sources)
        previous = scratch / 'previous'
        if existing:
            destination.rename(previous)
        try:
            candidate.rename(destination)
        except BaseException:
            if existing:
                previous.rename(destination)
            raise
    return destination / 'src'
