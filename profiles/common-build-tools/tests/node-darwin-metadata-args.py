#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""node-darwin-metadata.py must forward every required node26-source.py option."""
from pathlib import Path
import re

here = Path(__file__).resolve().parent
source = (here / 'node26-source.py').read_text()
required = re.search(r"for option in \(([^)]*)\):\n\s+p\.add_argument\('--' \+ option, type=Path, required=True\)",
                     source).group(1)
options = re.findall(r"'([a-z-]+)'", required)
assert options, 'node26-source.py required options not found'
caller = (here / 'node-darwin-metadata.py').read_text()
call = caller[caller.index("tests/node26-source.py'"):]
call = call[:call.index('args.work)')]
missing = [o for o in options if "'--" + o + "'" not in call]
assert not missing, 'node-darwin-metadata.py does not pass: ' + ', '.join(missing)
head = caller[:caller.index("tests/node26-source.py'")]
assert "'-S'" not in head[head.rindex("run('source'"):], 'node26-source.py needs site-packages for GYP packaging'
print('PASS: node-darwin-metadata forwards', ', '.join(options))
