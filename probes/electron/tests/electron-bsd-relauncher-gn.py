#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise Electron's actual platform source selection with real GN."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True, help='unpatched Chromium src')
p.add_argument('--work', type=Path, required=True, help='new temporary directory')
p.add_argument('--gn', type=Path, required=True)
p.add_argument('--git', type=Path, default=Path('/usr/bin/git'))
a = p.parse_args()
assert a.source.is_absolute() and a.work.is_absolute() and not a.work.exists()
a.work.mkdir(parents=True)
patch = Path(__file__).resolve().parents[1] / 'patches/electron-bsd-desktop-guards.patch'
# Only the BUILD.gn hunk is needed; apply the entire actual patch to small copied inputs.
import re
for name in re.findall(r'^--- a/([^\n]+)', patch.read_text(), re.MULTILINE):
    dst = a.work/'src'/name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(a.source/name, dst)
subprocess.run([str(a.git), 'apply', '--check', str(patch)], cwd=a.work/'src', check=True)
subprocess.run([str(a.git), 'apply', str(patch)], cwd=a.work/'src', check=True)
text = (a.work/'src/electron/BUILD.gn').read_text()
start = text.index('  sources = filenames.lib_sources\n')
end = text.index('\n  if (electron_generate_js2c_code_cache)', start)
selection = text[start:end]
for os_name in ('linux', 'netbsd', 'mac'):
    root = a.work/os_name
    (root/'electron/shell/browser').mkdir(parents=True)
    for name in ('base.cc', 'linux.cc', 'mac.cc', 'views.cc', 'relauncher_linux.cc', 'relauncher_mac.cc'):
        (root/'electron/shell/browser'/name).write_text('')
    (root/'.gn').write_text('buildconfig="//BUILDCONFIG.gn"\n')
    (root/'BUILDCONFIG.gn').write_text('is_win=false\nis_posix=true\nis_linux='+str(os_name in ('linux','netbsd')).lower()+'\nis_netbsd='+str(os_name=='netbsd').lower()+'\nis_mac='+str(os_name=='mac').lower()+'\nset_default_toolchain("//:target")\n')
    (root/'BUILD.gn').write_text('group("all") { deps=["//electron:lib"] }\ntoolchain("target") { tool("stamp") { command="touch {{output}}" } tool("cxx") { command="true" outputs=["{{source_out_dir}}/{{source_name_part}}.o"] } }\n')
    files='''filenames = {
 lib_sources = [ "shell/browser/base.cc" ]
 lib_sources_posix = []
 lib_sources_linux = [ "shell/browser/linux.cc", "shell/browser/relauncher_linux.cc" ]
 lib_sources_mac = [ "shell/browser/mac.cc", "shell/browser/relauncher_mac.cc" ]
 lib_sources_views = [ "shell/browser/views.cc" ]
 lib_sources_win = []
}
'''
    (root/'electron/BUILD.gn').write_text(files+'source_set("lib") {\n'+selection+'\n}\n')
    def command(*args):
        r = subprocess.run([str(a.gn), *map(str,args)], cwd=root, text=True, capture_output=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return r.stdout
    command('gen', root/'out')
    result=json.loads(command('desc',root/'out','//electron:lib','--format=json'))['//electron:lib']['sources']
    linux='//electron/shell/browser/relauncher_linux.cc' in result
    mac='//electron/shell/browser/relauncher_mac.cc' in result
    assert (linux, mac)==({'linux':(True,False),'netbsd':(False,True),'mac':(False,True)}[os_name]), (os_name,result)
    (root/'sources.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: real GN selects exactly one expected relauncher on Linux, NetBSD and macOS')
