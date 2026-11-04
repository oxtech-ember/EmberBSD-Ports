#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check installed target Config conversion using a real configured Perl tree."""
import argparse
import os
import re
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
    output = root / 'nested' / 'target-config'
    command = [str(a.perl), str(helper), str(a.source), str(a.sysroot), str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    config = (output / 'config.sh').read_text()
    for line in ("aphostname='/bin/hostname'", "lns='/bin/ln -s'", "rm_try='/bin/rm -f try try a.out .out try.[cho] try..o core core.try* try.core*'"):
        assert line in config, line
    assert str(a.sysroot) not in config and '/Users/' not in config
    source_config = (a.source / 'config.sh').read_text()
    for field in ('ccflags', 'cppflags', 'optimize', 'ldflags', 'lddlflags',
                  'libpth', 'libspath', 'locincpth', 'loclibpth'):
        before_field = re.search(r'^' + field + r"='([^']*)'$", source_config, re.M)
        after_field = re.search(r'^' + field + r"='([^']*)'$", config, re.M)
        assert before_field and after_field, field
        expected = before_field.group(1).replace('--sysroot=' + str(a.sysroot), '')
        expected = expected.replace(str(a.sysroot) + '/', '/')
        assert after_field.group(1) == expected, field
    assert (output / 'lib/Config.pm').is_file()
    header = (output / 'config.h').read_text()
    assert '#define PHOSTNAME "/bin/hostname"' in header and '/Users/' not in header
    names = ('config.sh', 'config.h', 'myconfig.SH', 'lib/Config.pm',
             'lib/Config.pod', 'lib/Config_git.pl', 'lib/Config_heavy.pl')
    before = {name: (output / name).read_bytes() for name in names}
    sentinel = output / 'unrelated'
    sentinel.write_text('preserve me\n')
    stable = output / 'config.h'
    stable_time = (1_600_000_000, 1_600_000_000)
    os.utime(stable, stable_time)
    unchanged_time = (output / 'myconfig.SH').stat().st_mtime_ns
    changed = root / 'changed-source'
    changed.mkdir()
    for name in ('config.sh', 'config.h'):
        shutil.copyfile(a.source / name, changed / name)
    shutil.copyfile(a.source / 'configpm', changed / 'configpm')
    (changed / 'lib').mkdir()
    shutil.copyfile(a.source / 'myconfig.SH', changed / 'myconfig.SH')
    shutil.copyfile(a.source / 'lib/Config_git.pl', changed / 'lib/Config_git.pl')
    with (changed / 'config.sh').open('a') as stream:
        stream.write('# repeat-generation fixture\n')
    result = subprocess.run([str(a.perl), str(helper), str(changed), str(a.sysroot), str(output)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '# repeat-generation fixture' in (output / 'config.sh').read_text()
    assert (output / 'config.h').read_bytes() == before['config.h']
    assert (output / 'config.h').stat().st_mtime == stable_time[1]
    assert (output / 'myconfig.SH').read_bytes() == before['myconfig.SH']
    assert (output / 'myconfig.SH').stat().st_mtime_ns == unchanged_time
    assert sentinel.read_text() == 'preserve me\n'
    bad = root / 'bad-source'
    bad.mkdir()
    for name in ('config.sh', 'config.h'):
        shutil.copyfile(a.source / name, bad / name)
    shutil.copyfile(a.source / 'configpm', bad / 'configpm')
    (bad / 'lib').mkdir()
    shutil.copyfile(a.source / 'myconfig.SH', bad / 'myconfig.SH')
    shutil.copyfile(a.source / 'lib/Config_git.pl', bad / 'lib/Config_git.pl')
    with (bad / 'config.sh').open('a') as stream:
        stream.write("unrelated_host_tool='/private/host-tool'\n")
    previous = {name: (output / name).read_bytes() for name in names}
    result = subprocess.run([str(a.perl), str(helper), str(bad), str(a.sysroot), str(output)],
                            capture_output=True, text=True)
    assert result.returncode != 0 and 'Untranslated build-host path' in result.stderr
    assert {name: (output / name).read_bytes() for name in names} == previous
    assert '# repeat-generation fixture' in (output / 'config.sh').read_text()
    assert sentinel.read_text() == 'preserve me\n'
    bad_layout = root / 'bad-layout'
    bad_layout.mkdir()
    (bad_layout / 'lib').symlink_to(output / 'lib', target_is_directory=True)
    result = subprocess.run([str(a.perl), str(helper), str(a.source), str(a.sysroot), str(bad_layout)],
                            capture_output=True, text=True)
    assert result.returncode != 0 and 'Output lib is not a directory' in result.stderr
    assert list(bad_layout.iterdir()) == [bad_layout / 'lib']
print('Perl installed target Config: PASS')
