#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Causal test for staged tool addition, removal, retry, and preservation."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--sdk-source', type=Path, required=True)
p.add_argument('--shell', type=Path, required=True)
a = p.parse_args()
helper = Path(__file__).resolve().parents[1] / 'stage-local-configure-preserve.py'

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve()
    work = root / 'work'
    source = work / 'src'
    source.mkdir(parents=True)
    recipe = root / 'recipe'
    recipe.mkdir()
    tools = work / '.tools' / 'bin'
    tools.mkdir(parents=True)
    (work / 'fail-once').write_text('yes')
    (work / 'use-tools').write_text('old autoconf\n')
    (work / 'phase-cache-tools').write_text('old autoconf\n')
    (work / '.tools_done').write_text('old\n')
    (work / '.configure_done').write_text('done\n')
    (tools / 'autoconf').write_text('missing\n')
    unchanged = tools / 'same'
    unchanged.write_text('same\n')
    (tools / 'alias').symlink_to('wrong')
    untouched = tools / 'untouched'
    untouched.write_text('same\n')
    obj = source / 'old.o'
    obj.write_text('object\n')
    before = (unchanged.stat().st_mtime_ns, untouched.stat().st_ino,
              untouched.stat().st_mtime_ns, obj.stat().st_ino, obj.stat().st_mtime_ns)
    (source / 'Makefile').write_text('CFLAGS=-O2\n')
    (source / 'config.h').write_text('old\n')
    (source / 'config.status').write_text(
        "printf '%s\\n' 'Configuration files:' ' Makefile' "
        "'Configuration headers:' ' config.h' 'Configuration commands:'\n")

    fake = root / 'bmake'
    fake.write_text('#!' + sys.executable + '\n' + '''import pathlib,sys
args=sys.argv[1:];work=pathlib.Path(''' + repr(str(work)) + ''');source=work/'src';live=work/'.tools';cookie=work/'.tools_done'
if '-V' in args:
 if any(x.startswith('TOOLS_DIR=') for x in args):
  scratch=next(x.split('=',1)[1] for x in args if x.startswith('TOOLS_DIR='))
  selected=next((x.split('=',1)[1].split() for x in args if x.startswith('USE_TOOLS=')),(work/'use-tools').read_text().split())
  groups=[]
  if 'autoconf' in selected:groups.append('autoconf|'+scratch+'/bin/autoconf|same,alias,untouched')
  if 'gmake' in selected:groups.append('gmake|'+scratch+'/bin/gmake|make')
  if 'bmake' in selected:groups.append('bmake|'+scratch+'/bin/bmake|make')
  print(' '.join(groups))
 else:print((work/'use-tools').read_text().strip()+'\\n'+str(work)+'\\n'+str(cookie))
 sys.exit()
if 'show-vars' in args:
 print(str(work)+'\\n'+str(source)+'\\n'+''' + repr(str(a.shell)) + '''+'\\n'+str(work/'.configure_done')+'\\nyes\\n'+str(source));sys.exit()
if 'post-tools' in args:sys.exit()
if 'tools-cookie' in args:
 selected=next((x.split('=',1)[1]+'\\n' for x in args if x.startswith('USE_TOOLS=')),(work/'phase-cache-tools').read_text())
 pathlib.Path(next(x.split('=',1)[1] for x in args if x.startswith('_COOKIE.tools='))).write_text(selected);sys.exit()
if 'configure-clean' in args:
 if (work/'fail-remove-cookie').exists():
  (work/'fail-remove-cookie').unlink();sys.exit(9)
 (work/'.configure_done').unlink(missing_ok=True);sys.exit()
if 'configure' in args:
 assert (live/'bin/autoconf').read_text()=='real\\n'
 (source/'config.h').write_text('#define NEW_MACRO 1\\n');(work/'.configure_done').write_text('done\\n');sys.exit()
for x in args:
 if '/bin/' in x and not x.startswith('TOOLS_DIR='):
  if not any(x.startswith('USE_TOOLS=') for x in args):sys.exit(8)
  f=pathlib.Path(x);f.parent.mkdir(parents=True,exist_ok=True)
  if f.parent==live/'bin' and f.name=='autoconf' and (work/'fail-once').exists():
   f.write_text('partial');(work/'fail-once').unlink();sys.exit(7)
  f.write_text('real\\n' if f.name in ('autoconf','gmake','bmake') else 'same\\n')
  if f.name=='autoconf':
   (f.parent/'same').write_text('same\\n');(f.parent/'untouched').write_text('same\\n')
   alias=f.parent/'alias';alias.unlink(missing_ok=True);alias.symlink_to('same')
  if f.name=='gmake':
   alias=f.parent/'make';alias.unlink(missing_ok=True);alias.symlink_to('gmake')
  if f.name=='bmake':
   alias=f.parent/'make';alias.unlink(missing_ok=True);alias.symlink_to('bmake')
''')
    fake.chmod(0o755)
    cmd = [sys.executable, '-B', str(helper), '--sdk-source', str(a.sdk_source),
           '--bmake', str(fake), '--recipe', str(recipe), '--expected-work', str(work)]

    first = subprocess.run(cmd, capture_output=True, text=True)
    assert first.returncode and (work / '.emberbsd-tools-refresh.json').is_file(), first.stdout + first.stderr
    subprocess.run(cmd + ['--make-arg', 'MAKE_JOBS=1'], check=True, text=True)
    assert not (work / '.emberbsd-tools-refresh.json').exists()
    assert (source / 'config.h').read_text() == '#define NEW_MACRO 1\n'
    assert (unchanged.stat().st_mtime_ns, untouched.stat().st_ino,
            untouched.stat().st_mtime_ns, obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    assert os.readlink(tools / 'alias') == 'same'
    assert (work / '.tools_done').read_text().split() == ['old', 'autoconf']
    output = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    assert 'Refreshed' not in output

    # A changed stale wrapper is not owned by the old factory and must survive.
    (work / '.tools_done').write_text('old autoconf gmake\n')
    (work / 'use-tools').write_text('autoconf bmake\n')
    (work / 'phase-cache-tools').write_text('old autoconf gmake\n')
    gmake = tools / 'gmake'
    gmake.write_text('real\n')
    (tools / 'make').symlink_to('gmake')
    gmake.write_text('locally changed\n')
    rejected = subprocess.run(cmd, capture_output=True, text=True)
    assert rejected.returncode and 'refusing to remove changed staged tool: gmake' in rejected.stderr, rejected.stdout + rejected.stderr
    assert not (work / '.emberbsd-tools-refresh.json').exists()
    assert gmake.read_text() == 'locally changed\n'

    gmake.write_text('real\n')
    (work / 'fail-remove-cookie').write_text('yes')
    interrupted = subprocess.run(cmd, capture_output=True, text=True)
    assert interrupted.returncode == 1 and (work / '.emberbsd-tools-refresh.json').is_file()
    assert not gmake.exists() and os.readlink(tools / 'make') == 'bmake'
    assert (work / '.tools_done').read_text().split() == ['old', 'autoconf', 'gmake']
    removed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    assert 'Refreshed staged pkgsrc tools' in removed.stdout
    assert not gmake.exists() and os.readlink(tools / 'make') == 'bmake'
    assert unchanged.stat().st_mtime_ns == before[0]
    assert untouched.stat().st_ino == before[1] and untouched.stat().st_mtime_ns == before[2]
    assert obj.stat().st_ino == before[3] and obj.stat().st_mtime_ns == before[4]
    assert (work / '.tools_done').read_text().split() == ['autoconf', 'bmake']
    output = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    assert 'Refreshed' not in output

print('PASS: tool addition/removal is journaled; changed stale files are refused; unchanged wrappers and objects survive; retries converge to a no-op')
