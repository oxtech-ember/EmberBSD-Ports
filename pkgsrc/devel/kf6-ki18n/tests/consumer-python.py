#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse, os, pathlib, shlex, subprocess, tempfile
parser=argparse.ArgumentParser()
parser.add_argument('--cmake', required=True)
parser.add_argument('--source', required=True, type=pathlib.Path)
parser.add_argument('--ninja', required=True)
options=parser.parse_args()
cmake=options.cmake
source=options.source / 'cmake'
with tempfile.TemporaryDirectory(prefix='ki18n fixture ') as temp:
 root=pathlib.Path(temp); (root/'modules').mkdir(); (root/'modules/FindGettext.cmake').write_text('set(Gettext_FOUND TRUE)\n')
 host=root/'host bin'; host.mkdir(); python=host/'python3'; python.write_text('#!/bin/sh\nexit 0\n'); python.chmod(0o755)
 target=root/'sysroot/usr/bin'; target.mkdir(parents=True); (target/'python3').write_text('#!/bin/sh\nexit 91\n'); (target/'python3').chmod(0o755)
 script=root/'check.cmake'; script.write_text(f'set(CMAKE_MODULE_PATH "{root}/modules")\nset(CMAKE_FIND_ROOT_PATH "{root}/sysroot")\nset(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM ONLY)\ninclude("{source}/KF6I18nMacros.cmake.in")\nfile(WRITE "{root}/selected" "${{KI18N_PYTHON_EXECUTABLE}}")\n')
 def run(path, extra=[]): return subprocess.run([cmake,*extra,'-P',str(script)],env={'PATH':path},capture_output=True,text=True)
 explicit=root/'explicit python'; explicit.write_text('#!/bin/sh\nprintf invoked > '+shlex.quote(str(root/'invoked'))+'\nexit 0\n'); explicit.chmod(0o755)
 assert run(str(host),['-DPython3_EXECUTABLE='+str(explicit)]).returncode==0 and (root/'selected').read_text()==str(explicit)
 assert run(str(host)).returncode==0 and (root/'selected').read_text()==str(python)
 assert run(str(root)).returncode==0 and (root/'selected').read_text().endswith('-NOTFOUND')
 po=root/'po'; po.mkdir(); out=root/'out'; out.mkdir(); ts=source/'build-tsfiles.cmake'; args=[cmake,'-DPO_DIR='+str(po),'-DCOPY_TO='+str(out),'-DPython3_EXECUTABLE=KI18N_PYTHON_EXECUTABLE-NOTFOUND','-P',str(ts)]
 assert subprocess.run(args,capture_output=True).returncode==0
 (po/'sub').mkdir(); (po/'sub/sample.pmap').write_text('test')
 fail=subprocess.run(args,capture_output=True,text=True); assert fail.returncode and 'Python 3 is required' in fail.stderr
 project=root/'project'; project.mkdir(); (project/'po/sub').mkdir(parents=True); (project/'po/sub/sample.pmap').write_text('test')
 (project/'CMakeLists.txt').write_text(f'cmake_minimum_required(VERSION 3.20)\nproject(fixture NONE)\nset(CMAKE_MODULE_PATH "{root}/modules")\nset(KDE_INSTALL_LOCALEDIR share/locale)\ninclude("{source}/KF6I18nMacros.cmake.in")\nKI18N_INSTALL("{project}/po")\n')
 env=dict(os.environ, PATH=str(host)+':'+os.environ.get('PATH',''))
 conf=subprocess.run([cmake,'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+options.ninja,'-S',str(project),'-B',str(root/'build'),'-DPython3_EXECUTABLE='+str(explicit)],env=env,capture_output=True,text=True); assert conf.returncode==0, conf.stderr
 result=subprocess.run([cmake,'--build',str(root/'build'),'--target','tsfiles'],env=env,capture_output=True,text=True); assert result.returncode==0, result.stdout+result.stderr
 assert (root/'invoked').read_text()=='invoked'
 print('PASS: explicit path, host PATH despite cross root, missing only on pmap')
