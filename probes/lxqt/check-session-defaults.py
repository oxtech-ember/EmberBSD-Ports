#!/usr/bin/env python3
"""Check LXQt Wayland defaults and the source route to its real locker."""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile


def read(text):
    config = configparser.ConfigParser(interpolation=None)
    config.read_string(text)
    return {section: dict(config[section]) for section in config.sections()}


def selected(config):
    assert config['General']['compositor'] == 'labwc'
    assert config['General']['lock_command_wayland'] == 'swaylock'
    assert config['General']['lock_command'] == 'i3lock --nofork'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--patch-tool', required=True)
    p.add_argument('--liblxqt-source', type=Path, required=True)
    a = p.parse_args()
    pin = 'd77f378ece0bfc7195f1964e88f55919729c3b0a55a858d7155ffaacc57bba44'
    assert hashlib.sha256(a.archive.read_bytes()).hexdigest() == pin
    assert not a.output.exists()
    a.output.mkdir(parents=True)
    with tarfile.open(a.archive) as tf:
        original = tf.extractfile('lxqt-session-2.4.0/config/session.conf').read().decode()
        leave = tf.extractfile('lxqt-session-2.4.0/lxqt-leave/main.cpp').read().decode()
    source = a.output/'source/config/session.conf'
    source.parent.mkdir(parents=True)
    source.write_text(original)
    patch = Path(__file__).parent/'recipes/x11/lxqt-session/patches/patch-config_session.conf'
    cmd = [a.patch_tool, '-p0', '-F0', '-i', str(patch.resolve())]
    run = subprocess.run(cmd, cwd=source.parent.parent, capture_output=True, text=True)
    (a.output/'patch.log').write_text(run.stdout + run.stderr)
    assert run.returncode == 0, (run.stdout, run.stderr)
    before = read(original)
    after = read(source.read_text())
    selected(after)
    restored = {s: dict(v) for s, v in after.items()}
    del restored['General']['compositor']
    del restored['General']['lock_command_wayland']
    del restored['General']['lock_command']
    assert restored == before
    rejected = 0
    for config in [before, read(source.read_text().replace('lock_command_wayland=swaylock', 'lock_command_wayland=')),
                   read(source.read_text().replace('compositor=labwc', 'compositor='))]:
        try:
            selected(config)
        except (AssertionError, KeyError):
            rejected += 1
        else:
            raise AssertionError('The policy accepted incomplete defaults')
    assert re.search(r'if\s*\(parser.isSet\(lockscreenOption\)\)\s*\{[^}]*screensaver.lockScreen\(\)', leave)
    saver = a.liblxqt_source/'lxqtscreensaver.cpp'
    text = saver.read_text()
    assert 'platformName() == QStringLiteral("wayland")' in text
    assert 'sessionSettings.value(QL1SV("lock_command_wayland"), lockCommand)' in text
    assert 'QProcess::splitCommand(d->lock_command)' in text
    assert 'd->m_lockProcess->start(program, args, QIODevice::ReadWrite)' in text
    result = {'archive_sha256': pin, 'patch_command': cmd,
              'defaults': after['General'], 'preserved_existing_settings': True,
              'rejected_incomplete_defaults': rejected,
              'source_route': ['lxqt-leave --lockscreen', 'LXQt::ScreenSaver::lockScreen',
                               'session lock_command_wayland', 'QProcess::start swaylock'],
              'liblxqt_source_sha256': hashlib.sha256(saver.read_bytes()).hexdigest(),
              'scope': 'Source and configuration contract only. No locker, compositor, authentication or target session was executed.'}
    (a.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
