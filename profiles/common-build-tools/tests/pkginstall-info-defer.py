#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Run Bash's real generated install hooks without selected coreutils."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('package', 'tar', 'shell', 'install-script'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()

services = {
    'AWK': '/usr/bin/awk', 'BASENAME': '/usr/bin/basename', 'CAT': '/bin/cat',
    'CHGRP': '/usr/bin/chgrp', 'CHMOD': '/bin/chmod', 'CHOWN': '/usr/sbin/chown',
    'CMP': '/usr/bin/cmp', 'CP': '/bin/cp', 'DIRNAME': '/usr/bin/dirname',
    'ECHO': '/bin/echo', 'ECHO_N': '/bin/echo -n', 'EGREP': '/usr/bin/egrep',
    'EXPR': '/bin/expr', 'FALSE': '/usr/bin/false', 'FIND': '/usr/bin/find',
    'GREP': '/usr/bin/grep', 'HEAD': '/usr/bin/head', 'ID': '/usr/bin/id',
    'LN': '/bin/ln', 'LS': '/bin/ls', 'MKDIR': '/bin/mkdir -p', 'MV': '/bin/mv',
    'PWD_CMD': '/bin/pwd', 'RM': '/bin/rm', 'RMDIR': '/bin/rmdir',
    'SED': '/usr/bin/sed', 'SETENV': '/usr/bin/env', 'SORT': '/usr/bin/sort',
    'TEST': '/bin/test', 'TOUCH': '/usr/bin/touch', 'TR': '/usr/bin/tr',
    'TRUE': '/usr/bin/true', 'XARGS': '/usr/bin/xargs',
}

with tempfile.TemporaryDirectory(prefix='pkginstall-info-host-services-') as tmp:
    work = Path(tmp).resolve()
    package = Path(a.package).resolve(strict=True)
    members = subprocess.check_output([a.tar, '-tzf', str(package)], text=True).splitlines()
    raw = package
    if '+CONTENTS' not in members:
        nested = next((name for name in members if name.endswith('.tgz')), None)
        assert nested, 'signed package has no inner pkgsrc archive'
        raw = work / Path(nested).name
        with raw.open('wb') as output:
            subprocess.run([a.tar, '-xOzf', str(package), nested], stdout=output, check=True)
    contents = subprocess.check_output([a.tar, '-xOf', str(raw), '+CONTENTS'], text=True)
    script = Path(a.install_script).read_text()
    cwd = re.search(r'^@cwd\s+(\S+)\s*$', contents, re.MULTILINE)
    assert cwd and cwd.group(1).startswith('/'), 'package has no absolute @cwd'
    original_prefix = cwd.group(1)
    package_name = re.search(r'^@name\s+(\S+)\s*$', contents, re.MULTILINE)
    assert package_name, 'package has no @name'
    pkgname = package_name.group(1)
    assert original_prefix in script, 'generated hook does not match package @cwd'

    # Native Darwin hooks use known OS utilities; package tools remain selected.
    for role, command in services.items():
        assert f'{role}="{command}"' in script, (role, command)
    selected = {}
    for role in ('SH', 'INSTALL_INFO', 'PKG_ADMIN', 'PKG_INFO'):
        match = re.search(rf'^{role}="([^"\n]+)"$', script, re.MULTILINE)
        assert match and match.group(1).startswith('/'), role
        selected[role] = match.group(0)
    assert '# INFO:' in script

    prefix = work / 'prefix-without-coreutils'
    metadata = work / 'pkgdb' / pkgname
    script = script.replace(original_prefix, str(prefix))
    shell_path = selected['SH'].split('=', 1)[1].strip('"')
    relocated_shell = str(prefix) + shell_path.removeprefix(original_prefix)
    script = script.replace('#!' + relocated_shell, '#!' + shell_path)
    for role, assignment in selected.items():
        script = re.sub(rf'^{role}="[^"\n]*"$', lambda _: assignment,
                        script, count=1, flags=re.MULTILINE)

    index_dir = prefix / 'info-index' / 'nested'
    def contain_info_entries(source):
        def relocate(match):
            fields = match.group(1).split()
            assert fields, 'empty INFO_FILES entry'
            path = Path(fields[0])
            if not path.is_absolute():
                path = prefix / path
            assert path.is_relative_to(prefix), f'INFO file escapes fixture: {path}'
            return f'# INFO: {path} {index_dir}'
        result = re.sub(r'^# INFO: (.*)$', relocate, source, flags=re.MULTILINE)
        entries = [line[8:].split() for line in result.splitlines()
                   if line.startswith('# INFO: ')]
        assert entries, 'Bash package has no generated INFO_FILES entries'
        for fields in entries:
            assert Path(fields[0]).is_relative_to(prefix), 'INFO file escapes fixture'
            assert Path(fields[1]).is_relative_to(prefix), 'INFO index escapes fixture'
        return result, entries

    script, install_entries = contain_info_entries(script)
    info_path = Path(install_entries[0][0])

    info_path.parent.mkdir(parents=True)
    info_path.write_text('This is bash.info, produced by makeinfo.\n\x1f\n'
                         'File: bash.info, Node: Top, Next: Index, Up: (dir)\n\n'
                         'Bash\n****\n\n\x1f\nINFO-DIR-SECTION Shells\n'
                         'START-INFO-DIR-ENTRY\n* Bash: (bash).\n'
                         'END-INFO-DIR-ENTRY\n')
    metadata.mkdir(parents=True)
    hook = metadata / '+INSTALL'
    hook.write_text(script)
    env = dict(os.environ, PATH='/usr/bin:/bin:/usr/sbin:/sbin', LC_ALL='C',
               PKG_PREFIX=str(prefix), PKG_DBDIR=str(metadata.parent),
               PKG_REFCOUNT_DBDIR=str(work / 'pkgdb.refcount'),
               PKG_METADATA_DIR=str(metadata), PKG_REGISTER_SHELLS='NO')
    assert not (prefix / 'gnu' / 'bin').exists()
    for stage in ('PRE-INSTALL', 'POST-INSTALL'):
        result = subprocess.run([a.shell, str(hook), pkgname, stage], cwd=metadata,
                                env=env, text=True, capture_output=True)
        assert result.returncode == 0, (stage, result.stdout, result.stderr)
    info_hook = metadata / '+INFO_FILES'
    assert info_hook.is_file() and os.access(info_hook, os.X_OK), 'POST-INSTALL did not generate +INFO_FILES'
    assert info_hook.read_text().startswith('#!' + shell_path + '\n'), '+INFO_FILES did not retain selected SH'
    assert selected['INSTALL_INFO'] in info_hook.read_text(), '+INFO_FILES did not retain selected INSTALL_INFO'
    _, info_entries = contain_info_entries(info_hook.read_text())
    assert install_entries == info_entries, 'INSTALL and generated +INFO_FILES metadata differ'
    index = index_dir / 'dir'
    assert index.is_file() and '* Bash: (bash).' in index.read_text(), 'INFO_FILES did not register Bash'
    removed = subprocess.run([a.shell, str(info_hook), 'REMOVE', str(metadata)], cwd=metadata,
                             env=env, text=True, capture_output=True)
    assert removed.returncode == 0, (removed.stdout, removed.stderr)
    assert not index.exists() or '* Bash: (bash).' not in index.read_text(), 'INFO_FILES did not remove Bash'

print('PASS: Bash INFO_FILES install/removal uses host services without prefix coreutils')
