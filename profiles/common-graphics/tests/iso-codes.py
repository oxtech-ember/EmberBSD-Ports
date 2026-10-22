#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual iso-codes installed data contracts.
"""Check current ISO data, legacy XML, translations and obsolete-name aliases."""
import argparse
import gettext
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


DOMAINS = ('15924', '3166-1', '3166-2', '3166-3', '4217', '639-2', '639-3', '639-5')
ALIASES = {'3166-1': '3166', '3166-2': '3166_2', '639-2': '639',
           '639-3': '639_3', '639-5': '639_5'}


def require(value, message):
    if not value:
        raise ValueError(message)


def check(source, prefix, logical_prefix, producers):
    inputs, catalogs, aliases = {}, 0, 0
    for domain in DOMAINS:
        for name in ('iso_' + domain + '.json', 'schema-' + domain + '.json'):
            original, installed = source / 'data' / name, prefix / 'share/iso-codes/json' / name
            data = original.read_bytes()
            inputs[str(original)] = hashlib.sha256(data).hexdigest()
            require(data == installed.read_bytes(), 'Installed JSON differs from its source: ' + name)
            parsed = json.loads(data)
            require(isinstance(parsed, dict) and parsed, 'Invalid JSON object: ' + name)
            if name.startswith('iso_'):
                require(isinstance(parsed.get(domain), list) and parsed[domain], 'Empty ISO domain: ' + name)
        if domain != '3166-3':
            xml = ET.parse(prefix / 'share/xml/iso-codes' / ('iso_' + domain + '.xml')).getroot()
            require(len(xml) > 0, 'Empty legacy XML domain: ' + domain)
            if domain == '3166-1':
                historic = json.loads((source / 'data/iso_3166-3.json').read_bytes())['3166-3']
                actual = {row.attrib['alpha_4_code'] for row in xml.findall('iso_3166_3_entry')}
                require(actual == {row['alpha_4'] for row in historic}, 'Historic country XML records differ.')
        if domain == '3166-2':
            original = json.loads((source / 'data/iso_3166-2.json').read_bytes())['3166-2']
            actual = {row.attrib['code']: row.attrib['name']
                      for row in xml.findall('.//iso_3166_2_entry')}
            require(actual == {row['code']: row['name'] for row in original},
                    'Subdivision XML lost or changed a source code/name pair.')
        linguas = source / ('iso_' + domain) / 'LINGUAS'
        inputs[str(linguas)] = hashlib.sha256(linguas.read_bytes()).hexdigest()
        for language in linguas.read_text().splitlines():
            if not language or language.startswith('#'):
                continue
            require(re.fullmatch(r'[A-Za-z0-9_@-]+', language), 'Unexpected language identifier.')
            po = source / ('iso_' + domain) / (language + '.po')
            original = po.read_bytes()
            original.decode('utf-8', errors='strict')
            inputs[str(po)] = hashlib.sha256(original).hexdigest()
            folder = prefix / 'share/locale' / language / 'LC_MESSAGES'
            name = 'iso_' + domain + '.mo'
            with (folder / name).open('rb') as stream:
                messages = gettext.GNUTranslations(stream)
            require(messages.gettext(''), 'Missing gettext catalog metadata: ' + str(folder / name))
            catalogs += 1
            if domain in ALIASES:
                alias = folder / ('iso_' + ALIASES[domain] + '.mo')
                require(alias.is_symlink() and str(alias.readlink()) == name,
                        'Missing or incorrect gettext alias: ' + str(alias))
                require(alias.read_bytes() == (folder / name).read_bytes(), 'Broken gettext alias.')
                aliases += 1
    xml_dir = prefix / 'share/xml/iso-codes'
    # The generator stores historic records in iso_3166-1.xml.
    empty_domain = xml_dir / 'iso_3166-3.xml'
    require(not empty_domain.exists() and not empty_domain.is_symlink(),
            'Meson installed an empty standalone historic-country XML file.')
    for domain, alias in ALIASES.items():
        link = xml_dir / ('iso_' + alias + '.xml')
        name = 'iso_' + domain + '.xml'
        require(link.is_symlink() and str(link.readlink()) == name, 'Incorrect legacy XML alias.')
        require(link.read_bytes() == (xml_dir / name).read_bytes(), 'Broken legacy XML alias.')
        aliases += 1
    metadata = (prefix / 'share/pkgconfig/iso-codes.pc').read_text()
    require('prefix=' + logical_prefix in metadata.splitlines(), 'Wrong installed pkg-config prefix.')
    require('Version: 4.20.1' in metadata.splitlines(), 'Wrong installed ISO data version.')
    domains = next((line.removeprefix('domains=') for line in metadata.splitlines()
                    if line.startswith('domains=')), '').split()
    require(domains == ['iso_' + d for d in DOMAINS], 'Changed pkg-config domain contract.')
    require(not any(str(path) in metadata for path in producers), 'pkg-config exposes a producer path.')
    return dict(status='PASS', input_sha256=inputs, json_files=16, legacy_xml_files=7,
                utf8_source_catalogs=catalogs, gettext_catalogs=catalogs, relative_aliases=aliases,
                scope='Installed JSON source identity/parsing, XML syntax, historic-country codes, '
                      'complete subdivision codes/names, every declared UTF-8 source/gettext '
                      'catalog, relative aliases and pkg-config version/prefix/domains. '
                      'JSON Schema validation and GUI execution are separate.')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('source', type=Path)
    cli.add_argument('installed_prefix', type=Path)
    cli.add_argument('new_results', type=Path)
    cli.add_argument('--logical-prefix', required=True)
    cli.add_argument('--producer-path', type=Path, action='append', required=True)
    args = cli.parse_args()
    source, prefix = (p.resolve(strict=True) for p in (args.source, args.installed_prefix))
    out = args.new_results
    require(out.is_absolute() and out.resolve() == out and not out.exists() and not out.is_symlink(),
            'Use a new canonical result directory.')
    require(not any(out.is_relative_to(p) for p in (source, prefix)), 'Keep results outside the inputs.')
    require(args.logical_prefix.startswith('/'), 'Use an absolute logical install prefix.')
    producers = [p.resolve(strict=True) for p in args.producer_path]
    require(Path(args.logical_prefix) not in producers, 'A producer path equals the logical prefix.')
    result = check(source, prefix, args.logical_prefix, producers)
    out.mkdir(mode=0o700, parents=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: 16 JSON files, seven legacy XML files, all catalogs and relative aliases.')


if __name__ == '__main__':
    main()
