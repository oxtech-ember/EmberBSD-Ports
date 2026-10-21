#!/usr/bin/env python3
"""Check fresh-document registration failures and normal results in real sources."""
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
a = ap.parse_args()
src, xml, out = (p.resolve() for p in (a.source, a.xml_prefix, a.output))
tests = pathlib.Path(__file__).resolve().parent
out.mkdir(parents=True, exist_ok=False)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
rows = []

def run(name, cmd):
    r = subprocess.run([str(x) for x in cmd], capture_output=True, text=True, timeout=120)
    row = {'name': name, 'command': [str(x) for x in cmd], 'exit': r.returncode,
           'stdout': r.stdout, 'stderr': r.stderr}
    rows.append(row)
    return row

for unit, cases in [('variables', ['global']), ('exslt', ['node-set', 'result',
                    'tokenize', 'split', 'return-string', 'map'])]:
    objects = sorted(f for f in (src/'libxslt/.libs').glob('*.o')
                     if not (unit == 'variables' and f.stem == 'variables'))
    if unit == 'exslt':
        objects += sorted(f for f in (src/'libexslt/.libs').glob('*.o')
                          if f.stem not in ('common', 'functions', 'strings', 'dynamic'))
    if not objects:
        raise SystemExit('Configured production PIC objects are required')
    archive = out/(unit+'.a')
    r = run(unit+'-archive', [a.ar, 'cr', archive]+objects)
    if r['exit']:
        raise SystemExit(r['stderr'])
    exe = out/unit
    flags = ['-O2', '-g', '-DHAVE_CONFIG_H', '-I'+str(src), '-I'+str(src/'libxslt'),
             '-I'+str(src/'libexslt'), '-I'+str(xml/'include/libxml2'), '-I'+str(tests)]
    r = run(unit+'-build', [a.cc]+flags+[tests/('libxslt-fresh-'+unit+'.c'), archive,
            '-L'+str(xml/'lib'), '-Wl,-rpath,'+str(xml/'lib'), '-lxml2', '-lpthread',
            '-lm', '-o', exe])
    if r['exit']:
        raise SystemExit(r['stderr'])
    r = run(unit+'-ldd', ['ldd', exe])
    if r['exit'] or 'not found' in r['stdout'] or str(xml/'lib') not in r['stdout']:
        raise SystemExit('The selected libxml2 runtime is required: '+r['stdout']+r['stderr'])
    for case in cases:
        for mode in ('oom', 'ok'):
            r = run(unit+'-'+case+'-'+mode, [exe, case, mode])
            r['passed'] = r['exit'] == 0
            print('PASS' if r['passed'] else 'FAIL', r['name'], flush=True)
checks = [r for r in rows if 'passed' in r]
report = {'commands': rows, 'passed': sum(r['passed'] for r in checks), 'total': len(checks)}
(out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
raise SystemExit(0 if report['passed'] == report['total'] else 1)
