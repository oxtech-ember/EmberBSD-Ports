import json,subprocess,tempfile,shutil
from pathlib import Path
import argparse
parser=argparse.ArgumentParser()
for name in ('prefix','sysroot','target-cxx','patch-tool','source'):parser.add_argument('--'+name,type=Path,required=True)
a=parser.parse_args();p=a.prefix.resolve(strict=True);s=a.sysroot.resolve(strict=True);src=a.source.resolve(strict=True);t=str(a.target_cxx.resolve(strict=True))
owner=Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory(prefix='spirv-gn-link-') as td:
 r=Path(td)
 def put(n,v):f=r/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(v);return f
 patch=(owner/'probes/electron/patches/gn-common-codecs.patch').read_text().split('+++ b/build/config/emberbsd_codecs.gni\n',1)[1]
 put('build/config/emberbsd_codecs.gni',''.join(x[1:] for x in patch.splitlines(True)[1:] if x.startswith('+')))
 put('build/config/linux/pkg_config.gni','template("pkg_config") { not_needed(invoker,"*") config(target_name) {} }')
 put('.gn','buildconfig="//config.gn"\n');put('config.gn','set_default_toolchain("//:tc")\nemberbsd_pkg_config_role="target"\nis_mac=false\n')
 wrapper=r/'build/linux/unbundle/vulkan-SPIRV-Tools.gn';wrapper.parent.mkdir(parents=True);shutil.copy2(src/'build/linux/unbundle/vulkan-SPIRV-Tools.gn',wrapper)
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(owner/'probes/electron/patches/gn-common-spirv-tools.patch')],cwd=r,check=True,capture_output=True)
 put('third_party/spirv-tools/BUILD.gn',wrapper.read_text())
 put('probe.cc','#include <spirv-tools/linker.hpp>\nextern "C" int probe() { spvtools::Context c(SPV_ENV_UNIVERSAL_1_0); std::vector<std::vector<uint32_t>> i; std::vector<uint32_t> o; return spvtools::Link(c,i,&o); }\n')
 put('BUILD.gn',f'''toolchain("tc") {{
 tool("stamp") {{ command="touch {{{{output}}}}" }}
 tool("cxx") {{ command="{t} --sysroot={s} -fPIC -I{s}/usr/pkg/include -c {{{{source}}}} -o {{{{output}}}}" outputs=["{{{{source_out_dir}}}}/{{{{target_output_name}}}}.o"] }}
 tool("solink") {{ command="{t} --sysroot={s} -fuse-ld=lld -shared -Wl,--no-undefined {{{{ldflags}}}} -o {{{{output}}}} {{{{inputs}}}} {{{{libs}}}}" outputs=["{{{{root_out_dir}}}}/{{{{target_output_name}}}}{{{{output_extension}}}}"] default_output_extension=".so" output_prefix="lib" }}
}}
shared_library("test") {{ sources=["probe.cc"] deps=["//third_party/spirv-tools:spvtools", "//third_party/spirv-tools:spvtools_opt", "//third_party/spirv-tools:spvtools_link"] }}
''')
 lib=s/'usr/pkg/lib';opt=[lib/'libSPIRV-Tools-opt.a',lib/'libSPIRV-Tools.a'];link=[lib/'libSPIRV-Tools-link.a',*opt]
 for name,archives in [('opt',opt),('link',link)]:put(name+'-group.a','GROUP ( '+' '.join('"'+str(x)+'"' for x in archives)+' )\n')
 identity=put('identity','identity');header=put('header','header');table=put('core_tables_header.inc','table');out=r/'out';out.mkdir();args='emberbsd_common_spirv_tools=true\n'+f'emberbsd_spirv_source_identity="{identity}"\n'
 for role in ('host','target'):
  for name,libs in [('spirv_core',[lib/'libSPIRV-Tools.a']),('spirv_tools',[r/'opt-group.a']),('spirv_link',[r/'link-group.a'])]:
   args+=f'emberbsd_{name}_{role}_libraries=['+','.join('"'+str(x)+'"' for x in libs)+f']\nemberbsd_{name}_{role}_inputs=["{identity}"]\n'
  args+=f'emberbsd_spirv_tools_{role}_table="{table}"\nemberbsd_spirv_headers_{role}_inputs=["{header}"]\n'
 (out/'args.gn').write_text(args)
 subprocess.run([str(p/'bin/gn'),'gen',str(out),'--fail-on-unused-args'],cwd=r,check=True)
 process=subprocess.run([str(p/'bin/ninja'),'-C',str(out),'-v','test'],cwd=r,text=True,capture_output=True)
 print(process.stdout,process.stderr,'exit',process.returncode)
 if process.returncode:raise SystemExit(process.returncode)
