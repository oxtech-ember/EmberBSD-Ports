#!/usr/bin/env python3
"""Exercise Meson's real Darwin dependency scan with selected native lipo."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('meson-source', 'python', 'cc', 'lipo', 'ninja', 'library-dir', 'prefix'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
env = dict(os.environ, PATH=a.prefix + '/bin:' + a.prefix + '/gnu/bin')
with tempfile.TemporaryDirectory(prefix='meson-lipo-') as temporary:
    root = Path(temporary)
    source = root / 'src'
    source.mkdir()
    (source / 'main.c').write_text('int main(void) { return 0; }\n')
    (source / 'meson.build').write_text("project('lipo-smoke', 'c')\n"
        + "executable('smoke', 'main.c', link_args : ['-L" + a.library_dir + "', '-lcrypto'])\n")
    def setup(name, lipo):
        machine = root / (name + '.ini')
        machine.write_text('[binaries]\nc = ' + repr(a.cc) + '\nlipo = ' + lipo + '\n')
        return subprocess.run([a.python, '-B', a.meson_source + '/meson.py', 'setup',
                               str(root / name), str(source), '--native-file', str(machine)],
                              text=True, env=env, capture_output=True)
    good = setup('good', repr(a.lipo))
    assert good.returncode == 0, good.stdout + good.stderr
    subprocess.run([a.ninja, '-C', str(root / 'good')], env=env, check=True, capture_output=True)
    subprocess.run([str(root / 'good/smoke')], env=env, check=True)
    empty = setup('empty', '[]')
    assert empty.returncode and 'selected lipo command is empty' in empty.stdout + empty.stderr
    missing = setup('missing', repr(str(root / 'missing-lipo')))
    assert missing.returncode and 'missing-lipo' in missing.stdout + missing.stderr
print('PASS: Meson Darwin lipo selection, real link, empty and missing selectors')
