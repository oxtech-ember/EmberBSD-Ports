#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check actual Electron libuv link blocks with real GN."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('source', 'gn', 'git'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
source = args.source.resolve(strict=True)
gn = args.gn.resolve(strict=True)
git = args.git.resolve(strict=True)
patch = Path(__file__).resolve().parents[1] / 'patches/electron-shared-libuv-link.patch'
original = (source / 'electron/BUILD.gn').read_text()
assert 'import("//third_party/electron_node/node.gni")' in original

def extract(text, platform):
    if platform == 'mac':
        start = text.index('    ldflags = [\n      "-Wl,-install_name,@rpath/$output_name.framework/$output_name"')
        end = text.index('    if (is_component_build)', start)
    else:
        start = text.index('    if (is_linux) {\n      ldflags = [', text.index('"/DEF:"'))
        end = text.index('      if (!is_component_build && is_component_ffmpeg)', start)
    return text[start:end] + ('    }\n' if platform != 'mac' else '')

with tempfile.TemporaryDirectory(prefix='electron-libuv-gn-') as temporary:
    root = Path(temporary)
    copy = root / 'source/electron/BUILD.gn'
    copy.parent.mkdir(parents=True)
    copy.write_text(original)
    subprocess.run([str(git), 'apply', '--check', str(patch)], cwd=root / 'source', check=True)
    subprocess.run([str(git), 'apply', str(patch)], cwd=root / 'source', check=True)
    patched = copy.read_text()
    for platform in ('linux', 'netbsd', 'mac'):
        for shared in (False, True):
            for control in (False, True):
                fixture = root / f'{platform}-{shared}-{control}'
                fixture.mkdir()
                (fixture / '.gn').write_text('buildconfig = "//buildconfig.gn"\n')
                (fixture / 'buildconfig.gn').write_text('set_default_toolchain("//:fixture")\n')
                block = extract(original if control else patched, platform)
                archive = 'obj/third_party/electron_node/deps/uv/libuv.a'
                expected = 'true' if not shared else 'false'
                if platform == 'mac':
                    predicate = '"-Wl,-force_load,' + archive + '"'
                else:
                    predicate = '"' + archive + '"'
                (fixture / 'BUILD.gn').write_text('''toolchain("fixture") {
  tool("stamp") { command = "touch {{output}}" }
}
node_shared_libuv = SHARED
assert(node_shared_libuv == SHARED)
PLATFORM_VARIABLE
group("all") {
BLOCK
  matched = filter_include(ldflags, [ PREDICATE ])
  assert((matched != []) == EXPECTED)
PIE
}
'''.replace('SHARED', str(shared).lower()).replace('LINUX', str(platform != 'mac').lower())
                   .replace('PLATFORM_VARIABLE', 'output_name = "Electron"' if platform == 'mac' else 'is_linux = true')
                   .replace('BLOCK', block).replace('PREDICATE', predicate).replace('EXPECTED', expected)
                   .replace('PIE', '  assert(filter_include(ldflags, [ "-pie" ]) != [])' if platform != 'mac' else ''))
                result = subprocess.run([str(gn), 'gen', str(fixture / 'out')], cwd=fixture,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                expect_success = not (control and shared)
                if (result.returncode == 0) != expect_success:
                    raise AssertionError(f'{platform=} {shared=} {control=}: {result.stdout}')
print('PASS: real GN evaluates actual libuv link blocks on Linux, NetBSD and macOS')
