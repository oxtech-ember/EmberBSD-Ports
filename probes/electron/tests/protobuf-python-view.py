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
provider = owner / '../../pkgsrc/devel/electron44/files/protobuf-source-view.py'
spec = importlib.util.spec_from_file_location('protobuf_source_view', provider)
view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view)

descriptor_proto = protobuf / 'src/google/protobuf/descriptor.proto'
plugin_proto = protobuf / 'src/google/protobuf/compiler/plugin.proto'
python_source = protobuf / 'python'
source_before = (hashlib.sha256(descriptor_proto.read_bytes()).digest(),
                 hashlib.sha256(plugin_proto.read_bytes()).digest(),
                 source_snapshot(python_source))
source_descriptors = (protobuf / 'python/google/protobuf/descriptor_pb2.py',
                      protobuf / 'python/google/protobuf/compiler/plugin_pb2.py')
require(not any(path.exists() for path in source_descriptors),
        'common source unexpectedly contains a generated Protobuf Python module')

with tempfile.TemporaryDirectory(prefix='electron-protobuf-python-view-') as temporary:
    runtime = Path(temporary) / 'python'
    view.python_view(protobuf, runtime, protoc)
    generated = {
        runtime / 'google/protobuf/descriptor_pb2.py': 'descriptor_pb2.py',
        runtime / 'google/protobuf/compiler/plugin_pb2.py': 'compiler/plugin_pb2.py',
    }
    for path, name in generated.items():
        require(path.is_file() and not path.is_symlink(),
                'python_view did not generate ' + name + ' with selected protoc')

    child = r'''import sys
sys.path.insert(0, sys.argv[1])
from google.protobuf import descriptor_pb2 as descriptor
from google.protobuf.compiler import plugin_pb2 as plugin

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

assert plugin.DESCRIPTOR.name == "google/protobuf/compiler/plugin.proto"
assert plugin.DESCRIPTOR.package == "google.protobuf.compiler"
request_schema = plugin.DESCRIPTOR.message_types_by_name["CodeGeneratorRequest"]
assert request_schema.fields_by_name["proto_file"].number == 15
response_file = plugin.DESCRIPTOR.message_types_by_name["CodeGeneratorResponse"].nested_types_by_name["File"]
assert response_file.fields_by_name["content"].number == 15

request = plugin.CodeGeneratorRequest(file_to_generate=["sample.proto"])
request.proto_file.add(name="sample.proto", package="regression")
request_round_trip = plugin.CodeGeneratorRequest.FromString(request.SerializeToString())
assert request_round_trip.file_to_generate == ["sample.proto"]
assert request_round_trip.proto_file[0].name == "sample.proto"

response = plugin.CodeGeneratorResponse()
response.file.add(name="sample.pb.h", content="generated payload")
response_round_trip = plugin.CodeGeneratorResponse.FromString(response.SerializeToString())
assert response_round_trip.file[0].name == "sample.pb.h"
assert response_round_trip.file[0].content == "generated payload"
print("PASS: generated descriptor/plugin metadata and pure-Python message round trips")
'''
    environment = os.environ.copy()
    environment['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
    subprocess.run([sys.executable, '-B', '-I', '-S', '-c', child, str(runtime)],
                   check=True, env=environment)

    view.python_view(protobuf, runtime, protoc, verify=True)
    generated_bytes = {path: path.read_bytes() for path in generated}
    for path, name in generated.items():
        path.write_bytes(generated_bytes[path] + b'\n# tampered\n')
        try:
            view.python_view(protobuf, runtime, protoc, verify=True)
        except ValueError as error:
            require(str(path) in str(error), 'tamper was rejected for an unrelated reason: ' + str(error))
        else:
            raise AssertionError('tampered ' + name + ' was accepted')
        path.write_bytes(generated_bytes[path])
        view.python_view(protobuf, runtime, protoc, verify=True)

        path.unlink()
        try:
            view.python_view(protobuf, runtime, protoc, verify=True)
        except ValueError as error:
            require(str(path) in str(error), 'deletion was rejected for an unrelated reason: ' + str(error))
        else:
            raise AssertionError('deleted ' + name + ' was accepted')
        path.write_bytes(generated_bytes[path])
        view.python_view(protobuf, runtime, protoc, verify=True)

require((hashlib.sha256(descriptor_proto.read_bytes()).digest(),
         hashlib.sha256(plugin_proto.read_bytes()).digest(),
         source_snapshot(python_source)) == source_before,
        'common Protobuf source inputs were modified')
require(not any(path.exists() for path in source_descriptors),
        'generated Protobuf Python modules escaped into common source')
print('PASS: selected-protoc descriptor/plugin generation, verification, and source isolation')
