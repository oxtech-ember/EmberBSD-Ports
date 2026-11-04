#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check the native bootstrap dependency graph with the real pkgsrc recipes."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--bmake', required=True)
p.add_argument('--pkgsrc', required=True, type=Path)
p.add_argument('--makeconf', required=True)
p.add_argument('--tsort', required=True)
a = p.parse_args()
def dependencies(package):
    result = subprocess.run([a.bmake, '-C', str(a.pkgsrc / package),
        'MAKECONF=' + a.makeconf, 'USE_CROSS_COMPILE=no',
        '-V', '${OPSYS}', '-V', '${TOOL_DEPENDS}'], text=True, capture_output=True, check=True)
    rows = result.stdout.splitlines()
    return rows[0], {word.split(':', 1)[1].removeprefix('../../')
                     for word in rows[1].split() if ':' in word}
opsys, installer = dependencies('sysutils/bsdinstall')
checker_opsys, checker = dependencies('sysutils/checkperms')
consumer_opsys, consumer = dependencies('devel/zlib')
assert opsys == checker_opsys == consumer_opsys
assert 'sysutils/checkperms' not in installer, installer
if opsys == 'Darwin':
    assert 'sysutils/bsdinstall' in checker, checker
assert 'sysutils/checkperms' in consumer, consumer
graph = {'sysutils/bsdinstall': installer, 'sysutils/checkperms': checker,
         'devel/zlib': consumer}
assert all(node not in deps for node, deps in graph.items()), graph
edges = ''.join(f'{node} {node}\n' for node in graph)
edges += ''.join(f'{dep} {node}\n' for node, deps in graph.items()
                 for dep in deps if dep in graph and dep != node)
result = subprocess.run([a.tsort], input=edges, text=True, capture_output=True, check=True)
order = result.stdout.splitlines()
assert set(order) == set(graph), order
assert order.index('sysutils/checkperms') < order.index('devel/zlib')
if opsys == 'Darwin':
    assert order.index('sysutils/bsdinstall') < order.index('sysutils/checkperms')
print('native bsdinstall/checkperms order and ordinary consumer PASS')
