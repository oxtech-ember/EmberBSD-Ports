#!/usr/bin/env python3
"""Check the actual frame-release dispatch against real GLib worker/main loops.

Only the GL deletion callback and wx thread-identity predicate are harness
callbacks. No GTK or GL headers, context or renderer is emulated.
Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--cxx', required=True)
p.add_argument('--pkg-config', required=True)
p.add_argument('--cxx-flag', action='append', default=[])
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
s = (a.source / 'src/gtk/glcanvas_gtk4.inc').read_text()
start = s.index('static void wxGTKGLReleaseFrame(')
end = s.index('\nstatic void wxGTKGLSnapshot(', start)
method = s[start:end]
harness = r'''
#include <glib.h>
#include <atomic>
#include <cstdio>
static GThread* ui;
static std::atomic<int> calls(0), wrong(0);
static bool wxIsMainThread() { return g_thread_self() == ui; }
static gboolean wxGTKGLDeleteFrame(gpointer)
{
    if (!wxIsMainThread()) ++wrong;
    ++calls;
    return G_SOURCE_REMOVE;
}
METHOD
static gpointer Release(gpointer data) { wxGTKGLReleaseFrame(data); return NULL; }
int main()
{
    ui = g_thread_self();
    // The UI deliberately does not own the default context: invoke() is then
    // allowed to execute immediately in a worker, which this case must reject.
    GThread* worker = g_thread_new("release", Release, NULL);
    g_thread_join(worker);
    if (calls != 0 || wrong != 0) return 1;
    while (g_main_context_iteration(NULL, FALSE)) {}
    if (calls != 1 || wrong != 0) return 2;
    wxGTKGLReleaseFrame(NULL);
    if (calls != 2 || wrong != 0) return 3;
    std::puts("frame release queues worker cleanup and executes on UI thread PASS");
    return 0;
}
'''.replace('METHOD', method)
flags = shlex.split(subprocess.check_output(
    [a.pkg_config, '--cflags', '--libs', 'glib-2.0'], text=True))
with tempfile.TemporaryDirectory(prefix='wx-gl-release-', dir=a.work_parent) as tmp:
    path = Path(tmp) / 'release.cpp'
    path.write_text(harness)
    binary = Path(tmp) / 'release'
    subprocess.run([a.cxx, '-std=c++11', '-Wall', '-Wextra', '-Werror',
                    *a.cxx_flag, str(path), *flags, '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True, timeout=10,
                   env={**os.environ, 'G_DEBUG': 'fatal-criticals'})
