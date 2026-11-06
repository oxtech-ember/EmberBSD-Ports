#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise actual codec consumer GN blocks before and after their patch."""
import argparse, json, re, subprocess, tempfile
from pathlib import Path, PurePosixPath
p = argparse.ArgumentParser()
p.add_argument('--source', required=True, type=Path)
p.add_argument('--patch', required=True, type=Path)
p.add_argument('--gn', required=True, type=Path)
p.add_argument('--patch-tool', required=True, type=Path)
a = p.parse_args()
paths = ['third_party/blink/renderer/platform/media/BUILD.gn', 'third_party/pdfium/core/fxcodec/BUILD.gn']

def block(text, needle):
    start = text.index(needle)
    pos = text.index('{', start)
    level = 0
    for i in range(pos, len(text)):
        if text[i] == '{':
            level += 1
        if text[i] == '}':
            level -= 1
            if not level:
                return text[start:i + 1] + '\n'
    raise ValueError('unterminated target')

def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)

def run(root, cmd):
    r = subprocess.run(cmd, cwd=root, text=True, capture_output=True)
    if r.returncode:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout
with tempfile.TemporaryDirectory(prefix='codec-header-gn-') as tmp:
    tmp = Path(tmp)
    baseline = tmp / 'baseline'
    fixed = tmp / 'fixed'
    for root in (baseline, fixed):
        for path in paths:
            put(root, path, (a.source / path).read_text())

    def patch_check(root, direction, dry_run):
        command = [str(a.patch_tool), '--batch', '--force', '-p1', '-F0', direction]
        if dry_run:
            command.append('--dry-run')
        command += ['-i', str(a.patch.resolve())]
        result = subprocess.run(command, cwd=root, text=True, capture_output=True)
        output = result.stdout + result.stderr
        return (result.returncode == 0 and (not re.search('offset|fuzz', output, re.I)), output)
    forward, _ = patch_check(fixed, '--forward', True)
    reverse, _ = patch_check(baseline, '--reverse', True)
    if forward == reverse:
        raise RuntimeError('source must match the entire baseline or patched form')
    target, direction = (fixed, '--forward') if forward else (baseline, '--reverse')
    ok, output = patch_check(target, direction, False)
    if not ok:
        raise RuntimeError(output)
    for root in (baseline, fixed):
        blocks = [block((root / paths[0]).read_text(), 'component("media") {'), block((root / paths[1]).read_text(), 'source_set("fxcodec") {')]
        blocks = [re.sub('  visibility = \\[.*?\\]\\n', '', s, flags=re.S) for s in blocks]
        put(root, paths[0], blocks[0].replace('component("media")', 'source_set("media")'))
        put(root, paths[1], blocks[1])
        put(root, '.gn', 'buildconfig="//config.gn"\n')
        put(root, 'config.gn', 'set_default_toolchain("//:tc")\nset_defaults("source_set") { configs=[] }\nmedia_use_ffmpeg=false\npdf_enable_brotli=false\npdf_enable_xfa=false\npdf_enable_rust_jpeg=false\nis_win=false\n')
        put(root, 'BUILD.gn', 'toolchain("tc") { tool("stamp") { command="touch {{output}}" } }\nsource_set("consumer") { deps=["//third_party/pdfium/core/fxcodec", "//third_party/blink/renderer/platform/media:media"] }\n')
        labels = {}
        for path, s in zip(paths, blocks):
            here = PurePosixPath(path).parent
            for label in re.findall('"((?://|\\.\\./|:)[^" ]+)"', s):
                if label.endswith('*'):
                    continue
                lpath, sep, name = label.partition(':')
                if lpath.startswith('//'):
                    directory = PurePosixPath(lpath[2:])
                elif lpath:
                    directory = PurePosixPath(__import__('posixpath').normpath(str(here / lpath)))
                else:
                    directory = here
                target = name if sep else directory.name
                if (str(directory), target) in [('third_party/ffmpeg', 'ffmpeg'), ('third_party/pdfium/third_party', 'lcms2'), ('third_party/pdfium/third_party', 'libopenjpeg2')]:
                    continue
                kind = 'config' if target in ('blink_platform_config', 'blink_platform_implementation', 'pdfium_strict_config', 'pdfium_noshorten_config') else 'group'
                labels.setdefault(str(directory), set()).add((kind, target))
        for directory, entries in labels.items():
            path = directory + '/BUILD.gn'
            if path in paths:
                continue
            put(root, path, ''.join((f'{kind}("{name}") {{}}\n' for kind, name in sorted(entries))))
        put(root, 'third_party/ffmpeg/BUILD.gn', 'config("headers") { include_dirs=["//sys-ffmpeg"] }\ngroup("ffmpeg") { public_configs=[":headers"] }\n')
        put(root, 'third_party/pdfium/third_party/BUILD.gn', 'config("lcms_config") { defines=["USE_SYSTEM_LCMS2"] include_dirs=["//sys-lcms"] }\nconfig("jpeg_config") { defines=["USE_SYSTEM_LIBOPENJPEG2"] include_dirs=["//sys-openjpeg"] }\ngroup("lcms2") { if (system_pdf) { public_configs=[":lcms_config"] } }\ngroup("libopenjpeg2") { if (system_pdf) { public_configs=[":jpeg_config"] } }\ngroup("zlib") {} group("png") {} group("tiff") {}\n')
        for ff in (False, True):
            for system in (False, True):
                cfg = (root / 'config.gn').read_text()
                cfg = re.sub('media_use_ffmpeg=(true|false)', f'media_use_ffmpeg={str(ff).lower()}', cfg)
                cfg += 'system_pdf=' + str(system).lower() + '\n'
                put(root, 'config.gn', cfg)
                out = root / ('out-%s-%s' % (ff, system))
                run(root, [str(a.gn), 'gen', str(out)])

                def desc(label):
                    return json.loads(run(root, [str(a.gn), 'desc', str(out), label, '--format=json']))[label]
                media = desc('//third_party/blink/renderer/platform/media:media')
                consumer = desc('//:consumer')
                expected = root == fixed
                assert ('//sys-ffmpeg/' in media.get('include_dirs', [])) == (expected and ff), media.get('include_dirs', [])
                for define, inc in [('USE_SYSTEM_LCMS2', '//sys-lcms/'), ('USE_SYSTEM_LIBOPENJPEG2', '//sys-openjpeg/')]:
                    assert (define in consumer.get('defines', [])) == (expected and system), consumer.get('defines', [])
                    assert (inc in consumer.get('include_dirs', [])) == (expected and system), consumer.get('include_dirs', [])
    print('PASS: baseline loses codec header requirements; patched propagation, disabled FFmpeg and bundled PDF')
