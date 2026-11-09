#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Refresh one package buildlink provider through the pkgsrc factory."""
import argparse
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import tempfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_path(root, rel):
    require(rel.parts and not rel.is_absolute() and all(x not in ('', '.', '..') for x in rel.parts), 'invalid buildlink path')
    p = root
    for part in rel.parts[:-1]:
        p = p / part
        if p.is_symlink():
            raise ValueError('symlink ancestor: ' + str(p))
        if p.exists():
            require(p.is_dir(), 'non-directory ancestor: ' + str(p))
    return root / rel


def parse_cookie(cookie, root):
    result = {}
    for row in cookie.read_text().splitlines():
        dest, sep, target = row.partition(' -> ')
        require(sep and Path(dest).is_absolute() and Path(target).is_absolute(), 'invalid cookie row')
        rel = Path(dest).relative_to(root)
        safe_path(root, rel)
        require(rel not in result, 'duplicate cookie destination')
        result[rel] = target
    return result


def regular(path):
    return path.is_file() and not path.is_symlink()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bmake', required=True)
    p.add_argument('--recipe', type=Path, required=True)
    p.add_argument('--expected-work', type=Path, required=True)
    p.add_argument('--provider', required=True)
    p.add_argument('--make-arg', action='append', default=[])
    p.add_argument('--native', action='store_true')
    a = p.parse_args()
    require(re.fullmatch(r'[A-Za-z0-9_+-]+', a.provider), 'invalid provider')
    # A retained phase cache can name an uninstalled provider revision. Query
    # and run the factory against pkgdb, without rewriting the stage caches.
    cmd = [a.bmake, '-C', str(a.recipe), '_PKGSRC_BARRIER=yes',
           '_MAKEVARS_MK=defined', *a.make_arg]
    fields = ['WRKDIR', 'BUILDLINK_DIR', 'BUILDLINK_X11_DIR', 'USE_BUILTIN.' + a.provider,
              'BUILDLINK_PREFIX.' + a.provider, 'TOOLS_CROSS_DESTDIR', 'BUILDLINK_PKGNAME.' + a.provider,
              '_BLNK_COOKIE.' + a.provider, '_BLNK_PKG_INFO.' + a.provider,
              '_BLNK_FILES_CMD.' + a.provider, 'GREP']
    query = cmd + sum((['-V', '${' + k + '}'] for k in fields), [])
    values = subprocess.run(query, check=True, text=True, stdout=subprocess.PIPE).stdout.splitlines()
    require(len(values) == len(fields), 'invalid bmake metadata')
    work, live, x11, builtin, prefix, cross, pkgname, cookie, pkginfo, files_cmd, grep = values
    work, live, x11, cookie = map(Path, (work, live, x11, cookie))
    require(work.resolve(strict=True) == a.expected_work.resolve(strict=True), 'unexpected work')
    require(live.is_dir() and not live.is_symlink() and live.resolve().is_relative_to(work.resolve()), 'invalid buildlink root')
    require(x11.resolve() == live.resolve(), 'distinct X11 buildlink root unsupported')
    require(builtin.lower() == 'no' and prefix.startswith('/') and not prefix.endswith('not_found') and pkgname, 'provider is not installed pkgsrc package')
    require((bool(cross) and Path(cross).is_absolute() or a.native and not cross) and Path(cross + prefix).is_dir(), 'invalid provider prefix')
    require(pkginfo and files_cmd and grep and Path(grep).is_absolute(), 'missing selected provider tools')
    installed = subprocess.run(shlex.split(pkginfo) + ['-f', pkgname], check=True, text=True, stdout=subprocess.PIPE).stdout
    require(any(line.lstrip().startswith('File:') for line in installed.splitlines()), 'empty provider package inventory')
    require(cookie.parent == live and cookie.name == '.buildlink_' + a.provider + '_done', 'invalid provider cookie')
    if os.path.lexists(cookie):
        require(regular(cookie), 'invalid provider cookie')
        old = parse_cookie(cookie, live)
    else:
        # A newly added buildlink dependency has no prior inventory. The same
        # factory and collision checks below safely add its links and cookie.
        old = {}
    others = set()
    for other in live.glob('.buildlink_*_done'):
        if other != cookie:
            require(regular(other), 'invalid other provider cookie')
            others.update(parse_cookie(other, live))
    with tempfile.TemporaryDirectory(prefix='buildlink-plan-') as tmp:
        candidate = Path(tmp)
        plan_cmd = cmd + ['BUILDLINK_DIR=' + tmp, 'BUILDLINK_X11_DIR=' + tmp, 'buildlink-' + a.provider]
        subprocess.run(plan_cmd, check=True)
        planned = parse_cookie(candidate / cookie.name, candidate)
        require(planned or not old, 'empty provider plan with existing links')
        files = {}
        for path in candidate.rglob('*'):
            if path.is_dir() and not path.is_symlink():
                continue
            rel = path.relative_to(candidate)
            if rel == Path(cookie.name):
                continue
            require(rel not in others, 'other provider collision: ' + str(rel))
            if path.is_symlink():
                require(rel in planned and os.readlink(path) == planned[rel], 'invalid planned link')
            else:
                require(regular(path) and path.suffix == '.la', 'unexpected candidate output')
                files[rel] = path.read_bytes().replace(os.fsencode(candidate), os.fsencode(live))
        require(set(planned) == {p.relative_to(candidate) for p in candidate.rglob('*') if p.is_symlink()}, 'incomplete candidate cookie')
        for rel, target in old.items():
            dst = safe_path(live, rel)
            require(rel not in others and ((not dst.exists() and not dst.is_symlink()) or
                    (dst.is_symlink() and os.readlink(dst) in (target, planned.get(rel)))), 'old link changed: ' + str(rel))
        for rel, target in planned.items():
            dst = safe_path(live, rel)
            if dst.exists() or dst.is_symlink():
                require(dst.is_symlink() and os.readlink(dst) in (target, old.get(rel)), 'destination collision: ' + str(rel))
        for rel, data in files.items():
            dst = safe_path(live, rel)
            if dst.exists() or dst.is_symlink():
                require(regular(dst) and dst.read_bytes() == data,
                        'unsupported changed .la: ' + str(rel))
        with tempfile.TemporaryDirectory(prefix='.buildlink-refresh-', dir=live) as stage:
            temp_cookie = Path(stage) / cookie.name
            filtered = ('( ( ' + files_cmd + ' ) | ' + shlex.quote(grep) + r" -v '\.la$' || : )").replace('$', '$$')
            real_cmd = cmd + ['_BLNK_COOKIE.' + a.provider + '=' + str(temp_cookie),
                              '_BLNK_FILES_CMD.' + a.provider + '=' + filtered, 'buildlink-' + a.provider]
            subprocess.run(real_cmd, check=True)
            actual = parse_cookie(temp_cookie, live)
            require(actual == planned, 'regenerated inventory differs from plan')
            for rel, target in actual.items():
                dst = safe_path(live, rel)
                require(dst.is_symlink() and os.readlink(dst) == target, 'generated link mismatch')
            for rel, data in files.items():
                dst = safe_path(live, rel)
                if dst.exists() or dst.is_symlink():
                    require(regular(dst) and dst.read_bytes() == data, 'generated .la mismatch')
            for rel in old.keys() - actual.keys():
                dst = safe_path(live, rel)
                if dst.exists() or dst.is_symlink():
                    require(dst.is_symlink() and os.readlink(dst) == old[rel], 'obsolete link changed')
                    dst.unlink()
            os.replace(temp_cookie, cookie)
    print('Refreshed buildlink provider:', a.provider)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit('buildlink refresh refused: ' + str(exc))
