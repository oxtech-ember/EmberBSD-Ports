#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Upstream status: not submitted.
"""Check pkgsrc's selected libpcap builtin header on a cross metadata query."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('bmake', 'shell', 'grep', 'package', 'makeconf', 'sysroot', 'path', 'tmpdir', 'version'):
    parser.add_argument('--' + name, required=True)
parser.add_argument('--override-prefix', action='store_true')
parser.add_argument('--native', action='store_true')
parser.add_argument('--make-arg', action='append', default=[])
a = parser.parse_args()
for value in (a.bmake, a.shell, a.grep, a.package, a.makeconf, a.tmpdir):
    assert Path(value).is_absolute()
with tempfile.TemporaryDirectory(dir=a.tmpdir, prefix='pcap-builtin-') as tmp:
    root = Path(tmp)
    log = root / 'grep-argv'
    wrapper = root / 'grep'
    wrapper.write_text('#!' + a.shell + '\n' +
                       'printf "%s\\n" "$@" >> ' + shlex.quote(str(log)) + '\n' +
                       'exec ' + shlex.quote(a.grep) + ' "$@"\n')
    wrapper.chmod(0o755)
    env = dict(os.environ, PATH=a.path, MAKECONF=a.makeconf, TMPDIR=a.tmpdir)
    overrides = ['TOOLS_CROSS_DESTDIR=' + a.sysroot] if a.override_prefix else []
    overrides += a.make_arg
    result = subprocess.run([a.bmake, '-C', a.package, 'GREP=' + str(wrapper), *overrides,
                             '-V', '${H_LIBPCAP}', '-V', '${TOOLS_CROSS_DESTDIR}',
                             '-V', '${BUILTIN_VERSION.libpcap}', '-V', '${USE_BUILTIN.libpcap}'],
                            env=env, text=True, capture_output=True)
    assert result.returncode == 0 and not result.stderr, result.stderr
    header, prefix, version, builtin = result.stdout.splitlines()
    assert prefix == ('' if a.native else a.sysroot) and version == a.version and builtin == 'yes', result.stdout
    target = prefix + header
    assert Path(target).is_file() and not target.startswith(root.as_posix())
    args = log.read_text().splitlines()
    assert args.count(target) == 9, args
    if not a.native:
        assert header not in args, args
print('libpcap builtin selected header and version: PASS')
