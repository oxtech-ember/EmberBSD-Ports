#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), bundled nawk source-payload producer.
"""Regenerate source tables with explicitly selected tools; this is not SDK admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'byacc', 'cc', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--ccflags', required=True, help='Selected native GCC16 compiler and linker flags')
    cli.add_argument('--plan', action='store_true', help='Print argv only; do not run generators or write files')
    args = cli.parse_args()
    if not all(path.is_absolute() for path in (args.source, args.byacc, args.cc, args.work)):
        cli.error('Use absolute selected source, tool and work paths')
    if args.work.exists():
        cli.error('The work directory must be new')
    for tool in (args.byacc, args.cc):
        if not tool.is_file() or not os.access(tool, os.X_OK):
            cli.error('Missing selected tool: ' + str(tool))
    flags = shlex.split(args.ccflags)
    commands = [[str(args.byacc), '-d', '-b', 'awkgram', 'awkgram.y'],
                [str(args.cc), *flags, 'maketab.c', '-o', str(args.work / 'maketab')],
                [str(args.work / 'maketab'), 'awkgram.tab.h']]
    if args.plan:
        print(json.dumps(commands, indent=2))
        return
    args.work.mkdir()
    for name in ('home', 'tmp', 'cache', 'config', 'data'):
        (args.work / name).mkdir()
    env = dict(os.environ, HOME=str(args.work / 'home'), TMPDIR=str(args.work / 'tmp'), LC_ALL='C',
               CFFIXED_USER_HOME=str(args.work / 'home'), XDG_CACHE_HOME=str(args.work / 'cache'),
               XDG_CONFIG_HOME=str(args.work / 'config'), XDG_DATA_HOME=str(args.work / 'data'))
    inputs = ('awkgram.y', 'awk.h', 'proto.h', 'maketab.c')
    for name in inputs:
        shutil.copy2(args.source / name, args.work / name)
    record = dict(commands=commands, inputs={name: sha(args.source / name) for name in inputs}, tools={})
    for role, tool, version_flag in (('byacc', args.byacc, '-V'), ('cc', args.cc, '--version')):
        version = subprocess.run([str(tool), version_flag], env=env, cwd=args.work,
                                 check=True, capture_output=True, text=True)
        record['tools'][role] = dict(sha256=sha(tool), version=(version.stdout + version.stderr).splitlines()[0])
    major = subprocess.check_output([str(args.cc), '-dumpversion'], env=env, cwd=args.work, text=True).strip()
    if major.split('.')[0] != '16' or 'clang' in record['tools']['cc']['version'].lower():
        raise ValueError('Select the admitted native GCC16 producer')
    (args.work / 'record.json').write_text(json.dumps(record, indent=2) + '\n')
    for index, command in enumerate(commands):
        process = subprocess.run(command, cwd=args.work, env=env, capture_output=True)
        (args.work / ('command-' + str(index) + '.out')).write_bytes(process.stdout)
        (args.work / ('command-' + str(index) + '.err')).write_bytes(process.stderr)
        process.check_returncode()
        if index == 2:
            (args.work / 'proctab.c').write_bytes(process.stdout)
    record['outputs'] = {name: sha(args.work / name) for name in ('awkgram.tab.c', 'awkgram.tab.h', 'proctab.c')}
    (args.work / 'record.json').write_text(json.dumps(record, indent=2) + '\n')
    # This manifest contains no local paths. Keep exact argv in the private record.
    public = {key: record[key] for key in ('inputs', 'outputs')}
    public['tools'] = {}
    for role, tool in (('byacc', args.byacc), ('cc', args.cc)):
        value = record['tools'][role]
        public['tools'][role] = {**value, 'version': value['version'].replace(str(tool), tool.name)}
    (args.work / 'GENERATED.json').write_text(json.dumps(public, indent=2) + '\n')
    print('Generated source tables only. Review and copy outputs plus GENERATED.json into files/.')
    print('Retain record.json and diagnostics as private producer evidence.')


if __name__ == '__main__':
    main()
