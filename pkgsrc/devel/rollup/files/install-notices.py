#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Preserve the pinned Rust crate notices and their original package metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tomllib

STANDARD_LICENSES=('mit','apache-2.0','boost-license','unicode-v3','zlib','modified-bsd','isc','0-clause-bsd')


def install(lock, vendor, output, license_root, extra_notices=None):
    entries=[]
    copies=[]
    for package in tomllib.loads(lock.read_text())['package']:
        if 'source' not in package:
            continue
        if package['source']!='registry+https://github.com/rust-lang/crates.io-index':
            raise ValueError('an undeclared non-registry crate needs an explicit source/notice contract')
        key=package['name']+'-'+package['version']
        if not re.fullmatch(r'[A-Za-z0-9_.+-]+',key):
            raise ValueError('invalid Cargo package directory')
        source=vendor/key
        metadata=tomllib.loads((source/'Cargo.toml').read_text())['package']
        checksum=json.loads((source/'.cargo-checksum.json').read_text())['package']
        if metadata['name']!=package['name'] or metadata['version']!=package['version'] or checksum!=package['checksum']:
            raise ValueError('prepared crate identity/checksum differs from Cargo.lock: '+key)
        notices=sorted(path for path in source.rglob('*') if path.is_file() and
                       path.name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE','AUTHORS')))
        original_notices=[str(path.relative_to(source)) for path in notices]
        selected=[source/'Cargo.toml',*notices]
        if (source/'.cargo_vcs_info.json').is_file():
            selected.append(source/'.cargo_vcs_info.json')
        # Some upstream crates omit standalone notice files. Retain their exact
        # SPDX/authors/repository metadata and any supplied README as evidence;
        # do not invent copyright years or replace missing VCS pins with HEAD.
        if not notices and isinstance(metadata.get('readme'),str):
            readme=source/metadata['readme']
            if readme.is_file():
                selected.append(readme)
        record={name:metadata[name] for name in ('name','version','license','license-file','authors','repository') if name in metadata}
        record.update(archive_sha256=checksum,original_notices=original_notices,restored_notices=[],files=[])
        for path in selected:
            if not path.resolve().is_relative_to(source.resolve()):
                raise ValueError('crate notice leaves its source directory: '+str(path))
            relative=path.relative_to(source)
            target=Path('crates')/key/relative
            data=path.read_bytes()
            copies.append((target,data))
            record['files'].append({'path':str(target),'sha256':hashlib.sha256(data).hexdigest()})
        entries.append(record)
    if extra_notices is not None:
        by_name={entry['name']+'-'+entry['version']:entry for entry in entries}
        for origin in json.loads(extra_notices.read_text()):
            key=origin['crate'];entry=by_name[key]
            vcs=json.loads((vendor/key/'.cargo_vcs_info.json').read_text())
            expected_repository='https://github.com/'+origin['repository']
            if vcs['git']['sha1']!=origin['commit'] or entry.get('repository','').removesuffix('.git')!=expected_repository:
                raise ValueError('restored notice does not match the crate VCS identity: '+key)
            name=origin['file']
            if not re.fullmatch(r'[A-Za-z0-9_-]+[.]LICENSE',name):
                raise ValueError('invalid restored notice filename')
            data=(extra_notices.parent/name).read_bytes()
            blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if blob!=origin['git_blob']:
                raise ValueError('restored notice differs from the pinned upstream blob: '+name)
            target=Path('crates')/key/('UPSTREAM-'+name)
            copies.append((target,data))
            entry['restored_notices'].append(dict(origin))
            entry['files'].append({'path':str(target),'sha256':hashlib.sha256(data).hexdigest()})
    for name in STANDARD_LICENSES:
        copies.append((Path('standard-license-texts')/name,(license_root/name).read_bytes()))
    for relative,data in copies:
        target=output/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    summary={'format':1,'scope':'original crate notices and metadata; standard texts do not invent missing upstream copyright notices','crates':entries}
    (output/'index.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    return len(entries),sum(len(entry['original_notices']) for entry in entries)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('lock','vendor','output','license-root'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--extra-notices',type=Path)
    try:
        count,notices=install(**vars(parser.parse_args()))
    except (ValueError,OSError,KeyError) as error:
        parser.exit(1,f'Rollup crate notices: {error}\n')
    print(f'Preserved {notices} original notice files and metadata for {count} pinned crates.')


if __name__=='__main__':
    main()
