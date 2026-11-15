#!/usr/bin/env python3
"""Independently check the core PLIST against the pinned upstream inputs.

Usage: check-core.py PATH_TO_PATCHED_XAPP_SOURCE PATH_TO_RECIPE
This validates source-level inventory, not a staged Meson install.
"""
import hashlib
import re
import sys
from pathlib import Path
src, recipe = map(Path, sys.argv[1:])
meson = (src / 'libxapp/meson.build').read_text()
opt = (src / 'meson_options.txt').read_text()
top = (src / 'meson.build').read_text()
make = (recipe / 'Makefile').read_text()
raw = (recipe / 'PLIST').read_text().splitlines()
lines = [s for s in raw if not s.startswith('@comment')]
assert len(lines) == len(set(lines)), 'duplicate paths in PLIST'
headers_block = re.search(r'xapp_headers\s*=\s*\[(.*?)\]', meson, re.S).group(1)
headers = set(re.findall(r"'([^']+\.h)'", headers_block))
headers.add('xapp-statusicon-interface.h')  # installed gdbus-codegen header
expected = {'include/xapp/libxapp/' + h for h in headers}
expected |= {
    '${PYSITELIB}/gi/overrides/XApp.py',
    'lib/girepository-1.0/XApp-1.0.typelib',
    'lib/libxapp.so', 'lib/libxapp.so.1', 'lib/libxapp.so.3.4.0',
    'lib/pkgconfig/xapp.pc', 'share/gir-1.0/XApp-1.0.gir',
    'share/glade/catalogs/xapp-glade-catalog.xml',
    'share/glib-2.0/schemas/org.x.apps.gschema.xml',
}
langs = (src / 'po/LINGUAS').read_text().splitlines()
expected |= {'share/locale/' + lang.strip() + '/LC_MESSAGES/xapp.mo'
             for lang in langs if lang.strip() and not lang.startswith('#')}
assert set(lines) == expected, ('missing', sorted(expected - set(lines)), 'extra', sorted(set(lines) - expected))
for token in ('-Dapp-lib-only=true', '-Dintrospection=true', '-Dkbd-layout-controller=disabled',
              '-Dstatus-notifier=false', '-Dgtk-layer-shell=disabled', '-Dmate=false', '-Dxfce=false',
              '-Dwayland-backend=enabled', '-Dwayland-backend=disabled',
              '../../devel/wayland-protocols/cross-scanner.mk'):
    assert token in make, token
assert "option('wayland-backend'" in opt
for name in ('wayland-scanner', 'wayland-client', 'gdk-wayland-3.0'):
    assert re.search(r"dependency\('" + re.escape(name) + r"', required: get_option\('wayland-backend'\)", meson), name
assert 'if not app_lib_only' in top and "subdir('icons')" in top
for file in (recipe / 'patches').iterdir():
    assert hashlib.sha1(file.read_bytes()).hexdigest() in (recipe / 'distinfo').read_text(), file.name
print('PASS: source-derived core inventory, locale list, explicit backends and patch hashes')
