#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check a second pkgsrc Meson configure updates options without deleting objects."""
import argparse
import hashlib
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'prefix', 'clang', 'meson-build-mk'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
source = args.meson_build_mk.read_text()
start = source.index('meson-configure:\n.for d in ${CONFIGURE_DIRS}')
end = source.index('\ndo-build: meson-build', start)
rule = source[start:end]
with tempfile.TemporaryDirectory(prefix='meson-refresh-') as temporary:
    root = Path(temporary)
    src = root / 'source'
    src.mkdir()
    (src / 'meson.build').write_text("project('refresh-fixture')\n"
                                    "cfg=configuration_data()\n"
                                    "cfg.set('VALUE', get_option('tests') ? 1 : 0)\n"
                                    "configure_file(output: 'value.h', configuration: cfg)\n")
    (src / 'meson_options.txt').write_text("option('tests', type: 'boolean', value: false)\n")
    makefile = root / 'Makefile'
    makefile.write_text('WRKSRC=' + str(src) + '\nCONFIGURE_DIRS=.\nRUN=\nSETENV=/usr/bin/env\n'
                        'MAKE_ENV=PATH=' + str(args.prefix/'bin') + ':' + str(args.prefix/'gnu/bin') + '\n'
                        'PREFIX=/usr/pkg\nPKGMANDIR=man\nPKG_SYSCONFDIR=/usr/pkg/etc\n' + rule + '\n')
    def configure(value):
        return subprocess.run([str(args.bmake), '-r', '-f', str(makefile),
                               'MESON_ARGS=-Dtests=' + value, 'meson-configure'],
                              cwd=root, capture_output=True, text=True)
    first = configure('false')
    assert first.returncode == 0, first.stdout + first.stderr
    obj = src/'output/kept.o'
    subprocess.run([str(args.clang), '-x', 'c', '-c', '-o', str(obj), '-'],
                   input='int kept_object = 7;\n', text=True, check=True)
    before = (obj.stat().st_mtime_ns, hashlib.sha256(obj.read_bytes()).hexdigest())
    second = configure('true')
    assert second.returncode == 0, second.stdout + second.stderr
    assert '#define VALUE 1' in (src/'output/value.h').read_text()
    assert (obj.stat().st_mtime_ns, hashlib.sha256(obj.read_bytes()).hexdigest()) == before
print('PASS: second actual Meson setup refreshes option and preserves compiled object')
