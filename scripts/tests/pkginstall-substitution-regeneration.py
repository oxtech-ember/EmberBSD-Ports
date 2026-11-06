#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

p = argparse.ArgumentParser()
for name in ('original', 'candidate', 'templates', 'make', 'sed', 'chmod', 'shell', 'tools', 'work'):
    p.add_argument('--' + name, required=True, type=Path)
args = p.parse_args()
if any(not x.is_absolute() for x in (args.original, args.candidate, args.templates, args.make, args.sed, args.chmod, args.shell, args.tools, args.work)):
    p.error('all paths must be absolute')
if any(not x.is_file() for x in (args.original, args.candidate, args.make, args.sed, args.chmod, args.shell)):
    p.error('selected make, sed, chmod, shell and source files must exist')
if not args.templates.is_dir() or not args.tools.is_dir():
    p.error('template and selected tool directories must exist')
if args.work.exists() and any(args.work.iterdir()):
    p.error('work directory must be empty')
env = dict(os.environ)
env['PATH'] = str(args.tools)
def run(cmd, cwd):
    return subprocess.run([str(x) for x in cmd], cwd=cwd, env=env, text=True,
                          capture_output=True, check=True, timeout=30)
def extract(text, start, end):
    start_at = text.index(start)
    return text[start_at:text.index(end, start_at)]
for label, source in (('old', args.original), ('new', args.candidate)):
    root = args.work / label
    pkg = root / 'pkgsrc/security/test'
    mk = root / 'pkgsrc/mk/pkginstall'
    pkg.mkdir(parents=True, exist_ok=True)
    mk.mkdir(parents=True, exist_ok=True)
    for name in ('files', 'dirs', 'header'):
        shutil.copyfile(args.templates / name, mk / name)
    config = mk / 'bsd.pkginstall.mk'
    config.write_text('HOOK_CAT=/old/tool/cat\n')
    (pkg / 'files-data').write_text('# FILE: etc/a c share/a\n')
    (pkg / 'dirs-data').write_text('# DIR: var/a m\n')
    text = source.read_text()
    fragments = []
    sections = [
        ('${_INSTALL_FILES_FILE}: ${_INSTALL_FILES_DATAFILE}', '\n# OWN_DIRS'),
        ('${_INSTALL_DIRS_FILE}: ${_INSTALL_DIRS_DATAFILE}', '\n# INFO_DIR'),
        ('${_DEINSTALL_FILE_DFLT}: ${_DEINSTALL_TEMPLATES_DFLT}', '\n# rc.d scripts'),
    ]
    for start, end in sections:
        if label == 'new':
            at = text.index(start)
            line = text.rfind('\n', 0, at)
            before = text.rfind('\n', 0, line)
            if 'bsd.pkginstall.mk' in text[before + 1:line]:
                start = text[before + 1:line] + '\n' + start
        fragments.append(extract(text, start, end))
    rc_start='${RCD_SCRIPT_WRK.${_script_}}: ${RCD_SCRIPT_SRC.${_script_}}'
    if label == 'new':
        rc_start='${RCD_SCRIPT_WRK.${_script_}}: ../../mk/pkginstall/bsd.pkginstall.mk\n'+rc_start
    rc = extract(text, rc_start, '\ninstall-rcd-')
    makefile = f'''SHELL={args.shell}
.SHELL: name=sh path={args.shell}
SH={args.shell}
SED={args.sed}
RUN=
TEST=test
MKDIR=mkdir -p
TOUCH=touch
CHMOD={args.chmod}
MV=mv
ECHO=echo
.include "../../mk/pkginstall/bsd.pkginstall.mk"
FILES_SUBST_SED= -e s!@CAT@!${{HOOK_CAT}}!g
_PKGINSTALL_DIR=generated
_INSTALL_FILES_DATAFILE=files-data
_INSTALL_DIRS_DATAFILE=dirs-data
_INSTALL_FILES_FILE=generated/files
_INSTALL_DIRS_FILE=generated/dirs
_INSTALL_FILE=generated/INSTALL
_DEINSTALL_FILE=generated/DEINSTALL
_INSTALL_FILE_DFLT=generated/INSTALL.default
_DEINSTALL_FILE_DFLT=generated/DEINSTALL.default
_INSTALL_TEMPLATES_DFLT=../../mk/pkginstall/header
_DEINSTALL_TEMPLATES_DFLT=../../mk/pkginstall/header
INSTALL_SRC=../../mk/pkginstall/header generated/files generated/dirs
DEINSTALL_SRC=../../mk/pkginstall/header generated/files generated/dirs
RCD_SCRIPT_WRK.demo=generated/rc-demo
RCD_SCRIPT_SRC.demo=../../mk/pkginstall/header
all: ${{_INSTALL_FILE}} ${{_DEINSTALL_FILE}} ${{_INSTALL_FILE_DFLT}} ${{_DEINSTALL_FILE_DFLT}} generated/rc-demo
'''+''.join(fragments)+'\n.for _script_ in demo\n'+rc+'\n.endfor\n'
    (pkg / 'Makefile').write_text(makefile)
    run([args.make,'-f','Makefile','all'],pkg)
    install = pkg / 'generated/INSTALL'
    assert 'CAT="/old/tool/cat"' in install.read_text(),label
    time.sleep(1.1)
    config.write_text('HOOK_CAT=/new/tool/cat\n')
    run([args.make,'-f','Makefile','all'],pkg)
    after = install.read_text()
    if label == 'old':
        assert 'CAT="/old/tool/cat"' in after, 'old did not reproduce'
    else:
        assert 'CAT="/new/tool/cat"' in after,'fixed output not updated'
        assert 'HOOK_CAT=/new' not in after,'dependency leaked into output'
        rc_out = pkg / 'generated/rc-demo'
        assert 'CAT="/new/tool/cat"' in rc_out.read_text(), 'rc.d output not updated'
        assert 'HOOK_CAT=/new' not in rc_out.read_text(), 'dependency leaked into rc.d'
        outputs=[pkg/'generated'/n for n in ('files','dirs','INSTALL','DEINSTALL','INSTALL.default','DEINSTALL.default','rc-demo')]
        before = [x.stat().st_mtime_ns for x in outputs]
        run([args.make,'-f','Makefile','all'],pkg)
        assert before==[x.stat().st_mtime_ns for x in outputs], 'no-op regenerated'
        run([args.make,'-f','Makefile','INSTALL_SRC=','DEINSTALL_SRC=',
       '_INSTALL_FILE=empty/INSTALL','_DEINSTALL_FILE=empty/DEINSTALL','all'],pkg)
        for name in ('INSTALL','DEINSTALL'):
            content=(pkg/'empty'/name).read_text()
            assert content == '#!'+str(args.shell)+'\nexit 0\n', ('bad empty hook',name,content)
    print('PASS', label)
