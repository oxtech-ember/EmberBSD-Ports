#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Compose real source, then test rootless tool tuples with explicit test tools.

Set EXPORT_TEST_GIT and EXPORT_TEST_PATCH for the existing source-test adapter.
Pass each member of the accepted make tuple with --make-arg. This test does
not admit tools or run a compiler. The caller owns input and work leases.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / 'profiles/development-toolchain/patches/pkgsrc-darwin-bootstrap-policy.patch'
RESTORE = '''# Ownership maps become commands after the tool paths are split.
# Keep all command forms complete in the explicit native bootstrap.
.if ${EMBERBSD_DARWIN_BOOTSTRAP:Uno} == "yes"
.  for _ember_ownership in chgrp chown
TOOLS_PATH.${_ember_ownership}= ${TOOLS_PLATFORM.${_ember_ownership}:[1]}
TOOLS_ARGS.${_ember_ownership}= ${TOOLS_PLATFORM.${_ember_ownership}:[2..-1]}
TOOLS_CMDLINE.${_ember_ownership}= ${TOOLS_PLATFORM.${_ember_ownership}}
TOOLS_${_TOOLS_VARNAME.${_ember_ownership}}= ${TOOLS_CMDLINE.${_ember_ownership}}
${_TOOLS_VARNAME.${_ember_ownership}}= ${TOOLS_CMDLINE.${_ember_ownership}}
.  endfor
.endif

'''


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def compose(work):
    require(work.is_absolute() and not work.exists() and not work.is_symlink() and
            not work.is_relative_to(ROOT) and not ROOT.is_relative_to(work), 'Use a new external absolute work root')
    require(not os.environ.get('FAKE_ARCHIVE'), 'Use the real pinned pkgsrc Git source')
    work.mkdir()
    path = ROOT / 'scripts/tests/export-fixture.py'
    spec = importlib.util.spec_from_file_location('rootless_source_adapter', path)
    adapter = importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), 'exec'), adapter.__dict__)
    selection, run = adapter.TestSelection(), adapter.test_runner
    exporter = adapter.load_exporter(ROOT)
    recipes, series, _, _ = exporter.configuration(ROOT)
    prefixes = ('mk', 'lang/gcc16', 'lang/gcc16-libs', 'lang/gcc16-libjit')
    require(not set(prefixes[1:]) & {name for name, _ in recipes}, 'Review a new GCC recipe overlay')
    pin = run([*selection.command('git'), '-C', str(ROOT), 'ls-files', '--stage', '--', 'upstream/pkgsrc'])
    require(len(pin.splitlines()) == 1 and pin.startswith(b'160000 '), 'Missing pkgsrc gitlink')
    revision = pin.split()[1].decode('ascii')
    require(run([*selection.command('git'), '-C', str(ROOT / 'upstream/pkgsrc'), 'rev-parse', 'HEAD']).strip()
            == revision.encode(), 'The checked-out pkgsrc revision differs')
    tree = work / 'source'
    archive = work / 'source.tar'
    run([*selection.command('git'), '-C', str(ROOT / 'upstream/pkgsrc'), 'archive', '--format=tar',
         '--output=' + str(archive), revision, *prefixes])
    tree.mkdir()
    exporter.extract_archive(archive, tree)
    applied = []
    for method, path, _, _ in series:
        if method == 'recipe-patch':
            continue
        require(method == 'patch', 'Review a new operation before the Darwin policy')
        chunks = []
        for section in re.split(r'(?m)(?=^--- )', path.read_text()):
            if not section.startswith('--- '):
                continue
            lines = section.splitlines()
            require(len(lines) > 1 and lines[1].startswith('+++ '), 'Malformed source patch section')
            names = [line.split()[1] for line in lines[:2] if line.split()[1] != '/dev/null']
            require(all(name.startswith(('a/', 'b/')) for name in names), 'Unexpected patch path')
            hits = [any(name[2:] == prefix or name[2:].startswith(prefix + '/') for prefix in prefixes) for name in names]
            require(not any(hits) or all(hits), 'A source section crosses the finite test tree')
            if hits and all(hits):
                chunks.append(section)
        if chunks:
            output = run([*selection.command('patch'), '-f', '-E', '-d', str(tree), '-p1', '-F', '0', '-V', 'none'],
                         input=''.join(chunks).encode())
            require(b'fuzz' not in output.lower(), 'Source composition used fuzz')
            (work / (f'{len(applied):02d}-' + path.stem + '.stdout')).write_bytes(output)
            applied.append(str(path.relative_to(ROOT)))
        if path == POLICY:
            break
    require(applied and applied[-1] == str(POLICY.relative_to(ROOT)) and not list(tree.rglob('*.rej')),
            'The actual ordered policy source did not compose')
    package = (tree / 'mk/bsd.pkg.mk').read_text()
    require(package.index('.include "tools/bsd.tools.mk"') <
            package.index('.include "unprivileged.mk"'), 'The real tool/unprivileged order changed')
    require('.include "replace.mk"' in (tree / 'mk/tools/bsd.tools.mk').read_text(),
            'The real tools module no longer includes replacement decisions')
    replacement = (tree / 'mk/unprivileged.mk').read_text()
    require(replacement.count(RESTORE) == 1, 'The late rootless-only restoration changed')
    old = work / 'old-unprivileged.mk'
    old.write_text(replacement.replace(RESTORE, '', 1))
    return tree, old, dict(pkgsrc_revision=revision, patches=applied,
        patch_options=['-f', '-E', '-p1', '-F', '0', '-V', 'none'])


def query(args, tree, replacement, unprivileged, work, env):
    fixture = work / ('query-' + replacement.stem + '-' + unprivileged + '.mk')
    lines = [f'.SHELL: name=sh path={args.shell} hasErrCtl=no check="set -e" ignore="set +e" echoFlag=v errFlag=e',
        'OPSYS=Darwin', 'NATIVE_OPSYS=Darwin', '_USE_DESTDIR=user-destdir', 'TOOLS_USE_CROSS_COMPILE=no',
        f'_PKGSRC_TOPDIR={tree}', 'PKGPATH=lang/gcc16',
        'USE_TOOLS=true',
        f'UNPRIVILEGED={unprivileged}', 'UNPRIVILEGED_USER=fixture-user',
        'UNPRIVILEGED_GROUP=fixture-group', 'UNPRIVILEGED_GROUPS=fixture-group',
        'EMBERBSD_DARWIN_BOOTSTRAP=yes', f'EMBERBSD_DARWIN_BUILTIN_SHELL={args.shell}',
        'EMBERBSD_DARWIN_NATIVE_TOOLS=chgrp chown',
        f'EMBERBSD_DARWIN_TOOL.chgrp={args.chgrp}', f'EMBERBSD_DARWIN_TOOL.chown={args.chown}',
        f'EMBERBSD_DARWIN_SH={args.shell}',
        f'.include "{tree}/mk/tools/tools.Darwin.mk"', f'.include "{tree}/mk/tools/defaults.mk"',
        'USE_TOOLS+=chgrp chown', f'.include "{tree}/mk/tools/replace.mk"', f'.include "{replacement}"']
    fixture.write_text('\n'.join(lines) + '\n')
    names = ['CHGRP', 'CHOWN', 'TOOLS_CHGRP', 'TOOLS_CHOWN', '_UNPRIVILEGED']
    names += [prefix + role for role in ('chgrp','chown') for prefix in
              ('TOOLS_PLATFORM.', 'TOOLS_PATH.', 'TOOLS_ARGS.', 'TOOLS_CMDLINE.', '_TOOLS_USE_PKGSRC.')]
    argv = [*args.make_arg, '-r', '-f', str(fixture)]
    for name in names:
        argv += ['-V', name + '=${' + name + '}']
    result = subprocess.run(argv, cwd=work, env=env, capture_output=True)
    stdout = fixture.with_suffix('.stdout')
    stderr = fixture.with_suffix('.stderr')
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    fixture.with_suffix('.result.json').write_text(json.dumps(dict(
        argv=argv, cwd=str(work), exit=result.returncode,
        stdout=str(stdout), stderr=str(stderr)), sort_keys=True, indent=2) + '\n')
    require(result.returncode == 0, 'The actual make query failed; see ' + str(stderr))
    rows = result.stdout.decode().splitlines()
    require(len(rows) == len(names) and all(row.startswith(name + '=') for name,row in zip(names,rows)),
            'The actual make query lost a named value')
    require(not result.stderr, 'The actual make query produced diagnostics: ' + result.stderr.decode())
    return {name: row[len(name)+1:] for name,row in zip(names,rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work', type=Path)
    parser.add_argument('--make-arg', action='append', required=True)
    parser.add_argument('--shell', required=True)
    parser.add_argument('--chown', required=True)
    parser.add_argument('--chgrp', required=True)
    args = parser.parse_args()
    require(all(os.path.isabs(path) and not any(c.isspace() for c in path)
                for path in (args.make_arg[0], args.shell, args.chown, args.chgrp)), 'Use explicit selected test paths')
    tree, old, composition = compose(args.work)
    empty = args.work / 'empty-bin'
    empty.mkdir()
    env = dict(PATH=str(empty), LC_ALL='C', TZ='UTC', SHELL=args.shell, TMPDIR=str(args.work))
    new = tree / 'mk/unprivileged.mk'
    rows = {(version, mode): query(args, tree, path, mode, args.work, env)
            for version,path in [('old',old), ('new',new)] for mode in ('yes','no')}
    helper = str(tree / 'mk/tools/emberbsd-darwin-builtin.sh')
    victim = args.work / 'victim'
    victim.write_bytes(b'unchanged source fixture\n')
    before = (victim.read_bytes(), victim.stat().st_mode, victim.stat().st_uid, victim.stat().st_gid)
    semantic = []
    for role, selected in [('chgrp',args.chgrp), ('chown',args.chown)]:
        name = role.upper()
        require(rows['old','yes'][name] == args.shell, 'The old route no longer has the causal lost tail')
        require(rows['old','yes']['TOOLS_'+name] == rows['old','yes']['TOOLS_CMDLINE.'+role] == args.shell and
                rows['old','yes']['_TOOLS_USE_PKGSRC.'+role] == 'no' and
                shlex.split(rows['old','yes']['TOOLS_PLATFORM.'+role]) == [args.shell,helper,'true',role],
                'The old route differs from the actual late platform override')
        require(shlex.split(rows['new','yes'][name]) == [args.shell,helper,'true',role] and
                rows['new','yes'][name] == rows['new','yes']['TOOLS_CMDLINE.'+role] ==
                rows['new','yes']['TOOLS_'+name], 'Incomplete rootless command')
        wrapper = rows['new','yes']['TOOLS_PATH.'+role] + ' ' + rows['new','yes']['TOOLS_ARGS.'+role]
        require(shlex.split(wrapper) == shlex.split(rows['new','yes'][name]),
                'The default tools wrapper lost the rootless command tail')
        require(rows['old','no'][name] == rows['new','no'][name] == selected, 'A privileged command changed')
        for version, command in [('old',rows['old','yes'][name]), ('new',rows['new','yes'][name]),
                                 ('new-wrapper',wrapper)]:
            result = subprocess.run([args.shell,'-c','${CMD} fixture-user victim'], cwd=args.work,
                env=dict(env,CMD=command), capture_output=True)
            require((result.returncode != 0 and result.stderr) if version == 'old' else
                    (result.returncode == 0 and not result.stdout and not result.stderr), 'Lost old/new semantic causality')
            semantic.append(dict(role=role, version=version, exit=result.returncode,
                stdout=result.stdout.decode(), stderr=result.stderr.decode()))
    require(before == (victim.read_bytes(),victim.stat().st_mode,victim.stat().st_uid,victim.stat().st_gid),
            'The rootless policy changed fixture ownership, mode or contents')
    report = dict(scope='Finite actual source composition and make/shell regression only; no tool qualification',
        composition=composition, values=[dict(version=version,unprivileged=mode,values=value)
            for (version,mode),value in rows.items()], semantics=semantic, fixture_unchanged=True)
    (args.work / 'result.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',result=str(args.work/'result.json'))))


if __name__ == '__main__':
    main()
