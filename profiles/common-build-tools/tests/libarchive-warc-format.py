#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; shared libarchive format-check regression.
"""Compile the shared WARC source with the selected target and headers."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
for name in ('source', 'clang', 'sysroot', 'config-include', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
source = args.source / 'libarchive/archive_write_set_format_warc.c'
text = source.read_text()
annotation = '''#if defined(__GNUC__) || defined(__clang__)
\t    __attribute__((__format__(__strftime__, 2, 0)))
#endif
'''
assert annotation in text
assert 'WARC-Date: %Y-%m-%dT%H:%M:%SZ' in text
with tempfile.TemporaryDirectory(dir=args.work_dir) as temp:
    for name, contents, success in (
        ('baseline', text.replace(annotation, ''), False),
        ('fixed', text, True),
    ):
        input_path = Path(temp) / (name + '.c')
        input_path.write_text(contents)
        command = [str(args.clang), '--target=aarch64--netbsd',
                   '--sysroot=' + str(args.sysroot), '-std=gnu11', '-Wall',
                   '-Wformat=2', '-Werror', '-Wno-unused-parameter',
                   '-DPLATFORM_CONFIG_H="config_netbsd.h"',
                   '-I' + str(args.config_include), '-I' + str(source.parent),
                   '-c', str(input_path), '-o', str(Path(temp) / (name + '.o'))]
        result = subprocess.run(command, text=True, capture_output=True)
        assert (result.returncode == 0) == success, (name, result.stderr)
        if not success:
            assert 'missing-format-attribute' in result.stderr, result.stderr
print('libarchive WARC target format regression: passed')
