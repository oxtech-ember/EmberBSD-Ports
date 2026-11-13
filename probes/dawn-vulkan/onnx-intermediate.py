#!/usr/bin/env python3
"""Inspect ONNX node outputs or select one float tensor as diagnostic graph output.

Uses only protobuf wire format; retains all fields and never overwrites input.
Unknown shapes are inferred by ONNX Runtime, not asserted by this utility.
"""
import argparse
from pathlib import Path


def varint(data, pos):
    value = 0
    for shift in range(0, 70, 7):
        if pos >= len(data): raise ValueError('truncated varint')
        byte = data[pos]; pos += 1; value |= (byte & 127) << shift
        if byte < 128: return value, pos
    raise ValueError('oversized varint')


def enc(value):
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128); value >>= 7
    result.append(value)
    return bytes(result)


def fields(data):
    pos = 0
    while pos < len(data):
        start = pos; tag, pos = varint(data, pos); number, wire = tag >> 3, tag & 7
        if number == 0: raise ValueError('invalid field number')
        if wire == 0: _, pos = varint(data, pos); value = None
        elif wire == 1: value = data[pos:pos+8]; pos += 8
        elif wire == 2:
            size, pos = varint(data, pos); value = data[pos:pos+size]; pos += size
        elif wire == 5: value = data[pos:pos+4]; pos += 4
        else: raise ValueError(f'unsupported wire type {wire}')
        if pos > len(data): raise ValueError('truncated field')
        yield number, wire, value, data[start:pos]


def wrapped(number, value): return enc(number << 3 | 2) + enc(len(value)) + value


def node_info(data):
    vals = {1: [], 2: [], 3: [], 4: []}
    for number, wire, value, _ in fields(data):
        if number in vals and wire == 2: vals[number].append(value.decode('utf-8'))
    return vals


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('model', type=Path)
    p.add_argument('--list', action='store_true', help='list graph nodes and tensor names')
    p.add_argument('--node', type=int, help='zero-based graph node index')
    p.add_argument('--no-prune', action='store_true', help='retain unrelated graph nodes')
    p.add_argument('--output', type=Path, help='diagnostic model path')
    a = p.parse_args(); source = a.model.read_bytes(); models = list(fields(source))
    graphs = [v for n,w,v,_ in models if n == 7 and w == 2]
    if len(graphs) != 1: raise ValueError('expected exactly one graph')
    graph = list(fields(graphs[0])); nodes = [node_info(v) for n,w,v,_ in graph if n == 1 and w == 2]
    if a.list:
        for i, x in enumerate(nodes): print(i, x[4][0] if x[4] else '?', x[3][0] if x[3] else '', 'in=',x[1], 'out=',x[2])
    if a.node is None:
        if not a.list: p.error('specify --list or --node and --output')
        return
    if a.output is None: p.error('--node requires --output')
    if a.model.resolve() == a.output.resolve() or a.output.exists(): raise ValueError('refusing to overwrite input or existing output')
    if a.node < 0 or a.node >= len(nodes): raise ValueError('node index out of range')
    node = nodes[a.node]
    if len(node[2]) != 1 or not node[2][0]: raise ValueError('node must have one named output')
    name = node[2][0].encode(); value_info = wrapped(1,name) + wrapped(2,wrapped(1,b'\x08\x01'))
    required = {node[2][0]}; retained = set()
    if not a.no_prune:
        # Graph nodes are topologically sorted. Reverse traversal retains exactly
        # the transitive node dependencies of the selected output.
        for i in range(len(nodes)-1, -1, -1):
            if required.intersection(nodes[i][2]):
                retained.add(i); required.update(x for x in nodes[i][1] if x)
    node_index = 0; parts = []
    for n,w,v,raw in graph:
        if n == 12: continue
        if n == 5 and w == 2 and not a.no_prune:
            tensor_names = [x.decode('utf-8') for f, t, x, _ in fields(v) if f == 8 and t == 2]
            if len(tensor_names) != 1: raise ValueError('initializer without exactly one name')
            if tensor_names[0] not in required: continue
        if n == 1 and w == 2:
            keep = a.no_prune or node_index in retained
            node_index += 1
            if not keep: continue
        parts.append(raw)
    rewritten = b''.join(parts) + wrapped(12,value_info)
    print('retained_nodes=%d/%d' % (len(nodes) if a.no_prune else len(retained),len(nodes)))
    result = b''.join(wrapped(7,rewritten) if n == 7 and w == 2 else raw for n,w,v,raw in models)
    with a.output.open('xb') as f: f.write(result)
    print('selected index=%d op=%s name=%s output=%s' % (a.node,node[4],node[3],node[2]))

if __name__ == '__main__': main()
