#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the producer's strict and incremental runtime-hook input rule."""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit('usage: host-runtime-hook.py SHELL')
producer = (Path(__file__).resolve().parents[1] / 'cross/build-host-tools.sh').read_text()
start = producer.index('        # An incremental configure may adopt the current owner runtime hook.')
end = producer.index('        old_path=$tool', start)
policy = producer[start:end]
with tempfile.TemporaryDirectory(prefix='qt-runtime-hook-') as tmp:
    root = Path(tmp)
    hook = root / 'native-host-runtime.cmake'
    old = b'execute_process(COMMAND "${PYTHON}" -I "${LAUNCHER}")\n'
    hook.write_bytes(b'execute_process(COMMAND "${PYTHON}" -I -S "${LAUNCHER}")\n')
    inputs = root / 'inputs'
    inputs.write_text(hashlib.sha256(old).hexdigest() + '  ' + str(hook) + '\n')
    script = root / 'test.sh'
    script.write_text('''set -eu
for tool in "$runtime_cmake"; do
''' + policy + '''    hash=$(shasum -a 256 "$tool" | cut -d ' ' -f 1)
    grep -F -x "$hash  $tool" "$inputs" >/dev/null || exit 9
done
''')
    env = os.environ.copy()
    env.update(runtime_cmake=str(hook), HOST_RUNTIME_VIEW=str(root / 'view'), inputs=str(inputs))
    for incremental, expected in (('0', 9), ('1', 0)):
        env['HOST_INCREMENTAL_RECONFIGURE'] = incremental
        result = subprocess.run([sys.argv[1], str(script)], env=env)
        if result.returncode != expected:
            raise SystemExit('runtime hook transition gave unexpected result')
print('PASS: strict hook identity and explicit incremental -I to -I -S')
