#!/usr/bin/env python3
"""Compare Waf's optional archive with the compiled TDB target objects."""
import json
from pathlib import Path
import subprocess
import sys

ar = Path(sys.argv[1])
enabled = Path(sys.argv[2])
default = Path(sys.argv[3])
assert ar.is_absolute()
archive = enabled / 'libtdb.a'
assert archive.is_file()
assert not (default / 'libtdb.a').exists()
commands = json.loads((enabled / 'compile_commands.json').read_text())
objects = []
for command in commands:
    outputs = [arg[2:] for arg in command['arguments'] if arg.startswith('-o') and len(arg) > 2]
    assert len(outputs) == 1
    objects.append(Path(outputs[0]).name)
archive_members = subprocess.check_output([str(ar), 't', str(archive)], text=True).splitlines()
assert len(objects) == len(set(objects))
assert sorted(archive_members) == sorted(objects)
assert archive_members
print('Waf optional TDB static archive: PASS')
