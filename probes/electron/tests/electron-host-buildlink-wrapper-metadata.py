#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check package-bound additive wrapper fields and reject foreign metadata."""
import hashlib,importlib.util,tempfile
from pathlib import Path
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/host-buildlink.py'
spec=importlib.util.spec_from_file_location('host',owner);host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
with tempfile.TemporaryDirectory(prefix='wrapper-metadata-') as td:
 root=Path(td).resolve();prefix=root/'prefix';prefix.mkdir();old=root/'old';new=root/'new'
 files={'libX11':('FIND_FILES_libX11','lib/pkgconfig/x11.pc'),
        'libxcb':('FIND_FILES_libxcb','lib/pkgconfig/xcb.pc'),
        'xcb-proto':('FIND_FILES_xcb-proto','share/pkgconfig/xcb-proto.pc'),
        'xorgproto':('FIND_FILES_xorgproto','lib/pkgconfig/xproto.pc'),
        'libXau':('H_XAUTH','include/X11/Xauth.h'),
        'libXdmcp':('H_XDMCP','include/X11/Xdmcp.h')}
 candidates={};dbs={};lines=['BASE=\told\n']
 def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
 for name in (*files,'vulkan-headers'):
  db=prefix/'pkgdb'/(name+'-1');db.mkdir(parents=True);dbs[name]=db
  contents=['@cwd '+str(prefix)]
  if name in files:
   key,rel=files[name];file=prefix/rel;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('owned '+name)
   contents += [rel,'@comment MD5:'+hashlib.md5(file.read_bytes(),usedforsecurity=False).hexdigest()];candidates[str(file)]=digest(file)
   lines += [key+'=\t'+str(file)+'\n','IS_BUILTIN.'+name+'=\tno\n','USE_BUILTIN.'+name+'=\tno\n']
  else:lines += ['PKG_BUILD_OPTIONS.vulkan-headers=\t\n']
  (db/'+CONTENTS').write_text('\n'.join(contents)+'\n');(db/'+BUILD_INFO').write_text('PKG_OPTIONS=\n')
  candidates.update({str(db/n):digest(db/n) for n in ('+CONTENTS','+BUILD_INFO')})
  lines += ['BUILDLINK_PREFIX.'+name+'=\t'+str(prefix)+'\n','_BLNK_PKG_DBDIR.'+name+'=\t'+str(db)+'\n']
 before=b'BASE=\told\n';after=''.join(lines).encode()
 host._additive_wrapper(before,after,old,new,prefix,candidates)
 def rejected(value, inputs=None):
  try:host._additive_wrapper(before,value,old,new,prefix,inputs or candidates)
  except (ValueError,OSError):return
  raise AssertionError('foreign wrapper accepted')
 rejected(after.replace(str(prefix/'include/X11/Xauth.h').encode(),b'/foreign/Xauth.h'))
 rejected(after.replace(b'IS_BUILTIN.libXau=\tno',b'IS_BUILTIN.libXau=\tyes'))
 rejected(after.replace(b'PKG_BUILD_OPTIONS.vulkan-headers=\t\n',b'PKG_BUILD_OPTIONS.vulkan-headers=\theadless\n'))
 rejected(after+b'IS_BUILTIN.libXau=\tno\n')
 rejected(after+b'BASE=\tchanged\n')
 rejected(after+b'UNEXPECTED=\tno\n')
 rejected(after+('BUILDLINK_PREFIX.=\t'+str(prefix)+'\n_BLNK_PKG_DBDIR.=\t'+str(dbs['libXau'])+'\n').encode())
 try:host._additive_wrapper(before+before,after+before,old,new,prefix,candidates)
 except ValueError:pass
 else:raise AssertionError('duplicate old wrapper key accepted')
 rejected(after.replace(b'USE_BUILTIN.libXau=\tno\n',b''))
 info=dbs['vulkan-headers']/'+BUILD_INFO';original_info=info.read_text();info.write_text(original_info+'PKG_OPTIONS=\n');bad=dict(candidates);bad[str(info)]=digest(info);rejected(after,bad);info.write_text(original_info)
 bad=dict(candidates);bad[str(prefix/'include/X11/Xauth.h')]='0'*64;rejected(after,bad)
 contents=dbs['libXau']/'+CONTENTS';original=contents.read_text();contents.write_text('@cwd '+str(prefix)+'\n');bad=dict(candidates);bad[str(contents)]=digest(contents);rejected(after,bad);contents.write_text(original)
 old_md5=hashlib.md5((prefix/'include/X11/Xauth.h').read_bytes(),usedforsecurity=False).hexdigest()
 contents.write_text(original.replace(old_md5,'0'*32));bad=dict(candidates);bad[str(contents)]=digest(contents);rejected(after,bad);contents.write_text(original)
 contents.write_text(original.replace('@cwd '+str(prefix),'@cwd /foreign'));bad=dict(candidates);bad[str(contents)]=digest(contents);rejected(after,bad);contents.write_text(original)
 file=prefix/'include/X11/Xauth.h';content=file.read_bytes();file.unlink();file.symlink_to(prefix/'include/X11/Xdmcp.h');rejected(after);file.unlink();file.write_bytes(content)
 print('PASS: 19 additive metadata fields, ownership, checksums, cwd and rejection cases')
