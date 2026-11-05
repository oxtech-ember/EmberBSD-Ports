#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise PDFium's actual system GN branches for both roles and XFA states."""
import argparse,json,re,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('source','gn','patch-tool'):p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--host-prefix',type=Path);p.add_argument('--sysroot',type=Path)
a=p.parse_args()
if bool(a.host_prefix)!=bool(a.sysroot):p.error('select both host prefix and sysroot')
real=bool(a.host_prefix)
a.host_prefix=a.host_prefix.resolve(strict=True) if real else None
a.sysroot=a.sysroot.resolve(strict=True) if real else None;source=a.source.resolve(strict=True);tests=Path(__file__).resolve().parents[1]/'patches'
codec=(tests/'gn-common-codecs.patch').read_text().split('+++ b/build/config/emberbsd_codecs.gni\n',1)[1]
codec_gni=''.join(line[1:] for line in codec.splitlines(True)[1:] if line.startswith('+'))
def extract(text,needle,start=0):
 begin=text.index(needle,start);brace=text.index('{',begin);level=0
 for i in range(brace,len(text)):
  if text[i]=='{':level+=1
  elif text[i]=='}':
   level-=1
   if level==0:return text[begin:i+1]+'\n'
 raise ValueError('unterminated GN block')
with tempfile.TemporaryDirectory(prefix='pdfium-gn-') as temp:
 root=Path(temp).resolve()
 def put(path,text):
  p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
 name='third_party/pdfium/third_party/BUILD.gn';put(name,(source/name).read_text())
 subprocess.run([str(a.patch_tool),'-p1','-F0','-i',str(tests/'gn-common-pdfium.patch')],cwd=root,check=True,capture_output=True)
 actual=(root/name).read_text();parts=[extract(actual,'if (emberbsd_common_pdf) {')]
 for name in ('lcms2','libopenjpeg2'):
  parts += [extract(actual,'if (use_system_'+name+') {'),extract(actual,'group("'+name+'") {')]
 pos=actual.index('if (use_system_libtiff) {');start=actual.rfind('if (pdf_enable_xfa) {',0,pos)
 parts.append(extract(actual,'if (pdf_enable_xfa) {',start))
 put('third_party/pdfium/third_party/BUILD.gn','import("//build/config/linux/pkg_config.gni")\nimport("//build/config/emberbsd_pdf.gni")\n'+''.join(parts)+'\nif (!use_system_lcms2) { source_set("fx_lcms2") {} }\nif (!use_system_libopenjpeg2) { source_set("fx_libopenjpeg") {} }\n')
 put('build/config/emberbsd_codecs.gni',codec_gni)
 if real:
  for path in ('build/config/linux/pkg_config.gni','build/config/linux/pkg-config.py'):
   put(path,(source/path).read_text())
  put('build/config/compute_inputs_for_analyze.gni','compute_inputs_for_analyze=false\n')
  for path in ('build/config/gclient_args.gni','build/config/sysroot.gni','build/toolchain/rbe.gni'):put(path,'')
 else:
  put('build/config/linux/pkg_config.gni','''template("pkg_config") {
   not_needed(invoker, "*")
   config(target_name) {
     if (defined(invoker.defines)) { defines = invoker.defines }
     if (defined(invoker.ignore_libs) && invoker.ignore_libs) { include_dirs = [ "//selected-headers" ] } else { libs = [ "foreign" ] }
   }
 }
 ''')
 put('.gn','buildconfig="//config.gn"\n')
 put('BUILD.gn','toolchain("tc") { tool("stamp") { command="touch {{output}}" } }\nsource_set("test") { deps=["//third_party/pdfium/third_party:lcms2", "//third_party/pdfium/third_party:libopenjpeg2"] if (pdf_enable_xfa) { deps += ["//third_party/pdfium/third_party:tiff"] } }\n')
 for role in ('native','target','explicit'):
  for xfa in (False,True):
   config='set_default_toolchain("//:tc")\n'+f'emberbsd_pkg_config_role="{role}"\npdf_enable_xfa={str(xfa).lower()}\nuse_system_lcms2=true\nuse_system_libopenjpeg2=true\nuse_system_libtiff=true\n'
   if real:
    native=role=='native';values={'host_toolchain':'//:tc','emberbsd_native_pkg_config_prefix':str(a.host_prefix),'emberbsd_native_pkg_config_buildlink':False,'emberbsd_target_sysroot':str(a.sysroot),'current_os':'mac' if native else 'netbsd','current_cpu':'arm64' if native else 'x64','sysroot':'' if native else str(a.sysroot),'target_sysroot':'' if native else str(a.sysroot),'use_sysroot':False,'use_remoteexec':False,'build_with_chromium':False}
    config+=''.join(k+'='+json.dumps(v)+'\n' for k,v in values.items())
   put('config.gn',config)
   out=root/f'out-{role}-{xfa}';out.mkdir();selected='host' if role=='native' else 'target'
   args=['emberbsd_common_pdf=true']
   if real:
    args+=['pkg_config='+json.dumps(str(a.host_prefix/'bin/pkg-config')),'host_pkg_config='+json.dumps(str(a.host_prefix/'bin/pkg-config'))]
    libraries={'lcms2':'liblcms2','openjpeg':'libopenjp2','tiff':'libtiff'}
    for item_role,prefix,suffix in (('host',a.host_prefix,'.dylib'),('target',a.sysroot/'usr/pkg','.so')):
     for name,lib in libraries.items():
      selected_file=(prefix/'lib'/(lib+suffix)).resolve(strict=True)
      for kind in ('libraries','inputs'):args.append(f'emberbsd_{name}_{item_role}_{kind}='+json.dumps([str(selected_file)]))
   else:
    args += [f'emberbsd_{name}_{r}_{k}=["{root}/{r}/{name}-{k}"]' for name in ('lcms2','openjpeg','tiff') for r in ('host','target') for k in ('libraries','inputs')]
   (out/'args.gn').write_text('\n'.join(args)+'\n')
   result=subprocess.run([str(a.gn),'gen',str(out),'--fail-on-unused-args']+(['--script-executable='+__import__('sys').executable] if real else []),cwd=root,text=True,capture_output=True)
   if result.returncode:raise RuntimeError(result.stdout+result.stderr)
   data=json.loads(subprocess.check_output([str(a.gn),'desc',str(out),'//:test','--format=json']+(['--script-executable='+__import__('sys').executable] if real else []),cwd=root,text=True))['//:test']
   names=('lcms2','openjpeg','tiff') if xfa else ('lcms2','openjpeg')
   provider=a.host_prefix if role=='native' else a.sysroot/'usr/pkg' if real else None
   expected_libs={str((provider/'lib'/(libraries[n]+('.dylib' if role=='native' else '.so'))).resolve(strict=True)) for n in names} if real else {'//'+selected+'/'+n+'-libraries' for n in names}
   assert set(data['libs']) == expected_libs,data
   if real:assert all(str(provider/'include') in x for x in data['cflags_cc']),data
   else:assert '//selected-headers/' in data['include_dirs']
   assert set(data['defines']) >= {'USE_SYSTEM_LCMS2','USE_SYSTEM_LIBOPENJPEG2'}
   assert ('USE_SYSTEM_LIBTIFF' in data['defines']) == xfa
   for n in names:
    label='//third_party/pdfium/third_party:emberbsd_'+n
    info=json.loads(subprocess.check_output([str(a.gn),'desc',str(out),label,'--format=json']+(['--script-executable='+__import__('sys').executable] if real else []),cwd=root,text=True))[label]
    expected_file=str((provider/'lib'/(libraries[n]+('.dylib' if role=='native' else '.so'))).resolve(strict=True)) if real else None
    assert info['inputs']==([expected_file] if real else ['//'+selected+'/'+n+'-inputs'])
    assert info['libs']==([expected_file] if real else ['//'+selected+'/'+n+'-libraries'])
    expected='-Wl,-rpath,'+str(provider/'lib' if real else root/'host') if role=='native' else '-Wl,-rpath=/usr/pkg/lib'
    assert info['ldflags']==[expected],info
 # The default unselected path keeps PDFium's bundled target edges.
 bundled_config='set_default_toolchain("//:tc")\nemberbsd_pkg_config_role="target"\npdf_enable_xfa=false\nuse_system_lcms2=false\nuse_system_libopenjpeg2=false\nuse_system_libtiff=false\n'
 if real:bundled_config+=''.join(k+'='+json.dumps(v)+'\n' for k,v in values.items())
 put('config.gn',bundled_config)
 out=root/'out-bundled';out.mkdir()
 result=subprocess.run([str(a.gn),'gen',str(out),'--fail-on-unused-args'],cwd=root,text=True,capture_output=True)
 if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 for label,expected in (('lcms2','fx_lcms2'),('libopenjpeg2','fx_libopenjpeg')):
  deps=subprocess.check_output([str(a.gn),'desc',str(out),'//third_party/pdfium/third_party:'+label,'deps'],cwd=root,text=True)
  assert '//third_party/pdfium/third_party:'+expected in deps
print('PASS: PDFium GN role selection, inputs, runtime paths, XFA on/off and bundled default')
