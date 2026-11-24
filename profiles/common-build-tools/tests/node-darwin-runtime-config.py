#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the configured Node runtime metadata with its own js2c and Node."""
import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='patched Node source tree')
    parser.add_argument('--js2c', type=Path, required=True, help='selected native node_js2c')
    parser.add_argument('--node', type=Path, required=True, help='selected native Node runtime')
    parser.add_argument('--config', type=Path, required=True, help='real configure-produced config.gypi')
    parser.add_argument('--check-installed', action='store_true',
                        help='also test the installed Node, its workers, and user snapshots')
    parser.add_argument('--restore-node', type=Path,
                        help='restore with the same package installed in another prefix')
    args = parser.parse_args()
    source = args.source.resolve()
    node = args.node.resolve()
    config = ast.literal_eval(args.config.read_text())
    prefix = config['variables']['node_prefix']
    assert prefix.startswith('/') and prefix != '/'
    with tempfile.TemporaryDirectory() as work:
        root = Path(work)
        (root / 'lib').mkdir()
        (root / 'lib/example.js').write_text('module.exports = 42;\n')
        input_dir = root / 'out/pkgsrc-runtime'
        input_dir.mkdir(parents=True)
        original = config['target_defaults']['include_dirs']
        original.extend([prefix + '/sub/../../external', prefix + '-neighbor/include', '/usr/pkg/include', 'text ' + prefix,
                         prefix + '/space and "quote"', 'pkgsrc_node_path'])
        config['target_defaults']['libraries'].append('-F' + prefix + '/Frameworks')
        config['variables']['test_external_object'] = {'pkgsrc_node_path': [prefix + '-other', 'unrelated']}
        tree = ast.parse((source / 'configure.py').read_text())
        function, = (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'runtime_config')
        ns = {}
        exec(compile(ast.Module([function], type_ignores=[]), str(source / 'configure.py'), 'exec'), ns)
        paths = []
        relative = ns['runtime_config'](config, prefix, paths)
        fixture = input_dir / 'config.gypi'
        fixture.write_text('# Generated fixture\n' + json.dumps({'config': relative, 'prefix_paths': paths}))
        out = root / 'node_javascript.cc'
        subprocess.run([args.js2c.resolve(), out, 'lib', 'out/pkgsrc-runtime/config.gypi'], cwd=root, check=True)
        text = out.read_text()
        match = re.search(r'\bconfig_raw\s*=.*?R"([^ (]*)\((.*?)\)\1"', text, re.S)
        assert match, 'missing js2c config resource'
        (root / 'embedded.json').write_text(match.group(2))
        options = json.loads(json.dumps(config).replace('"true"', 'true').replace('"false"', 'false'))
        (root / 'expected.json').write_text(json.dumps(options))
        script = root / 'verify.cjs'
        script.write_text("""'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const [source, producer] = process.argv.slice(2);
const wanted = JSON.parse(fs.readFileSync('expected.json'));
const fixture = fs.readFileSync('embedded.json', 'utf8');
const target = {};
const scope = {
  process: target,
  module: { exports: {} },
  internalBinding: () => ({ config: fixture }),
  primordials: {
    JSONParse: JSON.parse, ObjectDefineProperty: Object.defineProperty,
    ObjectFreeze: Object.freeze, ObjectKeys: Object.keys,
  },
};
vm.runInNewContext(fs.readFileSync(source, 'utf8'), scope);
const set = scope.module.exports.setConfig;
set(producer);
assert.deepEqual(JSON.parse(JSON.stringify(target.config)), wanted);
assert(Object.isFrozen(target.config) && Object.isFrozen(target.config.variables));
assert(Object.isFrozen(target.config.target_defaults.include_dirs));
const relocated = '/moved/sdk with "quotes"';
set(relocated);
assert.equal(target.config.variables.node_prefix, relocated);
const include = target.config.target_defaults.include_dirs;
assert(include.includes(producer + '-neighbor/include'));
assert(include.includes(producer + '/sub/../../external'));
assert(include.includes('/usr/pkg/include'));
assert(include.includes('text ' + producer));
assert(include.includes(relocated + '/space and "quote"'));
assert(target.config.target_defaults.libraries.includes('-F' + relocated + '/Frameworks'));
set();
assert.equal(target.config.variables.node_prefix, '@executable_path/..');
set(relocated);
assert.equal(target.config.variables.node_prefix, relocated);
""")
        module = source / 'lib/internal/process/pkgsrc_config.js'
        for flags in ([], ['--no-node-snapshot']):
            subprocess.run([node, *flags, script, module, prefix], cwd=root, check=True)
        if args.check_installed:
            probe = root / 'check-installed.cjs'
            probe.write_text("""'use strict';
const assert = require('node:assert/strict');
const { dirname } = require('node:path');
const { isMainThread, Worker } = require('node:worker_threads');
assert.equal(process.config.variables.node_prefix, dirname(dirname(process.execPath)));
assert(Object.isFrozen(process.config.variables));
if (isMainThread) {
  const worker = new Worker(__filename);
  worker.on('exit', code => assert.equal(code, 0));
}
""")
            for flags in ([], ['--no-node-snapshot']):
                subprocess.run([node, *flags, probe], cwd=root, check=True)
            build = root / 'make-snapshot.cjs'
            build.write_text("""'use strict';
const assert = require('node:assert/strict');
const { dirname } = require('node:path');
const { startupSnapshot } = require('node:v8');
function check() {
  assert.equal(process.config.variables.node_prefix, dirname(dirname(process.execPath)));
}
check();
startupSnapshot.addSerializeCallback(check);
startupSnapshot.addDeserializeCallback(check);
startupSnapshot.setDeserializeMainFunction(check);
""")
            blob = '--snapshot-blob=' + str(root / 'runtime.blob')
            subprocess.run([node, blob, '--build-snapshot', build], cwd=root, check=True)
            restored = args.restore_node.resolve() if args.restore_node else node
            subprocess.run([restored, blob], cwd=root, check=True)
        print('Verified', len(paths), 'package-owned config paths and the full js2c output')


if __name__ == '__main__':
    main()
