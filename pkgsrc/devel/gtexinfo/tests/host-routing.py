#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check actual full-cross Texinfo host and target tool separation."""
import argparse
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--build', type=Path, required=True)
p.add_argument('--host-prefix', type=Path, required=True)
a = p.parse_args()
host = a.build / 'tools/tta'
assert host.joinpath('libtool').stat().st_size > 10000, 'host libtool was replaced'
assert '.cwrapper/bin/libtool' not in host.joinpath('libtool').read_text()
target = a.build / 'tta/libtool'
assert '.cwrapper/bin/libtool' in target.read_text(), 'target libtool not routed through wrapper'
log = host.joinpath('config.log').read_text()
assert "LIBUNISTRING='" + str(a.host_prefix / 'lib') in log
assert '-I' + str(a.host_prefix / 'include') in log
check = host / 'perl/CheckXS/config.log'
assert 'CWRAPPERS_CONFIG_DIR is missing' not in check.read_text()
print('Texinfo full-cross host/target routing: PASS')
