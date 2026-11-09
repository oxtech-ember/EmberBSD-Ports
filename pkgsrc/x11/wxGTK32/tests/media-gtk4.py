#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run the actual GTK4 media mailbox/sample/snapshot code against native GLib.

Only GDK drawing and GStreamer sample inputs are mocked. Real GSource, mutex,
GObject weak references and worker threads exercise shutdown and dispatch.
This does not establish media decoding, audio output or GUI presentation.
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cxx', required=True)
    parser.add_argument('--pkg-config', required=True)
    parser.add_argument('--cxx-flag', action='append', default=[])
    parser.add_argument('--work-parent', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.read_text()
    # Test complete production presentation methods, excluding only the thin
    # GObject renderer registration whose ABI is checked by the target TU.
    source = source[source.index('struct wxGTKMediaFrame'):source.index('// GstPlayer\'s public renderer')]
    harness = Path(__file__).with_name('media-gtk4-harness.cpp').read_text()
    harness = harness.replace('// PRODUCTION_MEDIA_PRESENTATION', source)
    flags = shlex.split(subprocess.check_output(
        [args.pkg_config, '--cflags', '--libs', 'gobject-2.0'], text=True))
    with tempfile.TemporaryDirectory(prefix='wx-media-', dir=args.work_parent) as work:
        cpp, exe = Path(work)/'contract.cpp', Path(work)/'contract'
        cpp.write_text(harness)
        subprocess.run([args.cxx, '-std=c++17', '-pthread', '-Wall', '-Wextra',
                        '-Werror', *args.cxx_flag, str(cpp), *flags, '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True, timeout=20,
                       env={**os.environ, 'G_DEBUG': 'fatal-criticals'})


if __name__ == '__main__':
    main()
