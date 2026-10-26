#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Compile real backend functions, with OS and libusb plumbing stubbed.
import argparse,json,os,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('work',type=Path);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=False)
text=a.source.read_text()
def function(name):
 m=re.search(r'\n(?:static )?(?:int|void)\n'+name+r'\([^;]*?\n\{',text)
 if not m:return ''
 start=m.start();end=m.end();depth=1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]+'\n'
structs='\n'.join(re.search(r'struct '+n+r' \{.*?\n\};',text,re.S).group() for n in ('device_priv','handle_priv'))
functions=''.join(function(n) for n in ('_errno_to_libusb','_parse_bulk_read_ahead','_close_endpoints','_configure_bulk_read_ahead','netbsd_open','netbsd_close','netbsd_claim_interface','netbsd_release_interface','_access_endpoint','_sync_gen_transfer'))
assert function('netbsd_open') and function('_sync_gen_transfer')
here=Path(__file__).resolve().parent
fixture=a.work/'backend.c';fixture.write_text((here/'netbsd-header.c').read_text()+'\n'+structs+'\n'+functions+'\n'+(here/'netbsd-cases.c').read_text())
command=[os.environ['CC'],*os.environ.get('CFLAGS','').split()]
if os.environ.get('SDKROOT'):command+=['-isysroot',os.environ['SDKROOT']]
command+=['-std=c11','-Wall','-Wextra',str(fixture),'-o',str(a.work/'backend')];subprocess.run(command,check=True)
cases=['default','selected','unselected','out','interrupt','iso','cached-out','once','open-fail','option-fail','enable-fail','release','close','release-claim','release-close','double-release','claim-live','close-empty','mask-snapshot','multiple']
cases+=['invalid:'+x for x in ('','80','00','02','90','0x82',' 82','82 ','82,','82,,81','82,82','82,zz','82;81','82\n','8','082')]
results=[]
for case in cases:
 r=subprocess.run([str(a.work/'backend'),case],capture_output=True,text=True);results.append({'case':case,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
(a.work/'results.json').write_text(json.dumps({'command':command,'cases':results},indent=2)+'\n')
failed=[r['case'] for r in results if r['exit']];print(f'{len(cases)-len(failed)}/{len(cases)} PASS; failed: '+', '.join(failed));raise SystemExit(bool(failed))
