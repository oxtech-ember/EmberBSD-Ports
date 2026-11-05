#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Configure a locked existing stage, preserving unchanged generated inputs.

Inventory comes only from the existing Autoconf config.status report. A small
journal lets the same owner retry a failed configure or interrupted restore.
Compiled outputs are never included. The caller holds the stage lock.
"""
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import subprocess
import sys


def require(value, message):
    if not value:
        raise ValueError(message)


def valid_name(name):
    return (isinstance(name, str) and name and not PurePosixPath(name).is_absolute() and
            '\\' not in name and all(x not in ('', '.', '..') for x in name.split('/')) and
            not re.search(r'(?:\.o|\.lo|\.la|\.a|\.so(?:\.[0-9.]+)?|\.dylib)$', name))


def inventory(report):
    names=[]; section=None; seen=set(); saw_files=False; saw_headers=False
    for line in report.splitlines():
        if line == 'Configuration files:': section='files'; saw_files=True; continue
        if line == 'Configuration headers:': section='headers'; saw_headers=True; continue
        if line == 'Configuration commands:': section=None; continue
        if section and line.startswith(' '):
            for token in shlex.split(line):
                name=token.split(':',1)[0]; path=PurePosixPath(name)
                require(valid_name(name), 'unsupported configure output: '+name)
                require(name not in seen, 'duplicate configure output: '+name)
                seen.add(name); names.append(name)
        elif line and not line.startswith(' '):
            section=None
    require(saw_files and saw_headers, 'unsupported config.status inventory')
    return names


def entry(paths, root, name):
    require(valid_name(name), 'invalid configure journal path')
    current=root
    for part in name.split('/')[:-1]:
        current=current/part; paths.real_directory(str(current))
    return current/name.split('/')[-1]


def fingerprint(paths, path):
    handle,before=paths.open_regular(str(path))
    with handle:
        digest=hashlib.sha256()
        while True:
            block=handle.read(1024*1024)
            if not block:break
            digest.update(block)
        require(paths.stable_identity(os.fstat(handle.fileno())) == paths.stable_identity(before),
                'configure input changed while reading: '+str(path))
    paths.verify_stable(str(path),before)
    return {'sha256':digest.hexdigest(),'mode':stat.S_IMODE(before.st_mode),
            'mtime_ns':before.st_mtime_ns}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source','bmake','recipe','expected-work'):
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--make-arg',action='append',default=[])
    p.add_argument('bmake_args',nargs=argparse.REMAINDER)
    a=p.parse_args()
    if a.bmake_args[:1] == ['--']:
        a.bmake_args = a.bmake_args[1:]
    for name in ('sdk_source','bmake','recipe','expected_work'):
        require(getattr(a,name).is_absolute(), 'selected path must be absolute')
    # A fresh stage has no previous configure outputs to preserve.
    if not os.path.lexists(a.expected_work):
        return
    sys.path.insert(0,str(a.sdk_source/'src'))
    from emberbsd_sdk import jsonio,paths
    command=[str(a.bmake),'-C',str(a.recipe),*a.make_arg,*a.bmake_args]
    result=subprocess.run(command+['_MAKEVARS_MK=defined','show-vars','VARNAMES=WRKDIR WRKSRC CONFIG_SHELL _COOKIE.configure GNU_CONFIGURE CONFIGURE_DIRS'],
                          check=True,stdout=subprocess.PIPE,text=True)
    fields=result.stdout.splitlines();require(len(fields)==6,'invalid configure stage metadata')
    work,source,shell,cookie=map(Path,fields[:4]);gnu,dirs=fields[4:]
    require(paths.canonical_existing(str(work))==paths.canonical_existing(str(a.expected_work)),
            'selected WRKDIR differs from locked stage')
    work=Path(paths.canonical_existing(str(work)))
    marker=work/'.emberbsd-configure-preserve.json'
    # A partially created stage may not have extracted WRKSRC yet.
    if not os.path.lexists(source):
        require(not os.path.lexists(marker), 'configure source is missing during retry')
        return
    source=Path(paths.canonical_existing(str(source)))
    if not source.is_relative_to(work):
        require(not os.path.lexists(marker), 'configure source changed during retry')
        return
    require(shell.is_absolute() and cookie.is_absolute() and cookie.parent==work,
            'invalid configure stage paths')
    if gnu.lower() != 'yes':
        require(not os.path.lexists(marker), 'configure mode changed during retry')
        return
    if not os.path.lexists(marker) and cookie.exists():
        return
    status=source/'config.status'
    if not os.path.lexists(marker) and not status.is_file():
        return
    configure_dirs = shlex.split(dirs)
    if not (len(configure_dirs)==1 and Path(configure_dirs[0]).resolve(strict=True)==source):
        require(not os.path.lexists(marker), 'configure directory changed during retry')
        return
    identity={'work':str(work),'source':str(source),'cookie':str(cookie),
              'command':[arg for arg in command if not arg.startswith('MAKE_JOBS=')],
              'shell':str(shell)}
    if os.path.lexists(marker):
        record=jsonio.read_json(str(marker))
        require(isinstance(record,dict) and record.get('version')==1 and record.get('identity')==identity and
                isinstance(record.get('files'),dict), 'configure preservation journal changed')
        for name, data in record['files'].items():
            require(valid_name(name) and isinstance(data,dict) and set(data)=={'sha256','mode','mtime_ns'} and
                    isinstance(data['sha256'],str) and re.fullmatch(r'[0-9a-f]{64}',data['sha256']) and
                    type(data['mode']) is int and 0 <= data['mode'] <= 0o7777 and
                    type(data['mtime_ns']) is int and data['mtime_ns'] >= 0,
                    'invalid configure preservation journal file')
    else:
        # Unsupported Autoconf variants keep the ordinary pkgsrc path.
        if status.is_symlink():
            return
        try:
            report=subprocess.run([str(shell),str(status),'--help'],cwd=source,check=True,
                                  stdout=subprocess.PIPE,text=True).stdout
            names=inventory(report)
        except (ValueError, subprocess.CalledProcessError):
            return
        files={}
        for name in names:
            if os.path.lexists(source/name):
                path=entry(paths,source,name)
                files[name]=fingerprint(paths,path)
        record={'version':1,'identity':identity,'files':files}
        jsonio.write_json(str(marker),record)
    subprocess.run(command+['configure'],check=True)
    require(cookie.is_file() and not cookie.is_symlink(), 'configure did not finish')
    # A changed generated Makefile may encode different compiler or link
    # flags. In that case leave configure timestamps intact so existing make
    # dependencies can invalidate incompatible objects rather than hide the
    # changed build context. An unknown context is treated the same way.
    makefiles=[name for name in record['files'] if Path(name).name=='Makefile']
    same_context=bool(makefiles)
    for name in makefiles:
        if not os.path.lexists(source/name):
            same_context=False; break
        now=fingerprint(paths,entry(paths,source,name));old=record['files'][name]
        if now['sha256']!=old['sha256'] or now['mode']!=old['mode']:
            same_context=False; break
    restored=0
    if same_context:
        for name,old in record['files'].items():
            if not os.path.lexists(source/name):continue
            path=entry(paths,source,name)
            now=fingerprint(paths,path)
            if now['sha256']==old['sha256'] and now['mode']==old['mode']:
                info=paths.regular_file(str(path))
                if info.st_nlink == 1:
                    os.utime(path,ns=(info.st_atime_ns,old['mtime_ns']),follow_symlinks=False)
                    restored+=1
    marker.unlink()
    print('Preserved unchanged configure outputs:',restored)
    if not same_context:
        print('Generated Makefile changed or is missing; retained configure timestamps.')


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        sys.exit('stage configure preservation: '+str(error))
