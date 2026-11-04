#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise Terser's current Commander CLI and Node's native source maps."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--node', required=True, type=Path)
parser.add_argument('--module', required=True, type=Path)
args = parser.parse_args()
node = args.node.resolve(strict=True)
module = args.module.resolve(strict=True)
cli = module / 'bin/terser'
env = dict(os.environ, PATH=str(node.parent), NODE_PATH='', NODE_OPTIONS='')

with tempfile.TemporaryDirectory(prefix='terser-cli-') as temporary:
    work = Path(temporary)

    def run(command, text=None, ok=True):
        result = subprocess.run([str(node), *map(str, command)], input=text,
                                text=True, capture_output=True, cwd=work, env=env)
        assert (result.returncode == 0) == ok, result.stderr
        return result

    assert run([cli, '--version']).stdout.startswith('terser ')
    assert '--source-map' in run([cli, '--help']).stdout
    assert 'unknown option' in run([cli, '--not-a-terser-option'], ok=False).stderr

    result = run([cli, '-c', '-m'], 'function answer(){return 6*7}console.log(answer());')
    assert run(['-e', result.stdout]).stdout == '42\n'
    result = run([cli, '--parse', 'bare_returns', '-c', '--define', 'FLAG=true',
                  '--format', 'beautify'], 'if(FLAG) return 42;')
    assert result.stdout.strip() == 'return 42;'

    original = 'function fail() {\n  throw new Error("mapped fixture");\n}\nfail();\n'
    (work / 'input.js').write_text(original)
    run([cli, 'input.js', '-c', '-m', '--source-map', "url='out.js.map',includeSources",
         '--output', 'out.js'])
    source_map = json.loads((work / 'out.js.map').read_text())
    assert source_map['sources'] == ['input.js']
    assert source_map['sourcesContent'] == [original]
    stack = run(['--enable-source-maps', 'out.js'], ok=False).stderr
    assert 'input.js:2:' in stack, stack

    # Load a throwing mapped module only after the CLI has enabled the native
    # hook. No source-map-support package or NODE_OPTIONS is available here.
    fixture_map = {'version': 3, 'sources': ['original-cli.js'], 'names': [],
                   'mappings': 'AAIA', 'sourcesContent': ['\n\n\n\nthrow new Error();\n']}
    encoded = base64.b64encode(json.dumps(fixture_map).encode()).decode()
    (work / 'mapped.cjs').write_text('throw new Error("native map hook");\n'
        '//# sourceMappingURL=data:application/json;base64,' + encoded + '\n')
    (work / 'preload.cjs').write_text(
        'process.on("exit", () => require("./mapped.cjs"));\n')
    stack = run(['--require', work / 'preload.cjs', cli, '--version'], ok=False).stderr
    assert 'original-cli.js:5:' in stack, stack

print('PASS: CLI options, minification, generated maps and native stack mapping')
