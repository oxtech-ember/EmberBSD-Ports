#!/usr/bin/env python3
"""Exercise installed GLib gi-compile-repository default GIR lookup on Darwin."""
import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--prefix', type=Path, required=True, help='disposable installed prefix')
p.add_argument('--old-prefix', type=Path, required=True, help='existing producer prefix')
a = p.parse_args()
if platform.system() != 'Darwin':
    raise SystemExit('This fixture requires native Darwin GLib tools.')
prefix, old = a.prefix.resolve(strict=True), a.old_prefix.resolve(strict=True)
if prefix == old:
    raise SystemExit('the relocated and producer prefixes must differ')
tool = prefix / 'bin/gi-compile-repository'
old_gir = old / 'share/gir-1.0/GLib-2.0.gir'
new_gir = prefix / 'share/gir-1.0/GLib-2.0.gir'
if not tool.is_file() or not old_gir.is_file():
    raise SystemExit('installed compiler and producer GLib GIR are required')
if new_gir.exists() or new_gir.is_symlink():
    raise SystemExit('use a disposable prefix without a pre-existing GLib GIR')
if Path('/usr/share/gir-1.0/GLib-2.0.gir').exists():
    raise SystemExit('system GIR masks the negative control on this host')
with tempfile.TemporaryDirectory(prefix='glib-gir-test-') as temp:
    root = Path(temp)
    empty = root / 'empty'
    empty.mkdir()
    source = root / 'Probe-1.0.gir'
    source.write_text('<?xml version="1.0"?><repository version="1.2" '
                      'xmlns="http://www.gtk.org/introspection/core/1.0" '
                      'xmlns:c="http://www.gtk.org/introspection/c/1.0">'
                      '<include name="GLib" version="2.0"/><namespace '
                      'name="Probe" version="1.0"/></repository>')
    env = os.environ.copy()
    for name in ('GI_GIR_PATH', 'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH',
                 'DYLD_FRAMEWORK_PATH', 'DYLD_FALLBACK_LIBRARY_PATH',
                 'DYLD_INSERT_LIBRARIES'):
        env.pop(name, None)
    env.update(XDG_DATA_HOME=str(empty), XDG_DATA_DIRS=str(empty),
               G_MESSAGES_DEBUG='all', DYLD_PRINT_LIBRARIES='1')
    def run(name, extra, expected, selected=None, extra_env=None):
        e = env.copy()
        e.update(extra_env or {})
        result = subprocess.run([str(tool), '--debug', *extra, '-o',
                                 str(root / (name + '.typelib')), str(source)],
                                env=e, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=60)
        (root / (name + '.log')).write_text(result.stdout)
        if (result.returncode == 0) != expected:
            raise RuntimeError(name + ': unexpected exit ' + str(result.returncode))
        moved_lib = str(prefix / 'lib/libglib-2.0.0.dylib')
        if moved_lib not in result.stdout:
            raise RuntimeError(name + ': relocated GLib image not observed')
        if selected and ('Parsing include ' + str(selected)) not in result.stdout:
            raise RuntimeError(name + ': wrong GIR selected')
        if not expected and ('Parsing include ' + str(old_gir)) in result.stdout:
            raise RuntimeError(name + ': implicit producer GIR was used')
        print(name, 'PASS')
    run('missing', [], False)
    new_gir.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        # Never overwrite an installed file; the prefix is disposable and this
        # fixture removes only the file which it created.
        with new_gir.open('xb') as f:
            created = True
            f.write(old_gir.read_bytes())
        run('relocated-default', [], True, new_gir)
    finally:
        if created:
            new_gir.unlink(missing_ok=True)
    run('includedir', ['--includedir=' + str(old_gir.parent)], True, old_gir)
    run('gir-path', [], True, old_gir, {'GI_GIR_PATH': str(old_gir.parent)})
print('GLib installed GIR default and override checks PASS')
