#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise owner checkout migration and unchanged archive/tool requirements."""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit('usage: host-checkout-migration.py SELECTED_SHELL')
producer = (Path(__file__).resolve().parents[1] / 'cross/build-host-tools.sh').read_text()
start = producer.index('        old_path=$tool')
end = producer.index('    done\nelse\n', start)
policy = producer[start:end]
with tempfile.TemporaryDirectory(prefix='qt-checkout-') as tmp:
    root = Path(tmp); old = root / 'old'; new = root / 'new'; work = root / 'work'
    for p in (old, new, work): p.mkdir()
    (old/'patch').write_text('patch'); (new/'patch').write_text('patch')
    tool = root/'selected-tool'; tool.write_text('tool')
    inputs = work/'inputs.txt'
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    inputs.write_text(f'{digest(old/"patch")}  {old}/patch\n{digest(tool)}  {tool}\n')
    script = root/'check.sh'
    script.write_text('set -eu\nfor tool in "$toolkit/patch" "$selected_tool"; do\n'+policy+'done\n')
    env = dict(os.environ, toolkit=str(new), old_toolkit=str(old), work=str(work), selected_tool=str(tool), resume_start='1', HOST_INCREMENTAL_RECONFIGURE='1')
    def run(expected):
        rc = subprocess.run([sys.argv[1], str(script)], env=env, stdout=subprocess.DEVNULL).returncode
        if rc != expected: raise AssertionError((rc, expected))
    run(0)
    (new/'patch').write_text('changed'); run(2); (new/'patch').write_text('patch')
    tool.write_text('changed'); run(2)
    dist = root/'dist'; dist.mkdir(); archive = dist/'qttools-everywhere-src-6.12.0.tar.xz'; archive.write_text('archive')
    (new/'sources.tsv').write_text('qttools\t'+archive.name+'\t'+digest(archive)+'\n')
    (work/'source/qttools-everywhere-src-6.12.0').mkdir(parents=True)
    inputs.write_text(f'{digest(archive)}  {archive}\n')
    start = producer.index('for module in $modules; do\n    archive=$module-everywhere-src-6.12.0.tar.xz')
    end = producer.index('if [ "$HOST_QT_QUICK3D_BUILD_DIR"', start)
    script.write_text('set -eu\n'+producer[start:end])
    env.update(modules='qttools', distfiles=str(dist), RESUME='1')
    run(0)
    archive.write_text('changed'); run(2)
print('PASS: incremental checkout preserves owner patch, selected tool and archive identity')
