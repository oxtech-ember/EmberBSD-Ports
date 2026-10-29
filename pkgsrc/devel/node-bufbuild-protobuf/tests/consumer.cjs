// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
const assert = require('node:assert/strict');
const { create, fromBinary, toBinary } = require('@bufbuild/protobuf');
const { FileDescriptorProtoSchema } = require('@bufbuild/protobuf/wkt');
const message = create(FileDescriptorProtoSchema, {name: 'foo'});
const bytes = toBinary(FileDescriptorProtoSchema, message);
assert.deepEqual([...bytes], [10, 3, 102, 111, 111]);
assert.equal(fromBinary(FileDescriptorProtoSchema, bytes).name, 'foo');
assert.throws(() => fromBinary(FileDescriptorProtoSchema, new Uint8Array([10, 4, 1])));
