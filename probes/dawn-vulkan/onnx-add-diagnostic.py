#!/usr/bin/env python3
"""Generate a minimal ONNX Add(images, images) model using source model opsets."""
import argparse
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('onnx_intermediate', Path(__file__).with_name('onnx-intermediate.py'))
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)


def tensor(name):
    shape = b''.join(wire.wrapped(1, b'\x08' + wire.enc(d)) for d in (1, 3, 480, 640))
    tensor_type = b'\x08\x01' + wire.wrapped(2, shape)
    return wire.wrapped(1, name.encode()) + wire.wrapped(2, wire.wrapped(1, tensor_type))


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('model', type=Path); p.add_argument('output', type=Path); a=p.parse_args()
    if a.model.resolve()==a.output.resolve() or a.output.exists(): raise ValueError('refusing to overwrite input or existing output')
    original=list(wire.fields(a.model.read_bytes()))
    node=wire.wrapped(1,b'images')+wire.wrapped(1,b'images')+wire.wrapped(2,b'sum')+wire.wrapped(3,b'diagnostic_add')+wire.wrapped(4,b'Add')
    graph=wire.wrapped(1,node)+wire.wrapped(2,b'diagnostic_add')+wire.wrapped(11,tensor('images'))+wire.wrapped(12,tensor('sum'))
    if sum(n==7 and w==2 for n,w,v,r in original)!=1: raise ValueError('expected one graph')
    # Preserve IR version, metadata, and original opset imports unchanged.
    result=b''.join(wire.wrapped(7,graph) if n==7 and w==2 else raw for n,w,v,raw in original)
    with a.output.open('xb') as f: f.write(result)
    print('input images float32[1,3,480,640]; Add(images,images) -> sum; original opsets retained')

if __name__=='__main__': main()
