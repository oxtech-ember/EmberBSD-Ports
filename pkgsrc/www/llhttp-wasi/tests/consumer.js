'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const module_ = new WebAssembly.Module(fs.readFileSync(process.argv[2]));
const callbacks = [
  'wasm_on_headers_complete', 'wasm_on_message_begin', 'wasm_on_url',
  'wasm_on_status', 'wasm_on_header_field', 'wasm_on_header_value',
  'wasm_on_body', 'wasm_on_message_complete'
];
const imports = WebAssembly.Module.imports(module_);
assert.deepEqual(imports.map(x => [x.module, x.name, x.kind]).sort(),
  callbacks.map(name => ['env', name, 'function']).sort());
const exports_ = new Map(WebAssembly.Module.exports(module_).map(({name, kind}) => [name, kind]));
for (const [name, kind] of Object.entries({memory: 'memory', _initialize: 'function',
  llhttp_alloc: 'function', llhttp_execute: 'function', llhttp_free: 'function',
  malloc: 'function', free: 'function', __indirect_function_table: 'table'})) {
  assert.equal(exports_.get(name), kind, name);
}
let complete = 0, status = 0, body = '';
let instance;
const env = Object.fromEntries(callbacks.map(name => [name, () => 0]));
env.wasm_on_headers_complete = (_parser, code) => { status = code; return 0; };
env.wasm_on_message_complete = () => { complete++; return 0; };
env.wasm_on_body = (_parser, ptr, len) => { body += Buffer.from(instance.exports.memory.buffer, ptr, len).toString(); return 0; };
instance = new WebAssembly.Instance(module_, {env});
const w = instance.exports;
w._initialize();
const text = Buffer.from('HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello');
const parser = w.llhttp_alloc(2), buf = w.malloc(text.length);
new Uint8Array(w.memory.buffer, buf, text.length).set(text);
assert.equal(w.llhttp_execute(parser, buf, text.length), 0);
assert.equal(status, 200); assert.equal(body, 'hello'); assert.equal(complete, 1);
w.llhttp_free(parser); w.free(buf);
console.log('common llhttp WASI reactor API PASS');
