#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the generated common Protobuf Python runtime with selected protoc."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def source_snapshot(root):
    snapshot = {}
    for path in sorted(root.rglob('*')):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            snapshot[relative] = ('link', os.readlink(path))
        elif path.is_file():
            snapshot[relative] = ('file', hashlib.sha256(path.read_bytes()).digest())
    return snapshot


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--protobuf-source', required=True, type=Path)
parser.add_argument('--protoc', required=True, type=Path)
args = parser.parse_args()
for name, path in (('--protobuf-source', args.protobuf_source), ('--protoc', args.protoc)):
    require(path.is_absolute(), name + ' must be absolute')
protobuf = args.protobuf_source.resolve(strict=True)
protoc = args.protoc.resolve(strict=True)
require(protobuf.is_dir(), '--protobuf-source must be a directory')
require(protoc.is_file() and os.access(protoc, os.X_OK), '--protoc must be executable')

owner = Path(__file__).resolve().parents[1]
provider = owner / 'electron44/files/protobuf-source-view.py'
spec = importlib.util.spec_from_file_location('protobuf_source_view', provider)
view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view)

descriptor_proto = protobuf / 'src/google/protobuf/descriptor.proto'
python_source = protobuf / 'python'
source_before = (hashlib.sha256(descriptor_proto.read_bytes()).digest(),
                 source_snapshot(python_source))
source_descriptor = protobuf / 'python/google/protobuf/descriptor_pb2.py'
require(not source_descriptor.exists(), 'common source unexpectedly contains descriptor_pb2.py')

with tempfile.TemporaryDirectory(prefix='electron-protobuf-python-view-') as temporary:
    runtime = Path(temporary) / 'python'
    view.python_view(protobuf, runtime, protoc)
    generated = runtime / 'google/protobuf/descriptor_pb2.py'
    require(generated.is_file(), 'python_view did not generate descriptor_pb2.py with selected protoc')

    child = r'''import sys
sys.path.insert(0, sys.argv[1])
from google.protobuf import descriptor_pb2 as descriptor

assert descriptor.DESCRIPTOR.name == "google/protobuf/descriptor.proto"
assert descriptor.DESCRIPTOR.package == "google.protobuf"
schema = descriptor.DESCRIPTOR.message_types_by_name["DescriptorProto"]
assert schema.fields_by_name["name"].number == 1

message = descriptor.DescriptorProto(name="RegressionMessage")
field = message.field.add()
field.name = "value"
field.number = 7
field.label = descriptor.FieldDescriptorProto.LABEL_OPTIONAL
field.type = descriptor.FieldDescriptorProto.TYPE_STRING
round_trip = descriptor.DescriptorProto.FromString(message.SerializeToString())
assert round_trip == message
assert round_trip.field[0].name == "value" and round_trip.field[0].number == 7
print("PASS: generated descriptor metadata and pure-Python message round trip")
'''
    environment = os.environ.copy()
    environment['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
    subprocess.run([sys.executable, '-B', '-I', '-S', '-c', child, str(runtime)],
                   check=True, env=environment)

    view.python_view(protobuf, runtime, protoc, verify=True)
    generated.write_bytes(generated.read_bytes() + b'\n# tampered\n')
    try:
        view.python_view(protobuf, runtime, protoc, verify=True)
    except ValueError as error:
        require('generated descriptor_pb2 changed' in str(error),
                'tamper was rejected for an unrelated reason: ' + str(error))
    else:
        raise AssertionError('tampered descriptor_pb2.py was accepted')

    generated.unlink()
    try:
        view.python_view(protobuf, runtime, protoc, verify=True)
    except ValueError as error:
        require('generated descriptor_pb2 changed' in str(error),
                'deleted descriptor was rejected for an unrelated reason: ' + str(error))
    else:
        raise AssertionError('deleted descriptor_pb2.py was accepted')

require((hashlib.sha256(descriptor_proto.read_bytes()).digest(),
         source_snapshot(python_source)) == source_before,
        'common Protobuf source inputs were modified')
require(not source_descriptor.exists(), 'generated descriptor_pb2.py escaped into common source')
print('PASS: selected-protoc Python runtime generation, verification, and source isolation')
