#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check selected TypeScript action invalidation with real GN and Ninja."""
from pathlib import Path
import argparse,os,shutil,subprocess,json,sys
p=argparse.ArgumentParser(description=__doc__)
for name in ("source", "work", "host-prefix"):
 p.add_argument("--"+name, type=Path, required=True)
a=p.parse_args()
assert all(x.is_absolute() for x in (a.source,a.work,a.host_prefix))
assert not a.work.exists() and not a.work.is_relative_to(a.source)
root=a.work;root.mkdir(parents=True);host=a.host_prefix;source=a.source/'third_party/devtools-frontend/src/scripts/build';wrapper=a.source/'third_party/node/run_selected_tsc.py'
for name in ('run_with_restat.py','response_file.py'):shutil.copy2(source/name,root/name)
shutil.copy2(wrapper,root/'run_selected_tsc.py')
(root/'.gn').write_text('buildconfig="//build/config.gn"\n');(root/'build').mkdir();(root/'build/config.gn').write_text('declare_args() { selected_version="1.0" }\nset_default_toolchain("//build:host")\n');(root/'build/BUILD.gn').write_text('toolchain("host") { tool("stamp") { command="touch {{output}}" } }\n')
(root/'compiler_version').write_text('1.0\n'); fake=root/'fake_tsc';fake.write_text('#!'+str(host/'bin/python3.15')+'\nimport pathlib,sys\np=pathlib.Path(__file__).with_name("compiler_version")\nv=p.read_text().strip()\nif sys.argv[1:]==["--version"]: print("Version "+v)\nelse:\n o=pathlib.Path(sys.argv[2]);o.parent.mkdir(parents=True,exist_ok=True);o.write_text(v+"\\n")\n');fake.chmod(0o755)
(root/'BUILD.gn').write_text('''foreach(name, [ "dts", "js" ]) {
 action(name) {
  script = "//run_with_restat.py"
  inputs = [ "//run_selected_tsc.py", "//fake_tsc" ]
  outputs = [ "$target_gen_dir/$name.txt" ]
  response_file_contents = rebase_path(outputs, root_build_dir) + [ "--", "'''+str(host/'bin/python3.15')+'''", rebase_path("//run_selected_tsc.py", root_build_dir), selected_version, rebase_path("//fake_tsc", root_build_dir), "--out", rebase_path(outputs[0], root_build_dir) ]
  args = [ "@{{response_file_name}}" ]
 }
}
''')
env=dict(os.environ,PATH=str(host/'bin')+':'+str(host/'sbin'));gn=host/'bin/gn';ninja=host/'bin/ninja';out=root/'out'
def run(cmd):return subprocess.run(list(map(str,cmd)),env=env,cwd=root,check=True,capture_output=True,text=True)
def gen(v):run([gn,'gen',out,'--root='+str(root),'--script-executable='+str(host/'bin/python3.15'),'--args=selected_version='+json.dumps(v)])
def build():return run([ninja,'-C',out,'dts','js']).stdout
gen('1.0');first=build();assert (out/'gen/dts.txt').read_text()=='1.0\n' and (out/'gen/js.txt').read_text()=='1.0\n';vfile=root/'compiler_version';vstat=vfile.stat();fstat=fake.stat();vfile.write_text('2.0\n');os.utime(vfile,ns=(vstat.st_atime_ns,vstat.st_mtime_ns));os.utime(fake,ns=(fstat.st_atime_ns,fstat.st_mtime_ns));gen('2.0');second=build();assert (out/'gen/dts.txt').read_text()=='2.0\n' and (out/'gen/js.txt').read_text()=='2.0\n';assert second.count('ACTION')==2,second
print('GN/Ninja dts and JS actions rebuild on changed version at same path and preserved mtime PASS')
