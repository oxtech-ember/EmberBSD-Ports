#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Refuse prepared sources made from a recipe other than this Ports checkout's.

A prepared tree carries the receipt its owner wrote when it prepared the tree.
The receipt names the effective pkgsrc recipe (after all Ports overlays) and
the owner script.  This check recomputes both for the current checkout from
Git object ids and small recipe files only: it neither exports pkgsrc nor
reads or hashes the prepared tree, so it costs seconds for every source.

A tree prepared from a different recipe or by a different owner script is
stale: prepare it again through its owner.
"""

import argparse
import functools
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[1]
RECEIPT = 'emberbsd-prepared-source.json'

# SDK source name -> (owner script, package).
OWNERS = {
    'libarchive': ('scripts/libarchive-source.py', 'archivers/libarchive'),
    'libevent': ('scripts/source-inputs/libevent/source.py', 'devel/libevent'),
    'openssl': ('scripts/source-inputs/openssl/source.py', 'security/openssl'),
    'libfido2': ('scripts/source-inputs/libfido2/source.py', 'security/libfido2'),
    'libfetch': ('scripts/source-inputs/libfetch/source.py', 'net/libfetch'),
    'openldap': ('scripts/source-inputs/openldap/source.py', 'databases/openldap'),
    'unbound': ('scripts/source-inputs/unbound/source.py', 'net/unbound'),
    'openssh': ('scripts/source-inputs/openssh/source.py', 'security/openssh'),
    'wpa': ('scripts/source-inputs/wpa/source.py', 'net/wpa_supplicant'),
    'libcbor': ('scripts/source-inputs/libcbor/source.py', 'devel/libcbor'),
    'byacc': ('scripts/source-inputs/byacc/source.py', 'devel/byacc'),
    'texinfo': ('scripts/source-inputs/texinfo/source.py', 'devel/gtexinfo'),
    'rcs': ('scripts/source-inputs/rcs/source.py', 'devel/rcs'),
    'diffutils': ('scripts/source-inputs/diffutils/source.py', 'devel/diffutils'),
    'grep': ('scripts/source-inputs/grep/source.py', 'textproc/grep'),
    'ekermit': ('scripts/source-inputs/ekermit/source.py', 'comms/ekermit'),
    'nvi': ('scripts/source-inputs/nvi/source.py', 'editors/nvi'),
    'top': ('scripts/source-inputs/top/source.py', 'sysutils/top'),
    'iscsi': ('scripts/source-inputs/iscsi/source.py', 'devel/netbsd-iscsi-lib'),
    'ntp': ('scripts/source-inputs/ntp/source.py', 'net/ntp4'),
    'libopts': ('scripts/source-inputs/autogen/source.py', 'devel/autogen'),
    'libpcap': ('scripts/source-inputs/libpcap/source.py', 'net/libpcap'),
    'tcpdump': ('scripts/source-inputs/tcpdump/source.py', 'net/tcpdump'),
    'tcp-wrappers': ('scripts/source-inputs/tcp_wrappers/source.py', 'security/tcp_wrappers'),
    'gettext': ('scripts/source-inputs/gettext/source.py', 'devel/gettext'),
    'libxml2': ('scripts/source-inputs/libxml2/source.py', 'textproc/libxml2'),
    'ppp': ('scripts/source-inputs/ppp/source.py', 'net/pppd'),
    'tdb': ('scripts/source-inputs/tdb/source.py', 'databases/tdb'),
    'x11': ('scripts/source-inputs/xsrc/source.py', 'netbsd/xsrc'),
}


class Stale(Exception):
    pass


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.cache
def selector():
    """One effective-package selector for every source of this process.

    Reading the export configuration walks every Ports overlay, so it is read
    once here instead of once per package."""
    module = load(PORTS / 'scripts/pkgsrc-source-identity.py', 'pkgsrc_source_identity')
    exporter = module._exporter(PORTS)
    configuration = functools.cache(exporter.configuration)
    exporter.configuration = lambda root, **kwargs: configuration(Path(root).resolve(strict=True), **kwargs)
    families = functools.cache(exporter.version_families)
    exporter.version_families = lambda root: families(Path(root).resolve(strict=True))
    module._exporter = lambda root: exporter
    return module


def owner_module(name, path):
    """An owner script, sharing this process's selector."""
    module = load(path, 'owner_' + re.sub(r'\W', '_', name))
    if hasattr(module, 'identity_module'):
        module.identity_module = selector
    return module


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def blob_id(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def recipe_files(selector, package, git, patch):
    """The effective recipe files of one package, rebuilt from their sources.

    Every file before infrastructure patches is checked against the Git blob
    id that the effective package identity names, so the bytes are exactly
    those that identity describes.  Infrastructure patches which name only
    recipe files of this package (not its distinfo, patches or exported
    files) are then applied as the export applies them."""
    inputs = selector.git_package_inputs(PORTS, package, git)
    exporter = selector._exporter(PORTS)
    recipes, patches, files, _ = exporter.configuration(PORTS)
    overlay = dict(recipes).get(package)
    env = selector._git_environment()
    if overlay is not None:
        base = {relative: Path(overlay, relative).resolve(strict=True).read_bytes()
                for relative in inputs['tree'] if Path(overlay, relative).is_file()}
    else:
        upstream = PORTS / 'upstream/pkgsrc'
        base = {relative: subprocess.run([str(git), '-C', str(upstream), 'cat-file', 'blob', oid],
                                         stdout=subprocess.PIPE, check=True, env=env).stdout
                for relative, (_, oid) in
                selector._tree_rows(git, upstream, inputs['upstream'], package).items()}
    contents = dict(base)
    appended, replaced = [], set()
    for method, source, recipe, name in patches:
        if method == 'recipe-patch' and recipe == package:
            contents['patches/' + name] = Path(source).read_bytes()
            appended.append(f'SHA1 ({name}) = {exporter.patch_sha1(source)}\n')
            replaced.update(('patches/' + name, 'distinfo'))
    if appended:
        contents['distinfo'] += ''.join(appended).encode('utf-8')
    for source, destination in files:
        if destination.startswith(package + '/') and destination[len(package) + 1:] in inputs['tree']:
            contents[destination[len(package) + 1:]] = Path(source).read_bytes()
            replaced.add(destination[len(package) + 1:])
    for relative, (_, oid) in inputs['tree'].items():
        if relative not in contents or blob_id(contents[relative]) != oid:
            raise ValueError('cannot rebuild effective recipe file ' + package + '/' + relative)
    infrastructure = [Path(PORTS, relative) for _, relative, _ in inputs['infrastructure_patches']]
    if infrastructure:
        for source in infrastructure:
            targets = selector._patch_targets(source)
            if (targets is None or source.read_bytes().startswith(b'diff --git') or
                    any(not target.startswith(package + '/') or
                        target[len(package) + 1:] in replaced or
                        target[len(package) + 1:].startswith('patches/') or
                        target[len(package) + 1:] == 'distinfo' for target in targets)):
                raise Stale(source.name + ' changes more than its recipe files; verify it through its owner')
        if not patch or not os.path.isabs(patch):
            raise Stale('its recipe has infrastructure patches; select --patch')
        with tempfile.TemporaryDirectory(prefix='.recipe-current-') as temporary:
            root = Path(temporary)
            for relative, data in contents.items():
                target = root / package / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            for source in infrastructure:
                subprocess.run([patch, '-f', '-E', '-d', str(root), '-p1', '-F', '0', '-V', 'none',
                                '--no-backup-if-mismatch'], input=source.read_bytes(),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            contents = {relative: (root / package / relative).read_bytes()
                        for relative in contents if (root / package / relative).is_file()}
    return contents


def current(name, identity, git, sdk, patch=None):
    """Raise Stale unless `identity` names the current recipe; return notes.

    The owner script a receipt names is provenance: a different owner digest
    is reported, not refused, because an owner change need not change the
    tree it prepares."""
    script, package = OWNERS[name]
    owner_path = PORTS / script
    owner_sha256 = (owner_module(name, owner_path).owner_digest() if name == 'openldap'
                    else sha256(owner_path.read_bytes()))
    selector_module = selector()
    if isinstance(identity, dict) and set(identity) == {'effective', 'owner_sha256'}:
        if name == 'libarchive':
            now = selector_module.git_package_identity(PORTS, package, git)
        else:
            now = owner_module(name, owner_path).git_effective_identity(git)
        if identity['effective'].get('api') != selector_module.GIT_PACKAGE_API:
            raise Stale('its receipt does not name Git recipe objects; prepare it again')
        if not selector_module.equivalent_effective_package(identity['effective'], now):
            raise Stale('it was prepared from another ' + package + ' recipe')
        return [] if identity['owner_sha256'] == owner_sha256 else ['prepared by another ' + script]
    if name == 'x11':
        owner = owner_module(name, owner_path)
        owner.load_sdk(['--sdk-source', sdk])
        now = owner.source_identity()
        if {k: v for k, v in identity.items() if k != 'owner_sha256'} != {k: v for k, v in now.items() if k != 'owner_sha256'}:
            raise Stale('it was prepared from another xsrc archive or patch set')
        return [] if identity.get('owner_sha256') == now['owner_sha256'] else ['prepared by another ' + script]
    if name == 'libopts' and isinstance(identity, dict) and {'recipe', 'generation_recipe'} <= set(identity):
        contents = recipe_files(selector_module, package, git, patch)
        recipe = {package + '/distinfo': sha256(contents['distinfo'])}
        for relative in sorted(contents):
            if re.fullmatch(r'patches/patch-[^/]+', relative):
                recipe[package + '/' + relative] = sha256(contents[relative])
        generation = load(owner_path.with_name('recipe.py'), 'autogen_recipe').generation_recipe
        with tempfile.TemporaryDirectory(prefix='.libopts-recipe-') as temporary:
            for relative in ('Makefile', 'Makefile.common', 'options.mk'):
                if relative in contents:
                    Path(temporary, relative).write_bytes(contents[relative])
            generated = generation(temporary)
        if identity['recipe'] != recipe or identity['generation_recipe'] != generated:
            raise Stale('it was prepared from another ' + package + ' recipe')
        return []
    raise Stale('its receipt does not name its recipe; prepare it again')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True)
    parser.add_argument('--git', required=True, help='absolute Git inspector')
    parser.add_argument('--patch', help='absolute patch tool, for recipes with infrastructure patches')
    parser.add_argument('--source', action='append', default=[], metavar='NAME=PATH')
    args = parser.parse_args()
    if not os.path.isabs(args.git) or not os.path.isabs(args.sdk_source):
        parser.error('select an absolute Git and SDK source')
    stale, notes = [], []
    for item in args.source:
        name, sep, path = item.partition('=')
        if not sep or name not in OWNERS or not os.path.isabs(path):
            parser.error('use --source NAME=ABSOLUTE-PATH with a known source name')
        with open(os.path.join(path, RECEIPT), 'rb') as handle:
            record = json.loads(handle.read())
        if not isinstance(record, dict) or record.get('package') != OWNERS[name][1]:
            stale.append(f'{name}: {path} is not a prepared {OWNERS[name][1]} source')
            continue
        try:
            notes += [f'{name}: {path}: {note}' for note in
                      current(name, record.get('identity'), args.git, args.sdk_source, args.patch)]
        except Stale as exc:
            stale.append(f'{name}: {path} is stale: {exc}')
    for note in notes:
        sys.stderr.write('note: ' + note + '\n')
    if stale:
        sys.stderr.write('prepared sources do not match this Ports checkout:\n' +
                         ''.join('  ' + line + '\n' for line in stale))
        return 1
    sys.stdout.write(json.dumps({'current': sorted(item.partition('=')[0] for item in args.source)}) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
