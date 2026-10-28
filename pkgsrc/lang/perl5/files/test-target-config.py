#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check installed target Config conversion using a real configured Perl tree."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('perl', 'source', 'sysroot', 'work-dir'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
helper = Path(__file__).with_name('target-config.pl')
with tempfile.TemporaryDirectory(dir=a.work_dir) as temporary:
    root = Path(temporary)
    output = root / 'target-config'
    command = [str(a.perl), str(helper), str(a.source), str(a.sysroot), str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    config = (output / 'config.sh').read_text()
    for line in ("aphostname='/bin/hostname'", "lns='/bin/ln -s'", "rm_try='/bin/rm -f try try a.out .out try.[cho] try..o core core.try* try.core*'"):
        assert line in config, line
    assert str(a.sysroot) not in config and '/Users/' not in config
    assert (output / 'lib/Config.pm').is_file()
    header = (output / 'config.h').read_text()
    assert '#define PHOSTNAME "/bin/hostname"' in header and '/Users/' not in header
    bad = root / 'bad-source'
    bad.mkdir()
    for name in ('config.sh', 'config.h'):
        shutil.copyfile(a.source / name, bad / name)
    with (bad / 'config.sh').open('a') as stream:
        stream.write("unrelated_host_tool='/private/host-tool'\n")
    result = subprocess.run([str(a.perl), str(helper), str(bad), str(a.sysroot), str(root / 'bad-output')],
                            capture_output=True, text=True)
    assert result.returncode != 0 and 'Untranslated build-host path' in result.stderr
print('Perl installed target Config: PASS')
