#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Run the actual native TypeScript CLI through its upstream Node wrapper."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('module', 'binary', 'libs', 'node', 'work'):
        parser.add_argument('--' + key, required=True, type=Path)
    parser.add_argument('--platform', required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='typescript-', dir=args.work) as temporary:
        root = Path(temporary)
        modules = root / 'node_modules'
        module = modules / 'typescript'
        platform = modules / '@typescript' / ('typescript-' + args.platform)
        shutil.copytree(args.module, module)
        shutil.copytree(args.libs, platform / 'lib')
        binary = platform / 'lib/tsc'
        shutil.copyfile(args.binary, binary)
        binary.chmod(0o755)
        (platform / 'package.json').write_text(json.dumps({
            'name': '@typescript/typescript-' + args.platform,
            'version': '7.0.2', 'exports': {'./package.json': './package.json'}}))
        command = [str(args.node), str(module / 'bin/tsc')]

        def run(argv, success=True):
            result = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=60)
            if (result.returncode == 0) != success:
                raise RuntimeError(result.stdout + result.stderr)
            return result.stdout + result.stderr

        assert run(command + ['--version']).strip() == 'Version 7.0.2'
        (root / 'entry.ts').write_text('const value: number = 21 * 2; console.log(value);\n')
        compile_args = ['--strict', '--noEmitOnError', '--target', 'es2022',
                        '--module', 'commonjs', '--outDir', 'out', 'entry.ts']
        run(command + compile_args)
        assert run([str(args.node), str(root / 'out/entry.js')]).strip() == '42'
        (root / 'out/entry.js').unlink()
        (root / 'entry.ts').write_text('const value: number = "wrong";\n')
        error = run(command + compile_args, success=False)
        assert 'TS2322' in error and not (root / 'out/entry.js').exists(), error
        files = run(command + ['--listFilesOnly', '--lib', 'dom,es2022', 'entry.ts'])
        assert str(platform / 'lib/lib.dom.d.ts') in files, files
        binary.unlink()
        assert 'Executable not found' in run(command + ['--version'], success=False)
    print('PASS: native wrapper, version, compile/run, strict type error, declarations and missing-binary refusal')


if __name__ == '__main__':
    main()
