#!/usr/bin/env python3
"""Check ordinary pkgsrc dependency selection for both LXQt session policies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


X11 = {'openbox', 'obconf-qt', 'i3lock', 'xss-lock'}
WAYLAND = {'lxqt-wayland-session', 'labwc', 'swaylock', 'swayidle', 'qt6-qtwayland'}


def require_wayland(names):
    assert WAYLAND <= names, sorted(WAYLAND - names)
    assert not names & (X11 | {'xlockmore', 'gtk2', 'gtk3'}), sorted(names & X11)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pkgsrc', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--bmake', required=True)
    p.add_argument('--makeconf', type=Path, required=True)
    p.add_argument('--tmpdir', type=Path, required=True)
    a = p.parse_args()
    assert a.pkgsrc.is_absolute() and a.output.is_absolute()
    assert not a.output.exists()
    a.output.mkdir(parents=True)
    env = dict(os.environ, MAKECONF=str(a.makeconf), TMPDIR=str(a.tmpdir))
    result = {'scope': 'Ordinary direct runtime dependency selection. No build, install or complete runtime closure claim.',
              'recipe_sha256': {}, 'selections': {}}
    recipe = a.pkgsrc/'meta-pkgs/lxqt'
    for name in ['Makefile', 'options.mk']:
        result['recipe_sha256'][name] = hashlib.sha256((recipe/name).read_bytes()).hexdigest()
    for label, options in [('default', []), ('x11', ['PKG_OPTIONS.lxqt=-wayland openbox'])]:
        cmd = [a.bmake, '-C', str(recipe)] + options + ['show-var', 'VARNAME=DEPENDS']
        run = subprocess.run(cmd, env=env, capture_output=True, text=True)
        (a.output/(label+'.log')).write_text(run.stdout + run.stderr)
        assert run.returncode == 0, (run.stdout, run.stderr)
        dependencies = run.stdout.split()
        paths = {d.split(':', 1)[1] for d in dependencies}
        names = {Path(d).name for d in paths}
        assert not names & {'gtk2', 'gtk3', 'xscreensaver', 'xlockmore'}
        result['selections'][label] = {'command': cmd, 'dependencies': dependencies, 'names': sorted(names)}
        if label == 'x11':
            assert X11 <= names and not names & WAYLAND
        else:
            require_wayland(names)
    before = set(result['selections']['x11']['names'])
    after = set(result['selections']['default']['names'])
    assert before - after == X11 and after - before == WAYLAND
    try:
        require_wayland(before)
    except AssertionError:
        result['wrong_session_graph_rejected'] = True
    else:
        raise AssertionError('The Wayland check accepted the X11 graph')
    result['checks_passed'] = 3
    (a.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'output': str(a.output), 'checks_passed': 3,
                      'added': sorted(after-before), 'removed': sorted(before-after)}, indent=2))


if __name__ == '__main__':
    main()
