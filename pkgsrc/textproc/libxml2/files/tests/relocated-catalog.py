#!/usr/bin/env python3
# $NetBSD$
# Origin: EmberBSD (AI-assisted).
# Regression: a libxml2 shared library copied into another prefix must load
# that prefix's etc/xml/catalog when XML_CATALOG_FILES is unset.
#
# usage: relocated-catalog.py PREFIX [XMLCATALOG]
# PREFIX holds lib/libxml2* and etc/xml/catalog. XMLCATALOG defaults to
# PREFIX/bin/xmlcatalog and is copied beside the relocated library.
import os
import shutil
import subprocess
import sys
import tempfile

if len(sys.argv) < 2:
    raise SystemExit('usage: relocated-catalog.py PREFIX [XMLCATALOG]')
prefix = os.path.abspath(sys.argv[1])
xmlcatalog = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(prefix, 'bin/xmlcatalog')
libdir = os.path.join(prefix, 'lib')
catalog = os.path.join(prefix, 'etc/xml/catalog')
if not os.path.isfile(catalog):
    raise SystemExit(f'FAIL: missing catalog {catalog}')
libs = [name for name in os.listdir(libdir)
        if name.startswith('libxml2.') and not name.endswith('.la') and not name.endswith('.a')]
if not libs:
    raise SystemExit(f'FAIL: no libxml2 shared library in {libdir}')

entity = 'http://docbook.sourceforge.net/release/xsl/current/manpages/docbook.xsl'
probe = subprocess.run([xmlcatalog, catalog, entity], capture_output=True, text=True)
if probe.returncode != 0 or not probe.stdout.strip():
    sys.stderr.write(probe.stderr)
    raise SystemExit('FAIL: selected prefix catalog does not resolve the probe entity')
expected = probe.stdout.strip()

with tempfile.TemporaryDirectory(prefix='libxml2-relocated-') as tmp:
    moved = os.path.join(tmp, 'prefix')
    os.makedirs(os.path.join(moved, 'bin'))
    os.makedirs(os.path.join(moved, 'lib'))
    os.makedirs(os.path.join(moved, 'etc/xml'))
    shutil.copy2(xmlcatalog, os.path.join(moved, 'bin/xmlcatalog'))
    for name in libs:
        src = os.path.join(libdir, name)
        dst = os.path.join(moved, 'lib', name)
        if os.path.islink(src):
            os.symlink(os.readlink(src), dst)
        else:
            shutil.copy2(src, dst)
    shutil.copy2(catalog, os.path.join(moved, 'etc/xml/catalog'))
    share_xml = os.path.join(prefix, 'share/xml')
    share_xsl = os.path.join(prefix, 'share/xsl')
    if os.path.isdir(share_xml):
        os.makedirs(os.path.join(moved, 'share'), exist_ok=True)
        os.symlink(share_xml, os.path.join(moved, 'share/xml'))
    if os.path.isdir(share_xsl):
        os.makedirs(os.path.join(moved, 'share'), exist_ok=True)
        os.symlink(share_xsl, os.path.join(moved, 'share/xsl'))
    env = {key: value for key, value in os.environ.items() if key != 'XML_CATALOG_FILES'}
    lib_env = os.path.join(moved, 'lib')
    for key in ('DYLD_LIBRARY_PATH', 'LD_LIBRARY_PATH'):
        prev = env.get(key, '')
        env[key] = lib_env if not prev else lib_env + os.pathsep + prev
    tool = os.path.join(moved, 'bin/xmlcatalog')
    result = subprocess.run([tool, '', entity], capture_output=True, text=True, env=env)
    if result.returncode != 0 or expected not in result.stdout:
        sys.stderr.write(result.stderr)
        sys.stderr.write(result.stdout)
        raise SystemExit('FAIL: relocated libxml2 did not use its own default catalog')
    env['XML_CATALOG_FILES'] = '/nonexistent/xml/catalog'
    blocked = subprocess.run([tool, '', entity], capture_output=True, text=True, env=env)
    if expected in blocked.stdout:
        raise SystemExit('FAIL: XML_CATALOG_FILES override was ignored')
print('PASS: relocated libxml2 default catalog follows the library prefix')
