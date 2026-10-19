#!/usr/bin/env python3
"""Check recursive DNS-SD client linkage for native and cross OS selection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'pkgsrc', 'makeconf', 'bmake', 'gmake', 'patch', 'work'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    assert hashlib.sha256(a.archive.read_bytes()).hexdigest() == 'f665cf02b5c930f9b70fb39b7567f03dd821997594c56ce399098eaa0372fb15'
    assert not a.work.exists()
    a.work.mkdir(parents=True)
    commands = []

    def run(label, argv, cwd, env=None):
        argv = [str(p) for p in argv]
        p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
        (a.work / (label + '.stdout')).write_text(p.stdout)
        (a.work / (label + '.stderr')).write_text(p.stderr)
        commands.append(dict(label=label, argv=argv, status=p.returncode))
        (a.work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        assert p.returncode == 0, (label, p.stdout, p.stderr)
        return p.stdout

    recipe = Path(__file__).resolve().parents[1] / 'recipes/net/mDNSResponder'
    with tarfile.open(a.archive) as tf:
        tf.extractall(a.work / 'source', filter='data')
    source = a.work / 'source/mDNSResponder-mDNSResponder-2881.120.11'
    for patch in sorted((recipe / 'patches').iterdir()):
        run(patch.name, [a.patch, '--batch', '--fuzz=0', '-p0', '-i', patch], source)
    client = source / 'Clients/Makefile'
    assert 'SYSTEM := $(shell uname -s)' in client.read_text()
    assert 'ifeq ($(SYSTEM), Darwin)' in client.read_text()
    env = dict(os.environ, MAKECONF=str(a.makeconf))
    flags = run('actual-recipe-flags', [a.bmake, '-C', a.pkgsrc / 'net/mDNSResponder',
                '-V', '${MAKE_FLAGS}'], a.work, env).split()
    assert 'SYSTEM=NetBSD' in flags and 'os=netbsd' in flags, flags
    native_flags = run('actual-native-flags', [a.bmake, '-C', a.pkgsrc / 'net/mDNSResponder',
                       'USE_CROSS_COMPILE=no', '-V', '${MAKE_FLAGS}'], a.work, env).split()
    host = subprocess.check_output(['uname', '-s'], text=True).strip()
    assert 'SYSTEM=' + host in native_flags, native_flags
    # This control selects the actual failing host branch on every host.
    baseline = run('host-darwin-control', [a.gmake, '-n', 'SYSTEM=Darwin', 'all'], source / 'Clients')
    candidate = run('target-recursive', [a.gmake, '-n', *flags, 'all'], source / 'mDNSPosix')
    native = run('native-host-control', [a.gmake, '-n', *native_flags, 'all'], source / 'Clients')
    assert '-ldns_sd' not in baseline
    assert ('-ldns_sd' in native) == (host != 'Darwin')
    links = [line for line in candidate.splitlines() if re.search(r'\bdns-sd\.c\s+ClientCommon\.c\b', line)]
    assert len(links) == 1 and '-ldns_sd' in links[0], links
    # A recursive environment value alone cannot override the client's :=.
    ignored = run('environment-not-sufficient', [a.gmake, '-n', 'all'], source / 'Clients',
                  dict(os.environ, SYSTEM='NetBSD'))
    if host == 'Darwin':
        assert '-ldns_sd' not in ignored
    else:
        assert '-ldns_sd' in ignored
    result = dict(result='PASS', host=host, cases=4, make_flags=flags, native_make_flags=native_flags,
                  target_client_link=links[0], source_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),
                  scope='Actual patched GNU make graphs and pkgsrc flags; target compilation is separate')
    (a.work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
