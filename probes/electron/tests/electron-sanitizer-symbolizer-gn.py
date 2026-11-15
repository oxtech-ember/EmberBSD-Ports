#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise combined base and sanitizer symbolizer data with real GN/Ninja."""
import argparse,json,subprocess,tempfile
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--gn',type=Path,required=True);parser.add_argument('--ninja',type=Path,required=True);parser.add_argument('--symbolizer',type=Path,required=True);parser.add_argument('--sanitizers-build-gn',type=Path,required=True);parser.add_argument('--base-build-gn',type=Path,required=True);args=parser.parse_args();san=args.sanitizers_build_gn.read_text();base=args.base_build_gn.read_text()
s1=san.index('      data += [ "//tools/valgrind/asan/" ]');s2=san.index('    }\n    if (is_asan',s1);fragment=san[s1:s2];s1=san.index('if (is_netbsd && using_sanitizer) {\n  copy(');s2=san.index('\nassert(!(is_win',s1);copy=san[s1:s2]
b1=base.index('  if (using_sanitizer && !is_fuchsia) {',base.index('trace_event/address_space_dump_provider.cc'));b2=base.index('\n\n  if (!is_debug)',b1);base_fragment=base[b1:b2]
with tempfile.TemporaryDirectory(prefix='electron-symbolizer-combined-') as d:
 root=Path(d);(root/'build/config/sanitizers').mkdir(parents=True);(root/'build/config/clang').mkdir(parents=True);(root/'base').mkdir();(root/'tools/valgrind/asan').mkdir(parents=True);(root/'.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n');target=str(args.symbolizer.resolve())
 config='''set_default_toolchain("//:toolchain")
host_toolchain = "//:toolchain"
using_sanitizer = true
is_fuchsia = false
is_netbsd = true
is_win = false
clang_base_path = "/forbidden-host"
declare_args() { emberbsd_target_llvm_symbolizer = '''+json.dumps(target)+''' }
''';(root/'BUILDCONFIG.gn').write_text(config)
 (root/'BUILD.gn').write_text('''toolchain("toolchain") {
 tool("stamp") { command = "touch {{output}}" }
 tool("copy") { command = "cp -p {{source}} {{output}}" }
}
group("test") { data_deps = [ "//base:base", "//build/config/sanitizers:deps" ] }
''')
 (root/'base/BUILD.gn').write_text('group("base") {\n data = []\n data_deps = []\n'+base_fragment+'\n}\n')
 (root/'build/config/sanitizers/BUILD.gn').write_text('group("deps") {\n data = []\n'+fragment+'}\n'+copy+'\n')
 (root/'build/config/clang/BUILD.gn').write_text('group("llvm-symbolizer_data") { data = [ "$clang_base_path/bin/llvm-symbolizer" ] }\n')
 def run(cmd):
  q=subprocess.run(cmd,cwd=root,text=True,capture_output=True)
  if q.returncode:raise RuntimeError(q.stdout+q.stderr)
  return q.stdout
 out=root/'out';gn=str(args.gn.absolute());ninja=str(args.ninja.absolute());run([gn,'gen',str(out)]);deps=run([gn,'desc',str(out),'//:test','runtime_deps','--format=json']);entries=next(iter(json.loads(deps).values()))['runtime_deps'];assert 'forbidden-host' not in deps and sum(x=='llvm-symbolizer' for x in entries)==1,entries
 result=run([ninja,'-C',str(out),'test']);assert result.count('[1/1]')==1 and '[2/' not in result,result;assert (out/'llvm-symbolizer').read_bytes()==Path(target).read_bytes()
 config=config.replace('is_netbsd = true','is_netbsd = false');(root/'BUILDCONFIG.gn').write_text(config);run([gn,'gen',str(out)]);other=run([gn,'desc',str(out),'//:test','runtime_deps','--format=json']);assert 'forbidden-host' in other,other
 print('PASS combined base+sanitizer GN runtime deps: one target COPY, no host; other platform unchanged')
