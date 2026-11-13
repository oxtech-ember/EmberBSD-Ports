#!/usr/bin/env python3
"""Vulkan compute diagnostic, 921600 float values over two cycles."""
import ctypes as c
import argparse, base64, hashlib, math, struct
import sys

from vulkan_types import *

class Shader(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('size',c.c_size_t),('code',c.POINTER(U))]
class Binding(c.Structure): _fields_=[('binding',U),('type',U),('count',U),('stage',U),('samplers',P)]
class SetLayout(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('count',U),('bindings',c.POINTER(Binding))]
class PipelineLayout(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('count',U),('layouts',PP),('nrange',U),('ranges',P)]
class Stage(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('stage',U),('module',P),('name',c.c_char_p),('specialization',P)]
class Pipeline(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('stage',Stage),('layout',P),('base',P),('index',c.c_int32)]
class PoolSize(c.Structure): _fields_=[('type',U),('count',U)]
class DescPool(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('maxSets',U),('count',U),('sizes',c.POINTER(PoolSize))]
class SetAlloc(c.Structure): _fields_=[('s',U),('next',P),('pool',P),('count',U),('layouts',PP)]
class BufferInfo(c.Structure): _fields_=[('buffer',P),('offset',Z),('range',Z)]
class WriteSet(c.Structure): _fields_=[('s',U),('next',P),('set',P),('binding',U),('array',U),('count',U),('type',U),('image',P),('buffer',c.POINTER(BufferInfo)),('view',P)]

SHADER_BASE64 = 'AwIjBwAAAQALAAgALgAAAAAAAAARAAIAAQAAAAsABgABAAAAR0xTTC5zdGQuNDUwAAAAAA4AAwAAAAAAAQAAAA8ABgAFAAAABAAAAG1haW4AAAAACwAAABAABgAEAAAAEQAAAEAAAAABAAAAAQAAAAMAAwACAAAAwgEAAAUABAAEAAAAbWFpbgAAAAAFAAMACAAAAGkAAAAFAAgACwAAAGdsX0dsb2JhbEludm9jYXRpb25JRAAAAAUABAAYAAAAT3V0cHV0AAAGAAQAGAAAAAAAAAB4AAAABQADABoAAABkc3QABQAEAB8AAABJbnB1dAAAAAYABAAfAAAAAAAAAHgAAAAFAAMAIQAAAHNyYwBHAAQACwAAAAsAAAAcAAAARwAEABcAAAAGAAAABAAAAEcAAwAYAAAAAwAAAEgABAAYAAAAAAAAABkAAABIAAUAGAAAAAAAAAAjAAAAAAAAAEcAAwAaAAAAGQAAAEcABAAaAAAAIQAAAAEAAABHAAQAGgAAACIAAAAAAAAARwAEAB4AAAAGAAAABAAAAEcAAwAfAAAAAwAAAEgABAAfAAAAAAAAABgAAABIAAUAHwAAAAAAAAAjAAAAAAAAAEcAAwAhAAAAGAAAAEcABAAhAAAAIQAAAAAAAABHAAQAIQAAACIAAAAAAAAARwAEAC0AAAALAAAAGQAAABMAAgACAAAAIQADAAMAAAACAAAAFQAEAAYAAAAgAAAAAAAAACAABAAHAAAABwAAAAYAAAAXAAQACQAAAAYAAAADAAAAIAAEAAoAAAABAAAACQAAADsABAAKAAAACwAAAAEAAAArAAQABgAAAAwAAAAAAAAAIAAEAA0AAAABAAAABgAAACsABAAGAAAAEQAAAAAQDgAUAAIAEgAAABYAAwAWAAAAIAAAAB0AAwAXAAAAFgAAAB4AAwAYAAAAFwAAACAABAAZAAAAAgAAABgAAAA7AAQAGQAAABoAAAACAAAAFQAEABsAAAAgAAAAAQAAACsABAAbAAAAHAAAAAAAAAAdAAMAHgAAABYAAAAeAAMAHwAAAB4AAAAgAAQAIAAAAAIAAAAfAAAAOwAEACAAAAAhAAAAAgAAACAABAAjAAAAAgAAABYAAAArAAQABgAAACsAAABAAAAAKwAEAAYAAAAsAAAAAQAAACwABgAJAAAALQAAACsAAAAsAAAALAAAADYABQACAAAABAAAAAAAAAADAAAA+AACAAUAAAA7AAQABwAAAAgAAAAHAAAAQQAFAA0AAAAOAAAACwAAAAwAAAA9AAQABgAAAA8AAAAOAAAAPgADAAgAAAAPAAAAPQAEAAYAAAAQAAAACAAAALAABQASAAAAEwAAABAAAAARAAAA9wADABUAAAAAAAAA+gAEABMAAAAUAAAAFQAAAPgAAgAUAAAAPQAEAAYAAAAdAAAACAAAAD0ABAAGAAAAIgAAAAgAAABBAAYAIwAAACQAAAAhAAAAHAAAACIAAAA9AAQAFgAAACUAAAAkAAAAPQAEAAYAAAAmAAAACAAAAEEABgAjAAAAJwAAACEAAAAcAAAAJgAAAD0ABAAWAAAAKAAAACcAAACBAAUAFgAAACkAAAAlAAAAKAAAAEEABgAjAAAAKgAAABoAAAAcAAAAHQAAAD4AAwAqAAAAKQAAAPkAAgAVAAAA+AACABUAAAD9AAEAOAABAA=='

SHADERS = {'constant': 'AwIjBwAAAQALAAgAKAAAAAAAAAARAAIAAQAAAAsABgABAAAAR0xTTC5zdGQuNDUwAAAAAA4AAwAAAAAAAQAAAA8ABgAFAAAABAAAAG1haW4AAAAACwAAABAABgAEAAAAEQAAAEAAAAABAAAAAQAAAAMAAwACAAAAwgEAAAUABAAEAAAAbWFpbgAAAAAFAAMACAAAAGkAAAAFAAgACwAAAGdsX0dsb2JhbEludm9jYXRpb25JRAAAAAUABAAYAAAAT3V0cHV0AAAGAAQAGAAAAAAAAAB4AAAABQADABoAAABkc3QABQAEACUAAABJbnB1dAAAAAYABAAlAAAAAAAAAHgAAAAFAAMAJwAAAHNyYwBHAAQACwAAAAsAAAAcAAAARwAEABcAAAAGAAAABAAAAEcAAwAYAAAAAwAAAEgABAAYAAAAAAAAABkAAABIAAUAGAAAAAAAAAAjAAAAAAAAAEcAAwAaAAAAGQAAAEcABAAaAAAAIQAAAAEAAABHAAQAGgAAACIAAAAAAAAARwAEACMAAAALAAAAGQAAAEcABAAkAAAABgAAAAQAAABHAAMAJQAAAAMAAABIAAQAJQAAAAAAAAAYAAAASAAFACUAAAAAAAAAIwAAAAAAAABHAAMAJwAAABgAAABHAAQAJwAAACEAAAAAAAAARwAEACcAAAAiAAAAAAAAABMAAgACAAAAIQADAAMAAAACAAAAFQAEAAYAAAAgAAAAAAAAACAABAAHAAAABwAAAAYAAAAXAAQACQAAAAYAAAADAAAAIAAEAAoAAAABAAAACQAAADsABAAKAAAACwAAAAEAAAArAAQABgAAAAwAAAAAAAAAIAAEAA0AAAABAAAABgAAACsABAAGAAAAEQAAAAAQDgAUAAIAEgAAABYAAwAWAAAAIAAAAB0AAwAXAAAAFgAAAB4AAwAYAAAAFwAAACAABAAZAAAAAgAAABgAAAA7AAQAGQAAABoAAAACAAAAFQAEABsAAAAgAAAAAQAAACsABAAbAAAAHAAAAAAAAAArAAQAFgAAAB4AAAAAAIA/IAAEAB8AAAACAAAAFgAAACsABAAGAAAAIQAAAEAAAAArAAQABgAAACIAAAABAAAALAAGAAkAAAAjAAAAIQAAACIAAAAiAAAAHQADACQAAAAWAAAAHgADACUAAAAkAAAAIAAEACYAAAACAAAAJQAAADsABAAmAAAAJwAAAAIAAAA2AAUAAgAAAAQAAAAAAAAAAwAAAPgAAgAFAAAAOwAEAAcAAAAIAAAABwAAAEEABQANAAAADgAAAAsAAAAMAAAAPQAEAAYAAAAPAAAADgAAAD4AAwAIAAAADwAAAD0ABAAGAAAAEAAAAAgAAACwAAUAEgAAABMAAAAQAAAAEQAAAPcAAwAVAAAAAAAAAPoABAATAAAAFAAAABUAAAD4AAIAFAAAAD0ABAAGAAAAHQAAAAgAAABBAAYAHwAAACAAAAAaAAAAHAAAAB0AAAA+AAMAIAAAAB4AAAD5AAIAFQAAAPgAAgAVAAAA/QABADgAAQA=', 'add2d': 'AwIjBwAAAQALAAgAMwAAAAAAAAARAAIAAQAAAAsABgABAAAAR0xTTC5zdGQuNDUwAAAAAA4AAwAAAAAAAQAAAA8ABgAFAAAABAAAAG1haW4AAAAACwAAABAABgAEAAAAEQAAAEAAAAABAAAAAQAAAAMAAwACAAAAwgEAAAUABAAEAAAAbWFpbgAAAAAFAAMACAAAAGkAAAAFAAgACwAAAGdsX0dsb2JhbEludm9jYXRpb25JRAAAAAUABAAeAAAAT3V0cHV0AAAGAAQAHgAAAAAAAAB4AAAABQADACAAAABkc3QABQAEACUAAABJbnB1dAAAAAYABAAlAAAAAAAAAHgAAAAFAAMAJwAAAHNyYwBHAAQACwAAAAsAAAAcAAAARwAEAB0AAAAGAAAABAAAAEcAAwAeAAAAAwAAAEgABAAeAAAAAAAAABkAAABIAAUAHgAAAAAAAAAjAAAAAAAAAEcAAwAgAAAAGQAAAEcABAAgAAAAIQAAAAEAAABHAAQAIAAAACIAAAAAAAAARwAEACQAAAAGAAAABAAAAEcAAwAlAAAAAwAAAEgABAAlAAAAAAAAABgAAABIAAUAJQAAAAAAAAAjAAAAAAAAAEcAAwAnAAAAGAAAAEcABAAnAAAAIQAAAAAAAABHAAQAJwAAACIAAAAAAAAARwAEADIAAAALAAAAGQAAABMAAgACAAAAIQADAAMAAAACAAAAFQAEAAYAAAAgAAAAAAAAACAABAAHAAAABwAAAAYAAAAXAAQACQAAAAYAAAADAAAAIAAEAAoAAAABAAAACQAAADsABAAKAAAACwAAAAEAAAArAAQABgAAAAwAAAAAAAAAIAAEAA0AAAABAAAABgAAACsABAAGAAAAEAAAAIBwAAArAAQABgAAABEAAAABAAAAKwAEAAYAAAAXAAAAABAOABQAAgAYAAAAFgADABwAAAAgAAAAHQADAB0AAAAcAAAAHgADAB4AAAAdAAAAIAAEAB8AAAACAAAAHgAAADsABAAfAAAAIAAAAAIAAAAVAAQAIQAAACAAAAABAAAAKwAEACEAAAAiAAAAAAAAAB0AAwAkAAAAHAAAAB4AAwAlAAAAJAAAACAABAAmAAAAAgAAACUAAAA7AAQAJgAAACcAAAACAAAAIAAEACkAAAACAAAAHAAAACsABAAGAAAAMQAAAEAAAAAsAAYACQAAADIAAAAxAAAAEQAAABEAAAA2AAUAAgAAAAQAAAAAAAAAAwAAAPgAAgAFAAAAOwAEAAcAAAAIAAAABwAAAEEABQANAAAADgAAAAsAAAAMAAAAPQAEAAYAAAAPAAAADgAAAEEABQANAAAAEgAAAAsAAAARAAAAPQAEAAYAAAATAAAAEgAAAIQABQAGAAAAFAAAABAAAAATAAAAgAAFAAYAAAAVAAAADwAAABQAAAA+AAMACAAAABUAAAA9AAQABgAAABYAAAAIAAAAsAAFABgAAAAZAAAAFgAAABcAAAD3AAMAGwAAAAAAAAD6AAQAGQAAABoAAAAbAAAA+AACABoAAAA9AAQABgAAACMAAAAIAAAAPQAEAAYAAAAoAAAACAAAAEEABgApAAAAKgAAACcAAAAiAAAAKAAAAD0ABAAcAAAAKwAAACoAAAA9AAQABgAAACwAAAAIAAAAQQAGACkAAAAtAAAAJwAAACIAAAAsAAAAPQAEABwAAAAuAAAALQAAAIEABQAcAAAALwAAACsAAAAuAAAAQQAGACkAAAAwAAAAIAAAACIAAAAjAAAAPgADADAAAAAvAAAA+QACABsAAAD4AAIAGwAAAP0AAQA4AAEA'}

def main():
    parser=argparse.ArgumentParser(description='Vulkan isolated compute diagnostic')
    parser.add_argument('--variant',choices=('add1d','constant','add2d'),default='add1d')
    parser.add_argument('--source-memory',choices=('device-local','host'),default='device-local')
    parser.add_argument('--readback-memory',choices=('host','device-local'),default='host')
    parser.add_argument('--readback-type',type=int,help='require this compatible Vulkan memory type index')
    parser.add_argument('--staging',action='store_true',help='copy host input into device-local shader input')
    parser.add_argument('--vulkan-library',default='/usr/pkg/lib/libvulkan.so.1')
    parser.add_argument('--device-name',help='require this substring in the selected device name')
    args=parser.parse_args()
    SHADERS['add1d']=SHADER_BASE64
    vk=c.CDLL(args.vulkan_library)
    def f(name,restype,*args):
        fn=getattr(vk,name); fn.restype=restype; fn.argtypes=args; return fn
    def check(label,value):
        if value != 0: raise RuntimeError('%s VkResult %s'%(label,value))
    # All struct declarations and constants match installed vulkan_core.h on LP64.
    expected={App:48,Instance:64,Layer:520,QProps:24,QCreate:40,DevCreate:72,MemType:8,MemHeap:16,MemProps:520,Buffer:56,Requirements:24,Allocation:32,Pool:24,CommandAlloc:32,Begin:32,Copy:24,Barrier:56,Fence:24,Submit:72,Shader:40,Binding:24,SetLayout:32,PipelineLayout:48,Stage:48,Pipeline:96,PoolSize:8,DescPool:40,SetAlloc:40,BufferInfo:24,WriteSet:64}
    for t,size in expected.items():
        if c.sizeof(t)!=size: raise RuntimeError('unexpected ABI %s=%d expected %d'%(t.__name__,c.sizeof(t),size))
    n=U(); enumlayer=f('vkEnumerateInstanceLayerProperties',c.c_int,c.POINTER(U),c.POINTER(Layer)); check('layers count',enumlayer(c.byref(n),None)); layers=(Layer*n.value)(); check('layers enumerate',enumlayer(c.byref(n),layers)); available=[x.name.decode() for x in layers]; selected=b'VK_LAYER_KHRONOS_validation' if 'VK_LAYER_KHRONOS_validation' in available else None; layer_list=(c.c_char_p*1)(selected) if selected else None
    print('validation_layer',selected.decode() if selected else 'not installed',flush=True)
    app=App(0,None,b'ember-vulkan-copy-diagnostic',0,None,0,1<<22); ic=Instance(1,None,0,c.pointer(app),1 if selected else 0,layer_list,0,None); instance=P(); check('instance',f('vkCreateInstance',c.c_int,c.POINTER(Instance),P,PP)(c.byref(ic),None,c.byref(instance)))
    dev=P(); pool=P(); fence=P(); shader=P(); setlayout=P(); layout=P(); pipeline=P(); dpool=P(); buffers=[]; mems=[]; mapped=[]; pending=False
    try:
        enum=f('vkEnumeratePhysicalDevices',c.c_int,P,c.POINTER(U),PP); count=U(); check('physical count',enum(instance,c.byref(count),None));
        if count.value!=1: raise RuntimeError('expected exactly one physical GPU')
        physicals=(P*count.value)(); check('physical enumerate',enum(instance,c.byref(count),physicals)); physical=physicals[0]
        propbuf=c.create_string_buffer(4096); f('vkGetPhysicalDeviceProperties',None,P,P)(physical,propbuf); name=propbuf.raw[20:276].split(b'\0')[0].decode(errors='replace'); print('device',name,flush=True)
        max_groups=struct.unpack_from('=3I',propbuf.raw,516); max_invocations=struct.unpack_from('=I',propbuf.raw,528)[0]; max_size=struct.unpack_from('=3I',propbuf.raw,532); dispatch=(450,32,1) if args.variant=='add2d' else (14400,1,1)
        print('maxComputeWorkGroupCount',max_groups,'maxComputeWorkGroupSize',max_size,'maxComputeWorkGroupInvocations',max_invocations,'variant',args.variant,'dispatch',dispatch,flush=True)
        if any(x>y for x,y in zip(dispatch,max_groups)) or max_size[0]<64 or max_invocations<64: raise RuntimeError('dispatch exceeds device limits')
        if args.device_name and args.device_name not in name: raise RuntimeError('device name does not match --device-name')
        qp=f('vkGetPhysicalDeviceQueueFamilyProperties',None,P,c.POINTER(U),c.POINTER(QProps)); count=U(); qp(physical,c.byref(count),None); props=(QProps*count.value)(); qp(physical,c.byref(count),props); candidates=[i for i,x in enumerate(props) if x.count and x.flags&2];
        if not candidates: raise RuntimeError('no compute queue')
        family=candidates[0]; pri=c.c_float(1); qcreate=QCreate(2,None,0,family,1,c.pointer(pri)); dc=DevCreate(3,None,0,1,c.pointer(qcreate),0,None,0,None,None); check('device',f('vkCreateDevice',c.c_int,P,c.POINTER(DevCreate),P,PP)(physical,c.byref(dc),None,c.byref(dev))); queue=P(); f('vkGetDeviceQueue',None,P,U,U,PP)(dev,family,0,c.byref(queue))
        mp=MemProps(); f('vkGetPhysicalDeviceMemoryProperties',None,P,c.POINTER(MemProps))(physical,c.byref(mp)); print('queue family',family,flush=True)
        createbuf=f('vkCreateBuffer',c.c_int,P,c.POINTER(Buffer),P,PP); reqfn=f('vkGetBufferMemoryRequirements',None,P,P,c.POINTER(Requirements)); allocfn=f('vkAllocateMemory',c.c_int,P,c.POINTER(Allocation),P,PP); bind=f('vkBindBufferMemory',c.c_int,P,P,P,Z); size=3*480*640*4
        buffer_specs=([('src',1,6,1),('shader-input',0x22,1,0),('device',0x21,1,0),('readback',2,6,0)] if args.staging else [('src',0x20,6,1),('device',0x21,1,0),('readback',2,6,0)])
        input_index=1 if args.staging else 0; output_index=2 if args.staging else 1; readback_index=3 if args.staging else 2
        for label,usage,required,prefer in buffer_specs:
            b=P(); check(label+' buffer',createbuf(dev,c.byref(Buffer(12,None,0,size,usage,0,0,None)),None,c.byref(b))); buffers.append(b)
            r=Requirements(); reqfn(dev,b,c.byref(r))
            print(label,'usage',hex(usage),'memoryTypeBits',hex(r.bits),'requirements.size',r.size,'requirements.alignment',r.alignment,flush=True)
            valid=[i for i in range(mp.nt) if r.bits&(1<<i) and (mp.types[i].flags&required)==required]
            if label=='src' and args.source_memory=='host':
                valid=[i for i in valid if not mp.types[i].flags&1]
            if label=='readback':
                if args.readback_memory=='host':
                    valid=[i for i in valid if not mp.types[i].flags&1]
                else:
                    valid=[i for i in valid if mp.types[i].flags&1]
            if label=='readback' and args.readback_type is not None:
                valid=[i for i in valid if i==args.readback_type]
            if not valid: raise RuntimeError('no compatible memory type for '+label)
            if label=='src' and prefer and args.source_memory!='host': valid.sort(key=lambda i:not(mp.types[i].flags&prefer))
            index=valid[0]; m=P(); check(label+' allocation',allocfn(dev,c.byref(Allocation(5,None,r.size,index)),None,c.byref(m))); mems.append(m); check(label+' bind',bind(dev,b,m,0)); print(label,'memory type',index,'flags',hex(mp.types[index].flags),'heap',mp.types[index].heap,flush=True)
        mapfn=f('vkMapMemory',c.c_int,P,P,Z,Z,U,PP)
        for i in (0,readback_index):
            address=P(); check('map',mapfn(dev,mems[i],0,size,0,c.byref(address))); mapped.append((mems[i],address))
        shader_bytes=base64.b64decode(SHADERS[args.variant]); print('shader sha256',hashlib.sha256(shader_bytes).hexdigest(),flush=True)
        if len(shader_bytes)%4: raise RuntimeError('bad SPIR-V size')
        code=(U*(len(shader_bytes)//4)).from_buffer_copy(shader_bytes); sm=Shader(16,None,0,len(shader_bytes),code); check('shader',f('vkCreateShaderModule',c.c_int,P,c.POINTER(Shader),P,PP)(dev,c.byref(sm),None,c.byref(shader)))
        bs=(Binding*2)(Binding(0,7,1,0x20,None),Binding(1,7,1,0x20,None)); sl=SetLayout(32,None,0,2,bs); check('descriptor layout',f('vkCreateDescriptorSetLayout',c.c_int,P,c.POINTER(SetLayout),P,PP)(dev,c.byref(sl),None,c.byref(setlayout)))
        layouts=(P*1)(setlayout.value); pl=PipelineLayout(30,None,0,1,layouts,0,None); check('pipeline layout',f('vkCreatePipelineLayout',c.c_int,P,c.POINTER(PipelineLayout),P,PP)(dev,c.byref(pl),None,c.byref(layout)))
        st=Stage(18,None,0,0x20,shader,b'main',None); cp=Pipeline(29,None,0,st,layout,None,-1); check('compute pipeline',f('vkCreateComputePipelines',c.c_int,P,P,U,c.POINTER(Pipeline),P,PP)(dev,None,1,c.byref(cp),None,c.byref(pipeline)))
        ps=PoolSize(7,2); dp=DescPool(33,None,0,1,1,c.pointer(ps)); check('descriptor pool',f('vkCreateDescriptorPool',c.c_int,P,c.POINTER(DescPool),P,PP)(dev,c.byref(dp),None,c.byref(dpool)))
        descriptor=P(); da=SetAlloc(34,None,dpool,1,layouts); check('descriptor set',f('vkAllocateDescriptorSets',c.c_int,P,c.POINTER(SetAlloc),PP)(dev,c.byref(da),c.byref(descriptor)))
        db=(BufferInfo*2)(BufferInfo(buffers[input_index],0,size),BufferInfo(buffers[output_index],0,size)); writes=(WriteSet*2)(WriteSet(35,None,descriptor,0,0,1,7,None,c.pointer(db[0]),None),WriteSet(35,None,descriptor,1,0,1,7,None,c.pointer(db[1]),None)); f('vkUpdateDescriptorSets',None,P,U,c.POINTER(WriteSet),U,P)(dev,2,writes,0,None)
        check('command pool',f('vkCreateCommandPool',c.c_int,P,c.POINTER(Pool),P,PP)(dev,c.byref(Pool(39,None,0,family)),None,c.byref(pool))); cmd=P(); check('command buffer',f('vkAllocateCommandBuffers',c.c_int,P,c.POINTER(CommandAlloc),PP)(dev,c.byref(CommandAlloc(40,None,pool,0,1)),c.byref(cmd))); check('begin',f('vkBeginCommandBuffer',c.c_int,P,c.POINTER(Begin))(cmd,c.byref(Begin(42,None,0,None))))
        barrier=f('vkCmdPipelineBarrier',None,P,U,U,U,U,P,U,c.POINTER(Barrier),U,P); copy=f('vkCmdCopyBuffer',None,P,P,P,U,c.POINTER(Copy)); region=Copy(0,0,size); ignored=0xffffffff
        def bb(buffer,src,dst,ss,ds):
            b=Barrier(44,None,src,dst,ignored,ignored,buffer,0,size); barrier(cmd,ss,ds,0,0,None,1,c.byref(b),0,None)
        if args.staging:
            bb(buffers[0],0x4000,0x800,0x4000,0x1000)
            copy(cmd,buffers[0],buffers[input_index],1,c.byref(region))
            bb(buffers[input_index],0x1000,0x20,0x1000,0x800)
        else: bb(buffers[0],0x4000,0x20,0x4000,0x800)
        f('vkCmdBindPipeline',None,P,U,P)(cmd,1,pipeline)
        desc=(P*1)(descriptor.value); f('vkCmdBindDescriptorSets',None,P,U,P,U,U,PP,U,P)(cmd,1,layout,0,1,desc,0,None)
        f('vkCmdDispatch',None,P,U,U,U)(cmd,*dispatch)
        bb(buffers[output_index],0x40,0x800,0x800,0x1000); copy(cmd,buffers[output_index],buffers[readback_index],1,c.byref(region)); bb(buffers[readback_index],0x1000,0x2000,0x1000,0x4000)
        check('end',f('vkEndCommandBuffer',c.c_int,P)(cmd)); check('fence',f('vkCreateFence',c.c_int,P,c.POINTER(Fence),P,PP)(dev,c.byref(Fence(8,None,0)),None,c.byref(fence))); cmds=(P*1)(cmd.value); sub=Submit(4,None,0,None,None,1,cmds,0,None)
        submit=f('vkQueueSubmit',c.c_int,P,U,c.POINTER(Submit),P); wait=f('vkWaitForFences',c.c_int,P,U,PP,U,Z); reset=f('vkResetFences',c.c_int,P,U,PP); fp=(P*1)(fence.value)
        total_mismatch=0
        for cycle in range(2):
            # Alternating finite floats and varied words, unique across both cycles.
            pattern=(c.c_uint32*(size//4))(*([0x3f000000]*(size//4)))
            c.memmove(mapped[0][1],pattern,size); src_bytes=c.string_at(mapped[0][1],size); reference=c.string_at(c.addressof(pattern),size); src_mismatches=sum(a!=b for a,b in zip(src_bytes,reference)); print('cycle',cycle+1,'mapped_src_mismatched_bytes',src_mismatches,flush=True)
            if src_mismatches: raise RuntimeError('mapped CPU source differs before dispatch')
            c.memset(mapped[1][1],0xa5,size); print('submit cycle',cycle+1,flush=True); check('submit',submit(queue,1,c.byref(sub),fence)); pending=True; check('wait fence',wait(dev,1,fp,1,0xffffffffffffffff)); pending=False
            actual=c.string_at(mapped[1][1],size); expected_bytes=b'\x00\x00\x80\x3f'*(size//4); mismatch=sum(a!=b for a,b in zip(expected_bytes,actual)); first=next((i for i,(a,b) in enumerate(zip(expected_bytes,actual)) if a!=b),None); print('cycle',cycle+1,'bytes',size,'mismatched_bytes',mismatch,'first',first,flush=True)
            floats=struct.unpack('=%df'%(size//4),actual); boundary=512*1024
            for label,part in (('before_2MiB',floats[:boundary]),('at_after_2MiB',floats[boundary:])):
                print('cycle',cycle+1,label,'count',len(part),'correct',sum(x==1.0 for x in part),'nan',sum(math.isnan(x) for x in part),'inf',sum(math.isinf(x) for x in part),flush=True)
            if first is not None:
                lo=max(0,(first-16)//4); hi=min(len(floats),(first+64+3)//4)
                print('cycle',cycle+1,'floats_around_first_bad',[(i,floats[i]) for i in range(lo,hi)],flush=True)
            total_mismatch+=mismatch
            if cycle==0: check('reset fence',reset(dev,1,fp))
        if total_mismatch: raise RuntimeError('compute bytes differ')
        print('PASS Vulkan compute float addition',flush=True)
    finally:
        if dev.value and pending: check('device idle',f('vkDeviceWaitIdle',c.c_int,P)(dev))
        if dev.value:
            for mem,addr in mapped: f('vkUnmapMemory',None,P,P)(dev,mem)
            if dpool.value: f('vkDestroyDescriptorPool',None,P,P,P)(dev,dpool,None)
            if pipeline.value: f('vkDestroyPipeline',None,P,P,P)(dev,pipeline,None)
            if layout.value: f('vkDestroyPipelineLayout',None,P,P,P)(dev,layout,None)
            if setlayout.value: f('vkDestroyDescriptorSetLayout',None,P,P,P)(dev,setlayout,None)
            if shader.value: f('vkDestroyShaderModule',None,P,P,P)(dev,shader,None)
            if fence.value: f('vkDestroyFence',None,P,P,P)(dev,fence,None)
            if pool.value: f('vkDestroyCommandPool',None,P,P,P)(dev,pool,None)
            for b in buffers: f('vkDestroyBuffer',None,P,P,P)(dev,b,None)
            for m in mems: f('vkFreeMemory',None,P,P,P)(dev,m,None)
            f('vkDestroyDevice',None,P,P)(dev,None)
        f('vkDestroyInstance',None,P,P)(instance,None)
if __name__=='__main__':
    try: main()
    except Exception as e: print('FAIL:',e,file=sys.stderr,flush=True); sys.exit(1)
