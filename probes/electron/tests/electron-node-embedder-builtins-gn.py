#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise Node's real embedder conditionals in a minimal GN graph."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace

parser = argparse.ArgumentParser()
parser.add_argument('--node-source', required=True, type=Path)
parser.add_argument('--gn', required=True, type=Path)
args = parser.parse_args()
node = args.node_source.resolve(strict=True)
gn = args.gn.resolve(strict=True)
owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('build_electron', owner)
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
source = (node / 'unofficial.gni').read_text()
def between(start, end):
    return source[source.index(start):source.index(end, source.index(start))]
define = between('    if (node_embedder_builtins_target != "") {', '\n\n    if (is_win)')
inputs = between('    assert((node_embedder_builtins_target == "") ==', '\n\n    if (node_shared_perfetto)')
class Capture:
    @staticmethod
    def capture(*_args, **_kwargs):
        return SimpleNamespace(stdout=b'{}')
with tempfile.TemporaryDirectory(prefix='node-embedder-gn-') as tmp:
    root = Path(tmp)
    owner_script = root / 'ports/scripts/source-inputs/node/source.py'
    owner_script.parent.mkdir(parents=True); owner_script.touch()
    opts = SimpleNamespace(node_source=root/'node', node_pkgsrc=root/'pkgsrc', ports_source=root/'ports', sdk_source=root/'sdk')
    values = build.common_embedder_sources(opts, {'process': Capture()}, SimpleNamespace(tool=lambda _: '/python'), {})
    (root/'.gn').write_text('buildconfig="//config.gn"\n')
    (root/'config.gn').write_text('set_default_toolchain("//:toolchain")\n')
    (root/'BUILD.gn').write_text('''declare_args() {
  node_embedder_builtins_target = ""
  node_embedder_builtins_output = ""
}
toolchain("toolchain") {
  tool("stamp") { command = "touch {{output}}" }
  tool("cxx") { command = "true" outputs = [ "{{source_out_dir}}/{{target_output_name}}.{{source_name_part}}.o" ] }
}
source_set("libnode") {
  defines = []
  deps = []
  sources = [ "node_builtins.cc" ]
''' + define + '\n' + inputs + '\n}\n')
    (root/'node_builtins.cc').touch()
    electron = root/'electron'; electron.mkdir()
    (electron/'BUILD.gn').write_text('''action("electron_js2c") {
  script = "//stub.py"
  outputs = [ "$root_gen_dir/electron_natives.cc" ]
}
''')
    (root/'stub.py').write_text('')
    for name, selected in [('baseline', False), ('selected', True)]:
        out = root/name
        settings = {} if not selected else {k: values[k] for k in ('node_embedder_builtins_target', 'node_embedder_builtins_output')}
        subprocess.run([str(gn), 'gen', str(out), '--fail-on-unused-args', '--args='+' '.join(k + '=' + json.dumps(v) for k, v in settings.items())], cwd=root, check=True, text=True)
        def desc(field):
            return subprocess.run([str(gn), 'desc', str(out), '//:libnode', field, '--format=json'], cwd=root, check=True, capture_output=True, text=True).stdout
        defines, sources, deps = (json.loads(desc(x))['//:libnode'].get(x, []) for x in ('defines','sources','deps'))
        assert ('NODE_EMBEDDER_BUILTINS=1' in defines) == selected, (name, defines)
        assert sum(x.endswith('/electron_natives.cc') for x in sources) == int(selected), (name, sources)
        assert any('//electron:electron_js2c' in x for x in deps) == selected, (name, deps)
print('PASS: Node embedder GN baseline and selected source/define/dependency')
