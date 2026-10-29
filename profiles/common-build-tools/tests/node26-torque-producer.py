#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise Node's real GYP Torque producer in native and cross toolsets.

Arguments are a prepared Node source, selected host Python and selected GNU make.
"""
import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    source = Path(sys.argv[1]).resolve()
    python = str(Path(sys.argv[2]).resolve())
    make = str(Path(sys.argv[3]).resolve())
    node_gyp = ast.literal_eval((source / 'tools/v8_gypfiles/v8.gyp').read_text())
    target = next(t for t in node_gyp['targets'] if t.get('target_name') == 'run_torque')
    target.pop('direct_dependent_settings', None)
    condition = next(c for c in target['conditions'] if 'actions' in c[1])
    action = condition[1]['actions'][0]
    action.pop('variables', None)
    action['inputs'] = []
    action['outputs'] = ['<(SHARED_INTERMEDIATE_DIR)/result']
    action['action'] = [python, 'writer.py', '<(SHARED_INTERMEDIATE_DIR)/result']
    fixture = {'targets': [
        {'target_name': 'torque', 'type': 'none', 'toolsets': ['host', 'target']},
        target,
    ]}
    for cross in (0, 1):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'x.gyp').write_text(repr(fixture))
            (root / 'writer.py').write_text(
                "import pathlib,sys\n"
                "p=pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True,exist_ok=True)\n"
                "pathlib.Path('count').open('a').write('x'); p.write_text('ok')\n"
            )
            env = dict(os.environ)
            for name in ('GYP_CROSSCOMPILE', 'AR_host', 'AR_target', 'CC_host',
                         'CC_target', 'CXX_host', 'CXX_target'):
                env.pop(name, None)
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            if cross:
                env['GYP_CROSSCOMPILE'] = '1'
            subprocess.run([python, '-B', str(source / 'tools/gyp/gyp_main.py'), '-f', 'make',
                            '--depth=.', '-Dwant_separate_host_toolset=' + str(cross),
                            'x.gyp'], cwd=root, env=env, check=True)
            subprocess.run([make, '-j16', 'run_torque'], cwd=root, env=env, check=True)
            assert (root / 'count').read_text() == 'x'
    print('Node Torque single producer: native and cross PASS')


if __name__ == '__main__':
    main()
