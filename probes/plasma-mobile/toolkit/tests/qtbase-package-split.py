#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real pkgsrc PLIST contracts, without a Qt build.
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

if len(sys.argv) != 7:
    raise SystemExit('Usage: qtbase-package-split.py PKGSRC HOST_PREFIX CROSS_TOOLS SYSROOT HOST_QT NEW_WORK')
source, host, tools, sysroot, qt = (Path(p).resolve(strict=True) for p in sys.argv[1:6])
work = Path(sys.argv[6])
if not work.is_absolute() or work.exists(): raise SystemExit('new absolute work directory required')
work.mkdir(parents=True)
tree = work / 'pkgsrc'; tree.mkdir()
recipes = Path(__file__).resolve().parents[4] / 'pkgsrc'
# The source tree is read-only; only two recipes and the consumer fixture can write.
for category in source.iterdir():
    if category.name.startswith('.'): continue
    dest = tree / category.name
    if category.name in ('x11', 'devel', 'meta-pkgs'):
        dest.mkdir()
        for package in category.iterdir():
            if category.name == 'x11' and package.name in ('qt6-qtbase','qt6-qtbase-devel'): continue
            if category.name == 'meta-pkgs' and package.name == 'qt6':
                shutil.copytree(package, dest / 'qt6', symlinks=True)
                shutil.copy2(recipes / 'meta-pkgs/qt6/Makefile.common', dest / 'qt6/Makefile.common')
            else: (dest / package.name).symlink_to(package)
    else: dest.symlink_to(category)
for name in ('qt6-qtbase', 'qt6-qtbase-devel'):
    recipe = recipes / 'x11' / name
    if recipe.is_dir(): shutil.copytree(recipe, tree / 'x11' / name, symlinks=True)
host_makeconf = Path(os.environ.get('QT_SPLIT_HOST_MAKECONF', str(host / 'etc/mk.conf')))
if not host_makeconf.is_absolute() or not host_makeconf.is_file(): raise SystemExit('selected host makeconf must be an absolute file')
(work / 'mk.conf').write_text(f'.include "{host_makeconf}"\nWRKOBJDIR= {work}/objects\nPACKAGES= {work}/packages\nPKG_DBDIR= {work}/pkgdb\nCXXFLAGS= -O2\n')
common = [str(host / 'bin/bmake'), 'MAKECONF='+str(work/'mk.conf'), 'AWK='+str(host/'bin/nawk'), 'CAT='+str(host/'bin/gcat'), 'SED='+str(host/'bin/gsed'), 'TEST='+str(host/'bin/gtest'), 'MKDIR='+str(host/'bin/gmkdir')+' -p', 'PERL5='+str(host/'bin/perl'), 'FIND='+str(host/'bin/gfind'), 'LN='+str(host/'bin/gln'), 'INSTALL_DATA_DIR='+str(host/'bin/bsdinstall')+' -d', 'X11_TYPE=modular', 'PLATFORM_SUPPORTS_WAYLAND=no', 'EMBERBSD_QT_HOST_PATH='+str(qt)]
for tool, binary in (('m4', 'gm4'), ('yacc', 'yacc')):
    path = host / 'bin' / binary
    if not path.is_file() or not os.access(path, os.X_OK):
        raise SystemExit('missing selected native tool: ' + str(path))
    common.append('OSX_PATH_TO_'+tool.upper()+'='+str(path))
cross = ['USE_CROSS_COMPILE=yes','CROSS_OPSYS=NetBSD','CROSS_OS_VERSION=11.0','CROSS_OPSYS_VERSION=110000','CROSS_MACHINE_ARCH=x86_64','CROSS_LOWER_OPSYS=netbsd','CROSS_LOWER_OPSYS_VERSUFFIX=','CROSS_LOWER_OS_VARIANT=','CROSS_LOWER_VARIANT_VERSION=','CROSS_LOWER_VENDOR=','CROSS_OBJECT_FMT=ELF','CROSS_LOCALBASE=/usr/pkg','CROSS_DESTDIR='+str(sysroot),'TOOLDIR='+str(tools),'CROSS_PKG_TOOLS_BIN='+str(host/'sbin'),'USE_PKGSRC_GCC_RUNTIME=no']
def run(label, package, *args):
    cmd = common + ['-C', str(tree/'x11'/package)] + list(map(str,args))
    process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try: output, _ = process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL); output, _ = process.communicate()
        (work/(label+'.log')).write_text(output)
        raise SystemExit(label+': bounded source query exceeded 30 seconds')
    (work/(label+'.log')).write_text(output)
    if process.returncode: raise SystemExit(label+': '+output)
    return output
header = work/'eglext.h'; header.write_text('#define EGL_DRM_MASTER_FD_EXT 0x333C\n')
for phase in ('early','late'):
    directory = work/('egldevice-'+phase); directory.mkdir()
    if phase == 'late': (directory/'.stage-install_makevars.mk').write_text('.if !defined(_MAKEVARS_MK)\n_MAKEVARS_MK= defined\nBUILDLINK_PREFIX.MesaLib= /usr/pkg\n.endif\n')
    mode = cross + ['EMBERBSD_COMMON_GRAPHICS=yes','MESALIB_SUPPORTS_EGL=yes','EGL_EXT_HEADER='+str(work/'not-installed-eglext.h' if phase == 'early' else header),'WRKDIR='+str(directory)]
    variables=run('egldevice-'+phase+'-vars','qt6-qtbase-devel',*mode,'-V','${PLIST.egldevice}','-V','${CMAKE_CONFIGURE_ARGS}')
    if variables.splitlines()[0].strip() != 'yes' or '-DFEATURE_eglfs_egldevice:BOOL=ON' not in variables: raise SystemExit('modern EGLDevice contract depends on early header/cache availability')
    run('egldevice-'+phase+'-plist','qt6-qtbase-devel',*mode,'plist')
    entries=[s for s in (directory/'.PLIST_nokeywords').read_text().splitlines() if s.startswith('qt6/lib/cmake/Qt6Gui/Qt6QEglFSKmsEglDeviceIntegrationPlugin')]
    if len(entries)!=7: raise SystemExit('modern EGLDevice metadata partition is incomplete')
    (work/('egldevice-'+phase+'-entries')).write_text('\n'.join(sorted(entries))+'\n')
if (work/'egldevice-early-entries').read_bytes() != (work/'egldevice-late-entries').read_bytes(): raise SystemExit('early and cached EGLDevice manifests differ')
def plist(label, package, *mode):
    directory=work/label; run(label,package,*mode,'WRKDIR='+str(directory),'plist')
    return [x for x in (directory/'.PLIST_nokeywords').read_text().splitlines() if x]
runtime=plist('runtime','qt6-qtbase',*cross)
if any(p.startswith('qt6/include/') or p.endswith('.cmake') or p in ('qt6/bin/qmake','qt6/libexec/moc','qt6/libexec/rcc','qt6/libexec/uic') for p in runtime): raise SystemExit('runtime PLIST still contains target SDK or generators')
if not all(p in runtime for p in ('qt6/bin/qtpaths','qt6/bin/qtpaths6')): raise SystemExit('runtime qtpaths missing')
if run('runtime-name','qt6-qtbase',*cross,'-V','${PKGNAME}').strip() != 'qt6-qtbase-6.12.0nb5': raise SystemExit('runtime package identity was not revised')
if not (tree/'x11/qt6-qtbase-devel').is_dir(): raise SystemExit('SDK recipe missing')
sdk=plist('devel','qt6-qtbase-devel',*cross)
if run('devel-name','qt6-qtbase-devel',*cross,'-V','${PKGNAME}').strip() != 'qt6-qtbase-devel-6.12.0nb7': raise SystemExit('SDK revision differs')
if not all(p in sdk for p in ('qt6/bin/qmake','qt6/libexec/moc','qt6/libexec/rcc','qt6/libexec/uic','qt6/lib/cmake/Qt6/Qt6Config.cmake')): raise SystemExit('SDK PLIST lost the CMake/generator contract')
if set(runtime)&set(sdk): raise SystemExit('partition overlaps')
owner=tree/'x11/qt6-qtbase'; full_dir=work/'full'
run('full','qt6-qtbase',*cross,'WRKDIR='+str(full_dir),'PLIST='+str(full_dir/'.PLIST'),'PLIST_SRC='+str(owner/'PLIST.NetBSD')+' '+str(owner/'PLIST'),'plist')
full=[x for x in (full_dir/'.PLIST_nokeywords').read_text().splitlines() if x]
if sorted(runtime+sdk)!=sorted(full): raise SystemExit('expanded partition union differs from full pkgsrc PLIST')
helper=owner/'files/select-package-stage.pl'
if not helper.is_file(): raise SystemExit('stage partition helper missing')
native=plist('native','qt6-qtbase','USE_CROSS_COMPILE=no','PKGSRC_COMPILER=clang','CC='+str(host/'bin/clang'),'CXX='+str(host/'bin/clang++'),'USE_NATIVE_GCC=no','USE_PKGSRC_GCC=no')
if 'qt6/bin/qmake' not in native or not any(p.startswith('qt6/include/') for p in native): raise SystemExit('native full SDK behavior changed')
reasons=run('devel-metadata','qt6-qtbase-devel',*cross,'-V','${PKG_FAIL_REASON}','-V','${DEPENDS}','-V','${DISTINFO_FILE}','-V','${PATCHDIR}')
if reasons.splitlines()[0].strip() or 'qt6-qtbase-6.12.0nb5:' not in reasons or str(owner/'distinfo') not in reasons or str(owner/'patches') not in reasons: raise SystemExit('SDK source owner, exact runtime or platform contract differs')
consumer=tree/'devel/qtbase-split-consumer'; consumer.mkdir()
(consumer/'Makefile').write_text('DISTNAME= qtbase-split-contract-1\nCATEGORIES= devel\nCOMMENT= Qtbase buildlink source contract fixture\nLICENSE= 2-clause-bsd\nMETA_PACKAGE= yes\n.include "../../mk/bsd.prefs.mk"\n.include "../../x11/qt6-qtbase/buildlink3.mk"\n.include "../../mk/bsd.pkg.mk"\n')
out=run('buildlink','../devel/qtbase-split-consumer',*cross,'-V','${BUILD_DEPENDS}','-V','${DEPENDS}').splitlines()
if 'qt6-qtbase-devel>=6.12.0nb7:' not in out[0] or 'qt6-qtbase-devel' in out[1] or 'qt6-qtbase>=6.12.0nb5:' not in out[1]: raise SystemExit('SDK was not a separate target build-only dependency')
original=work/'normalized-full'; prefix=original/'usr/pkg'
for path in full:
    dest=prefix/path; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text('source-contract fixture: '+path+'\n')
run('normalize-full','qt6-qtbase',*cross,'WRKDIR='+str(work/'normalizer'),'DESTDIR='+str(original),'qt-target-metadata','pkgconfig-link')
def fingerprint(directory):
    files={}
    for parent, dirs, names in os.walk(directory, followlinks=False):
        parent=Path(parent)
        for name in list(dirs):
            path=parent/name
            if path.is_symlink(): files[str(path.relative_to(directory))]=('symlink',os.readlink(path)); dirs.remove(name)
        for name in names:
            path=parent/name; key=str(path.relative_to(directory))
            files[key]=('symlink',os.readlink(path)) if path.is_symlink() else ('file',hashlib.sha256(path.read_bytes()).hexdigest(),path.stat().st_mode & 0o7777)
    return files
before=fingerprint(prefix)
if sorted(before)!=sorted(full): raise SystemExit('full normalized fixture differs from the pkgsrc manifest')
for part in ('runtime','devel'):
    dest=work/(part+'-stage'); shutil.copytree(original,dest,symlinks=True,copy_function=shutil.copy2)
    package='qt6-qtbase' if part=='runtime' else 'qt6-qtbase-devel'
    run(part+'-select-stage',package,*cross,'WRKDIR='+str(work/(part+'-select')),'DESTDIR='+str(dest),'qtbase-select-stage')
    selected=runtime if part=='runtime' else sdk
    if fingerprint(dest/'usr/pkg') != {k:v for k,v in before.items() if k in selected}: raise SystemExit('selected stage bytes, modes or symlinks changed')
for case in ('missing','unknown','overlap','union','selected','symlink-parent','part'):
    dest=work/('reject-'+case); shutil.copytree(original,dest,symlinks=True,copy_function=shutil.copy2); stage=dest/'usr/pkg'
    lists=[full_dir/'.PLIST',work/'runtime/.PLIST',work/'devel/.PLIST',work/'runtime/.PLIST']; part='runtime'
    if case=='missing': (stage/sdk[0]).unlink()
    elif case=='unknown': (stage/'qt6/bin/unlisted-generator').write_text('unlisted fixture')
    elif case=='overlap': lists[2]=dest/'overlap.plist'; lists[2].write_text((work/'devel/.PLIST').read_text()+runtime[0]+'\n')
    elif case=='union': lists[2]=dest/'incomplete.plist'; lists[2].write_text('\n'.join(sdk[1:])+'\n')
    elif case=='selected': lists[3]=lists[2]
    elif case=='symlink-parent':
        outside=dest/'outside'; outside.mkdir(); (outside/'preserved').write_text('outside fixture'); shutil.rmtree(stage/'qt6/bin'); (stage/'qt6/bin').symlink_to(outside)
    else: part='unsupported'
    unchanged=fingerprint(stage)
    r=subprocess.run([str(host/'bin/perl'),str(helper),part,str(stage),*map(str,lists)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (work/('reject-'+case+'.log')).write_text(r.stdout)
    if r.returncode==0: raise SystemExit('invalid partition was accepted: '+case)
    if fingerprint(stage)!=unchanged: raise SystemExit('invalid partition changed staging: '+case)
print('PASS: real pkgsrc produces distinct runtime/SDK manifests and a revised runtime identity')
print('PASS: native full manifest, exact source/runtime dependencies, exhaustive union and build-only SDK contract')
print('PASS: actual full-stage normalizer and partition preserve selected bytes; seven invalid inputs fail before pruning')
print('SCOPE: source packaging contract only; no Qt compilation, target file execution or installed Qt acceptance')
