#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check Kerberos native package installation paths with real pkgsrc metadata.

usage: darwin-bootstrap-install-paths.py EXPORTED_PKGSRC BMAKE MAKECONF PROFILE WORK
The profile is the candidate darwin-bootstrap.mk.conf from this checkout.
"""
import json
import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 6:
        raise SystemExit(__doc__)
    pkgsrc, bmake, makeconf, profile, work = map(Path, sys.argv[1:])
    work.mkdir(parents=True, exist_ok=True)
    candidate = work / 'EMBERBSD-DARWIN-BOOTSTRAP-MK.CONF'
    candidate.write_text(profile.read_text())
    for name in ('EMBERBSD-DEVELOPMENT-MK.CONF', 'EMBERBSD-DEFAULTS-MK.CONF', 'EMBERBSD-VERSIONS.MK'):
        (work / name).write_text((pkgsrc / name).read_text())
    config = makeconf.read_text()
    old = str(pkgsrc / 'EMBERBSD-DARWIN-BOOTSTRAP-MK.CONF')
    if config.count(old) != 1:
        raise SystemExit('MAKECONF must include the selected exported profile once')
    localconf = work / 'mk.conf'
    localconf.write_text(config.replace(old, str(candidate)))
    names = ['LOCALBASE', 'VARBASE', 'SYSCONFBASE', 'PKG_SYSCONFBASEDIR',
             'PKG_SYSCONFDIR', 'RCD_SCRIPTS_DIR', 'OWN_DIRS_PERMS',
             'RCD_SCRIPTS', 'PKG_USERS', 'PKG_GROUPS', 'PKG_CREATE_USERGROUP',
             'PKG_RCD_SCRIPTS', 'UNPRIVILEGED', 'PKG_DBDIR']
    cmd = [str(bmake), '-C', str(pkgsrc / 'security/mit-krb5'),
           f'MAKECONF={localconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
           'show-vars', f'VARNAMES={" ".join(names)}']
    values = dict(zip(names, subprocess.run(cmd, check=True, text=True,
                                             capture_output=True).stdout.splitlines()))
    base = values['LOCALBASE']
    expected = {'VARBASE': base + '/var', 'SYSCONFBASE': base + '/etc',
                'PKG_SYSCONFBASEDIR': base + '/etc', 'PKG_SYSCONFDIR': base + '/etc',
                'RCD_SCRIPTS_DIR': base + '/etc/rc.d', 'UNPRIVILEGED': 'yes',
                'PKG_CREATE_USERGROUP': 'NO', 'PKG_RCD_SCRIPTS': 'NO',
                'PKG_USERS': '', 'PKG_GROUPS': ''}
    for name, value in expected.items():
        if values.get(name) != value:
            raise AssertionError(f'{name}: {values.get(name)!r} != {value!r}')
    if values['OWN_DIRS_PERMS'].split()[0] != base + '/var/krb5kdc':
        raise AssertionError(values['OWN_DIRS_PERMS'])
    if set(values['RCD_SCRIPTS'].split()) != {'kadmind', 'kdc'}:
        raise AssertionError(values['RCD_SCRIPTS'])
    # These modules are normally included during install-script generation.
    # Inspect their actual relative DIR records without installing any package.
    extra = work / 'install-modules.mk'
    extra.write_text('.include "../../mk/init/rc.d.mk"\n'
                     '.include "../../mk/pkgtasks/directories.mk"\n')
    install_cmd = [str(bmake), '-C', str(pkgsrc / 'security/mit-krb5'),
                   '-f', 'Makefile', '-f', str(extra), f'MAKECONF={localconf}',
                   'EMBERBSD_DARWIN_BOOTSTRAP=yes', f'WRKOBJDIR={work / "obj"}',
                   'show-vars', 'VARNAMES=_MAKE_DIRS _OWN_DIRS_PERMS']
    records = subprocess.run(install_cmd, check=True, text=True,
                             capture_output=True).stdout.splitlines()
    if 'etc/rc.d' not in records[0].split():
        raise AssertionError(f'rc installation directory: {records!r}')
    if records[1].split()[0] != 'var/krb5kdc':
        raise AssertionError(f'owned installation directory: {records!r}')
    baseline = subprocess.run([str(bmake), '-C', str(pkgsrc / 'security/mit-krb5'),
                               f'MAKECONF={makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                               'show-var', 'VARNAME=PKG_DBDIR'], check=True, text=True,
                              capture_output=True).stdout.strip()
    if values['PKG_DBDIR'] != baseline:
        raise AssertionError('package database path changed')
    print(json.dumps({'result': 'PASS', 'metadata': values,
                      'installer_directory_records': records}, sort_keys=True))


if __name__ == '__main__':
    main()
