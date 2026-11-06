#!/usr/bin/env python3
# Copyright (c) 2026 EmberBSD contributors
# SPDX-License-Identifier: BSD-2-Clause
"""Check actual pkgsrc DBus options across selected native and target roles."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'host-config', 'cross-conf', 'host-base', 'host-config-export',
                 'bmake', 'tools', 'prefix'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--recipe', type=Path, default=Path(__file__).resolve().parent.parent,
                        help='DBus owner recipe directory (default: parent of this test)')
    args = parser.parse_args()
    source, recipe = args.pkgsrc.resolve(), args.recipe.resolve()
    env = dict(os.environ, PATH=f'{args.tools}:{args.prefix}/bin:{args.prefix}/gnu/bin')
    cases = (
        ('target-unset', 'yes', None, True, True, True),
        ('target-explicit-off', 'yes', '-dbus-system -x11', True, False, False),
        ('target-explicit-on', 'yes', 'dbus-system -x11', True, True, False),
        ('native-inherited-off', 'no', None, True, False, True),
        ('native-default-off', 'no', None, False, False, True),
        ('native-explicit-on', 'no', 'dbus-system -x11', True, True, False),
    )
    with tempfile.TemporaryDirectory(prefix='dbus-options-') as tmp:
        root = Path(tmp); tree = root / 'pkgsrc'; tree.mkdir()
        for item in source.iterdir():
            if item.name != 'sysutils':
                (tree / item.name).symlink_to(item, item.is_dir())
        (tree / 'sysutils').mkdir(); package = tree / 'sysutils/dbus'; package.mkdir()
        for item in (source / 'sysutils/dbus').iterdir():
            if item.name in ('Makefile', 'options.mk', 'PLIST'):
                shutil.copyfile(recipe / item.name, package / item.name)
            else:
                (package / item.name).symlink_to(item, item.is_dir())
        base = args.cross_conf.read_text()
        assert str(args.host_base) in base and str(args.host_config_export) in base
        for name, role, override, host_setting, system, x11 in cases:
            host = root / (name + '-host.mk')
            host.write_text(args.host_base.read_text() +
                            ('\nPKG_OPTIONS.dbus?= -dbus-system\n' if host_setting else '\n'))
            config = base.replace(str(args.host_base), str(host)).replace(
                str(args.host_config_export), str(args.host_config.resolve(strict=True)))
            if override is not None:
                config = 'PKG_OPTIONS.dbus= ' + override + '\n' + config
            conf = root / (name + '.mk'); conf.write_text(config)
            variables = ('${PKG_OPTIONS.dbus:U<unset>}', '${PKG_OPTIONS}',
                         '${PLIST.dbus-system:Uno}', '${PKG_GROUPS:U}',
                         '${RCD_SCRIPTS:U}', '${SPECIAL_PERMS:U}',
                         '${OWN_DIRS:U}', '${OWN_DIRS_PERMS:U}', '${SMF_METHODS:U}')
            command = [str(args.bmake), '-C', str(package), 'USE_CROSS_COMPILE=' + role]
            for var in variables: command += ['-V', var]
            result = subprocess.run(command, env=dict(env, MAKECONF=str(conf)),
                                    text=True, capture_output=True, timeout=45, check=False)
            if result.returncode:
                raise RuntimeError(name + ': bmake failed: ' + result.stderr[-2500:])
            lines = result.stdout.splitlines()
            assert len(lines) == len(variables), (name, lines)
            selected, opts, plist, groups, rc, perms, dirs, owned, smf = lines
            assert ('dbus-system' in opts.split()) == system, (name, lines)
            assert ('x11' in opts.split()) == x11, (name, lines)
            assert (plist == 'yes') == system, (name, lines)
            assert bool(groups) == bool(rc) == bool(perms) == bool(smf) == system, (name, lines)
            assert ('system-services' in dirs) == system, (name, lines)
            assert ('/lib/dbus' in owned if system else '/lib/dbus' in dirs), (name, lines)
            if override is not None: assert selected == override, (name, lines)
            if name == 'target-unset': assert selected == '<unset>', (name, lines)
            print(name, 'PASS', flush=True)


if __name__ == '__main__':
    main()
