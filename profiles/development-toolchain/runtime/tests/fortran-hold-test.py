#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real lease HOLD, no compiler or SDK payload.
"""Check the actual Fortran HOLD functions with injected typed failures."""
import argparse,ast,copy,hashlib,importlib.util,json,os,signal,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
sys.dont_write_bytecode=True

def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def function(path,name):
    module=ast.parse(path.read_text());return next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name==name)
def emit(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-source',required=True,type=Path)
    parser.add_argument('--ports-source',required=True,type=Path)
    parser.add_argument('--sdk-source',required=True,type=Path)
    parser.add_argument('--new-work',required=True,type=Path)
    parser.add_argument('--child',choices=('protected','unguarded'))
    parser.add_argument('--stderr-case',choices=('normal','closed','EIO'))
    args=parser.parse_args()
    for name in ('candidate_source','ports_source','sdk_source'):setattr(args,name,getattr(args,name).resolve(strict=True))
    loader=args.ports_source/'profiles/development-toolchain/runtime/recipe/files/sdk_source.py'
    spec=importlib.util.spec_from_file_location('sdk_source',loader);sdk_source=importlib.util.module_from_spec(spec);spec.loader.exec_module(sdk_source);sdk_source.load(str(args.sdk_source))
    from emberbsd_sdk import paths
    from emberbsd_sdk.process import ContextLocks,OwnedProcessGroup
    from emberbsd_sdk.errors import SDKError,ProcessOwnershipError
    import inspect
    require('shared' in inspect.signature(ContextLocks).parameters,'SDK API1 shared leases required')
    support=args.candidate_source/'profiles/development-toolchain/cross/fortran_support.py'
    producer=args.candidate_source/'profiles/development-toolchain/bootstrap/fortran_runtime.py'
    source_pins={str(p):sha(p) for p in (support,producer,Path(__file__))}
    hold=function(support,'lease_hold');locked=function(producer,'locked_main')
    for source in (args.candidate_source,args.ports_source,args.sdk_source):paths.reject_overlap(source,args.new_work)
    if args.child:
        case=args.new_work.resolve(strict=True);host=case/'host';obj=case/'obj'
        class FixtureProducer:
            def __init__(self,remaining):
                require(not remaining,'Fixture has no producer arguments')
                self.pkgsrc=case/'pkgsrc';self.archive=case/'archive';self.compiler=case/'generation/toolchain'
                self.sysroot=case/'sysroot';self.base=case/'base';self.work=obj/'new-work'
            def build(self):
                emit(case/'entered.json',{'pid':os.getpid(),'scope':'Injected typed failure. No preflight, compiler, SDK payload or extractor ran.'})
                if args.stderr_case=='closed':os.close(2)
                elif args.stderr_case=='EIO':sys.stderr=FailingStderr()
                raise ProcessOwnershipError(123,'injected fixture ownership failure',None)
        if args.child=='unguarded':
            guarded=next(n for n in hold.body if isinstance(n,ast.Try))
            require(len(guarded.body)==1 and isinstance(guarded.body[0],ast.Expr) and isinstance(guarded.body[0].value,ast.Call) and isinstance(guarded.body[0].value.func,ast.Name) and guarded.body[0].value.func.id=='print','Expected the narrow diagnostic guard')
            index=hold.body.index(guarded);hold.body[index:index+1]=guarded.body
        namespace={'paths':paths,'require':require,'FortranRuntime':FixtureProducer,'PROFILE':case/'ports/profiles/profile','sdk_source':SimpleNamespace(load=lambda:str(case/'sdk')),'Path':Path,'ProcessOwnershipError':ProcessOwnershipError}
        exec(compile(ast.Module(body=[hold],type_ignores=[]),str(support),'exec'),namespace);namespace['ownership_hold']=namespace['lease_hold']
        exec(compile(ast.Module(body=[locked],type_ignores=[]),str(producer),'exec'),namespace)
        class FailingStderr:
            def write(self,value):raise OSError(9 if args.stderr_case=='closed' else 5,'injected diagnostic failure')
            def flush(self):pass
        namespace['locked_main'](['--lock-root',str(obj),'--host-prefix',str(host)])
        raise AssertionError('Production HOLD returned')
    work=args.new_work
    require(work.is_absolute() and work.resolve()==work and not os.path.lexists(work),'Use a new canonical work directory')
    work.mkdir();rows=[];live=[];all_drained=True
    def interrupted(number,frame):raise SystemExit(128+number)
    for number in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):signal.signal(number,interrupted)
    try:
        for stderr_case in ('normal','closed','EIO'):
            for variant in ('protected','unguarded'):
                if stderr_case=='normal' and variant=='unguarded':continue
                case=work/(stderr_case+'-'+variant);case.mkdir()
                for name in ('host','obj','pkgsrc','generation/toolchain','sysroot','base','ports/profiles/profile','sdk'):(case/name).mkdir(parents=True)
                (case/'archive').write_bytes(b'labelled fixture archive; no extractor')
                stdout=(case/'stdout.log').open('xb');stderr=(case/'stderr.log').open('xb')
                argv=[sys.executable,'-B',str(Path(__file__).resolve()),'--candidate-source',str(args.candidate_source),'--ports-source',str(args.ports_source),'--sdk-source',str(args.sdk_source),'--new-work',str(case),'--child',variant,'--stderr-case',stderr_case]
                group=OwnedProcessGroup(argv,cwd=str(case),env=os.environ.copy(),stdout=stdout,stderr=stderr);group.start();live.append((group,stdout,stderr));pid=group.pid
                identity=getattr(group.inspector,'identity',None);birth=None if identity is None else identity.birth(pid)
                deadline=time.monotonic()+15
                while not (case/'entered.json').exists() and group.poll() is None and time.monotonic()<deadline:time.sleep(.05)
                require((case/'entered.json').is_file(),'Fixture did not enter actual locked_main')
                if variant=='unguarded':
                    while group.poll() is None and time.monotonic()<deadline:time.sleep(.05)
                    require(group.poll() is not None and group.poll()!=0,'Removed diagnostic guard did not fail')
                else:
                    time.sleep(.2);require(group.poll() is None,'Protected HOLD returned')
                    for number in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):os.kill(group.pid,number)
                    time.sleep(.2);require(group.poll() is None,'HOLD did not retain signal policy')
                locks={}
                for target in (case/'sysroot',case/'host',case/'generation',case/'generation/toolchain',case/'obj/new-work'):
                    try:
                        with ContextLocks([str(target)],str(case/'obj')):pass
                    except SDKError as error:require('busy' in str(error),'Unexpected lease error');locks[target.name]=True
                    else:locks[target.name]=False
                require(all(locks.values()) if variant=='protected' else not any(locks.values()),'Incorrect real SH/work EX lifetime')
                group.stop();require(not group.alive(),'Own fixture session did not drain');stdout.close();stderr.close();live.remove((group,stdout,stderr))
                for target in (case/'sysroot',case/'host',case/'generation',case/'generation/toolchain',case/'obj/new-work'):
                    with ContextLocks([str(target)],str(case/'obj')):pass
                require(not (case/'obj/new-work').exists(),'Fixture unexpectedly created producer work')
                rows.append({'child_pid':pid,'child_birth_if_host_api_available':birth,'session_backend':group.inspector.describe(),'stderr':stderr_case,'variant':variant,'PASS':True,'locks_busy_before_own_test_stop':locks,'child_exit_after_stop':group.poll(),'stdout':(case/'stdout.log').read_text(errors='replace'),'stderr_log':(case/'stderr.log').read_text(errors='replace'),'limits':'Exact locked_main and lease_hold AST; injected producer.build, not a runtime producer.'})
    finally:
        for group,stdout,stderr in live:
            try:group.stop();require(not group.alive(),'Own fixture session did not drain')
            except BaseException:all_drained=False;raise
            finally:stdout.close();stderr.close()
    require(all_drained,'Fixture ownership remains unproved')
    require(all(sha(p)==digest for p,digest in source_pins.items()),'Source changed during lifecycle controls')
    result={'status':'PASS','source_pins':source_pins,'candidate_helper':str(support),'candidate_helper_sha256':sha(support),'candidate_producer_sha256':sha(producer),'test_source_sha256':sha(__file__),'cases':rows,'all_own_sessions_drained':True,'no_runtime_work_created':True,'SDK_payload_reads':False,'runtime_producers':0,'limits':'Real SDK shared/exclusive fixture leases and exact production function AST with an injected typed failure. Guard-removal witness is an in-memory AST change only. No compiler/preflight, normal package, Libtool, target execution, SDK or DB write.'}
    emit(work/'result.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
