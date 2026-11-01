#!/usr/bin/env python3
"""Check recursive DNS-SD client linkage for native and cross OS selection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
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

    recipe = Path(__file__).resolve().parents[1] / '../../pkgsrc/net/mDNSResponder'
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
                '-V', '${MAKE_FLAGS}'], a.work, env)
    flags = shlex.split(flags)
    assert 'SYSTEM=NetBSD' in flags and 'os=netbsd' in flags, flags
    assert not any(flag.startswith('LINKOPTS=') for flag in flags), flags
    native_flags = run('actual-native-flags', [a.bmake, '-C', a.pkgsrc / 'net/mDNSResponder',
                       'USE_CROSS_COMPILE=no', '-V', '${MAKE_FLAGS}'], a.work, env)
    native_flags = shlex.split(native_flags)
    darwin_prefix = run('actual-darwin-prefix', [a.bmake, 'OPSYS=Darwin',
                         '-C', a.pkgsrc / 'net/mDNSResponder', '-V', '${PREFIX}'], a.work, env).strip()
    darwin_soopts = run('actual-darwin-soopts', [a.bmake, 'OPSYS=Darwin',
                           '-C', a.pkgsrc / 'net/mDNSResponder', '-V', '${_MDNS_DARWIN_SOOPTS}'], a.work, env).strip()
    darwin_flags = run('actual-darwin-flags', [a.bmake, 'OPSYS=Darwin',
                         '-C', a.pkgsrc / 'net/mDNSResponder', '-V', '${MAKE_FLAGS}'], a.work, env)
    expected_soopts = '-dynamiclib -Wl,-install_name,' + darwin_prefix + '/lib/libdns_sd.dylib'
    assert darwin_soopts == expected_soopts, darwin_soopts
    assert 'SOOPTS=' in darwin_flags and \
           darwin_soopts.replace(' ', r'\ ') in darwin_flags, darwin_flags
    assert 'install_name_tool' not in (recipe / 'Makefile').read_text()
    host = subprocess.check_output(['uname', '-s'], text=True).strip()
    assert 'SYSTEM=' + host in native_flags, native_flags
    # This control selects the actual failing host branch on every host.
    baseline = run('host-darwin-control', [a.gmake, '-n', 'SYSTEM=Darwin', 'all'], source / 'Clients')
    candidate = run('target-recursive', [a.gmake, '-n', *flags, 'all'], source / 'mDNSPosix')
    darwin_library = run('darwin-library-link', [a.gmake, '-n', 'os=x',
                          'build/prod/libdns_sd.dylib', 'LINKOPTS=-lSystem', 'SOOPTS=' + darwin_soopts],
                         source / 'mDNSPosix')
    darwin_daemon = run('darwin-daemon-link', [a.gmake, '-n', 'os=x',
                         'build/prod/mdnsd', 'LINKOPTS=-lSystem', 'SOOPTS=' + darwin_soopts],
                        source / 'mDNSPosix')
    native = run('native-host-control', [a.gmake, '-n', *native_flags, 'all'], source / 'Clients')
    assert '-ldns_sd' not in baseline
    assert ('-ldns_sd' in native) == (host != 'Darwin')
    links = [line for line in candidate.splitlines() if re.search(r'\bdns-sd\.c\s+ClientCommon\.c\b', line)]
    assert len(links) == 1 and '-ldns_sd' in links[0], links
    dylib_links = [line for line in darwin_library.splitlines()
                   if 'libdns_sd.dylib' in line and '-dynamiclib' in line]
    assert len(dylib_links) == 1 and '-dynamiclib' in dylib_links[0] and '-lSystem' in dylib_links[0] and \
           ('-Wl,-install_name,' + darwin_prefix + '/lib/libdns_sd.dylib') in dylib_links[0], dylib_links
    daemon_links = [line for line in darwin_daemon.splitlines() if '-o build/prod/mdnsd ' in line]
    assert len(daemon_links) == 1 and '-install_name' not in daemon_links[0], daemon_links
    # A recursive environment value alone cannot override the client's :=.
    ignored = run('environment-not-sufficient', [a.gmake, '-n', 'all'], source / 'Clients',
                  dict(os.environ, SYSTEM='NetBSD'))
    if host == 'Darwin':
        assert '-ldns_sd' not in ignored
    else:
        assert '-ldns_sd' in ignored
    result = dict(result='PASS', host=host, cases=6, make_flags=flags, native_make_flags=native_flags,
                  darwin_soopts=darwin_soopts, darwin_library_link=dylib_links[0],
                  target_client_link=links[0], source_sha256=hashlib.sha256(a.archive.read_bytes()).hexdigest(),
                  scope='Actual patched GNU make graphs and pkgsrc flags; target compilation is separate')
    (a.work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
