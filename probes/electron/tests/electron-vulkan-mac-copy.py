#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise actual mac Vulkan copy/bundle guards with a real GN generator."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--baseline-source', type=Path, required=True)
p.add_argument('--fixed-source', type=Path, required=True)
p.add_argument('--gn', type=Path, required=True)
a = p.parse_args()

def balanced(text, start):
    opening = text.index('{', start); depth = 0; quoted = False; escaped = False; comment = False
    for i in range(opening, len(text)):
        c = text[i]
        if comment:
            if c == '\n': comment = False
            continue
        if quoted:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == '"': quoted = False
            continue
        if c == '#': comment = True
        elif c == '"': quoted = True
        elif c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if not depth: return text[start:i+1]
    raise ValueError('unterminated GN block')

def actual(text, needle, *, block):
    matches = list(re.finditer(re.escape(needle), text))
    if len(matches) != 1: raise ValueError('expected one actual GN statement: ' + needle)
    start = text.rfind('\n', 0, matches[0].start()) + 1
    prior_end = start - 1
    while True:
        while prior_end >= 0 and text[prior_end].isspace(): prior_end -= 1
        prior_start = text.rfind('\n', 0, prior_end + 1) + 1
        previous = text[prior_start:prior_end+1].strip()
        if not previous.startswith('#'): break
        prior_end = prior_start - 1
    if previous == 'if (!emberbsd_common_vulkan) {':
        return balanced(text, prior_start)
    if block: return balanced(text, start)
    return text[start:text.index('\n', start)]

def make_fixture(root, src, common, bundled):
    def put(name, content):
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
    put('.gn', 'buildconfig="//config.gn"\n')
    put('config.gn', f'set_default_toolchain("//:tc")\nemberbsd_common_vulkan={str(common).lower()}\n')
    put('BUILD.gn', 'toolchain("tc") { tool("stamp") { command="touch {{output}}" } tool("copy") { command="cp {{source}} {{output}}" } }\ngroup("root") { deps=["//ui/gl:entry","//chrome:entry","//content/shell:entry"] }\n')
    put('bundled-placeholder', '')
    loader = ('copy("libvulkan") { sources=["//bundled-placeholder"] outputs=["$root_out_dir/libvulkan.dylib"] }\n'
              if bundled else 'source_set("libvulkan") {}\n')
    put('third_party/vulkan-loader/src/BUILD.gn', loader)
    gl = (src / 'ui/gl/BUILD.gn').read_text()
    gl_target = actual(gl, 'copy("vulkan_loader_library_copy")', block=True)
    put('ui/gl/BUILD.gn', gl_target + '\ngroup("entry") {}\n')
    for path, target in (('chrome', 'vulkan_loader_binaries'),
                         ('content/shell', 'content_shell_vulkan_binaries')):
        text = (src / path / 'BUILD.gn').read_text()
        definition = actual(text, 'bundle_data("' + target + '")', block=True)
        binding = actual(text, 'bundle_deps += [ ":' + target + '" ]', block=False)
        put(path + '/BUILD.gn', definition + '\ngroup("entry") {\n bundle_deps=[]\n' + binding + '\n deps=bundle_deps\n}\n')

def run(root):
    return subprocess.run([str(a.gn.resolve(strict=True)), 'gen', str(root/'out'), '--root='+str(root)],
                          text=True, capture_output=True)
with tempfile.TemporaryDirectory(prefix='vulkan-mac-copy-') as temp:
    base = Path(temp).resolve()
    for name, src, common, bundled, expected in (
            ('baseline', a.baseline_source, True, False, False),
            ('shared', a.fixed_source, True, False, True),
            ('bundled', a.fixed_source, False, True, True)):
        root = base / name; root.mkdir(); make_fixture(root, src.resolve(strict=True), common, bundled)
        result = run(root)
        if not expected:
            assert result.returncode and 'libvulkan.dylib' in result.stdout and 'not generated' in result.stdout, result.stdout + result.stderr
            continue
        assert result.returncode == 0, result.stdout + result.stderr
        for label, target in (('//chrome:entry','//chrome:vulkan_loader_binaries'),
                              ('//content/shell:entry','//content/shell:content_shell_vulkan_binaries')):
            raw = subprocess.check_output([str(a.gn), 'desc', str(root/'out'), label, 'deps', '--format=json', '--root='+str(root)], text=True)
            present = target in json.loads(raw)[label]['deps']
            assert present == bundled, (name, label, raw)
print('PASS: actual mac copy and bundle guards reject missing baseline and preserve both modes')
