#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check the namespaced catalog and its shared package floor. AI-assisted."""

import argparse
import copy
from pathlib import Path
import re
import xml.etree.ElementTree as ET

NS = '{urn:oasis:names:tc:entity:xmlns:xml:catalog}'
OLD = 'http://docbook.sourceforge.net/release/xsl/current/'
NEW = 'http://docbook.sourceforge.net/release/xsl-ns/current/'
RULES = (('rewriteURI', 'uriStartString'), ('rewriteSystem', 'systemIdStartString'))

def load(path):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    root = ET.parse(path, parser=parser).getroot()
    if root.tag != NS + 'catalog':
        raise ValueError('Expected an OASIS XML catalog')
    return root

def tree_value(node):
    return (node.tag, tuple(sorted(node.attrib.items())), node.text, node.tail,
            tuple(tree_value(child) for child in node))

def check_catalog(path, baseline=None):
    root = load(path)
    for tag, key in RULES:
        rules = list(root.iter(NS + tag))
        matches = [node for node in rules if node.get(key) == NEW]
        if len(matches) != 1 or not matches[0].get('rewritePrefix'):
            raise ValueError('Expected one namespaced SourceForge ' + tag)
        if any(node.get(key) == OLD for node in rules):
            raise ValueError('The non-namespaced SourceForge URI has a different owner')
    if baseline is not None:
        expected = copy.deepcopy(load(baseline))
        for tag, key in RULES:
            matches = [node for node in expected.iter(NS + tag) if node.get(key) == OLD]
            if len(matches) != 1:
                raise ValueError('The baseline must contain one old ' + tag)
            matches[0].set(key, NEW)
        if tree_value(root) != tree_value(expected):
            raise ValueError('Catalog changes exceed the two SourceForge URI replacements')

def unconditional_lines(path, token):
    depth = 0
    matches = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if re.match(r'^\.(if|ifdef|ifndef)\b', stripped):
            depth += 1
        elif re.match(r'^\.endif\b', stripped):
            depth -= 1
        if token in line and not stripped.startswith('#'):
            matches.append((depth, stripped))
    return matches

def check_recipe(recipe, consumer):
    revisions = unconditional_lines(recipe / 'Makefile', 'PKGREVISION')
    if len(revisions) != 1 or revisions[0][0] != 0 or not re.fullmatch(r'PKGREVISION\s*=\s*1', revisions[0][1]):
        raise ValueError('Native and cross recipes require unconditional PKGREVISION=1')
    distname = unconditional_lines(recipe / 'Makefile', 'DISTNAME')
    if distname != [(0, 'DISTNAME=\t${PKGNAME_NOREV:S/-ns//}')]:
        raise ValueError('The upstream DISTNAME must exclude the package revision')
    dependencies = unconditional_lines(consumer, 'docbook-xsl-ns')
    expected = 'TOOL_DEPENDS+=\tdocbook-xsl-ns>=1.79.2nb1:../../textproc/docbook-xsl-ns'
    if dependencies != [(0, expected)]:
        raise ValueError('The native tool predicate must reject the broken old package')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    recipe = Path(__file__).resolve().parents[1]
    parser.add_argument('--recipe', type=Path, default=recipe)
    parser.add_argument('--libnotify-makefile', type=Path,
                        default=recipe.parents[1] / 'sysutils/libnotify/Makefile')
    args = parser.parse_args()
    try:
        check_catalog(args.catalog, args.baseline)
        check_recipe(args.recipe, args.libnotify_makefile)
    except (OSError, ValueError, ET.ParseError) as error:
        parser.exit(1, 'FAIL: ' + str(error) + '\n')
    print('PASS: two namespace URI rules and the unconditional shared package floor')

if __name__ == '__main__':
    main()
