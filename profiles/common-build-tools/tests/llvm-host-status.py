#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Inject failures into actual CLI main blocks.
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from llvm_fixture import FILES, load_sdk
sdk, args = load_sdk()
if len(args) != 1:
    sys.exit('Use NEW_WORK')
work = Path(args[0]).absolute()
work.mkdir()
cross = FILES.parents[3] / 'cross'
# No SDK producer runs here. The actual entrypoint handles a typed completed
# producer failure or a signal delivered to its own CLI process.
script = '''import ast, importlib.util, os, signal, sys
sys.dont_write_bytecode = True
path, function, failure = sys.argv[1:]
sys.path.insert(0, os.path.dirname(path))
spec = importlib.util.spec_from_file_location('entrypoint', path)
entrypoint = importlib.util.module_from_spec(spec)
original = tuple(signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP))
spec.loader.exec_module(entrypoint)
assert original == tuple(signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP))
entrypoint.load_sdk([])
from emberbsd_sdk.errors import CommandError
def injected(*args):
    if failure == 'exit97': raise CommandError(97, ['fixture-producer'])
    if failure == 'childTERM': raise CommandError(-signal.SIGTERM, ['fixture-producer'])
    os.kill(os.getpid(), getattr(signal, failure))
setattr(entrypoint, function, injected)
entrypoint.__dict__['__name__'] = '__main__'
sys.argv = [path]
source = ast.parse(open(path).read(), filename=path)
main = [n for n in source.body if isinstance(n, ast.If) and '__name__' in ast.unparse(n.test)]
assert len(main) == 1
exec(compile(ast.Module(body=main, type_ignores=[]), path, 'exec'), entrypoint.__dict__)
'''
checks, failures = [], []
for name, function in [('build-llvm-native', 'native'), ('build-clang-native', 'native'),
                       ('prepare-llvm-macos', 'prepare'), ('prepare-tools', 'prepare'),
                       ('build-llvm-dwp-tests', 'build')]:
    for failure, expected in [('exit97', 97), ('childTERM', 143), ('SIGTERM', 143), ('SIGHUP', 129)]:
        result = subprocess.run([sys.executable, '-B', '-c', script, str(cross / (name + '.py')), function, failure],
                                env=dict(os.environ, EMBERBSD_SDK_SOURCE=sdk, PYTHONDONTWRITEBYTECODE='1'), capture_output=True, timeout=10)
        label = name + '-' + failure
        (work / (label + '.log')).write_bytes(result.stdout + result.stderr)
        checks.append(dict(case=label, expected=expected, actual=result.returncode))
        if result.returncode != expected:
            failures.append(f'{label}: expected {expected}, got {result.returncode}')
(work / 'results.json').write_text(json.dumps(checks, indent=2) + '\n')
assert not failures, '\n'.join(failures)
print(f'PASS: {len(checks)} actual CLI main blocks preserve typed status and signal identity; no SDK producers ran')
