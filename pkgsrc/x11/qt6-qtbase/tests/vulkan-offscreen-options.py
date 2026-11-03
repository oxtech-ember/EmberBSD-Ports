#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check production QtBase options and consumer graph without a build."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', type=Path, required=True)
parser.add_argument('--work-parent', type=Path, required=True)
args = parser.parse_args()
if not args.bmake.is_absolute() or not args.bmake.is_file():
    raise SystemExit('Select an absolute bmake executable')
if not args.work_parent.is_absolute() or not args.work_parent.is_dir():
    raise SystemExit('Select an existing absolute work parent')
root = Path(__file__).resolve().parents[1]

def stub(path):
    lines = []
    for line in path.read_text().splitlines():
        if line.lstrip().startswith(('.include ', '.  include ')):
            line = 'TEST_INCLUDES+= ' + line.split('"')[1]
        lines.append(line)
    return '\n'.join(lines)

def run(fixture, fields):
    fixture.write_text(fixture.read_text() + '\nshow:\n' + ''.join(
        '\t@printf "%s\\n" ${' + field + ':Q}\n' for field in fields))
    result = subprocess.run([str(args.bmake), '-r', '-m', '/', '-f', str(fixture), 'show'],
                            capture_output=True, text=True)
    values = result.stdout.splitlines()
    if result.returncode or len(values) != len(fields):
        raise SystemExit('bmake failed: ' + result.stderr + result.stdout)
    return dict(zip(fields, values))

with tempfile.TemporaryDirectory(prefix='qt-vulkan-offscreen-', dir=args.work_parent) as work:
    fixture = Path(work) / 'fixture.mk'
    for platform, cross, options, valid in (
        ('NetBSD', 'yes', 'vulkan-offscreen', True),
        ('NetBSD', 'yes', 'software-rendering', True),
        ('NetBSD', 'yes', '', True),
        ('Linux', 'no', 'vulkan-offscreen', False),
        ('NetBSD', 'yes', 'vulkan-offscreen software-rendering', False),
        ('NetBSD', 'yes', 'vulkan-offscreen gtk3', False),
    ):
        fixture.write_text(f'OPSYS={platform}\nUSE_CROSS_COMPILE={cross}\n'
                           f'PKG_OPTIONS={options}\n' + stub(root / 'options.mk'))
        data = run(fixture, ('PKG_FAIL_REASON', 'CMAKE_CONFIGURE_ARGS',
                             'CONFIGURE_ARGS', 'PLIST.opengl', 'PLIST.vulkan', 'PLIST.vkkhrdisplay'))
        if bool(data['PKG_FAIL_REASON']) == valid:
            raise SystemExit('Invalid option acceptance: ' + platform + '/' + options)
        offscreen = 'vulkan-offscreen' in options
        if valid and ((data['PLIST.vkkhrdisplay'] == 'yes') != (platform == 'NetBSD' and options == '')):
            raise SystemExit('Unexpected Vulkan display plugin selection: ' + options)
        if offscreen and valid:
            flags = set(data['CMAKE_CONFIGURE_ARGS'].split())
            needed = {'-DFEATURE_vulkan:BOOL=ON', '-DFEATURE_xcb:BOOL=OFF',
                      '-DFEATURE_xlib:BOOL=OFF', '-DFEATURE_wayland:BOOL=OFF',
                      '-DFEATURE_egl:BOOL=OFF', '-DFEATURE_eglfs:BOOL=OFF', '-DFEATURE_vkkhrdisplay:BOOL=OFF',
                      '-DEMBERBSD_BSDFB_VULKAN_OFFSCREEN:BOOL=ON'}
            if not needed <= flags or data['PLIST.opengl'] or data['PLIST.vulkan'] != 'yes':
                raise SystemExit('Incomplete offscreen Vulkan selection: ' + repr(data))
    for options, has_glu, has_xcb in (
        ('vulkan-offscreen', False, False),
        ('software-rendering', False, True),
        ('', True, True),
    ):
        fixture.write_text('OPSYS=NetBSD\nUSE_CROSS_COMPILE=yes\n'
                           'PKG_BUILD_OPTIONS.qt6-qtbase=' + options + '\n' +
                           stub(root / 'buildlink3.mk'))
        data = run(fixture, ('TEST_INCLUDES',))
        includes = set(data['TEST_INCLUDES'].split())
        for dep, wanted in (('../../graphics/glu/buildlink3.mk', has_glu),
                            ('../../x11/libxcb/buildlink3.mk', has_xcb),
                            ('../../graphics/vulkan-headers/buildlink3.mk',
                             options != 'software-rendering')):
            if (dep in includes) != wanted:
                raise SystemExit('Unexpected consumer dependency: ' + dep + ' / ' + options)
    # Exercise the production EGL/GLU block with an EGL-capable Mesa selected.
    recipe = (root / 'Makefile').read_text()
    start = recipe.index('PLIST.x11=\tyes')
    end = recipe.index('.if empty(PKG_OPTIONS:Mheadless-generators)', start)
    source = recipe[start:end]
    source = '\n'.join('TEST_INCLUDES+= ' + line.split('"')[1]
                       if line.lstrip().startswith('.include ') else line
                       for line in source.splitlines())
    for options, egl in (('vulkan-offscreen', False), ('software-rendering', False), ('', True)):
        fixture.write_text('OPSYS=NetBSD\nUSE_CROSS_COMPILE=yes\nMESALIB_SUPPORTS_EGL=yes\n'
                           'EMBERBSD_COMMON_GRAPHICS=yes\nPKG_OPTIONS=' + options + '\n' + source)
        data = run(fixture, ('PLIST.egl', 'PLIST.egldevice'))
        if (data['PLIST.egl'] == 'yes') != egl or (data['PLIST.egldevice'] == 'yes') != egl:
            raise SystemExit('Unexpected EGL/EGLDevice selection: ' + options)
    # Makefile.common runs before the QtBase options resolver and must use
    # the explicitly selected target option from the MAKECONF.
    common = (root / 'Makefile.common').read_text()
    start = common.index('.if !empty(PLATFORM_SUPPORTS_WAYLAND:Myes)')
    end = common.index('# CMake validates imported include directories', start)
    source = common[start:end]
    for options, enabled in (('vulkan-offscreen', False), ('', True)):
        fixture.write_text('PLATFORM_SUPPORTS_WAYLAND=yes\n'
                           'EMBERBSD_WAYLAND_SCANNER=/bin/sh\n'
                           'PKG_OPTIONS.qt6-qtbase=' + options + '\n' + source)
        data = run(fixture, ('CMAKE_CONFIGURE_ARGS', 'PKG_FAIL_REASON'))
        if ('-DFEATURE_wayland_client:BOOL=ON' in data['CMAKE_CONFIGURE_ARGS']) != enabled:
            raise SystemExit('Unexpected common Wayland selection: ' + options)
print('PASS: option, consumer, EGL and common Wayland graph selections; no build')
