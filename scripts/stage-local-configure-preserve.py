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


def refresh_tools(a, paths, jsonio, command, work):
    """Refresh changed pkgsrc tool wrappers under the caller's stage lock."""
    import tempfile
    marker = work / '.emberbsd-tools-refresh.json'
    values = subprocess.run(command + ['-V', '${USE_TOOLS}', '-V', '${WRKDIR}',
                                       '-V', '${_COOKIE.tools}'], check=True, text=True,
                            stdout=subprocess.PIPE).stdout.splitlines()
    require(len(values) == 3, 'invalid tools metadata')
    use, selected_work, cookie_name = values
    require(Path(selected_work).resolve(strict=True) == work, 'selected tools work differs from lock')
    cookie = Path(cookie_name)
    require(cookie.parent == work and cookie.name == '.tools_done', 'invalid tools cookie')
    if not os.path.lexists(cookie) and not os.path.lexists(marker):
        return
    if os.path.lexists(cookie):
        require(cookie.is_file() and not cookie.is_symlink() and cookie.stat().st_nlink == 1,
                'invalid tools cookie file')
        old_use = cookie.read_text()
    else:
        old_use = ''
    identity = {'work': str(work), 'recipe': str(a.recipe), 'use': use.split(),
                'command': [x for x in command if not x.startswith(('MAKE_JOBS=', 'NATIVE_PKG_ADD_CMD='))]}
    if not os.path.lexists(marker) and old_use.split() == use.split():
        return
    require(set(old_use.split()) <= set(use.split()), 'removing USE_TOOLS is unsupported')
    with tempfile.TemporaryDirectory(prefix='ember-tools-plan-') as tmp:
        scratch = Path(tmp) / 'tools'
        query = command + ['TOOLS_DIR=' + str(scratch)]
        expr = '${TOOLS_CREATE:@t@${t}|${TOOLS_CMD.${t}}|${TOOLS_ALIASES.${t}:ts,}@}'
        groups = subprocess.run(query + ['-V', expr], check=True, text=True,
                                stdout=subprocess.PIPE).stdout.strip()
        live = work / '.tools'
        paths.real_directory(str(live)); paths.real_directory(str(live / 'bin'))
        if os.path.lexists(marker):
            record = jsonio.read_json(str(marker))
            require(record.get('identity') == identity and record.get('version') == 1,
                    'tools refresh journal changed')
        else:
            dry = subprocess.run(command + ['-n', 'post-tools'], check=True, text=True,
                                 stdout=subprocess.PIPE).stdout
            require(not dry.strip(), 'custom post-tools is unsupported')
            record = {'version': 1, 'identity': identity, 'files': {}, 'writing': []}
        specs = {}
        for group in groups.split():
            parts = group.split('|')
            require(len(parts) == 3 and parts[0] not in ('', '.', '..') and '/' not in parts[0] and '\\' not in parts[0], 'invalid tools group')
            primary = Path(parts[1]); require(primary.parent == scratch / 'bin', 'tool outside tools bin')
            aliases = [x for x in parts[2].split(',') if x]
            require(all(x not in ('', '.', '..') and '/' not in x and '\\' not in x for x in aliases), 'invalid tools alias')
            key = primary.name
            spec = (key, tuple(aliases))
            require(key not in specs or specs[key] == spec, 'conflicting tool targets')
            specs[key] = spec
        targets = [str(scratch / 'bin' / x) for x in specs]
        subprocess.run(query + targets, check=True)
        def state(path, normalize=False):
            if path.is_symlink():
                target = os.readlink(path)
                if normalize: target = target.replace(str(scratch), str(live))
                return {'kind': 'link', 'value': target}
            if not os.path.lexists(path): return {'kind': 'missing'}
            require(path.is_file() and path.stat().st_nlink == 1, 'unsafe tools file: ' + str(path))
            data = path.read_bytes()
            if normalize: data = data.replace(os.fsencode(scratch), os.fsencode(live))
            return {'kind': 'file', 'sha256': hashlib.sha256(data).hexdigest(),
                    'mode': stat.S_IMODE(path.stat().st_mode)}
        expected = {}
        for primary, aliases in specs.values():
            for name in (primary, *aliases):
                candidate = scratch / 'bin' / name
                item = state(candidate, True)
                require(item['kind'] != 'missing', 'factory did not produce tool: ' + name)
                require(name not in expected or expected[name] == item, 'conflicting tool alias')
                expected[name] = item
        if not record['files']:
            for name, goal in expected.items():
                path = live / 'bin' / name
                record['files'][name] = {'before': state(path), 'after': goal,
                                         'mtime_ns': path.lstat().st_mtime_ns if os.path.lexists(path) else None}
            jsonio.write_json(str(marker), record)
        require(set(record['files']) == set(expected), 'tool inventory changed during retry')
        for name, item in record['files'].items():
            require(item['after'] == expected[name], 'tool factory changed during retry')
            now = state(live / 'bin' / name)
            partial = name in record.get('writing', []) and now['kind'] == 'file'
            require(now in (item['before'], item['after'], {'kind': 'missing'}) or partial, 'tool changed during retry: ' + name)
        for primary, aliases in specs.values():
            for alias in aliases:
                path = live / 'bin' / alias
                require(not (path.is_symlink() and path.is_dir()), 'directory symlink tool alias: ' + alias)
        changed = []
        for primary, aliases in specs.values():
            if any(state(live / 'bin' / n) != expected[n] for n in (primary, *aliases)):
                changed.append(primary)
        changed = sorted(set(changed) | set(record.get('writing', [])))
        require(set(changed) <= set(specs), 'invalid writing journal')
        record['writing'] = changed
        jsonio.write_json(str(marker), record, exclusive=False)
        for primary in changed:
            path = live / 'bin' / primary
            if os.path.lexists(path):
                path.unlink()
        if changed:
            subprocess.run(command + [str(live / 'bin' / x) for x in changed], check=True)
        for name, item in record['files'].items():
            path = live / 'bin' / name
            require(state(path) == item['after'], 'tool factory output differs: ' + name)
            if item['before'] == item['after'] and item['mtime_ns'] is not None:
                info = path.lstat()
                os.utime(path, ns=(info.st_atime_ns, item['mtime_ns']), follow_symlinks=False)
        record['writing'] = []
        jsonio.write_json(str(marker), record, exclusive=False)
        with tempfile.TemporaryDirectory(prefix='.tools-cookie-', dir=work) as tmpcookie:
            temporary = Path(tmpcookie) / 'cookie'
            subprocess.run(command + ['_COOKIE.tools=' + str(temporary), 'tools-cookie'], check=True)
            require(temporary.is_file() and not temporary.is_symlink() and
                    temporary.read_text().split() == use.split(), 'invalid generated tools cookie')
            subprocess.run(command + ['configure-clean'], check=True)
            os.replace(temporary, cookie)
        marker.unlink()
        print('Refreshed staged pkgsrc tools')


def refresh_new_buildlinks(a, command, work):
    """Materialize newly added pkgsrc buildlink providers before configure."""
    live = work / '.buildlink'
    if not os.path.lexists(live):
        return
    require(live.is_dir() and not live.is_symlink(), 'invalid staged buildlink root')
    packages = subprocess.run(command + ['-V', '${_BLNK_PACKAGES}'], check=True,
                              text=True, stdout=subprocess.PIPE).stdout.split()
    if not packages:
        return
    fields = ['${TOOLS_CROSS_DESTDIR}']
    for provider in packages:
        require(re.fullmatch(r'[A-Za-z0-9_+-]+', provider), 'invalid buildlink provider name')
        fields.extend(('${USE_BUILTIN.' + provider + '}', '${_BLNK_COOKIE.' + provider + '}'))
    values = subprocess.run(command + sum((['-V', field] for field in fields), []), check=True,
                             text=True, stdout=subprocess.PIPE).stdout.splitlines()
    require(len(values) == len(fields), 'invalid buildlink metadata')
    cross = values[0].strip()
    for position, provider in enumerate(packages):
        index = 1 + position * 2
        builtin = values[index].strip().lower()
        if builtin == 'yes':
            continue
        require(builtin == 'no', 'invalid provider builtin setting')
        cookie = Path(values[index + 1].strip())
        require(cookie.name == '.buildlink_' + provider + '_done' and
                cookie.parent.resolve(strict=True) == live.resolve(strict=True),
                'unexpected buildlink provider cookie path')
        if os.path.lexists(cookie):
            require(cookie.is_file() and not cookie.is_symlink(), 'invalid provider cookie')
            continue
        helper = Path(__file__).with_name('stage-local-buildlink-refresh.py')
        args = [sys.executable, '-B', '-E', '-S', str(helper), '--bmake', str(a.bmake),
                '--recipe', str(a.recipe), '--expected-work', str(work),
                '--provider', provider]
        for value in (*a.make_arg, *a.bmake_args):
            args.extend(('--make-arg', value))
        if not cross:
            args.append('--native')
        subprocess.run(args, check=True)
        require(cookie.is_file() and not cookie.is_symlink(),
                'buildlink factory did not create provider cookie')


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
    refresh_tools(a, paths, jsonio, command, a.expected_work.resolve(strict=True))
    result=subprocess.run(command+['_MAKEVARS_MK=defined','show-vars','VARNAMES=WRKDIR WRKSRC CONFIG_SHELL _COOKIE.configure GNU_CONFIGURE CONFIGURE_DIRS'],
                          check=True,stdout=subprocess.PIPE,text=True)
    fields=result.stdout.splitlines();require(len(fields)==6,'invalid configure stage metadata')
    work,source,shell,cookie=map(Path,fields[:4]);gnu,dirs=fields[4:]
    require(paths.canonical_existing(str(work))==paths.canonical_existing(str(a.expected_work)),
            'selected WRKDIR differs from locked stage')
    work=Path(paths.canonical_existing(str(work)))
    marker=work/'.emberbsd-configure-preserve.json'
    refresh_new_buildlinks(a, command, work)
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
              'command':[arg for arg in command if not arg.startswith(('MAKE_JOBS=', 'NATIVE_PKG_ADD_CMD='))],
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
