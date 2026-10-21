#!/usr/bin/env python3
"""Exercise configured libxslt source ownership under deterministic allocation errors."""
import argparse
import json
import pathlib
import resource
import subprocess

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('source', type=pathlib.Path)
ap.add_argument('xml_prefix', type=pathlib.Path)
ap.add_argument('output', type=pathlib.Path)
ap.add_argument('--cc', required=True)
ap.add_argument('--ar', default='ar')
args = ap.parse_args()
src, xml, out = (p.resolve() for p in (args.source, args.xml_prefix, args.output))
tests = pathlib.Path(__file__).resolve().parent
out.mkdir(parents=True, exist_ok=False)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
rows = []

def run(name, cmd, *, source=None):
    p = subprocess.run([str(x) for x in cmd], input=source,
                       capture_output=True, text=True, timeout=120)
    row = {'name': name, 'command': [str(x) for x in cmd],
           'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
    rows.append(row)
    return row

flags = ['-O2', '-g', '-DHAVE_CONFIG_H', '-I'+str(src),
         '-I'+str(src/'libxslt'), '-I'+str(xml/'include/libxml2'), '-I'+str(tests)]
for unit, cases in [('transform', ['global', 'func', 'func-select']),
                    ('variables', ['stack-result', 'stack-select', 'eval-new',
                                   'eval-cached', 'eval-doc'])]:
    archive = out/(unit+'.a')
    objects = sorted(f for f in (src/'libxslt/.libs').glob('*.o') if f.stem != unit)
    if not objects:
        raise SystemExit('Configured production PIC objects are required')
    r = run(unit+'-archive', [args.ar, 'cr', archive]+objects)
    if r['exit']:
        raise SystemExit(r['stderr'])
    exe = out/unit
    r = run(unit+'-build', [args.cc]+flags+[tests/('libxslt-alloc-'+unit+'.c'),
            archive, '-L'+str(xml/'lib'), '-Wl,-rpath,'+str(xml/'lib'),
            '-lxml2', '-lpthread', '-lm', '-o', exe])
    if r['exit']:
        raise SystemExit(r['stderr'])
    run(unit+'-ldd', ['ldd', exe])
    for case in cases:
        r = run(unit+'-'+case, [exe, case])
        r['passed'] = r['exit'] == 0
        print('PASS' if r['passed'] else 'FAIL', r['name'], flush=True)

probe = '#include <libxslt/xsltInternals.h>\nvoid probe(xsltTransformContextPtr c) { %s(c,0); }\n'
for name, function, private, rejected in [
        ('public-control', 'xsltReleaseRVT', False, False),
        ('public-helper-rejected', 'xsltReleaseRVTList', False, True),
        ('internal-helper-accepted', 'xsltReleaseRVTList', True, False)]:
    cmd = [args.cc]+flags+['-Werror=implicit-function-declaration', '-fsyntax-only', '-x', 'c', '-']
    if private:
        cmd.insert(1, '-DIN_LIBXSLT')
    r = run(name, cmd, source=probe % function)
    r['passed'] = ((r['exit'] != 0 and 'implicit declaration' in r['stderr']
                    and function in r['stderr']) if rejected else r['exit'] == 0)
    print('PASS' if r['passed'] else 'FAIL', name, flush=True)
checks = [r for r in rows if 'passed' in r]
report = {'commands': rows, 'passed': sum(r['passed'] for r in checks), 'total': len(checks)}
(out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
raise SystemExit(0 if report['passed'] == report['total'] else 1)
