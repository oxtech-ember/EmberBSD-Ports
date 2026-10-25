#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Query the common selector only. No package target or selected tool is run."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('metadata_fixture', Path(__file__).with_name('gzip-source.py'))
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('metadata-selection', 'tool-records', 'pkgsrc', 'sysroot'):
        cli.add_argument('--' + name, type=Path, required=True)
    args = cli.parse_args()
    for p in (args.metadata_selection, args.tool_records, args.pkgsrc, args.sysroot):
        if not p.is_absolute() or not p.exists():
            cli.error('Select existing absolute fixture inputs.')
    selection = json.loads(args.metadata_selection.read_text())
    # The existing source-only fixture contract checks the complete five-word tuple.
    make, env, work, record = fixture.metadata_inputs(selection, args.pkgsrc)
    roles = json.loads(args.tool_records.read_text())
    assert set(roles) == {'AR', 'RANLIB', 'NM', 'STRIP', 'LD'}
    for row in roles.values():
        assert set(row) == {'path', 'sha256'}
        p = Path(row['path'])
        assert p.is_absolute() and p.is_file() and os.access(p, os.X_OK) and digest(p) == row['sha256']
    assert args.sysroot.is_dir()
    # Incomplete and relative selections must fail before any native child.
    for mode in ('incomplete', 'relative'):
        bad = copy.deepcopy(selection)
        if mode == 'incomplete':
            bad['make'].pop(1)
        else:
            bad['make'][0] = 'bmake'
        with patch('subprocess.Popen', side_effect=AssertionError('no child')):
            try:
                fixture.metadata_inputs(bad, args.pkgsrc)
            except ValueError:
                pass
            else:
                raise AssertionError('Invalid metadata route was accepted.')
    queries = []
    absent = work / 'absent'
    nonexec = work / 'nonexec'
    nonexec.write_text('Non-executable selector control.\n')

    def query(label, host='Darwin', cross='no', phase='initial', optional=None, wrappers='yes'):
        shell, mk = make[3].removeprefix('SHELL='), make[2]
        lines = [f'.if "${{.SHELL}}" != "{shell}" || "${{SHELL}}" != "{shell}"',
            '.error source fixture shell differs', '.endif',
            f'.if "${{.SYSPATH}}" != "{mk}"', '.error source fixture rules differ', '.endif',
            '_INITIAL_SHELL != print -r -- "$${KSH_VERSION-}"',
            '.if empty(_INITIAL_SHELL:M*MIRBSD*)', '.error parse-time shell differs', '.endif',
            'OPSYS= ' + host, 'USE_CROSS_COMPILE= ' + cross, '_USE_CWRAPPERS= ' + wrappers,
            'WRAPPER_BINDIR= ' + str(work / 'generated-wrappers')]
        lines += ['PKG_' + name + '= ' + row['path'] for name, row in roles.items()]
        if phase is not None:
            lines.append('EMBERBSD_DARWIN_TOOL_PHASE= ' + phase)
        lines.append('OSX_SDK_PATH= ' + str(args.sysroot))
        lines += [key + '= ' + value for key, value in (optional or {}).items()]
        lines.append('.include "' + str(ROOT / 'profiles/common-build-tools/cmake-binutils.mk') + '"')
        fragment = work / (label + '.mk')
        fragment.write_text('\n'.join(lines) + '\n')
        argv = [*make, '-f', str(fragment), '-v', '_EMBERBSD_CMAKE_BINUTILS_ARGS', '-v', 'PKG_FAIL_REASON']
        result = subprocess.run(argv, cwd=work, env=env, text=True, capture_output=True, timeout=30)
        queries.append(dict(case=label, argv=argv, cwd=str(work), environment=env,
            fragment=dict(path=str(fragment), sha256=digest(fragment)), actual_exit=result.returncode,
            stdout=result.stdout, stderr=result.stderr))
        assert result.returncode == 0, queries[-1]
        text = result.stdout.splitlines()
        return shlex.split(text[0]), '\n'.join(text[1:])

    argv, reason = query('initial-absent')
    assert not reason.strip(), reason
    assert '-DEMBERBSD_DARWIN_TOOL_PHASE:STRING=initial' in argv
    assert not any(value.startswith(('-DCMAKE_TAPI:', '-DCMAKE_INSTALL_NAME_TOOL:', '-DCMAKE_LIBTOOL:')) for value in argv)
    _, reason = query('default-full', phase=None)
    assert 'EMBERBSD_DARWIN_INSTALL_NAME_TOOL' in reason and 'EMBERBSD_DARWIN_TAPI' in reason
    for name in ('INSTALL_NAME_TOOL', 'TAPI'):
        for label, value in [('relative', 'relative'), ('missing-file', str(absent)),
                             ('nonexec', str(nonexec)), ('directory', str(work))]:
            _, reason = query(name + '-' + label, optional={'EMBERBSD_DARWIN_' + name: value})
            assert 'EMBERBSD_DARWIN_' + name in reason
    _, reason = query('unknown-phase', phase='unknown')
    assert 'EMBERBSD_DARWIN_TOOL_PHASE' in reason
    for host, cross in [('Linux', 'no'), ('NetBSD', 'no'), ('Darwin', 'yes')]:
        argv, reason = query(host + '-' + cross, host, cross)
        assert not reason.strip(), reason
        assert not any(value.startswith(('-DEMBERBSD_DARWIN_TOOL_PHASE:', '-DCMAKE_TAPI:', '-DCMAKE_INSTALL_NAME_TOOL:', '-DCMAKE_OSX_SYSROOT:')) for value in argv)
    query('initial-legacy', wrappers='no')
    with record.open('x') as stream:
        json.dump(dict(status='PASS_SOURCE_METADATA_ONLY', queries=queries, refused_routes=2,
            metadata_selection=dict(path=str(args.metadata_selection), sha256=digest(args.metadata_selection)),
            tool_records=dict(path=str(args.tool_records), sha256=digest(args.tool_records)),
            make_inputs=[dict(path=str(p), sha256=digest(p)) for p in
                [Path(make[0]), Path(make[3].removeprefix('SHELL=')), Path(make[2]) / 'sys.mk', Path(env['MAKECONF'])]],
            ordinary_provider_qualified=False, compiler_executed=False, cmake_executed=False), stream, indent=2)
        stream.write('\n')
    print('PASS:', len(queries), 'source metadata queries; two route refusals; no package target.')


if __name__ == '__main__':
    main()
