#!/usr/bin/env python3
"""Fetch the libserialport archive and verify it against distinfo."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True, help='bmake with the host mk files')
    parser.add_argument('--makeconf', required=True, help='MAKECONF with the Ports fetch client')
    parser.add_argument('--recipe', required=True, help='exported comms/libserialport')
    args = parser.parse_args()
    recipe = Path(args.recipe).resolve(strict=True)
    distinfo = (recipe / 'distinfo').read_text(encoding='utf-8')
    digest = re.search(r'^SHA512 \((\S+)\) = ([0-9a-f]{128})$', distinfo, re.M)
    size = re.search(r'^Size \(\S+\) = ([0-9]+) bytes$', distinfo, re.M)
    with tempfile.TemporaryDirectory() as temp:
        # A fresh DISTDIR makes the result depend only on MASTER_SITES.
        subprocess.run([args.bmake, 'MAKECONF=' + args.makeconf, 'DISTDIR=' + temp,
                        'WRKOBJDIR=' + temp + '/work', 'fetch'], cwd=recipe, check=True)
        data = (Path(temp) / digest.group(1)).read_bytes()
    assert hashlib.sha512(data).hexdigest() == digest.group(2)
    assert len(data) == int(size.group(1))
    print('PASS: fetched %s from MASTER_SITES with the distinfo checksum.' % digest.group(1))


if __name__ == '__main__':
    main()
