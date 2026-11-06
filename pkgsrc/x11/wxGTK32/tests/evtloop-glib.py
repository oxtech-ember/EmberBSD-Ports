#!/usr/bin/env python3
"""Run production wxGTK4 loop methods against real GLib, without a GTK display.

This is a bounded method-level check, not compilation of the whole wxGTK port.
The harness supplies the wx base-class lifecycle and app callbacks; loop methods
and native timeout callback are extracted verbatim from the prepared source.
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


def definition(text, name):
    start = text.index(name)
    start = text.rfind('\n', 0, start) + 1
    if text[start:].startswith(('wx_emission_hook(',)):
        start = text.rfind('\n', 0, start - 1) + 1
    brace = text.index('{', start)
    level = 1
    end = brace + 1
    while level:
        if text[end] == '{':
            level += 1
        elif text[end] == '}':
            level -= 1
        end += 1
    return text[start:end] + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cxx', required=True)
    parser.add_argument('--pkg-config', required=True)
    parser.add_argument('--cxx-flag', action='append', default=[])
    parser.add_argument('--work-parent', type=Path, required=True)
    args = parser.parse_args()
    source = (args.source / 'src/gtk/evtloop.cpp').read_text()
    methods = ['wxGUIEventLoop::wxGUIEventLoop()', 'wxGUIEventLoop::DoRun()',
               'wxGUIEventLoop::ScheduleExit(', 'wxGUIEventLoop::WakeUp()',
               'wxGUIEventLoop::Pending()', 'wxGUIEventLoop::Dispatch()',
               'wx_event_loop_timeout(', 'wxGUIEventLoop::DispatchTimeout(',
               'wxGUIEventLoop::YieldFor(', 'wxGUIEventLoop::DoYieldFor(']
    harness = Path(__file__).with_name('evtloop-glib-harness.cpp').read_text()
    harness = harness.replace('// PRODUCTION_LOOP_METHODS',
                              '\n'.join(definition(source, name) for name in methods))
    app = (args.source / 'src/gtk/app.cpp').read_text()
    app_methods = ["wx_emission_hook(", "wx_add_idle_hooks()", "wxapp_idle_callback(",
                   "wxApp::DoIdle()", "wxApp::WakeUpIdle()", "wxApp::EventsPending()"]
    harness = harness.replace('// PRODUCTION_IDLE_METHODS',
                              '\n'.join(definition(app, name) for name in app_methods))
    flags = shlex.split(subprocess.check_output(
        [args.pkg_config, '--cflags', '--libs', 'gobject-2.0'], text=True))
    with tempfile.TemporaryDirectory(prefix='wx-evtloop-', dir=args.work_parent) as work:
        source_path = Path(work) / 'contract.cpp'
        source_path.write_text(harness)
        executable = Path(work) / 'contract'
        subprocess.run([args.cxx, '-std=c++11', '-Wall', '-Wextra', '-Werror',
                        *args.cxx_flag, str(source_path), *flags, '-o', str(executable)], check=True)
        subprocess.run([str(executable)], check=True, timeout=20,
                       env={**os.environ, "G_DEBUG": "fatal-criticals"})


if __name__ == '__main__':
    main()
