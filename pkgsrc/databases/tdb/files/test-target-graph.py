#!/usr/bin/env python3
"""Check the ordinary TDB target build avoids an unused host replacement task."""
from pathlib import Path
import sys

log = Path(sys.argv[1]).read_text()
assert "'build' finished successfully" in log
assert log.count('Compiling lib/replace/replace.c') == 1
assert 'Linking ' in log and 'libtdb.so' in log
print('TDB target build graph: PASS')
