#!/usr/bin/env python3
"""Check Electron PDF policy against the selected Chromium GN sources."""
# Origin: EmberBSD contributors (AI-assisted); not submitted upstream.
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
for option in ('source', 'gn', 'git', 'patch'):
    parser.add_argument('--' + option, type=Path, required=True)
args = parser.parse_args()
source, gn, git, patch = (getattr(args, name).resolve(strict=True)
                          for name in ('source', 'gn', 'git', 'patch'))
all_gn = source / 'electron/build/args/all.gn'
features = source / 'pdf/features.gni'
if 'import("//pdf/features.gni")' not in (source / 'electron/BUILD.gn').read_text():
    raise SystemExit('Electron BUILD.gn no longer imports PDF features')

def run(argv, cwd):
    subprocess.run(list(map(str, argv)), cwd=cwd, check=True)

with tempfile.TemporaryDirectory(prefix='electron-pdf-policy-') as temp:
    root = Path(temp)
    target = root / 'patch-check/electron/build/args/all.gn'
    target.parent.mkdir(parents=True)
    target.write_bytes(all_gn.read_bytes())
    run([git, 'apply', '--check', patch], root / 'patch-check')
    run([git, 'apply', patch], root / 'patch-check')
    before = all_gn.read_text()
    after = target.read_text()
    pattern = r'^enable_pdf_save_to_drive\s*=\s*(?:true|false)\s*$'
    matches = re.findall(pattern, after, re.MULTILINE)
    if re.search(pattern, before, re.MULTILINE) or len(matches) != 1:
        raise SystemExit('expected one new literal PDF Drive assignment')
    assignment = matches[0]
    for name, extra, expected in [('control', '', 'true'),
                                  ('patched', assignment, 'false')]:
        fixture = root / name
        (fixture / 'pdf').mkdir(parents=True)
        (fixture / 'build/config').mkdir(parents=True)
        (fixture / '.gn').write_text('buildconfig = "//buildconfig.gn"\n')
        (fixture / 'buildconfig.gn').write_text('''is_android = false
is_ios = false
is_fuchsia = false
set_default_toolchain("//:fixture")
''')
        (fixture / 'build/config/cast.gni').write_text('is_castos = false\n')
        (fixture / 'pdf/features.gni').write_bytes(features.read_bytes())
        (fixture / 'BUILD.gn').write_text('''import("//pdf/features.gni")
assert(enable_pdf)
assert(enable_pdf_save_to_drive == EXPECTED)
toolchain("fixture") {
  tool("stamp") {
    command = "touch {{output}}"
  }
}
group("all") {
}
'''.replace('EXPECTED', expected))
        # GN applies args before declare_args, matching Electron's all.gn use.
        flags = 'enable_pdf = true ' + extra
        run([gn, 'gen', fixture / 'out', '--fail-on-unused-args', '--args=' + flags], fixture)
print('PASS: PDF remains enabled; patched Electron policy disables Save to Drive')
