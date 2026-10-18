# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted provenance for fresh libstdc++ rebuilds.
import hashlib
from pathlib import Path
import re
from emberbsd_sdk import inventory as sdk_inventory, jsonio
from runtime import Invalid, VERSION, SOURCE_SHA256, Stage, require, hash_file, text, hash_claims

PATCH = 'patch-libstdc++-v3_config_locale_generic_c__locale'
PATCH_SHA256 = '35a5220459db81dd19376dec091837fca12c24e3e2c1a8518af0536f3ed20fa2'
PARENT_FILES = ('inputs.txt', 'stage.sha256', 'stage.symlinks', 'build-success')
CONFIG_FILES = ('commands.json', 'configuration/config.status', 'configuration/config.h')
CRT_FILES = 'crtbegin.o crtbeginS.o crtbeginT.o crtend.o crtendS.o crtfastmath.o libgcc.a libgcc_eh.a libgcov.a'.split()


def inventory(root):
    result = {}
    for name, record in sdk_inventory.snapshot_tree(root).items():
        require(re.fullmatch(r'[A-Za-z0-9_+./-]+', name) and '..' not in name.split('/'), 'Unsafe component path')
        if record['kind'] == 'file':
            result[name] = {'sha256': record['sha256'], 'mode': record['mode']}
        elif record['kind'] == 'link':
            result[name] = {'link': record['target']}
    return result


def check_delta(old_recipe, new_recipe):
    old_recipe, new_recipe = Path(old_recipe), Path(new_recipe)
    def select(recipe):
        names = ['distinfo', 'Makefile', 'Makefile.common'] + ['patches/' + path.name for path in (recipe / 'patches').iterdir()]
        return {name: hash_file(recipe / name) for name in names}
    old, current = select(old_recipe), select(new_recipe)
    require(sorted(current) == sorted(list(old) + ['patches/' + PATCH]), 'Unexpected recipe file selection')
    for name, digest in old.items():
        if name not in ('Makefile', 'distinfo'):
            require(current[name] == digest, 'Changed inherited recipe input: ' + name)
    patch = new_recipe / 'patches' / PATCH
    require(hash_file(patch) == PATCH_SHA256, 'Unsupported locale source patch')
    make = text(old_recipe / 'Makefile')
    require(len(re.findall(r'^PKGREVISION=\s*1$', make, re.M)) == 1, 'Unexpected old compiler revision')
    require(text(new_recipe / 'Makefile') == re.sub(r'^(PKGREVISION=\s*)1$', r'\g<1>2', make, count=1, flags=re.M), 'Unexpected compiler recipe change')
    normalized = b''.join(line for line in patch.read_bytes().splitlines(keepends=True) if b'$NetBSD' not in line)
    line = 'SHA1 (' + PATCH + ') = ' + hashlib.sha1(normalized).hexdigest() + '\n'
    info = text(new_recipe / 'distinfo')
    require(info.splitlines(keepends=True).count(line) == 1 and info.replace(line, '', 1) == text(old_recipe / 'distinfo'), 'Unexpected patch manifest change')


def inherited_paths(parent):
    paths = ['usr/pkg/' + path for path in parent['files'] if not Path(path).name.startswith('libstdc++')]
    return paths + ['usr/pkg/gcc16/lib/gcc/' + parent['metadata']['GCC_RUNTIME_TRIPLET'] + '/' + VERSION + '/' + name for name in CRT_FILES]


def _verify(work, pkgsrc, archive, current, expected_source=SOURCE_SHA256):
    work, pkgsrc = Path(work), Path(pkgsrc)
    file = work / 'inheritance.json'
    receipt = jsonio.read_json(file)
    require(type(receipt['format']) is int and receipt['format'] == 1, 'Unknown inheritance format')
    require(hash_claims(text(work / 'inputs.txt'), file) == [hash_file(file)], 'Inheritance receipt not pinned by inputs')
    for name in PARENT_FILES:
        require(hash_file(work / 'parent' / name) == receipt['parent_receipts'][name], 'Changed parent receipt')
    parent = Stage(work / 'parent', work / 'parent-recipe', archive, expected_source=expected_source, receipt_paths=receipt['parent_paths'], allow_rebuild=False, historical=True).verify()
    for key in ('GCC_RUNTIME_TARGET', 'GCC_RUNTIME_TRIPLET', 'GCC_RUNTIME_LIBRARIES', 'EMBERBSD_SEED_SOURCE'):
        require(parent['metadata'][key] == current['metadata'][key], 'Parent runtime identity changed')
    check_delta(work / 'parent-recipe/lang/gcc16', pkgsrc / 'lang/gcc16')
    old = inventory(work / 'parent/stage')
    inherited = {path: old[path] for path in inherited_paths(parent)}
    require(receipt['inherited'] == inherited, 'Incorrect inherited component selection')
    fresh = receipt['rebuilt']
    require('usr/pkg/gcc16/include/c++/vector' in fresh and 'usr/pkg/gcc16/include/c++/' + current['metadata']['GCC_RUNTIME_TRIPLET'] + '/bits/c++locale.h' in fresh, 'Missing fresh libstdc++ headers')
    require(not fresh.keys() & inherited.keys(), 'Overlapping component ownership')
    require(all(path.startswith('usr/pkg/gcc16/') and not re.search(r'/lib/(?:gcc/|libgcc|libgomp|libatomic)', path) for path in fresh), 'Foreign rebuilt component')
    runtime = {path: item for path, item in fresh.items() if re.search(r'/lib/libstdc\+\+\.so\.7(?:\.[0-9]+)*$', path) and 'sha256' in item}
    require(len(runtime) == 1 and all(path in old and old[path].get('sha256') != item['sha256'] for path, item in runtime.items()), 'Missing or unchanged rebuilt libstdc++ DSO')
    require(inventory(work / 'stage') == dict(fresh, **inherited), 'Incorrect assembled component bytes')
    for name in ('configure.log', 'runtime-build.log', 'runtime-install.log'):
        require(hash_file(work / name) == receipt['build_logs'][name], 'Missing or changed genuine build log')
    for name in CONFIG_FILES:
        path = work / name
        require(hash_file(path) == receipt['configuration'][name] and hash_claims(text(work / 'inputs.txt'), path) == [hash_file(path)], 'Changed build configuration')
    return {'GCC_RUNTIME_BUILD_MODE': 'standalone-libstdcxx', 'GCC_RUNTIME_INHERITANCE_SHA256': hash_file(file), 'GCC_RUNTIME_PARENT_INPUTS_SHA256': receipt['parent_receipts']['inputs.txt'], 'GCC_RUNTIME_PARENT_STAGE_SHA256': receipt['parent_receipts']['stage.sha256']}


def verify(work, pkgsrc, archive, current, expected_source=SOURCE_SHA256):
    try:
        return _verify(work, pkgsrc, archive, current, expected_source)
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise Invalid("Invalid inheritance receipt: " + str(error)) from error
