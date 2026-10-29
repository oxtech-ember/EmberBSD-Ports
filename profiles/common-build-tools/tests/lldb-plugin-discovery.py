#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise LLDB plugin search using an isolated Darwin liblldb and home."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('clang', 'lldb', 'liblldb', 'sysroot'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
with tempfile.TemporaryDirectory(prefix='lldb-plugin-discovery-') as td:
    root = Path(td); lib = root / 'lib'; lib.mkdir(); home = root / 'home'; home.mkdir()
    shutil.copy2(a.liblldb, lib / 'liblldb.23.1.4.dylib')
    (lib / 'liblldb.23.1.dylib').symlink_to('liblldb.23.1.4.dylib')
    marker = root / 'loaded'
    source = root / 'plugin.c'
    source.write_text('''#include <stdio.h>\n#include <stdlib.h>\n#include <stdbool.h>\nbool INIT(void) { const char *p=getenv("LLDB_TEST_MARKER"); FILE *f=fopen(p,"a"); if (!f) return false; fputs(LABEL "\\n",f); fclose(f); return true; }\n''')
    fixtures = [
        (lib / 'liblldbPluginRoot.dylib', 'lldb_initialize_Root', 'root'),
        (lib / 'liblldbPluginLink.dylib', None, 'link'),
        (lib / 'ignored' / 'liblldbPluginIgnored.dylib', 'lldb_initialize_Ignored', 'ignored'),
        (lib / 'lldb/plugins/nested' / 'dedicated.dylib', 'LLDBPluginInitialize', 'dedicated'),
        (home / 'Library/Application Support/LLDB/PlugIns/nested' / 'user.dylib', 'LLDBPluginInitialize', 'user'),
    ]
    link_target = root / 'liblldbPluginLink.dylib'
    for path, symbol, label in fixtures:
        path.parent.mkdir(parents=True, exist_ok=True)
        if symbol is None:
            subprocess.run([str(a.clang), '-isysroot', str(a.sysroot), '-dynamiclib',
                            '-DINIT=lldb_initialize_Link', '-DLABEL="link"', str(source),
                            '-o', str(link_target)], check=True, capture_output=True)
            path.symlink_to(link_target)
        else:
            subprocess.run([str(a.clang), '-isysroot', str(a.sysroot), '-dynamiclib',
                            '-DINIT=' + symbol, '-DLABEL="' + label + '"', str(source),
                            '-o', str(path)], check=True, capture_output=True)
    env = {k: os.environ[k] for k in ('PATH', 'TMPDIR', 'USER', 'LOGNAME') if k in os.environ}
    env.update(HOME=str(home), DYLD_LIBRARY_PATH=str(lib), LLDB_TEST_MARKER=str(marker), LC_ALL='C')
    result = subprocess.run([str(a.lldb), '--version'], env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    assert result.returncode == 0, result.stderr
    found = marker.read_text().splitlines()
    assert sorted(found) == ['dedicated', 'link', 'root', 'user'], found
    print('PASS: root and symlink plugins; nested dedicated and user plugins; unrelated subtree skipped')
