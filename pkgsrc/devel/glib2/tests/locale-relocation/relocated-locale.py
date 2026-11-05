#!/usr/bin/env python3
"""Exercise GLib locale lookup from the actual relocated shared library."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser()
for arg in ('cc', 'msgfmt', 'sdk', 'old-lib', 'new-lib', 'old-tool', 'new-tool', 'output'):
    p.add_argument('--' + arg, type=Path, required=True)
p.add_argument('--locale', default='fr_FR.UTF-8')
a = p.parse_args()
here = Path(__file__).resolve().parent
root = a.output.resolve()
root.mkdir(parents=True, exist_ok=True)
for mode, source in (('old', a.old_lib), ('new', a.new_lib)):
    prefix = root / mode
    (prefix / 'lib').mkdir(parents=True, exist_ok=True)
    dest = prefix / 'lib/libglib-2.0.0.dylib'
    shutil.copy2(source, dest)
    catalog = prefix / 'share/locale/fr/LC_MESSAGES/glib20.mo'
    catalog.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(a.msgfmt), '-o', str(catalog), str(here / 'fr.po')], check=True)
probe = root / 'locale-probe'
subprocess.run([str(a.cc), '-std=c11', '-I' + str(a.sdk / 'include/glib-2.0'),
                '-I' + str(a.sdk / 'lib/glib-2.0/include'), str(here / 'locale-probe.c'),
                '-L' + str(a.sdk / 'lib'), '-Wl,-rpath,' + str(a.sdk / 'lib'),
                '-lglib-2.0', '-o', str(probe)], check=True)
for mode, tool, expected in (('old', a.old_tool, 'EMBERBSD synthetic relocated locale probe'),
                             ('new', a.new_tool, 'EMBERBSD traduction relocalisee')):
    library = root / mode / 'lib/libglib-2.0.0.dylib'
    env = os.environ.copy()
    env.update(LC_ALL=a.locale, LANGUAGE='fr', XDG_DATA_DIRS=str(a.sdk / 'share'), DYLD_LIBRARY_PATH=str(library.parent))
    subprocess.run([str(probe), str(library), expected], env=env, check=True)
    env['DYLD_PRINT_LIBRARIES'] = '1'
    result = subprocess.run([str(tool), 'get', 'org.emberbsd.synthetic.missing', 'key'],
                            env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    translated = 'SCHEMA RELOCALISE org.emberbsd.synthetic.missing' in result.stderr
    if result.returncode == 0 or translated != (mode == 'new') or str(library) not in result.stderr:
        raise SystemExit(mode + ' gsettings locale or loaded library check failed')
    print(mode + ' actual gsettings PASS')
