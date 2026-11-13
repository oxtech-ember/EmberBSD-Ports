#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise common cross-package PaX routing with the selected host tool."""
import argparse, importlib.util, os, shutil, struct, subprocess, sys, tempfile
from unittest.mock import patch
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--tool',type=Path,required=True); p.add_argument('--bmake',type=Path,required=True); p.add_argument('--pax-mk',type=Path,required=True); p.add_argument('--sdk-source',type=Path,required=True); p.add_argument('--adapter',type=Path,required=True); a=p.parse_args()
sys.path.insert(0,str(a.sdk_source/'src'))
from emberbsd_sdk.host_prefix import load_host_prefix
from emberbsd_sdk.errors import SDKError
with tempfile.TemporaryDirectory(prefix='pax-route-') as temp:
 root=Path(temp); prefix=root/'prefix'; (prefix/'bin').mkdir(parents=True)
 tool=prefix/'bin/paxctl'; shutil.copyfile(a.tool,tool); tool.chmod(0o755)
 selected=load_host_prefix(prefix,required_roles=('paxctl',))
 assert Path(selected.tool('paxctl')).resolve()==tool.resolve()
 # The dispatcher remains unchanged while the dependency is installed later.
 spec=importlib.util.spec_from_file_location('adapter',a.adapter); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 python=prefix/'bin/python3.15';shutil.copyfile(sys.executable,python);python.chmod(0o755)
 args=['--host-prefix',str(prefix),'--role','paxctl','--','+m','/fixture']
 tool.unlink()
 with patch.object(sys,'executable',str(python)):
  try: mod.exec_tool(args)
  except SDKError: pass
  else: raise AssertionError('missing deferred dependency accepted')
  shutil.copyfile(a.tool,tool);tool.chmod(0o755)
  with patch('os.execvpe',side_effect=SystemExit(47)) as invoke:
   try: mod.exec_tool(args)
   except SystemExit as error: assert error.code==47
   else: raise AssertionError('exec status not propagated')
   command,argv,env=invoke.call_args.args
   assert Path(command).resolve()==tool.resolve() and argv[1:]==['+m','/fixture']
   assert Path(env['PATH'].split(os.pathsep)[0]).resolve()==(prefix/'bin').resolve()
 tool.unlink(); tool.symlink_to(a.tool.resolve())
 try: load_host_prefix(prefix,required_roles=('paxctl',))
 except SDKError: pass
 else: raise AssertionError('outside prefix accepted')
 tool.unlink(); tool.write_bytes(b'\x7fELF\x02\x01\x01'+bytes(9)+struct.pack('<HHI',2,183,1)+bytes(40)); tool.chmod(0o755)
 try: load_host_prefix(prefix,required_roles=('paxctl',),host={'os':'Linux','cpu':'x86_64'})
 except SDKError: pass
 else: raise AssertionError('foreign CPU accepted')
 tool.unlink(); shutil.copyfile(a.tool,tool);tool.chmod(0o755)
 def fixture(path):
  e=bytearray(212); e[:16]=b'\x7fELF\x02\x01\x01'+bytes(9)
  struct.pack_into('<HHIQQQIHHHHHH',e,16,2,62,1,0,0,64,0,64,0,0,64,2,0)
  struct.pack_into('<IIQQQQIIQQ',e,128,0,7,0,0,192,20,0,0,4,0)
  struct.pack_into('<III4sI',e,192,4,4,3,b'PaX\0',0); path.write_bytes(e)
 for variable,expected,kind in (('NOT_PAX_MPROTECT_SAFE',2,'m'),('NOT_PAX_ASLR_SAFE',32,'a')):
  dest=root/kind; (dest/'usr/pkg/bin').mkdir(parents=True); elf=dest/'usr/pkg/bin/example';fixture(elf)
  make=root/('Makefile-'+kind); make.write_text(f'''OPSYS=NetBSD\nUSE_CROSS_COMPILE=yes\n{variable}=bin/example\nDESTDIR={dest}\nPREFIX=/usr/pkg\nRUN=\nFALSE=/usr/bin/false\nFAIL_MSG=echo\nSTEP_MSG=echo\n.include "{a.pax_mk}"\npost-install:\n''')
  dep=subprocess.run([str(a.bmake),'-r','-f',str(make),'-V','TOOL_DEPENDS'],check=True,capture_output=True,text=True)
  assert 'emberbsd-paxctl>=20261113:../../sysutils/emberbsd-paxctl' in dep.stdout
  cmd=[str(a.bmake),'-r','-f',str(make),'TOOLS_PLATFORM.paxctl='+str(tool),'post-install']
  subprocess.run(cmd,check=True,capture_output=True)
  assert struct.unpack_from('<I',elf.read_bytes(),208)[0]==expected
  subprocess.run(cmd,check=True,capture_output=True)
  assert struct.unpack_from('<I',elf.read_bytes(),208)[0]==expected
  fixture(elf)
  missing=subprocess.run([str(a.bmake),'-r','-f',str(make),'TOOLS_PLATFORM.paxctl=','post-install'],capture_output=True)
  assert missing.returncode and struct.unpack_from('<I',elf.read_bytes(),208)[0]==0
  host=subprocess.run([str(a.bmake),'-r','-f',str(make),'OPSYS=Darwin','TOOLS_PLATFORM.paxctl='+str(tool),'post-install'],capture_output=True)
  assert host.returncode==0 and struct.unpack_from('<I',elf.read_bytes(),208)[0]==0
  hostdep=subprocess.run([str(a.bmake),'-r','-f',str(make),'OPSYS=Darwin','-V','TOOL_DEPENDS'],check=True,capture_output=True,text=True)
  assert 'emberbsd-paxctl' not in hostdep.stdout
  native_dep=subprocess.run([str(a.bmake),'-r','-f',str(make),'USE_CROSS_COMPILE=no','_EMBER_SDK_PAXCTL_SELECTED=yes','-V','TOOL_DEPENDS'],check=True,capture_output=True,text=True)
  assert 'emberbsd-paxctl>=20261113:../../sysutils/emberbsd-paxctl' in native_dep.stdout
  native_missing=subprocess.run([str(a.bmake),'-r','-f',str(make),'USE_CROSS_COMPILE=no','_EMBER_SDK_PAXCTL_SELECTED=yes','TOOLS_PLATFORM.paxctl=','post-install'],capture_output=True)
  assert native_missing.returncode
  subprocess.run([str(a.bmake),'-r','-f',str(make),'USE_CROSS_COMPILE=no','TOOLS_PLATFORM.paxctl='+str(tool),'post-install'],check=True,capture_output=True)
  assert struct.unpack_from('<I',elf.read_bytes(),208)[0]==expected
 # The OS host tool handles both ELF widths and byte orders, independent of host CPU.
 for bits in (32,64):
  for endian in ('<','>'):
   ehsize,shsize=(52,40) if bits==32 else (64,64)
   note=ehsize+2*shsize
   data=bytearray(note+20);data[:16]=b'\x7fELF'+bytes((1 if bits==32 else 2,1 if endian=='<' else 2,1))+bytes(9)
   if bits==32:
    struct.pack_into(endian+'HHIIIIIHHHHHH',data,16,2,3,1,0,0,ehsize,0,ehsize,0,0,shsize,2,0)
    struct.pack_into(endian+'IIIIIIIIII',data,ehsize+shsize,0,7,0,0,note,20,0,0,4,0)
   else:
    struct.pack_into(endian+'HHIQQQIHHHHHH',data,16,2,62,1,0,0,ehsize,0,ehsize,0,0,shsize,2,0)
    struct.pack_into(endian+'IIQQQQIIQQ',data,ehsize+shsize,0,7,0,0,note,20,0,0,4,0)
   struct.pack_into(endian+'III4sI',data,note,4,4,3,b'PaX\0',16)
   target=root/f'elf-{bits}-{ord(endian)}';target.write_bytes(data)
   subprocess.run([str(tool),'+m',str(target)],check=True,capture_output=True)
   assert struct.unpack_from(endian+'I',target.read_bytes(),note+16)[0]==18
 broken=root/'invalid';broken.write_bytes(b'not an ELF');before=broken.read_bytes()
 assert subprocess.run([str(tool),'+m',str(broken)],capture_output=True).returncode
 assert broken.read_bytes()==before
 print('PASS: both cross PaX declarations, ELF32/64 and byte order, flag preservation, idempotence, missing tool, selected prefix and CPU rejection')
