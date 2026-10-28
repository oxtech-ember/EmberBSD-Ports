#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check real pkgsrc host PATH for an SDK cross profile and native builds."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'shell', 'prefix', 'pkgsrc', 'cross-conf', 'native-conf', 'work-dir'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
env = dict(os.environ, PATH=str(a.prefix / 'bin') + ':' + str(a.prefix / 'gnu/bin'))
with tempfile.TemporaryDirectory(dir=a.work_dir) as temporary:
    root = Path(temporary)
    for name in ('target', 'x11'):
        path = root / name / 'bin'
        path.mkdir(parents=True)
        (path / 'ember-path-fixture').write_text('not executed\n')
        (path / 'ember-path-fixture').chmod(0o755)
    target, x11 = str(root / 'target'), str(root / 'x11')
    def query(config, cross):
        result = subprocess.run([str(a.bmake), '-C', str(a.pkgsrc / 'lang/perl5'),
                                 'MAKECONF=' + str(config), 'LOCALBASE=' + target, 'TOOLBASE=' + str(a.prefix),
                                 'X11BASE=' + x11, 'X11_TYPE=native', 'USE_X11=yes',
                                 *([] if cross else ['EMBERBSD_DARWIN_BOOTSTRAP=yes']), '-V', '${PATH}', '-V', '${ALL_ENV}'],
                                env=env, capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        path = lines[0].split(':')
        all_env = shlex.split(lines[1])
        configured = [x[5:] for x in all_env if x.startswith('PATH=')]
        assert len(configured) == 1, configured
        configure_path = configured[0].split(':')
        for values in (path, configure_path):
            assert ((target + '/bin') in values) != cross, values
            assert ((x11 + '/bin') in values) != cross, values
            if cross:
                assert str(a.prefix / 'bin') in values, values
        return path, configure_path
    cross, configured = query(a.cross_conf, True)
    native, native_configured = query(a.native_conf, False)
    for values in (cross, configured):
        result = subprocess.run([str(a.shell), '-c', 'command -v ember-path-fixture'],
                                env=dict(env, PATH=':'.join(values)), capture_output=True, text=True)
        assert result.returncode != 0 and not result.stdout, result.stdout
print('SDK cross host PATH selection: PASS')
