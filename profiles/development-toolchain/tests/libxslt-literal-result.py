#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted); Chromium issue 503879106.
"""Check DTD handling in a literal-result XSLT stylesheet with selected xsltproc."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('xsltproc', type=Path)
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix='libxslt-literal-') as temp:
    root = Path(temp)
    (root / 'input.xml').write_text('<root/>\n')
    (root / 'style.xsl').write_text(
        '<!DOCTYPE html [<!-- comment --><!ENTITY x "test">]>\n'
        '<html xmlns:xsl="http://www.w3.org/1999/XSL/Transform" '
        'xsl:version="1.0">&x;</html>\n')
    result = subprocess.run([str(args.xsltproc.resolve(strict=True)),
                             str(root / 'style.xsl'), str(root / 'input.xml')],
                            capture_output=True, text=True, timeout=30)
    if result.returncode != 0 or '<html>test</html>' not in result.stdout:
        raise SystemExit(f'FAIL: exit={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}')
print('PASS: literal-result stylesheet with DTD comment and entity')
