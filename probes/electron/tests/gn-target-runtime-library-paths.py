#!/usr/bin/env python3
# Origin: EmberBSD contributors (AI-assisted); not submitted upstream.
"""Exercise final-link wrapper rpaths and GN propagation across private static deps."""
import argparse
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('source','gn','git','patch'):
    p.add_argument('--'+name, type=Path, required=True)
a = p.parse_args()
src, gn, git, patch = (getattr(a,k).resolve(strict=True) for k in ('source','gn','git','patch'))
files=('build/config/linux/pkg-config.py','build/config/linux/pkg_config.gni','build/toolchain/gcc_link_wrapper.py','build/toolchain/gcc_solink_wrapper.py','build/toolchain/wrapper_utils.py','build/toolchain/whole_archive.py','build/toolchain/gcc_toolchain.gni','build/toolchain/linux/unbundle/BUILD.gn')
with tempfile.TemporaryDirectory(prefix='target-runtime-link-') as tmp:
    root=Path(tmp); tree=root/'source'
    for path in files:
        dest=tree/path; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src/path,dest)
    subprocess.run([str(git),'apply','--check',str(patch)],cwd=tree,check=True)
    subprocess.run([str(git),'apply',str(patch)],cwd=tree,check=True)
    sysroot=root/'sys root'; (sysroot/'usr/pkg/lib/nss').mkdir(parents=True); (sysroot/'usr/pkg/lib/nspr').mkdir(parents=True)
    # GN's config and dependency semantics are real. The toolchain in this
    # fixture emits no real compiler actions and records the propagated inputs.
    (tree/'.gn').write_text('buildconfig = "//config.gn"\n')
    (tree/'config.gn').write_text('set_default_toolchain("//:tools")\n')
    (tree/'BUILD.gn').write_text('''config("private") {
  lib_dirs = [ "SYSROOT/usr/pkg/lib/nss", "SYSROOT/usr/pkg/lib/nspr", "SYSROOT/usr/pkg/lib" ]
  ldflags = [ "-Wl,-rpath=/private-not-propagated" ]
}
toolchain("tools") {
  tool("cc") { command = "unused {{source}} {{output}}" outputs = [ "{{source_out_dir}}/{{target_output_name}}.o" ] }
  tool("alink") { command = "unused {{output}}" outputs = [ "{{target_out_dir}}/{{target_output_name}}.a" ] }
  tool("link") { command = "unused {{output}}" outputs = [ "{{target_out_dir}}/{{target_output_name}}" ] }
  tool("solink") { command = "unused {{output}}" outputs = [ "{{target_out_dir}}/{{target_output_name}}.so" ] }
  tool("stamp") { command = "unused {{output}}" }
}
static_library("inner") { sources = [ "dummy.c" ] configs = [ ":private" ] }
executable("app") { deps = [ ":inner" ] }
shared_library("shared") { deps = [ ":inner" ] }
'''.replace('SYSROOT',str(sysroot)))
    (tree/'dummy.c').touch()
    out=tree/'out'; subprocess.run([str(gn),'gen',str(out)],cwd=tree,check=True)
    dirs=[]
    for target in ('app','shared'):
        r=subprocess.run([str(gn),'desc',str(out),'//:'+target,'--format=json'],cwd=tree,check=True,text=True,capture_output=True)
        obj=next(iter(json.loads(r.stdout).values())); paths=[path.rstrip('/') for path in obj.get('lib_dirs',[])]
        assert set(paths)=={str(sysroot/'usr/pkg/lib/nss'),str(sysroot/'usr/pkg/lib/nspr'),str(sysroot/'usr/pkg/lib')}, obj
        assert '-Wl,-rpath=/private-not-propagated' not in obj.get('ldflags',[])
        dirs.append(paths)
    record=root/'record.json'; fake=root/'fake-linker.py'
    fake.write_text('import json,os,sys\nopen(os.environ["RECORD"],"w").write(json.dumps(sys.argv[1:]))\n')
    rsp=root/'inner.rsp'; nested=root/'nested.rsp'
    rsp.write_text(shlex.quote('-L'+dirs[0][0])+' @nested.rsp -L '+shlex.quote(dirs[0][1]))
    nested.write_text(shlex.quote('-L'+dirs[0][2])+' '+shlex.quote('-L'+dirs[0][0])+' -Lrelative -L/outside')
    env=dict(os.environ,RECORD=str(record),PYTHONDONTWRITEBYTECODE='1')
    fake_toc = root/'fake-toc-tool'
    fake_toc.write_text('#!' + sys.executable + '\n' + 'import sys\nsys.exit(0)\n')
    fake_toc.chmod(0o755)
    for kind in ('link','solink'):
        wrapper=tree/'build/toolchain'/('gcc_'+kind+'_wrapper.py')
        opts=['--output',str(root/'out.so')]
        if kind=='solink': opts+=['--readelf',str(fake_toc),'--nm',str(fake_toc),'--tocfile',str(root/'out.toc')]
        cmd=[sys.executable,str(wrapper),*opts,'--',sys.executable,str(fake),'-Wl,-rpath=$ORIGIN','@'+str(rsp)]
        subprocess.run(cmd,cwd=root,env=env,check=True); old=json.loads(record.read_text())
        assert not any(x.startswith('-Wl,-rpath=/usr/pkg') for x in old)
        cmd[2:2]=['--runtime-sysroot',str(sysroot)]
        subprocess.run(cmd,cwd=root,env=env,check=True); final=json.loads(record.read_text())
        expected=['-Wl,-rpath=/usr/pkg/lib/nss','-Wl,-rpath=/usr/pkg/lib/nspr','-Wl,-rpath=/usr/pkg/lib']
        assert final[:len(old)]==old and set(final[len(old):])==set(expected) and len(final)==len(old)+3
        assert '@nested.rsp' in rsp.read_text() and nested.read_text().count('-L')==4
        cycle=root/'cycle.rsp'; cycle.write_text('@'+str(cycle))
        bad=[sys.executable,str(wrapper),*opts,'--runtime-sysroot',str(sysroot),'--',sys.executable,str(fake),'@'+str(cycle)]
        assert subprocess.run(bad,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode!=0
        for invalid in (['--runtime-sysroot','relative','--',sys.executable,str(fake)],
                        ['--runtime-sysroot',str(sysroot),'--',sys.executable,str(fake),'-L'],
                        ['--runtime-sysroot',str(sysroot),'--',sys.executable,str(fake),'-L'+str(sysroot/'usr/pkg/lib,bad')],
                        ['--runtime-sysroot',str(sysroot),'--',sys.executable,str(fake),'-L'+str(sysroot/'usr/pkg/lib:bad')]):
            bad=[sys.executable,str(wrapper),*opts,*invalid]
            assert subprocess.run(bad,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode!=0
    # Production wiring is part of the patch; fixture above does not emulate
    # all gcc_toolchain imports or claim Rust wrapper coverage.
    gni=(tree/'build/toolchain/gcc_toolchain.gni').read_text(); leaf=(tree/'build/toolchain/linux/unbundle/BUILD.gn').read_text()
    assert gni.count('$runtime_sysroot_switch -- $link_command')==3
    target,host=leaf.split('gcc_toolchain("host")',1)
    assert 'target_runtime_sysroot = emberbsd_target_sysroot' in target and 'target_runtime_sysroot' not in host
    # Exercise the actual unbundle leaf with a capture-only toolchain template.
    leaf_tree = root/'leaf'
    leaf_path = leaf_tree/'build/toolchain/linux/unbundle/BUILD.gn'
    leaf_path.parent.mkdir(parents=True)
    shutil.copyfile(tree/'build/toolchain/linux/unbundle/BUILD.gn', leaf_path)
    (leaf_tree/'build/toolchain/gcc_toolchain.gni').write_text('''template("gcc_toolchain") {
  value = ""
  if (defined(invoker.target_runtime_sysroot)) { value = invoker.target_runtime_sysroot }
  write_file("$root_build_dir/$target_name.sysroot", value)
  not_needed(invoker, "*")
  group(target_name) {}
}
''')
    (leaf_tree/'.gn').write_text('buildconfig = "//config.gn"\n')
    (leaf_tree/'config.gn').write_text('''declare_args() {
  fixture_os = "netbsd"
  emberbsd_pkg_config_role = "explicit"
  emberbsd_target_sysroot = ""
}
current_os = fixture_os
current_cpu = "x64"
host_os = "mac"
set_default_toolchain("//:fixture")
''')
    (leaf_tree/'BUILD.gn').write_text('''toolchain("fixture") { tool("stamp") { command = "unused" } }
group("all") { deps = [ "//build/toolchain/linux/unbundle:default", "//build/toolchain/linux/unbundle:host" ] }
''')
    leaf_env=dict(env, CC='/target/cc', CXX='/target/cxx', AR='/target/ar', NM='/target/nm', READELF='/target/readelf', BUILD_CC='/host/cc', BUILD_CXX='/host/cxx', BUILD_AR='/host/ar', BUILD_NM='/host/nm')
    for name, role, os_name, expected in [('explicit','explicit','netbsd',True), ('target','target','netbsd',True), ('native','native','netbsd',False), ('upstream','upstream','netbsd',False), ('linux','target','linux',False)]:
        output = leaf_tree/name
        flags='emberbsd_pkg_config_role = '+json.dumps(role)+' fixture_os = '+json.dumps(os_name)+' emberbsd_target_sysroot = '+json.dumps(str(sysroot))
        subprocess.run([str(gn),'gen',str(output),'--fail-on-unused-args','--args='+flags],cwd=leaf_tree,env=leaf_env,check=True)
        assert (output/'default.sysroot').read_text().strip() == (str(sysroot) if expected else '')
        assert (output/'host.sysroot').read_text().strip() == ''
print('PASS: GN private static deps propagate -L to final targets; both wrappers map response-file paths; defaults unchanged')
