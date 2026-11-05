#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise actual Chromium FreeType and HarfBuzz GN paths for both roles."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('source', 'gn', 'patch-tool'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
source = a.source.resolve(strict=True)
patch = Path(__file__).resolve().parents[1] / 'patches/gn-common-font.patch'
with tempfile.TemporaryDirectory(prefix='electron-font-gn-') as tmp:
    root = Path(tmp).resolve()
    def write(name, text):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    for name in ('build/config/freetype/BUILD.gn', 'build/linux/BUILD.gn', 'third_party/harfbuzz/BUILD.gn'):
        write(name, (source/name).read_text())
    subprocess.run([str(a.patch_tool), '-p1', '-F0', '-i', str(patch)], cwd=root,
                   capture_output=True, check=True)
    write('.gn', 'buildconfig = "//config.gn"\n')
    write('build/config/features.gni', '')
    write('build/config/ui.gni', '')
    write('build/config/chrome_build.gni', '')
    write('build/config/buildflags_paint_preview.gni', '')
    write('build/config/freetype/freetype.gni', 'use_system_freetype = true\nenable_freetype = true\n')
    write('third_party/harfbuzz/harfbuzz.gni', 'use_system_harfbuzz = true\n')
    write('build/config/linux/pkg_config.gni', '''template("pkg_config") {
  not_needed(invoker, "*")
  config(target_name) { include_dirs = [ "//selected-headers" ] }
}
''')
    write('BUILD.gn', 'toolchain("tc") { tool("stamp") { command = "touch {{output}}" } }\ngroup("default") { deps = [ "//skia:skia" ] }\n')
    write('skia/BUILD.gn', 'source_set("skia") { deps = [ "//build/config/freetype", "//third_party/harfbuzz" ] }\n')
    for role in ('native', 'target'):
        write('config.gn', f'''set_default_toolchain("//:tc")
emberbsd_pkg_config_role = "{role}"
use_gio = false
is_castos = false
build_with_chromium = false
CHECK_INCLUDES_STRICT_PUBLIC_INCLUDES_PRIVATE = false
template("component") {{ source_set(target_name) {{ forward_variables_from(invoker, "*") }} }}
''')
        out = root/('out-' + role)
        args = ['emberbsd_common_font=true']
        for name in ('freetype', 'harfbuzz'):
            for r in ('host', 'target'):
                for kind in ('libraries', 'inputs'):
                    args.append(f'emberbsd_{name}_{r}_{kind}=["//{name}-{r}-{kind}"]')
        generated = subprocess.run([str(a.gn), 'gen', str(out), '--args=' + ' '.join(args), '--fail-on-unused-args'],
                                   cwd=root, capture_output=True, text=True)
        assert generated.returncode == 0, generated.stdout + generated.stderr
        def desc(label):
            return json.loads(subprocess.check_output([str(a.gn), 'desc', str(out), label, '--format=json'], cwd=root, text=True))[label]
        info = desc('//skia:skia')
        selected = 'host' if role == 'native' else 'target'
        assert set(info['libs']) == {'//' + name + '-' + selected + '-libraries' for name in ('freetype', 'harfbuzz')}
        assert '//selected-headers/' in info['include_dirs']
        for name,label in (('freetype','//build/config/freetype:emberbsd_freetype'),('harfbuzz','//third_party/harfbuzz:emberbsd_harfbuzz')):
            data = desc(label)
            assert data['inputs'] == ['//' + name + '-' + selected + '-inputs']
            assert data['ldflags'] == ['-Wl,-rpath=' + (str(root) if role == 'native' else '/usr/pkg/lib')]
print('PASS: FreeType and HarfBuzz GN inputs, transitive links and role rpaths')
