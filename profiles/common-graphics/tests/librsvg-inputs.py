#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check librsvg's pinned Cargo closure against the package recipe."""
import re
import sys
import tomllib
from pathlib import Path


def fail(message):
    raise SystemExit(message)


if len(sys.argv) != 4:
    fail('Usage: librsvg-inputs.py ORIGINAL_SOURCE PATCHED_SOURCE VENDOR')

original, patched, vendor = (Path(arg).resolve(strict=True) for arg in sys.argv[1:])
recipe = Path(__file__).resolve().parents[3] / 'pkgsrc/graphics/librsvg'
original_lock = (original / 'Cargo.lock').read_bytes()
lock_text = (patched / 'Cargo.lock').read_text()
if original_lock == lock_text.encode():
    fail('expected the recipe-patched Cargo.lock')
lock = tomllib.loads(lock_text)
packages = lock['package']
registry_packages = [p for p in packages if p.get('source') ==
                     'registry+https://github.com/rust-lang/crates.io-index']
expected = sorted(f"{p['name']}-{p['version']}" for p in registry_packages)
declared = sorted(re.findall(r'^CARGO_CRATE_DEPENDS\+=\s+(\S+)$',
                             (recipe / 'cargo-depends.mk').read_text(), re.M))
if declared != expected:
    fail('Cargo recipe differs from the patched lock closure')

versions = {}
for item in registry_packages:
    versions.setdefault(item['name'], set()).add(item['version'])
required = {
    'av-data': '0.4.4',
    'cssparser': '0.38.0',
    'cssparser-color': '0.6.0',
    'cssparser-macros': '0.7.1',
    'dav1d': '0.11.1',
    'image': '0.25.10',
    'markup5ever': '0.40.0',
    'num-derive': '0.5.1',
    'phf': '0.14.0',
    'phf_codegen': '0.14.0',
    'phf_generator': '0.14.0',
    'phf_macros': '0.14.0',
    'phf_shared': '0.14.0',
    'selectors': '0.42.0',
    'servo_arc': '0.6.0',
    'string_cache': '0.11.0',
    'string_cache_codegen': '0.11.2',
    'web_atoms': '0.3.0',
    'xml5ever': '0.40.0',
}
for name, version in required.items():
    if versions.get(name) != {version}:
        fail(f'patched lock must select only {name}-{version}')

manifest = tomllib.loads((patched / 'Cargo.toml').read_text())
dependencies = manifest.get('workspace', {}).get('dependencies', {})
dependencies.update(manifest.get('dependencies', {}))
for name in ('cssparser', 'cssparser-color', 'markup5ever', 'selectors',
             'string_cache', 'xml5ever'):
    constraint = dependencies.get(name)
    if not isinstance(constraint, str) or constraint != required[name]:
        fail(f'Cargo.toml must require {name} {required[name]}')

def package(name):
    matches = [p for p in packages if p['name'] == name]
    if len(matches) != 1:
        fail(f'expected exactly one locked {name} package')
    return matches[0]


def has_dependency(owner, dependency):
    return any((dep.split(' ', 1)[0] == dependency)
               for dep in package(owner).get('dependencies', []))


for owner, dependency in (('image', 'dav1d'), ('dav1d', 'av-data'),
                          ('av-data', 'num-derive'), ('num-derive', 'syn')):
    if not has_dependency(owner, dependency):
        fail(f'AVIF dependency chain is missing {owner} -> {dependency}')
if 'syn 3.0.9' not in package('num-derive').get('dependencies', []):
    fail('num-derive must resolve through Syn 3')
if 'syn 3.0.9' not in package('cssparser-macros').get('dependencies', []):
    fail('cssparser-macros must resolve through Syn 3')
if 'hashbrown 0.17.1' not in package('selectors').get('dependencies', []):
    fail('selectors must use shared hashbrown 0.17.1')
selectors_manifest = tomllib.loads(
    (vendor / 'selectors-0.42.0/Cargo.toml').read_text())
hashbrown_config = selectors_manifest.get('dependencies', {}).get('hashbrown', {})
if (hashbrown_config.get('default-features') is not False or
        'inline-more' not in hashbrown_config.get('features', [])):
    fail('selectors must use shared hashbrown without unused default features')

av_data_bytes = (vendor / 'av-data-0.4.4/Cargo.toml').read_bytes()
av_data_manifest = tomllib.loads(av_data_bytes.decode())
av_data_dep = av_data_manifest.get('dependencies', {}).get('num-derive', {})
if (av_data_manifest['package']['name'] != 'av-data' or
        av_data_manifest['package']['version'] != '0.4.4' or
        av_data_dep.get('version') != '0.5'):
    fail('shared av-data patch must select num-derive 0.5')


print(f'PASS: {len(expected)} Cargo crate pins match; AVIF path uses num-derive 0.5.1/Syn 3')
