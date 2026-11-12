#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Generate Chromium's recovery amalgamation from the verified common SQLite tree."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
owner_path = Path(__file__).with_name('source.py')
spec = importlib.util.spec_from_file_location('sqlite_source_owner', owner_path)
owner_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(owner_module)
owner = owner_module.Owner()
args = owner.load_sdk(sys.argv[1:])
from emberbsd_sdk import cpu_capacity, host_prefix, host_services, jsonio, paths, process
from emberbsd_sdk.errors import SDKError


def require(value, message):
    if not value:
        raise SDKError(message)


def flags_from_gni(path, variable):
    """Read the same literal flag lists used by Chromium's generator and GN."""
    tree = ast.parse(path.read_text(), filename=str(path))
    values = [ast.literal_eval(item.value) for item in tree.body if isinstance(item, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == variable for target in item.targets)]
    require(len(values) == 1 and isinstance(values[0], list) and
            all(isinstance(item, str) and re.fullmatch(r'SQLITE_[A-Z0-9_]+(?:=[A-Za-z0-9_,.-]+)?', item)
                for item in values[0]), 'invalid Chromium SQLite flag list')
    return values[0]


def selected_tcl(prefix, executable, native):
    """Bind the Tcl interpreter to its selected installed common package."""
    prefix = Path(prefix).resolve(strict=True)
    logical = Path(executable)
    require(logical.is_absolute() and logical.is_relative_to(prefix), 'Tcl must be in selected host prefix')
    resolved = logical.resolve(strict=True)
    host_prefix.validate_host_executable(str(prefix), str(resolved), native.host, search_path=native.path)
    packages = [p for p in (prefix/'pkgdb').iterdir() if (p/'+BUILD_INFO').is_file() and
                'PKGPATH=lang/tcl' in (p/'+BUILD_INFO').read_text().splitlines()]
    require(len(packages) == 1, 'selected common Tcl package missing or ambiguous')
    package = packages[0]; manifest = (package/'+CONTENTS').read_text().splitlines()
    logical_entry = str(logical.relative_to(prefix)); actual_entry = str(resolved.relative_to(prefix))
    require(logical_entry in manifest and actual_entry in manifest, 'Tcl executable is not package-owned')
    index = manifest.index(actual_entry)
    require(index + 1 < len(manifest) and re.fullmatch(r'@comment MD5:[0-9a-f]{32}', manifest[index+1]),
            'Tcl executable has no package checksum')
    stream, before = paths.open_regular(resolved)
    with stream:
        data = stream.read()
        require(paths.stable_identity(os.fstat(stream.fileno())) == paths.stable_identity(before),
                'Tcl executable changed during verification')
    paths.verify_stable(resolved, before)
    require(hashlib.md5(data, usedforsecurity=False).hexdigest() == manifest[index+1].split(':',1)[1],
            'Tcl executable differs from installed package')
    return resolved, package, hashlib.sha256(data).hexdigest()


def run(command, *, cwd, env, input=None):
    try:
        return subprocess.run(command, cwd=cwd, env=env, input=input, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    except subprocess.CalledProcessError as error:
        raise SDKError('command failed: ' + str(command[0]) + '\n' + error.stderr[-4000:]) from error


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source','chromium','work','host-prefix','tcl','git','lock-root'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--archive', type=Path); p.add_argument('--patch', type=Path)
    p.add_argument('--pkgsrc-export', type=Path); p.add_argument('--export-patch', type=Path)
    p.add_argument('--jobs', type=int); p.add_argument('--host-compiler-family', choices=('clang','gcc'), default='clang')
    p.add_argument('--host-cflag', action='append', default=[])
    p.add_argument('--host-ldflag', action='append', default=[])
    selected = p.parse_args(args)
    for name in ('source','chromium','work','host_prefix','tcl','git','lock_root'):
        require(getattr(selected,name).is_absolute(), '--'+name.replace('_','-')+' must be absolute')
    source=selected.source.resolve(strict=True); chromium=selected.chromium.resolve(strict=True)
    work=selected.work; paths.reject_overlap(str(work),str(source)); paths.reject_overlap(str(work),str(chromium))
    work.mkdir(parents=True,exist_ok=True); require(not work.is_symlink(), 'work must be a real directory')
    native=host_prefix.load_host_prefix(selected.host_prefix,
        required_roles=('cc','cxx','cpp','ar','ranlib','gmake','python','sh','awk','sed'),
        compiler_family=selected.host_compiler_family)
    toolpath=host_services.build_path(native,str(work)); environment=process.sanitized_environment()
    environment.update(PATH=toolpath,SHELL=native.tool('sh'),CONFIG_SHELL=native.tool('sh'),
                       PKG_CONFIG_LIBDIR=os.pathsep.join((str(selected.host_prefix/'lib/pkgconfig'),
                                                         str(selected.host_prefix/'share/pkgconfig'))))
    environment.pop('PKG_CONFIG_PATH',None); environment.pop('PKG_CONFIG_SYSROOT_DIR',None)
    for command in ('cp','mv','touch'):
        tool=shutil.which(command,path=toolpath)
        require(tool, 'selected host prefix lacks '+command)
        host_prefix.validate_host_executable(str(selected.host_prefix),tool,native.host,search_path=toolpath)
    tcl,package,tcl_hash=selected_tcl(selected.host_prefix,selected.tcl,native)
    version=run([str(tcl)],cwd=work,env=environment,input='puts [info patchlevel]\n').strip()
    require(re.fullmatch(r'9\.1(?:\.\d+)?',version), 'selected Tcl must be 9.1')
    icu=(selected.host_prefix/'bin/icu-config').resolve(strict=True)
    host_prefix.validate_host_executable(str(selected.host_prefix),str(icu),native.host,search_path=toolpath)
    cppflags=shlex.split(run([str(icu),'--cppflags'],cwd=work,env=environment))
    ldflags=shlex.split(run([str(icu),'--ldflags'],cwd=work,env=environment))
    for flag in cppflags+ldflags:
        if flag.startswith(('-I','-L')) and len(flag)>2:
            require(Path(flag[2:]).resolve(strict=True).is_relative_to(selected.host_prefix.resolve(strict=True)),
                    'ICU path escapes selected host prefix')
    common=chromium/'sqlite_common_configuration_flags.gni'; chrome=chromium/'sqlite_chromium_configuration_flags.gni'
    dev=chromium/'sqlite_dev_configuration_flags.gni'
    extractor=chromium/'scripts/extract_sqlite_api.py'
    common_flags=flags_from_gni(common,'sqlite_common_configuration_flags')
    flags=common_flags+flags_from_gni(chrome,'sqlite_chromium_configuration_flags')
    dev_flags=common_flags+flags_from_gni(dev,'sqlite_dev_configuration_flags')
    require('SQLITE_HAVE_SQLITE3R' in flags and 'SQLITE_OMIT_LOAD_EXTENSION' in flags and
            'SQLITE_SECURE_DELETE' in flags, 'Chromium SQLite recovery or privacy policy missing')
    with process.ContextLocks([str(source),str(work)],str(selected.lock_root)):
        receipt=owner.verify(str(source),str(selected.git),
            archive=str(selected.archive) if selected.archive else None,
            patch=str(selected.patch) if selected.patch else None,
            pkgsrc_export=str(selected.pkgsrc_export) if selected.pkgsrc_export else None,
            export_patch=str(selected.export_patch) if selected.export_patch else None)
        identity={'source':str(source),'tree':receipt['tree_sha256'],'tcl':str(tcl),'tcl_sha256':tcl_hash,
                  'tcl_package':package.name,'native':native.as_dict(), 'flags':flags, 'dev_flags':dev_flags,
                  'icu_cppflags':cppflags,'icu_ldflags':ldflags,
                  'host_cflags':selected.host_cflag,'host_ldflags':selected.host_ldflag,
                  'extractor_sha256':hashlib.sha256(extractor.read_bytes()).hexdigest(),
                  'common_gni_sha256':hashlib.sha256(common.read_bytes()).hexdigest(),
                  'chromium_gni_sha256':hashlib.sha256(chrome.read_bytes()).hexdigest(),
                  'dev_gni_sha256':hashlib.sha256(dev.read_bytes()).hexdigest(),
                  'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        identity_digest=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        build_root=work/('build-'+identity_digest); build_root.mkdir(exist_ok=True)
        require(not build_root.is_symlink(), 'build directory must be real')
        jobs=cpu_capacity.resolve_jobs(selected.jobs)
        builds={}
        for name, selected_flags in (('chromium',flags),('dev',dev_flags)):
            build=build_root/name; build.mkdir(exist_ok=True)
            require(not build.is_symlink(), 'build directory must be real')
            config=build/'configure-inputs.json'; pending=build/'configure-incomplete'
            old=json.loads(config.read_text()) if config.is_file() else None
            if old != identity or pending.exists():
                require(not (build/'jimsh0').exists() and not (build/'jimsh').exists(),
                        'SQLite build contains an unintended Jim interpreter')
                pending.write_text('configure incomplete\n')
                cc=shlex.join([*native.command('cc'),*native.abi_flags['cflags'],*selected.host_cflag])
                environment.update(CC=cc,CC_FOR_BUILD=cc,AR=native.tool('ar'),RANLIB=native.tool('ranlib'),
                                   LD=native.tool('ld'), WRAPPER=str(source/'configure'))
                cflags=shlex.join(['-Os',*('-D'+flag for flag in selected_flags),*cppflags])
                cmd=[str(tcl),str(source/'autosetup/autosetup'),'CFLAGS='+cflags,
                     'LDFLAGS='+shlex.join([*native.abi_flags['ldflags'],*selected.host_ldflag,*ldflags]),
                     '--prefix='+str(selected.host_prefix),'--disable-load-extension','--enable-amalgamation',
                     '--enable-threadsafe','--with-tclsh='+str(tcl)]
                run(cmd,cwd=build,env=environment)
                jsonio.write_json(str(config),identity,exclusive=False); pending.unlink()
            run([native.tool('gmake'),'-j'+str(jobs),'B.tclsh='+str(tcl),'TCLSH_CMD='+str(tcl),
                 'SHELL='+native.tool('sh'),'shell.c','sqlite3r.h','sqlite3r.c'],cwd=build,env=environment)
            builds[name]=build
        with tempfile.TemporaryDirectory(prefix='.sqlite-output-',dir=work) as temp:
            stage=Path(temp)
            extract_spec=importlib.util.spec_from_file_location('chromium_extract_sqlite_api',extractor)
            module=importlib.util.module_from_spec(extract_spec); extract_spec.loader.exec_module(module)
            files=[]
            for name, subdir in (('chromium',Path('.')),('dev',Path('dev'))):
                output=stage/subdir; (output/'shell').mkdir(parents=True)
                for src,dst in (('sqlite3r.c','sqlite3.c'),('sqlite3r.h','sqlite3.h'),('shell.c','shell/shell.c')):
                    shutil.copyfile(builds[name]/src,output/dst)
                    files.append(str(subdir/dst))
                module.ProcessSourceFile(api_export_macro='SQLITE_API',symbol_prefix='chrome_',
                    header_line=module.header_line,footer_line=module.footer_line,
                    input_file=str(output/'sqlite3.h'),output_file=str(output/'rename_exports.h'))
                files.append(str(subdir/'rename_exports.h'))
            hashes={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in files}
            manifest={'format':'emberbsd-chromium-sqlite','version':1,
                      'identity':identity,'files':hashes}
            encoded=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
            digest=hashlib.sha256(encoded).hexdigest()
            (stage/'receipt.json').write_bytes(encoded)
            destination=work/('amalgamation-'+digest)
            if destination.exists():
                require(destination.is_dir() and not destination.is_symlink() and
                        (destination/'receipt.json').read_bytes()==encoded and
                        all((destination/name).read_bytes()==(stage/name).read_bytes() for name in files),
                        'existing amalgamation differs from generated output')
            else:
                owner.publish_directory_noreplace(stage,destination)
        print(destination)


if __name__ == '__main__':
    try: main()
    except (SDKError,OSError,ValueError,subprocess.CalledProcessError) as error:
        sys.exit('SQLite Chromium amalgamation: '+str(error))
