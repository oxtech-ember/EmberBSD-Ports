#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check MIT Kerberos cross-build client-keytab defaults against generated configure."""
import argparse
from pathlib import Path
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True
from sdk_source import load_sdk


def fail(message):
    raise ValueError(message)


def run_case(shell, harness, work, name, environment, expected, call_log,
             expect_host_query):
    case_dir = work / name
    case_dir.mkdir()
    log = case_dir / 'krb5-config-client-default.calls'
    env = {
        'PATH': str(work / 'host-bin') + ':/usr/bin:/bin',
        'KRB5_CONFIG_CALLS': str(log),
        'HOST_CLIENT_KEYTAB': 'FILE:/build-host/pkgsrc/var/krb5/user/%{euid}/client.keytab',
    }
    env.update(environment)
    result = subprocess.run([str(shell), str(harness)], cwd=case_dir,
                            env=env, text=True, capture_output=True,
                            timeout=15, check=False)
    if result.returncode != 0:
        fail(name + ' configure fragment failed: ' + result.stderr.strip())
    values = [line.removeprefix('RESULT=') for line in result.stdout.splitlines()
              if line.startswith('RESULT=')]
    if values != [expected]:
        fail(name + ' selected ' + repr(values) + ', expected ' + repr(expected))
    if not (case_dir / 'confdefs.h').is_file():
        fail(name + ' did not write configure definitions')
    if '#define DEFCKTNAME "' + expected + '"' not in (case_dir / 'confdefs.h').read_text():
        fail(name + ' did not define the selected client keytab')
    queried = log.is_file() and '--defcktname\n' in log.read_text()
    if queried != expect_host_query:
        fail(name + ' host krb5-config query state is ' + str(queried))
    call_log.append(dict(case=name, result=expected,
                         queried_host_default=queried,
                         exit=result.returncode))


def main():
    sdk, args = load_sdk()
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import write_json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path,
                        help='extracted and patched MIT Kerberos source directory')
    parser.add_argument('--recipe', required=True, type=Path,
                        help='mit-krb5 package Makefile')
    parser.add_argument('--target-statedir', required=True, type=Path,
                        help='target MIT_KRB5_STATEDIR value reported by pkgsrc')
    parser.add_argument('--work', required=True, type=Path,
                        help='new, exclusive directory outside source and recipe')
    arg = parser.parse_args(args)
    if any(not value.is_absolute() for value in
           (arg.source, arg.recipe, arg.target_statedir, arg.work)):
        fail('All paths must be absolute')
    target_statedir = arg.target_statedir
    source = arg.source.resolve(strict=True)
    recipe = arg.recipe.resolve(strict=True)
    work = arg.work.resolve(strict=False)
    if work.exists():
        fail('Work must be unused')
    if any(work == owned or work in owned.parents or owned in work.parents
           for owned in (source, recipe)):
        fail('Work must be disjoint from the source and recipe')
    configure = source / 'configure'
    configure_ac = source / 'configure.ac'
    if not configure.is_file() or not configure_ac.is_file():
        fail('Source must contain configure and configure.ac')
    ac_text = configure_ac.read_text()
    for fragment in (
        'AC_ARG_VAR(DEFCKTNAME, [Default client keytab name])',
        ': "' + chr(36) + '{DEFCKTNAME=' + chr(96) + '$with_krb5_config --defcktname' + chr(96) + '}"',
        'DEFCKTNAME=FILE:$exp_localstatedir/krb5/user/%{euid}/client.keytab',
    ):
        if fragment not in ac_text:
            fail('Upstream configure.ac default behavior changed: ' + fragment)
    recipe_text = recipe.read_text()
    override = ('CONFIGURE_ENV+=\t\tDEFCKTNAME=FILE:'
                '${MIT_KRB5_STATEDIR}/krb5/user/%{euid}/client.keytab')
    lines = recipe_text.splitlines()
    matching = [i for i, line in enumerate(lines) if line == override]
    if len(matching) != 1:
        fail('Recipe must set the target DEFCKTNAME exactly once')
    index = matching[0]
    previous_if = max((i for i in range(index) if lines[i].startswith('.if ')),
                      default=-1)
    previous_endif = max((i for i in range(index) if lines[i] == '.endif'),
                         default=-1)
    if previous_if <= previous_endif or lines[previous_if] != '.if ${USE_CROSS_COMPILE:Uno} == "yes"':
        fail('Target DEFCKTNAME must be inside the cross-build conditional')
    if 'MIT_KRB5_STATEDIR?=\t${VARBASE}' not in recipe_text:
        fail('Target client-keytab path must derive from the recipe VARBASE policy')

    configure_text = configure.read_text()
    start_marker = '# Check whether --with-krb5-config was given.'
    end_marker = 'if test "${PKCS11_MODNAME+set}" != set; then'
    start = configure_text.find(start_marker)
    end = configure_text.find(end_marker, start + 1)
    if start < 0 or end < 0 or configure_text.find(start_marker, start + 1) >= 0:
        fail('Could not isolate the generated upstream krb5-config default block')
    fragment = configure_text[start:end]
    work.mkdir()
    host_bin = work / 'host-bin'
    host_bin.mkdir()
    krb5_config = host_bin / 'krb5-config'
    krb5_config.write_text('''#!/bin/sh
case "$1" in
--help) printf '%s\n' 'Options: --defccname --defktname --defcktname' ;;
--defccname) printf '%s\n' 'API:host' ;;
--defktname) printf '%s\n' 'FILE:/build-host/etc/krb5.keytab' ;;
--defcktname) printf '%s\n' "$1" >> "$KRB5_CONFIG_CALLS"; printf '%s\n' "$HOST_CLIENT_KEYTAB" ;;
*) exit 2 ;;
esac
''')
    krb5_config.chmod(0o755)
    shell = Path('/bin/sh')
    if not shell.is_file():
        fail('POSIX shell is unavailable at /bin/sh')
    harness = work / 'configure-defaults.sh'
    harness_text = ('#!/bin/sh\nset -eu\nexec 5>/dev/null 6>/dev/null\n'
                    'as_me=./configure\nLINENO=15256\n'
                    'localstatedir=' + shlex.quote(str(target_statedir)) + '\n'
                    'prefix=/usr/pkg\nexec_prefix=\'${prefix}\'\n'
                    'ac_default_prefix=/usr/pkg\n' + fragment +
                    '\nprintf \'RESULT=%s\\n\' "$DEFCKTNAME"\n')
    harness.write_text(harness_text)
    cases = []
    target = 'FILE:' + str(target_statedir) + '/krb5/user/%{euid}/client.keytab'
    host = 'FILE:/build-host/pkgsrc/var/krb5/user/%{euid}/client.keytab'
    run_case(shell, harness, work, 'upstream-host-default', {}, host, cases, True)
    run_case(shell, harness, work, 'cross-explicit-target-default',
             {'DEFCKTNAME': target}, target, cases, False)
    run_case(shell, harness, work, 'upstream-localstatedir-fallback',
             {'with_krb5_config': 'no'}, target, cases, False)
    write_json(work / 'receipt.json', dict(
        sdk_source=sdk,
        source_configure_sha256=sha256_file(configure),
        source_configure_ac_sha256=sha256_file(configure_ac),
        recipe_sha256=sha256_file(recipe),
        tests=cases,
        target_statedir=str(target_statedir),
        scope='generated Autoconf default block only; no compiler or target binary ran'))
    print('PASS: cross build uses target client-keytab path; native upstream default is unchanged')


if __name__ == '__main__':
    main()
