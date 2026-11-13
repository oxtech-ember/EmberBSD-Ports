"""Shared LP64 Vulkan ctypes declarations for the diagnostics."""
import ctypes as c

U=c.c_uint32; Z=c.c_uint64; P=c.c_void_p; PP=c.POINTER(P)
class App(c.Structure): _fields_=[('s',U),('next',P),('name',c.c_char_p),('av',U),('engine',c.c_char_p),('ev',U),('api',U)]
class Instance(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('app',c.POINTER(App)),('nl',U),('layers',c.POINTER(c.c_char_p)),('ne',U),('ext',P)]
class Layer(c.Structure): _fields_=[('name',c.c_char*256),('spec',U),('impl',U),('description',c.c_char*256)]
class Extent(c.Structure): _fields_=[('x',U),('y',U),('z',U)]
class QProps(c.Structure): _fields_=[('flags',U),('count',U),('bits',U),('gran',Extent)]
class QCreate(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('family',U),('count',U),('priorities',c.POINTER(c.c_float))]
class DevCreate(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('nq',U),('queues',c.POINTER(QCreate)),('nl',U),('layers',P),('ne',U),('extensions',P),('features',P)]
class MemType(c.Structure): _fields_=[('flags',U),('heap',U)]
class MemHeap(c.Structure): _fields_=[('size',Z),('flags',U)]
class MemProps(c.Structure): _fields_=[('nt',U),('types',MemType*32),('nh',U),('heaps',MemHeap*16)]
class Buffer(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('size',Z),('usage',U),('sharing',U),('nq',U),('families',P)]
class Requirements(c.Structure): _fields_=[('size',Z),('alignment',Z),('bits',U)]
class Allocation(c.Structure): _fields_=[('s',U),('next',P),('size',Z),('type',U)]
class Pool(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('family',U)]
class CommandAlloc(c.Structure): _fields_=[('s',U),('next',P),('pool',P),('level',U),('count',U)]
class Begin(c.Structure): _fields_=[('s',U),('next',P),('flags',U),('inherit',P)]
class Copy(c.Structure): _fields_=[('src',Z),('dst',Z),('size',Z)]
class Barrier(c.Structure): _fields_=[('s',U),('next',P),('srcAccess',U),('dstAccess',U),('srcFamily',U),('dstFamily',U),('buffer',P),('offset',Z),('size',Z)]
class Fence(c.Structure): _fields_=[('s',U),('next',P),('flags',U)]
class Submit(c.Structure): _fields_=[('s',U),('next',P),('waitCount',U),('waits',P),('stages',P),('cmdCount',U),('cmds',PP),('signalCount',U),('signals',P)]

