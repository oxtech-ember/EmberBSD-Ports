#!/usr/bin/env python3
# Origin: EmberBSD contributors (AI-assisted); not submitted upstream.
"""Exercise the selected Node external config with real GN, without compiling."""
import argparse
import importlib.util
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
for name in ('node-source', 'gn'):
    parser.add_argument('--' + name, required=True, type=Path)
args = parser.parse_args()
node, gn = args.node_source.resolve(strict=True), args.gn.resolve(strict=True)
owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_electron', owner / 'electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
text = (node / 'unofficial.gni').read_text()
start = text.index('  config("node_external_config") {')
end = text.index('\n  config("node_internal_config")', start)
config = text[start:end].replace('"$node_v8_path:external_config"', '":v8_external_config"')
node_gni = (node / 'node.gni').read_text()
if 'node_inspector_string_traits_header = ""' not in node_gni:
    raise SystemExit('Node default inspector traits selection changed')
# Extract the production value, avoiding an independently copied policy.
class Capture:
    @staticmethod
    def capture(*args, **kwargs):
        from types import SimpleNamespace
        return SimpleNamespace(stdout=b'{}')
from types import SimpleNamespace
with tempfile.TemporaryDirectory(prefix='node-traits-gn-') as tmp:
    root = Path(tmp)
    ports = root / 'ports'; script = ports / 'scripts/source-inputs/node/source.py'
    script.parent.mkdir(parents=True); script.touch()
    opts = SimpleNamespace(node_source=root/'node', node_pkgsrc=root/'pkgsrc', ports_source=ports, sdk_source=root/'sdk')
    value = build.common_embedder_sources(opts, {'process': Capture()}, SimpleNamespace(tool=lambda _: '/python'), {})['node_inspector_string_traits_header']
    (root / '.gn').write_text('buildconfig = "//config.gn"\n')
    (root / 'config.gn').write_text('set_default_toolchain("//:test")\n')
    (root / 'BUILD.gn').write_text('''declare_args() {
  node_inspector_string_traits_header = ""
  node_enable_inspector = true
}
node_module_version = "1"
node_builtin_cache_status = false
node_inspector_protocol_path = "//third_party/inspector_protocol"
node_embedder_cppheap_pointer_tag = ""
config("node_features") {}
config("v8_external_config") {}
''' + config + '''
toolchain("test") {
  tool("stamp") { command = "touch {{output}}" }
}
group("consumer") { public_configs = [ ":node_external_config" ] }
''')
    for name, selection in [('standalone', ''), ('shared', value)]:
        out = root / name
        gnargs = build.gn_arguments({'node_inspector_string_traits_header': selection}).splitlines()[-1]
        subprocess.run([str(gn), 'gen', str(out), '--fail-on-unused-args', '--args='+gnargs], cwd=root, check=True)
        result = subprocess.run([str(gn), 'desc', str(out), '//:node_external_config', 'defines'], cwd=root, check=True, text=True, capture_output=True).stdout
        marker = 'NODE_INSPECTOR_STRING_TRAITS_HEADER='
        if (marker in result) != bool(selection) or (selection and selection not in result):
            raise SystemExit(f'{name}: incorrect exported traits definition: {result}')
print('PASS: common Node exports selected traits header; standalone leaves it unset')
