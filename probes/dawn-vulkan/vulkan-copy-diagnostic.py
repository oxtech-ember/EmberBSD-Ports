#!/usr/bin/env python3
"""Vulkan transfer-only round-trip of two 4 MiB deterministic patterns."""
import ctypes as c
import sys
import argparse

from vulkan_types import *

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vulkan-library',default='/usr/pkg/lib/libvulkan.so.1')
    parser.add_argument('--device-name',help='require this substring in the selected device name')
    args=parser.parse_args()
    vk=c.CDLL(args.vulkan_library)
    def f(name,restype,*args):
        fn=getattr(vk,name); fn.restype=restype; fn.argtypes=args; return fn
    def check(label,value):
        if value != 0: raise RuntimeError('%s VkResult %s'%(label,value))
    # All struct declarations and constants match installed vulkan_core.h on LP64.
    expected={App:48,Instance:64,Layer:520,QProps:24,QCreate:40,DevCreate:72,MemType:8,MemHeap:16,MemProps:520,Buffer:56,Requirements:24,Allocation:32,Pool:24,CommandAlloc:32,Begin:32,Copy:24,Barrier:56,Fence:24,Submit:72}
    for t,size in expected.items():
        if c.sizeof(t)!=size: raise RuntimeError('unexpected ABI %s=%d expected %d'%(t.__name__,c.sizeof(t),size))
    n=U(); enumlayer=f('vkEnumerateInstanceLayerProperties',c.c_int,c.POINTER(U),c.POINTER(Layer)); check('layers count',enumlayer(c.byref(n),None)); layers=(Layer*n.value)(); check('layers enumerate',enumlayer(c.byref(n),layers)); available=[x.name.decode() for x in layers]; selected=b'VK_LAYER_KHRONOS_validation' if 'VK_LAYER_KHRONOS_validation' in available else None; layer_list=(c.c_char_p*1)(selected) if selected else None
    print('validation_layer',selected.decode() if selected else 'not installed',flush=True)
    app=App(0,None,b'ember-vulkan-copy-diagnostic',0,None,0,1<<22); ic=Instance(1,None,0,c.pointer(app),1 if selected else 0,layer_list,0,None); instance=P(); check('instance',f('vkCreateInstance',c.c_int,c.POINTER(Instance),P,PP)(c.byref(ic),None,c.byref(instance)))
    dev=P(); pool=P(); fence=P(); buffers=[]; mems=[]; mapped=[]; pending=False
    try:
        enum=f('vkEnumeratePhysicalDevices',c.c_int,P,c.POINTER(U),PP); count=U(); check('physical count',enum(instance,c.byref(count),None));
        if count.value!=1: raise RuntimeError('expected exactly one physical GPU')
        physicals=(P*count.value)(); check('physical enumerate',enum(instance,c.byref(count),physicals)); physical=physicals[0]
        propbuf=c.create_string_buffer(4096); f('vkGetPhysicalDeviceProperties',None,P,P)(physical,propbuf); name=propbuf.raw[20:276].split(b'\0')[0].decode(errors='replace'); print('device',name,flush=True)
        if args.device_name and args.device_name not in name: raise RuntimeError('device name does not match --device-name')
        qp=f('vkGetPhysicalDeviceQueueFamilyProperties',None,P,c.POINTER(U),c.POINTER(QProps)); count=U(); qp(physical,c.byref(count),None); props=(QProps*count.value)(); qp(physical,c.byref(count),props); candidates=[i for i,x in enumerate(props) if x.count and x.flags&2];
        if not candidates: raise RuntimeError('no compute queue')
        family=candidates[0]; pri=c.c_float(1); qcreate=QCreate(2,None,0,family,1,c.pointer(pri)); dc=DevCreate(3,None,0,1,c.pointer(qcreate),0,None,0,None,None); check('device',f('vkCreateDevice',c.c_int,P,c.POINTER(DevCreate),P,PP)(physical,c.byref(dc),None,c.byref(dev))); queue=P(); f('vkGetDeviceQueue',None,P,U,U,PP)(dev,family,0,c.byref(queue))
        mp=MemProps(); f('vkGetPhysicalDeviceMemoryProperties',None,P,c.POINTER(MemProps))(physical,c.byref(mp)); print('queue family',family,flush=True)
        createbuf=f('vkCreateBuffer',c.c_int,P,c.POINTER(Buffer),P,PP); reqfn=f('vkGetBufferMemoryRequirements',None,P,P,c.POINTER(Requirements)); allocfn=f('vkAllocateMemory',c.c_int,P,c.POINTER(Allocation),P,PP); bind=f('vkBindBufferMemory',c.c_int,P,P,P,Z); size=4*1024*1024
        for label,usage,required,prefer in [('src',1,6,1),('device',3,1,0),('readback',2,6,0)]:
            b=P(); check(label+' buffer',createbuf(dev,c.byref(Buffer(12,None,0,size,usage,0,0,None)),None,c.byref(b))); buffers.append(b)
            r=Requirements(); reqfn(dev,b,c.byref(r)); valid=[i for i in range(mp.nt) if r.bits&(1<<i) and (mp.types[i].flags&required)==required]
            if not valid: raise RuntimeError('no compatible memory type '+label)
            if prefer: valid.sort(key=lambda i:not(mp.types[i].flags&prefer))
            elif label=='readback': valid.sort(key=lambda i:bool(mp.types[i].flags&1))
            index=valid[0]; m=P(); check(label+' allocation',allocfn(dev,c.byref(Allocation(5,None,r.size,index)),None,c.byref(m))); mems.append(m); check(label+' bind',bind(dev,b,m,0)); print(label,'memory type',index,'flags',hex(mp.types[index].flags),'heap',mp.types[index].heap,flush=True)
        mapfn=f('vkMapMemory',c.c_int,P,P,Z,Z,U,PP)
        for i in (0,2):
            address=P(); check('map',mapfn(dev,mems[i],0,size,0,c.byref(address))); mapped.append((mems[i],address))
        check('command pool',f('vkCreateCommandPool',c.c_int,P,c.POINTER(Pool),P,PP)(dev,c.byref(Pool(39,None,0,family)),None,c.byref(pool))); cmd=P(); check('command buffer',f('vkAllocateCommandBuffers',c.c_int,P,c.POINTER(CommandAlloc),PP)(dev,c.byref(CommandAlloc(40,None,pool,0,1)),c.byref(cmd))); check('begin',f('vkBeginCommandBuffer',c.c_int,P,c.POINTER(Begin))(cmd,c.byref(Begin(42,None,0,None))))
        barrier=f('vkCmdPipelineBarrier',None,P,U,U,U,U,P,U,c.POINTER(Barrier),U,P); copy=f('vkCmdCopyBuffer',None,P,P,P,U,c.POINTER(Copy)); region=Copy(0,0,size); ignored=0xffffffff
        def bb(buffer,src,dst,ss,ds):
            b=Barrier(44,None,src,dst,ignored,ignored,buffer,0,size); barrier(cmd,ss,ds,0,0,None,1,c.byref(b),0,None)
        bb(buffers[0],0x4000,0x800,0x4000,0x1000); copy(cmd,buffers[0],buffers[1],1,c.byref(region)); bb(buffers[1],0x1000,0x800,0x1000,0x1000); copy(cmd,buffers[1],buffers[2],1,c.byref(region)); bb(buffers[2],0x1000,0x2000,0x1000,0x4000)
        check('end',f('vkEndCommandBuffer',c.c_int,P)(cmd)); check('fence',f('vkCreateFence',c.c_int,P,c.POINTER(Fence),P,PP)(dev,c.byref(Fence(8,None,0)),None,c.byref(fence))); cmds=(P*1)(cmd.value); sub=Submit(4,None,0,None,None,1,cmds,0,None)
        submit=f('vkQueueSubmit',c.c_int,P,U,c.POINTER(Submit),P); wait=f('vkWaitForFences',c.c_int,P,U,PP,U,Z); reset=f('vkResetFences',c.c_int,P,U,PP); fp=(P*1)(fence.value)
        for cycle in range(2):
            # Alternating finite floats and varied words, unique across both cycles.
            pattern=(c.c_uint32*(size//4))(*(0x3f000000 if i%4==0 else ((i*2654435761+cycle*97)&0xffffffff) for i in range(size//4)))
            c.memmove(mapped[0][1],pattern,size); c.memset(mapped[1][1],0xa5,size); print('submit cycle',cycle+1,flush=True); check('submit',submit(queue,1,c.byref(sub),fence)); pending=True; check('wait fence',wait(dev,1,fp,1,0xffffffffffffffff)); pending=False
            actual=c.string_at(mapped[1][1],size); expected_bytes=c.string_at(c.addressof(pattern),size); mismatch=sum(a!=b for a,b in zip(expected_bytes,actual)); first=next((i for i,(a,b) in enumerate(zip(expected_bytes,actual)) if a!=b),None); print('cycle',cycle+1,'bytes',size,'mismatched_bytes',mismatch,'first',first,flush=True)
            if mismatch: raise RuntimeError('transfer bytes differ')
            if cycle==0: check('reset fence',reset(dev,1,fp))
        print('PASS Vulkan copy round-trip',flush=True)
    finally:
        if dev.value and pending: check('device idle',f('vkDeviceWaitIdle',c.c_int,P)(dev))
        if dev.value:
            for mem,addr in mapped: f('vkUnmapMemory',None,P,P)(dev,mem)
            if fence.value: f('vkDestroyFence',None,P,P,P)(dev,fence,None)
            if pool.value: f('vkDestroyCommandPool',None,P,P,P)(dev,pool,None)
            for b in buffers: f('vkDestroyBuffer',None,P,P,P)(dev,b,None)
            for m in mems: f('vkFreeMemory',None,P,P,P)(dev,m,None)
            f('vkDestroyDevice',None,P,P)(dev,None)
        f('vkDestroyInstance',None,P,P)(instance,None)
if __name__=='__main__':
    try: main()
    except Exception as e: print('FAIL:',e,file=sys.stderr,flush=True); sys.exit(1)
