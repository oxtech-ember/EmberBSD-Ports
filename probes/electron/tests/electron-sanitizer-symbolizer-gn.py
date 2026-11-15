import argparse,json,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--gn',type=Path,required=True);p.add_argument('--ninja',type=Path,required=True);p.add_argument('--symbolizer',type=Path,required=True);p.add_argument('--build-gn',type=Path,required=True);args=p.parse_args();source=args.build_gn.read_text(); start=source.index('      data += [ "//tools/valgrind/asan/" ]');end=source.index('    }\n    if (is_asan',start); fragment=source[start:end];start=source.index('if (is_netbsd && using_sanitizer) {\n  copy(');end=source.index('\nassert(!(is_win',start);copy_block=source[start:end]
with tempfile.TemporaryDirectory(prefix='electron-symbolizer-gn-') as d:
 root=Path(d);(root/'tools/valgrind/asan').mkdir(parents=True);(root/'.gn').write_text('buildconfig = "//BUILDCONFIG.gn"\n');(root/'BUILDCONFIG.gn').write_text('set_default_toolchain("//:toolchain")\n');target=str(args.symbolizer.resolve())
 text='''is_netbsd = true
using_sanitizer = true
clang_base_path = "/forbidden-host"
is_win = false
not_needed([ "is_win", "clang_base_path", "using_sanitizer" ])
declare_args() { emberbsd_target_llvm_symbolizer = '''+json.dumps(target)+''' }
toolchain("toolchain") {
  tool("stamp") { command = "touch {{output}}" }
  tool("copy") { command = "cp -p {{source}} {{output}}" }
}
group("deps") {
  data = []
'''+fragment+'''}
'''+copy_block
 (root/'BUILD.gn').write_text(text);out=root/'out';gn=str(args.gn.absolute());ninja=str(args.ninja.absolute())
 def run(cmd):
  r=subprocess.run(cmd,cwd=root,text=True,capture_output=True)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
  return r.stdout
 run([gn,'gen',str(out)]);deps=run([gn,'desc',str(out),'//:deps','runtime_deps','--format=json']);obj=json.loads(deps);assert 'forbidden-host' not in deps and 'llvm-symbolizer' in deps,deps
 run([ninja,'-C',str(out),'deps']);actual=out/'llvm-symbolizer';assert actual.is_file() and actual.read_bytes()==Path(target).read_bytes() and actual.stat().st_mode&0o111
 # The non-NetBSD sanitizer continues to advertise its native host tool.
 (root/'BUILD.gn').write_text(text.replace('is_netbsd = true', 'is_netbsd = false'))
 run([gn,'gen',str(out)]);other=run([gn,'desc',str(out),'//:deps','runtime_deps','--format=json'])
 assert 'forbidden-host' in other and 'llvm-symbolizer' in other,other
 print('PASS NetBSD target symbolizer copy and unchanged non-NetBSD host tool path')
