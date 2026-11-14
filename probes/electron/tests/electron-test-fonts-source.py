#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import argparse, importlib.util, json, os, subprocess, tempfile
from pathlib import Path
import sys
parser=argparse.ArgumentParser()
parser.add_argument('--sdk-source',type=Path,required=True)
parser.add_argument('--workspace',type=Path,required=True)
parser.add_argument('--archive',type=Path,required=True)
parser.add_argument('--git',type=Path,required=True)
args=parser.parse_args()
sys.path.insert(0,str(args.sdk_source/'src'))
from emberbsd_sdk import paths, sourceprep, publication
from emberbsd_sdk.errors import SDKError
spec=importlib.util.spec_from_file_location('fonts',Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/test-fonts-source.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sdk={'paths':paths,'sourceprep':sourceprep,'publication':publication}
workspace=args.workspace
archive=args.archive
deps=subprocess.check_output([str(args.git),'-C',str(workspace/'src'),'show','HEAD:DEPS']).decode()
for field in ('size','generation'):
 bad=deps.replace(str(m.IDENTITY[field]),str(m.IDENTITY[field])+'0',1)
 try:m.validate_deps(bad)
 except ValueError as e:assert 'DEPS identity changed' in str(e)
 else:raise AssertionError('changed '+field+' accepted')
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp); dest=root/'prepared'
 bad=root/'bad.tar.gz';bad.write_bytes(b'bad')
 try:m.prepare(sdk,workspace,str(args.git),bad,root/'bad-dest')
 except ValueError as e:assert 'archive mismatch' in str(e)
 else:raise AssertionError('corrupt archive accepted')
 assert not (root/'bad-dest').exists()
 m.prepare(sdk,workspace,str(args.git),archive,dest)
 target=m.validate(sdk,workspace,str(args.git),dest)
 assert (target/'Ahem.ttf').is_file() and len(list(target.iterdir()))==83
 work=root/'work';work.mkdir(); fake=root/'workspace'; (fake/'src/third_party/test_fonts').mkdir(parents=True)
 link=fake/'src/third_party/test_fonts/test_fonts'; marker=work/'serial-test-fonts-link.json'
 with m.linked(work,fake,target): assert link.is_symlink() and marker.is_file()
 assert not link.exists() and not marker.exists()
 try:
  with m.linked(work,fake,target):raise RuntimeError('failed Ninja')
 except RuntimeError:pass
 assert not os.path.lexists(link) and not marker.exists()
 marker.write_text(json.dumps({'link':str(link),'target':str(target)}));link.symlink_to(target)
 m.recover(work,fake,target);assert not link.exists() and not marker.exists()
 link.symlink_to(target)
 try:m.recover(work,fake,target)
 except ValueError as e:assert 'foreign' in str(e)
 else:raise AssertionError('foreign link accepted')
 assert link.is_symlink();link.unlink()
 marker.write_text(json.dumps({'link':str(link),'target':'/unexpected'}));link.symlink_to(target)
 try:m.recover(work,fake,target)
 except ValueError as e:assert 'foreign' in str(e)
 else:raise AssertionError('foreign marker accepted')
 assert link.is_symlink() and marker.is_file();link.unlink();marker.unlink()
 (target/'Ahem.ttf').write_bytes(b'corrupt')
 try:m.validate(sdk,workspace,str(args.git),dest)
 except SDKError as e:assert 'prepared source identity or payload changed' in str(e)
 else:raise AssertionError('corrupt payload accepted')
 print('PASS real archive and SDK receipt; owned cleanup/recovery; foreign link and corrupt tree rejected')
