#!/usr/bin/env python3
# Origin: EmberBSD contributors (AI-assisted); not submitted upstream.
"""Exercise the actual GN pkg-config template with real target metadata."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'sysroot', 'gn', 'pkg-config', 'git', 'patch'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
source, sysroot, gn, pkgconf, git, patch = (getattr(a, n).resolve(strict=True) for n in ('source','sysroot','gn','pkg_config','git','patch'))
files = ('build/config/linux/pkg_config.gni', 'build/config/linux/pkg-config.py')
with tempfile.TemporaryDirectory(prefix='electron-pkg-rpath-') as tmp:
    root = Path(tmp)
    def make_tree(name, patched):
        tree = root/name
        for name in files:
            path = tree/name; path.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source/name, path)
        if patched:
            subprocess.run([str(git),'apply','--check',str(patch)],cwd=tree,check=True)
            subprocess.run([str(git),'apply',str(patch)],cwd=tree,check=True)
        for name in ('build/config/compute_inputs_for_analyze.gni','build/config/gclient_args.gni','build/config/sysroot.gni','build/toolchain/rbe.gni'):
            path=tree/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text('')
        (tree/'.gn').write_text('buildconfig = "//config.gn"\nscript_executable = '+json.dumps(sys.executable)+'\n')
        (tree/'config.gn').write_text('''declare_args() {
  emberbsd_pkg_config_role = "target"
  emberbsd_target_sysroot = ""
  emberbsd_native_pkg_config_prefix = ""
  emberbsd_native_pkg_config_buildlink = false
  sysroot = ""
  target_sysroot = ""
  use_sysroot = false
  use_remoteexec = false
  compute_inputs_for_analyze = false
  fixture_ignore = false
  fixture_native = false
}
host_os = "mac"
current_os = "netbsd"
if (fixture_native) { current_os = "mac" }
current_cpu = "x64"
host_toolchain = "//:host"
set_default_toolchain("//:fixture")
''')
        (tree/'BUILD.gn').write_text('''import("//build/config/linux/pkg_config.gni")
pkg_config("metadata") {
  packages = [ "nspr", "nss", "libuv" ]
  ignore_libs = fixture_ignore
}
toolchain("fixture") { tool("stamp") { command = "unused" } }
group("all") { public_configs = [ ":metadata" ] }
''')
        return tree
    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for key in ('PKG_CONFIG_PATH','PKG_CONFIG_LIBDIR','PKG_CONFIG_SYSROOT_DIR','PYTHONPATH','PYTHONHOME'): env.pop(key,None)
    output={}
    for name, fixed in [('old',False),('fixed',True)]:
        tree=make_tree(name,fixed)
        for ignore in (False,True):
            out=tree/('ignore' if ignore else 'normal')
            args=dict(emberbsd_target_sysroot=str(sysroot),pkg_config=str(pkgconf),fixture_ignore=ignore)
            args_text=' '.join(k+' = '+json.dumps(v) for k,v in args.items())
            subprocess.run([str(gn),'gen',str(out),'--fail-on-unused-args','--args='+args_text],cwd=tree,env=env,check=True)
            r=subprocess.run([str(gn),'desc',str(out),'//:metadata','--format=json'],cwd=tree,env=env,check=True,capture_output=True,text=True)
            output[(name,ignore)]=next(iter(json.loads(r.stdout).values()))
    old=output[('old',False)]; fixed=output[('fixed',False)]
    assert not old.get('ldflags'), old
    assert set(fixed['ldflags']) >= {'-Wl,-rpath=/usr/pkg/lib/nspr','-Wl,-rpath=/usr/pkg/lib/nss','-Wl,-rpath=/usr/pkg/lib'}, fixed
    assert all(x.startswith('-Wl,-rpath=/usr/') and str(sysroot) not in x and '/Volumes/' not in x for x in fixed['ldflags'])
    assert not output[('fixed',True)].get('ldflags') and not output[('fixed',True)].get('libs')
    assert fixed['libs']==old['libs'] and fixed['lib_dirs']==old['lib_dirs']
    for version in ('old', 'fixed'):
        tree = root/version
        out = tree/'native'
        args = dict(emberbsd_pkg_config_role='native', fixture_native=True,
                    emberbsd_native_pkg_config_prefix=str(sysroot/'usr/pkg'),
                    host_pkg_config=str(pkgconf))
        args_text = ' '.join(k+' = '+json.dumps(v) for k,v in args.items())
        subprocess.run([str(gn),'gen',str(out),'--fail-on-unused-args','--args='+args_text],cwd=tree,env=env,check=True)
        r=subprocess.run([str(gn),'desc',str(out),'//:metadata','--format=json'],cwd=tree,env=env,check=True,capture_output=True,text=True)
        output[(version,'native')]=next(iter(json.loads(r.stdout).values()))
    assert output[('old','native')]==output[('fixed','native')]
    assert not output[('fixed','native')].get('ldflags')
    script=root/'fixed'/files[1]
    def invoke(*argv):
        return subprocess.run([sys.executable,str(script),*map(str,argv)],env=env,text=True,capture_output=True)
    base=['-p',pkgconf,'--allow-cross-sysroot','-s',sysroot,'-a','x64','--system_libdir','pkg/lib']
    plain=invoke(*base,'nspr'); assert plain.returncode==0 and len(json.loads(plain.stdout))==4
    selected=invoke(*base,'--emberbsd-target-runtime-libdirs','nspr'); assert selected.returncode==0 and len(json.loads(selected.stdout))==5
    for extra in ([],['-s','relative'],['-s',sysroot,'--emberbsd-native-prefix','/tmp/native']):
        r=invoke('--emberbsd-target-runtime-libdirs',*extra,'nspr'); assert r.returncode != 0
    import runpy
    convert = runpy.run_path(str(script))['TargetRuntimeLibdirs']
    assert convert([str(sysroot/'usr/pkg/lib'),str(sysroot/'usr/pkg/lib')],str(sysroot)) == ['-Wl,-rpath=/usr/pkg/lib']
    for invalid in ('relative', str(sysroot), str(sysroot)+'-other/lib', str(sysroot)+'/usr/../lib', str(sysroot)+'/usr/pkg/lib:a', str(sysroot)+'/usr/pkg/lib,a', str(sysroot)+'/usr/pkg/lib\nother'):
        try: convert([invalid],str(sysroot))
        except ValueError: pass
        else: raise AssertionError('accepted invalid library directory: '+repr(invalid))
print('PASS: actual GN + real nspr/nss metadata; target rpaths, ignore_libs and four-field default')
