#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the real exported Vulkan-Headers package and installed-consumer graph."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory(prefix='vulkan-options-', dir=a.work_parent) as work:
    w = Path(work)
    d = w / 'graphics/vulkan-headers'
    d.mkdir(parents=True)
    for name in ('Makefile', 'buildlink3.mk'):
        (d / name).write_bytes((root / 'upstream/pkgsrc/graphics/vulkan-headers' / name).read_bytes())
    with (root / 'profiles/common-build-tools/patches/vulkan-headers-headless.patch').open('rb') as patch:
        subprocess.run(['patch', '-p1', '-d', str(w)], stdin=patch, check=True, capture_output=True)
    for kind in ('Makefile', 'buildlink3.mk'):
        text = (d / kind).read_text()
        lines = []
        for line in text.splitlines():
            if line.lstrip().startswith('.include '):
                if '/x11/' in line:
                    lines.append('GRAPH+= ' + line.split('/x11/')[1].split('/')[0])
                continue
            if line.startswith('pkgbase:='):
                continue
            lines.append(line)
        body = '\n'.join(lines)
        for opts, installed, expect_x, tests in (
            ('', '', True, False), ('headless', 'headless', False, False),
            ('tests', '', True, True), ('headless tests', 'headless', False, True),
            ('headless', '', True, False), ('', 'headless', False, False)):
            fixture = w / 'fixture.mk'
            fixture.write_text('OPSYS=NetBSD\nPKG_OPTIONS=' + opts +
                               '\nPKG_BUILD_OPTIONS.vulkan-headers=' + installed +
                               '\n' + body + '\nshow:\n\t@printf "%s\\n" "${GRAPH}" "${CMAKE_CONFIGURE_ARGS}"\n')
            r = subprocess.run([str(a.bmake), '-r', '-m', '/', '-f', str(fixture), 'show'],
                               text=True, capture_output=True, check=True)
            graph, cmake = r.stdout.splitlines()
            expected = expect_x if kind == 'buildlink3.mk' else 'headless' not in opts.split()
            if bool(graph.strip()) != expected:
                raise SystemExit('unexpected X11 graph: ' + kind + ' ' + opts + '/' + installed)
            if kind == 'Makefile' and ('-DVULKAN_HEADERS_ENABLE_TESTS=ON' in cmake) != tests:
                raise SystemExit('unexpected upstream tests setting')
print('PASS: Vulkan-Headers default/headless/tests and installed-option consumer graphs')
