# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
import importlib.util, tempfile
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
s=importlib.util.spec_from_file_location('owner',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
label=m.SERIAL_TEST_LABEL
assert m.selected_test({}) is None
assert m.root_patterns(None)==['--root-target=//electron','--root-pattern=//electron:electron_dist_zip','--fail-on-unused-args']
assert m.selected_test({},label)==label
assert m.selected_test({'test_target':label})==label
assert m.selected_test({'test_target':label},clear=True) is None
assert 'test_target' not in m.test_configuration({}, {}, '/src', '/sdk', '/host', 'amd64', None)
assert m.test_configuration({}, {}, '/src', '/sdk', '/host', 'amd64', label)['test_target']==label
try: m.selected_test({},label,True)
except Exception: pass
else: raise AssertionError('select and clear accepted')
assert m.root_patterns(label)==['--root-target=//electron','--root-pattern=//electron:electron_dist_zip','--root-pattern='+label,'--fail-on-unused-args']
for saved,requested in [({'test_target':'//bad'},None),({},'//bad')]:
 try: m.selected_test(saved,requested)
 except Exception: pass
 else: raise AssertionError('invalid test selection accepted')
with tempfile.TemporaryDirectory() as t:
 root=Path(t)
 for n in ('work','workspace','sysroot','host','ports','sdk','source','packages','release'): (root/n).mkdir()
 o=SimpleNamespace(work=root/'work',workspace=root/'workspace',sysroot=root/'sysroot',host_prefix=root/'host',ports_source=root/'ports',sdk_source=root/'sdk',diagnostic_output=root/'diag',jobs=4,keep_going=1)
 o.diagnostic_inputs=m.context_keys(o.work,o.workspace,o.sysroot,o.host_prefix,o.ports_source,o.sdk_source,root/'packages',root/'release')
 calls=[]
 sdk={'process':SimpleNamespace(run_logged=lambda *a,**kw:calls.append((a,kw)))}
 native=SimpleNamespace(tool=lambda x:'/selected/bin/'+x)
 m.run_test_ninja(o,sdk,native,root/'source',{'PYTHON_CPU_COUNT':'8'})
 argv=calls[0][0][0]
 assert argv==['/selected/bin/ninja','-C',str(root/'work'/'out'),'-j','4','-k','1','netbsd_serial_refresh_unittests']
 assert calls[0][1]['env']['PYTHON_CPU_COUNT']=='1'
 try: m.run_test_ninja(o,sdk,native,root/'source',{})
 except Exception: pass
 else: raise AssertionError('existing diagnostic output accepted')
 o.diagnostic_output=root/'work'/'diag'
 try: m.run_test_ninja(o,sdk,native,root/'source',{})
 except Exception: pass
 else: raise AssertionError('overlapping diagnostic output accepted')
with tempfile.TemporaryDirectory() as t:
 root=Path(t); protected=root/'release'; protected.mkdir()
 assert str(protected.resolve()) in m.context_keys(protected)
print('owner test-selection API PASS')
