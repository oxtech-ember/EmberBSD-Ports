// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
import assert from 'node:assert/strict';
import { create, fromBinary, toBinary } from '@bufbuild/protobuf';
import { FileDescriptorProtoSchema } from '@bufbuild/protobuf/wkt';
const message = create(FileDescriptorProtoSchema, {name: 'foo'});
const bytes = toBinary(FileDescriptorProtoSchema, message);
assert.deepEqual([...bytes], [10, 3, 102, 111, 111]);
assert.equal(fromBinary(FileDescriptorProtoSchema, bytes).name, 'foo');
assert.throws(() => fromBinary(FileDescriptorProtoSchema, new Uint8Array([10, 4, 1])));
