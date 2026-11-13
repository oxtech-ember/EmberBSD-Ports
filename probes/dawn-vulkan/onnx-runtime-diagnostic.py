#!/usr/bin/env python3
"""ORT 1.31 CPU/WebGPU diagnostic. Compare all float32 outputs of a fixed-shape ONNX model across CPU and WebGPU."""
import argparse, ctypes as c, json, math, os, re, sys, collections
P=c.c_void_p; PP=c.POINTER(P); S=c.c_size_t; I=c.c_int; B=c.c_char_p


def api_names(hdr, struct_name):
    body=hdr.split('struct '+struct_name+' {',1)[1].split('\n};',1)[0]
    body=re.sub(r'/\*.*?\*/|//[^\n]*','',body,flags=re.S)
    names=[]
    for decl in body.split(';'):
        decl=decl.strip()
        if not decl: continue
        m=re.search(r'ORT_API2_STATUS\(\s*(\w+)|ORT_CLASS_RELEASE\(\s*(\w+)|\(ORT_API_CALL\s*\*\s*(\w+)\)|ORT_API_T\(\s*[^,]+,\s*(\w+)',decl)
        if not m: raise RuntimeError('unrecognized '+struct_name+' entry '+decl[:100])
        n=m.group(1) or ('Release'+m.group(2) if m.group(2) else None) or m.group(3) or m.group(4); names.append(n)
    return names

def compare_outputs(cpu, gpu, atol, rtol):
    if len(cpu) != len(gpu): raise RuntimeError('CPU/GPU output counts differ')
    failures = 0
    for (name, ashape, aout), (bname, bshape, bout) in zip(cpu, gpu):
        if name != bname or ashape != bshape or len(aout) != len(bout):
            raise RuntimeError('CPU/GPU output shapes or names differ')
        bad = sum(not math.isfinite(a) or not math.isfinite(b) or
                  abs(a-b) > atol + rtol*abs(a) for a,b in zip(aout,bout))
        maxdiff = max((abs(a-b) for a,b in zip(aout,bout) if math.isfinite(a) and math.isfinite(b)), default=0)
        print('compare output=%s count=%d mismatches=%d max_abs_diff=%g' %
              (name.decode(), len(aout), bad, maxdiff), flush=True)
        failures += bad
    return failures

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=['cpu','compare'],default='compare'); ap.add_argument('--strict',action='store_true',help='reject CPU-assigned graph nodes'); ap.add_argument('--model',required=True); ap.add_argument('--prefix',default='/usr/pkg'); ap.add_argument('--vendor',type=lambda x:int(x,0)); ap.add_argument('--device',type=lambda x:int(x,0)); ap.add_argument('--profile-dir',required=True); ap.add_argument('--expected',type=float); ap.add_argument('--ep-option',action='append',default=[],metavar='KEY=VALUE'); ap.add_argument('--output-dir',help='existing directory for exclusive raw output snapshots'); ap.add_argument('--input-file',help='raw little-endian float32 tensor data'); ap.add_argument('--fill',type=float,help='constant input instead of deterministic pattern'); ap.add_argument('--atol',type=float,default=1e-3); ap.add_argument('--rtol',type=float,default=1e-3); args=ap.parse_args()
    if args.input_file and args.fill is not None: ap.error('--input-file and --fill are mutually exclusive')
    if not math.isfinite(args.atol) or not math.isfinite(args.rtol) or args.atol < 0 or args.rtol < 0: ap.error('tolerances must be finite and nonnegative')
    if args.expected is not None and not math.isfinite(args.expected): ap.error('--expected must be finite')
    if (args.vendor is None) != (args.device is None): ap.error('--vendor and --device must be supplied together')
    if not os.path.isdir(args.profile_dir): raise RuntimeError('profile directory must already exist')
    if args.output_dir and not os.path.isdir(args.output_dir): raise RuntimeError('output directory must already exist')
    if args.output_dir and sys.byteorder!='little': raise RuntimeError('output snapshots require little-endian host')
    # ORT uses a stable versioned function-pointer table; derive indices from the installed header.
    hdr=open(os.path.join(args.prefix,'include/onnxruntime/onnxruntime_c_api.h')).read()
    if not re.search(r'#define\s+ORT_API_VERSION\s+31\b',hdr): raise RuntimeError('expected ORT C API 31 header')
    names=api_names(hdr, 'OrtApi')
    lib=c.CDLL(os.path.join(args.prefix,'lib/libonnxruntime.so.1')); lib.OrtGetApiBase.restype=PP; base=lib.OrtGetApiBase()
    getapi=c.CFUNCTYPE(P,c.c_uint)(base[0]); address=getapi(31)
    if not address: raise RuntimeError('runtime does not support ORT API 31')
    table=c.cast(address,PP)
    def fn(name,ret,*types): return c.CFUNCTYPE(ret,*types)(table[names.index(name)])
    err=fn('GetErrorMessage',B,P); release_status=fn('ReleaseStatus',None,P)
    def call(name,types,*values):
        status=fn(name,P,*types)(*values)
        if status:
            msg=err(status).decode(errors='replace'); release_status(status); raise RuntimeError(name+': '+msg)
    def drop(name,obj):
        if obj and obj.value: fn('Release'+name,None,P)(obj); obj.value=None
    env=P(); call('CreateEnv',[I,B,PP],2,b'onnx-webgpu-diagnostic',c.byref(env)); allocator=P(); call('GetAllocatorWithDefaultOptions',[PP],c.byref(allocator))
    mem=P(); tensor=P(); data=None; input_contract=None
    call('CreateCpuMemoryInfo',[I,I,PP],1,0,c.byref(mem))
    def shape_info(info):
        kind=I(); call('GetTensorElementType',[P,c.POINTER(I)],info,c.byref(kind))
        nd=S(); call('GetDimensionsCount',[P,c.POINTER(S)],info,c.byref(nd))
        dims=(c.c_int64*nd.value)(); call('GetDimensions',[P,c.POINTER(c.c_int64),S],info,dims,nd.value)
        return kind.value, tuple(dims)
    def metadata(session, which):
        count=S(); call('SessionGet'+which+'Count',[P,c.POINTER(S)],session,c.byref(count))
        entries=[]
        for index in range(count.value):
            name=P(); typ=P(); tensor_info=P()
            try:
                call('SessionGet'+which+'Name',[P,S,P,PP],session,index,allocator,c.byref(name))
                call('SessionGet'+which+'TypeInfo',[P,S,PP],session,index,c.byref(typ))
                call('CastTypeInfoToTensorInfo',[P,PP],typ,c.byref(tensor_info))
                if not tensor_info.value: raise RuntimeError(which+' is not a tensor')
                kind,dims=shape_info(tensor_info)
                entries.append((c.string_at(name),kind,dims))
            finally:
                drop('TypeInfo',typ)
                if name.value: call('AllocatorFree',[P,P],allocator,name)
        return entries
    def prepare_input(entries):
        nonlocal data,input_contract
        if len(entries)!=1: raise RuntimeError('expected exactly one input tensor')
        name,kind,dims=entries[0]
        if kind!=1 or len(dims)!=4 or any(d<=0 for d in dims):
            raise RuntimeError('input must be fixed-shape rank-4 float32: '+str(entries))
        count=math.prod(dims)
        if count>100_000_000: raise RuntimeError('input tensor too large')
        if input_contract is not None:
            if entries!=input_contract: raise RuntimeError('CPU and GPU input metadata differ')
            return
        input_contract=entries
        if args.input_file:
            if sys.byteorder!='little': raise RuntimeError('input-file requires little-endian host')
            raw=open(args.input_file,'rb').read()
            if len(raw)!=count*4: raise RuntimeError('input file length does not match model')
            data=(c.c_float*count).from_buffer_copy(raw)
        elif args.fill is not None:
            data=(c.c_float*count)(*([args.fill]*count))
        else:
            data=(c.c_float*count)(*((i%251-125)/250.0 for i in range(count)))
        if any(not math.isfinite(x) for x in data): raise RuntimeError('input contains nonfinite values')
        shape=(c.c_int64*len(dims))(*dims)
        call('CreateTensorWithDataAsOrtValue',[P,P,S,c.POINTER(c.c_int64),S,I,PP],mem,c.cast(data,P),c.sizeof(data),shape,len(dims),1,c.byref(tensor))
        print('input name=%s dtype=float32 shape=%s source=%s'%(name.decode(),dims,args.input_file or ('fill' if args.fill is not None else 'deterministic')),flush=True)
    registered=False
    def run(which):
        nonlocal registered
        opt=P(); session=P(); info=P(); profile=P(); outputs=None
        try:
            call('CreateSessionOptions',[PP],c.byref(opt)); call('SetIntraOpNumThreads',[P,I],opt,2); call('SetSessionGraphOptimizationLevel',[P,I],opt,99)
            prefix=os.path.join(args.profile_dir,'onnx-diagnostic-'+which).encode(); call('EnableProfiling',[P,B],opt,prefix)
            if which=='gpu':
                os.environ.pop('ORT_WEBGPU_EP_ALLOW_SOFTWARE_ADAPTER',None)
                call('RegisterExecutionProviderLibrary',[P,B,B],env,b'diagnostic_webgpu',os.fsencode(os.path.join(args.prefix,'lib/libonnxruntime_providers_webgpu.so'))); registered=True
                devices=PP(); count=S(); call('GetEpDevices',[P,c.POINTER(PP),c.POINTER(S)],env,c.byref(devices),c.byref(count))
                epname=fn('EpDevice_EpName',B,P); hardware=fn('EpDevice_Device',P,P); vendor=fn('HardwareDevice_VendorId',c.c_uint32,P); devid=fn('HardwareDevice_DeviceId',c.c_uint32,P); typ=fn('HardwareDevice_Type',I,P)
                matches=[]
                for i in range(count.value):
                    ep=devices[i]; name=epname(ep) or b''; hw=hardware(ep)
                    if hw and b'WebGpu' in name and typ(hw)==1 and (args.vendor is None or (vendor(hw)==args.vendor and devid(hw)==args.device)): matches.append(ep)
                if len(matches)!=1: raise RuntimeError('expected exactly one matching WebGPU device, found '+str(len(matches)))
                selected=(P*1)(matches[0]); call('SessionOptionsAppendExecutionProvider_V2',[P,P,PP,S,PP,PP,S],opt,env,selected,1,None,None,0)
                for option in args.ep_option:
                    key, sep, value=option.partition('=')
                    if not sep or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*',key) or not value: raise RuntimeError('invalid EP option: '+option)
                    call('AddSessionConfigEntry',[P,B,B],opt,('ep.webgpuexecutionprovider.'+key).encode(),value.encode()); print('WebGPU option '+key+'='+value,flush=True)
                if args.strict: call('AddSessionConfigEntry',[P,B,B],opt,b'session.disable_cpu_ep_fallback',b'1')
                hw=hardware(matches[0]); print('selected ORT hardware vendor=%04x device=%04x strict=%s (Dawn adapter selected separately)'%(vendor(hw),devid(hw),args.strict),flush=True)
            print(which+' create session',flush=True); call('CreateSession',[P,B,P,PP],env,os.fsencode(args.model),opt,c.byref(session))
            inputs=metadata(session,'Input'); descriptions=metadata(session,'Output')
            if not descriptions: raise RuntimeError('model has no outputs')
            for name,kind,dims in descriptions:
                if kind!=1: raise RuntimeError('output %s is not float32 (type %s)'%(name.decode(),kind))
                print('%s output_metadata name=%s dtype=float32 shape=%s'%(which,name.decode(),dims),flush=True)
            prepare_input(inputs)
            ins=(B*1)(inputs[0][0]); outs=(B*len(descriptions))(*(x[0] for x in descriptions))
            vals=(P*1)(tensor.value); results=[]; result_errors=[]
            for iteration in (1,2):
                print(which+' inference '+str(iteration),flush=True)
                outputs=(P*len(descriptions))()
                call('Run',[P,P,c.POINTER(B),PP,S,c.POINTER(B),S,PP],session,None,ins,vals,1,outs,len(descriptions),outputs)
                run_results=[]
                for index,(name,declared_type,declared_shape) in enumerate(descriptions):
                    value=P(outputs[index]); call('GetTensorTypeAndShape',[P,PP],value,c.byref(info))
                    kind,dims=shape_info(info)
                    if kind!=declared_type or len(dims)!=len(declared_shape) or any(want>=0 and got!=want for want,got in zip(declared_shape,dims)):
                        raise RuntimeError('output metadata mismatch '+name.decode())
                    n=S(); call('GetTensorShapeElementCount',[P,c.POINTER(S)],info,c.byref(n))
                    if n.value>100_000_000: raise RuntimeError('output tensor too large')
                    ptr=P(); call('GetTensorMutableData',[P,PP],value,c.byref(ptr))
                    if args.output_dir:
                        stem=os.path.join(args.output_dir,'%s-run%d-output%d'%(which,iteration,index))
                        with open(stem+'.f32','xb') as f: f.write(c.string_at(ptr,n.value*4))
                        with open(stem+'.json','x') as f:
                            json.dump({'name':name.decode(),'dtype':'float32','byte_order':'little','shape':dims},f)
                        print('snapshot='+stem+'.f32',flush=True)
                    result=list(c.cast(ptr,c.POINTER(c.c_float*n.value)).contents)
                    bad=[(i,str(x)) for i,x in enumerate(result) if not math.isfinite(x)]
                    print('%s run=%d output=%s shape=%s len=%d nonfinite=%d first_bad=%s'%(which,iteration,name.decode(),dims,len(result),len(bad),bad[:10]),flush=True)
                    if bad: result_errors.append(which+' output nonfinite: '+name.decode())
                    if args.expected is not None and any(abs(x-args.expected)>args.atol+args.rtol*abs(args.expected) for x in result):
                        result_errors.append(which+' output differs from expected: '+name.decode())
                    run_results.append((name,dims,result))
                    drop('TensorTypeAndShapeInfo',info)
                    drop('Value',value); outputs[index]=None
                results.append(run_results)
            if result_errors: raise RuntimeError('; '.join(result_errors))
            return descriptions,results
        finally:
            drop('TensorTypeAndShapeInfo',info)
            if outputs is not None:
                for output in outputs:
                    value=P(output); drop('Value',value)
            profile_error=None
            if session.value:
                try:
                    call('SessionEndProfiling',[P,P,PP],session,allocator,c.byref(profile))
                    profile_path=os.fsdecode(c.string_at(profile)); print(which+' profile='+profile_path,flush=True)
                    with open(profile_path) as f: events=json.load(f)
                    assigned=collections.Counter((e.get('args') or {}).get('provider') for e in events if (e.get('args') or {}).get('provider'))
                    print(which+' profile_provider_events='+str(dict(assigned)),flush=True)
                    if which=='gpu' and not any('WebGpu' in str(name) or 'WebGPU' in str(name) for name in assigned):
                        raise RuntimeError('profile has no WebGPU-executed nodes')
                except Exception as e:
                    profile_error=e
                finally:
                    if profile.value: call('AllocatorFree',[P,P],allocator,profile)
            drop('Session',session); drop('SessionOptions',opt)
            print(which+' session released',flush=True)
            if profile_error: raise profile_error
    try:
        cpu_meta,cpu=run('cpu')
        if args.mode=='compare':
            gpu_meta,gpu=run('gpu')
            if cpu_meta!=gpu_meta: raise RuntimeError('CPU/GPU output metadata differ')
            failures=0
            for iteration,(cpu_run,gpu_run) in enumerate(zip(cpu,gpu),1):
                print('comparison run=%d'%iteration,flush=True)
                failures += compare_outputs(cpu_run,gpu_run,args.atol,args.rtol)
            if failures: raise RuntimeError('CPU/GPU output comparison failed')
    finally:
        drop('Value',tensor); drop('MemoryInfo',mem)
        if registered: call('UnregisterExecutionProviderLibrary',[P,B],env,b'diagnostic_webgpu'); print('provider unregistered',flush=True)
        drop('Env',env); print('environment released',flush=True)
if __name__=='__main__':
    try: main()
    except Exception as e: print('FAIL:',e,file=sys.stderr,flush=True); sys.exit(1)
