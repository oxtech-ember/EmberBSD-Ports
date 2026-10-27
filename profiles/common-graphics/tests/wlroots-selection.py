#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual consumer recipe and scanner guards.
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'makeconf', 'host-prefix', 'utility-path', 'work'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if any(not path.is_absolute() for path in vars(args).values()) or args.work.exists():
        parser.error('supply absolute inputs and a new work directory')
    prefix = args.host_prefix
    if not Path(sys.executable).resolve().is_relative_to(prefix.resolve()):
        parser.error('run with the selected native prefix Python')
    args.work.mkdir()
    environment = dict(os.environ, PATH=str(args.utility_path))
    base = [str(prefix/'bin/bmake'), '-m', str(prefix/'share/mk'),
        'SHELL='+str(prefix/'bin/mksh'), '-C', str(args.pkgsrc/'wayland/wlroots'),
        'MAKECONF='+str(args.makeconf), 'WRKOBJDIR='+str(args.work/'objects')]
    checks = []

    def run(name, extra=(), success=True):
        result = subprocess.run([*base, *extra], env=environment, capture_output=True, text=True)
        output = result.stdout+result.stderr
        (args.work/(name+'.log')).write_text(output)
        assert (result.returncode == 0) == success, name+'\n'+output
        return result.stdout

    def parse(name, extra=()):
        names = ['PKG_FAIL_REASON', 'PKG_OPTIONS', 'MESON_ARGS', 'TOOL_DEPENDS',
                 'DEPENDS', 'TOOLBASE', 'EMBERBSD_WAYLAND_SCANNER']
        result = run(name, [*extra, *[part for var in names for part in ('-V', '${'+var+'}')]])
        values = result.splitlines();assert len(values)==len(names), result
        return dict(zip(names, values))

    minimal = parse('minimal', ['EMBERBSD_WLROOTS_PROFILE=headless-gles2'])
    assert not minimal['PKG_FAIL_REASON'] and minimal['PKG_OPTIONS']=='glesv2', minimal
    assert set(['-Dallocators=gbm', '-Drenderers=gles2', '-Dbackends=', '-Dsession=disabled',
        '-Dxwayland=disabled', '-Dexamples=false', '--wrap-mode=nofallback']) <= set(shlex.split(minimal['MESON_ARGS']))
    assert not re.search(r'glslang|hwdata|seatd|libopeninput|libliftoff|lcms2|cairo|vulkan-loader|xcb-util',minimal['TOOL_DEPENDS']+minimal['DEPENDS'])
    checks.append('headless GLES2 excludes optional dependency closure')
    full = parse('full', ['EMBERBSD_WLROOTS_PROFILE=full'])
    assert not full['PKG_FAIL_REASON'], full
    assert set(full['PKG_OPTIONS'].split())==set('glesv2 vulkan drm libinput x11 session color-management libliftoff examples xwayland xcb-errors'.split())
    assert ':../../graphics/glslang' in full['TOOL_DEPENDS'] and ':../../sysutils/hwdata' in full['TOOL_DEPENDS']
    assert not re.search(r'glslang|hwdata',full['DEPENDS'])
    checks.append('full route preserves functions and native generator dependency roles')
    drm = parse('drm', ['EMBERBSD_WLROOTS_PROFILE=drm-gles2'])
    assert not drm['PKG_FAIL_REASON'], drm
    assert set(drm['PKG_OPTIONS'].split())==set('glesv2 drm libinput session color-management libliftoff'.split())
    assert set(['-Drenderers=gles2','-Dbackends=drm,libinput','-Dsession=enabled',
        '-Dcolor-management=enabled','-Dlibliftoff=enabled']) <= set(shlex.split(drm['MESON_ARGS']))
    assert 'hwdata>=0.412:../../sysutils/hwdata' in drm['TOOL_DEPENDS']
    assert 'glslang' not in drm['TOOL_DEPENDS'] and not re.search(r'vulkan-loader|cairo|xcb-util',drm['DEPENDS'])
    checks.append('DRM stage retains input, session, color and plane allocation')
    native = parse('native', ['USE_CROSS_COMPILE=no'])
    assert not native['PKG_FAIL_REASON'] and native['PKG_OPTIONS']==full['PKG_OPTIONS'], native
    checks.append('native defaults unchanged')
    for name, extra, expected in (
        ('unknown-profile', ['EMBERBSD_WLROOTS_PROFILE=unknown'], 'must be full, headless-gles2 or drm-gles2'),
        ('minimal-override', ['EMBERBSD_WLROOTS_PROFILE=headless-gles2','PKG_OPTIONS.wlroots=glesv2 vulkan'], 'rejects option overrides'),
        ('drm-override', ['EMBERBSD_WLROOTS_PROFILE=drm-gles2','PKG_OPTIONS.wlroots=glesv2'], 'rejects option overrides'),
        ('missing-session', ['EMBERBSD_WLROOTS_PROFILE=full','PKG_OPTIONS.wlroots=-session'], 'require the session option')):
        value = parse(name, extra)
        assert expected in value['PKG_FAIL_REASON'], value
        checks.append(name+' refused')
    run('scanner-positive', ['EMBERBSD_WLROOTS_PROFILE=headless-gles2','emberbsd-scanner-check'])
    run('wrong-scanner', ['EMBERBSD_WLROOTS_PROFILE=headless-gles2',
        'EMBERBSD_WAYLAND_SCANNER=/usr/bin/false','emberbsd-scanner-check'], success=False)
    assert 'differs from the native Ports prefix' in (args.work/'wrong-scanner.log').read_text()
    checks.append('actual pre-configure accepts selected scanner and refuses external selection')
    # Copy only required native tools for a semantic negative. A different
    # scanner version must fail without a separate checksum admission file.
    negative = args.work/'negative-prefix'
    (negative/'bin').mkdir(parents=True);(negative/'lib/pkgconfig').mkdir(parents=True)
    for name in ('python3.15','pkg-config','wayland-scanner'):
        shutil.copy2(prefix/'bin'/name,negative/'bin'/name)
    pc=(prefix/'lib/pkgconfig/wayland-scanner.pc').read_text().replace(str(prefix),str(negative))
    (negative/'lib/pkgconfig/wayland-scanner.pc').write_text(pc)
    override=['EMBERBSD_WLROOTS_PROFILE=headless-gles2','TOOLBASE='+str(negative),
        'TOOL_PYTHONBIN='+str(negative/'bin/python3.15'),
        'EMBERBSD_WAYLAND_SCANNER='+str(negative/'bin/wayland-scanner'),'emberbsd-scanner-check']
    run('copied-scanner-positive',override)
    (negative/'bin/wayland-scanner').write_text('#!'+str(negative/'bin/python3.15')+'\nprint("wayland-scanner 1.25.0")\n')
    run('scanner-negative',override,success=False)
    assert 'must report exactly 1.26.0' in (args.work/'scanner-negative.log').read_text()
    checks.append('actual pre-configure refuses wrong scanner version')
    summary={'passed':checks,'scope':'actual recipe selection and native scanner guard; no target renderer execution'}
    (args.work/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
