#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check paired Rollup inputs and write the standard Cargo native-library override."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import tomllib


def prepare(source, version, rust_target, napi_base, mimalloc_libdir, output):
    if not re.fullmatch(r'[A-Za-z0-9_]+(?:-[A-Za-z0-9_.]+){2,}',rust_target):
        raise ValueError('select an explicit supported EMBER_CARGO_TARGET')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)+',napi_base):
        raise ValueError('select the matching upstream ROLLUP_NAPI_BASE')
    for name in ('package.json','npm/package/package.json'):
        manifest=json.loads((source/name).read_text())
        if manifest['name']!='rollup' or manifest['version']!=version:
            raise ValueError('Rollup Git and npm source versions must match the recipe')
    if any((source/'npm/package').rglob('*.node')):
        raise ValueError('npm input must not supply a prebuilt native binding')
    manifest=tomllib.loads((source/'rust/bindings_napi/Cargo.toml').read_text())
    dependencies=[table['dependencies']['mimalloc-safe'] for table in manifest['target'].values()
                  if 'mimalloc-safe' in table.get('dependencies',{})]
    if not dependencies or not all('v3' in dependency.get('features',[]) for dependency in dependencies):
        raise ValueError('Rollup must explicitly select the shared mimalloc v3 ABI')
    helper = Path(__file__).resolve().parents[2] / 'mimalloc/files/cargo-overrides.py'
    spec = importlib.util.spec_from_file_location('mimalloc_cargo_overrides', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.write_override(mimalloc_libdir, output)



def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','mimalloc-libdir','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    for name in ('version','rust-target','napi-base'):
        parser.add_argument('--'+name,required=True)
    try:
        prepare(**vars(parser.parse_args()))
    except (ValueError,OSError,KeyError) as error:
        parser.exit(1,f'Rollup source inputs: {error}\n')


if __name__=='__main__':
    main()
