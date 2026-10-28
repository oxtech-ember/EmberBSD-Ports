#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Origin: nodejs/undici build/llhttp.js, adapted by EmberBSD (AI-assisted).
"""Generate Undici's upstream-format WASM wrappers from shared llhttp."""
import argparse
import base64
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
for option in ('wasm-dir', 'output-dir', 'loader', 'install-dir'):
    p.add_argument('--' + option, type=Path, required=True)
a = p.parse_args()
if not all(path.is_absolute() for path in (a.wasm_dir, a.output_dir, a.loader, a.install_dir)):
    p.error('all paths must be absolute')
for binary, wrapper in (('llhttp.wasm', 'llhttp-wasm.js'),
                        ('llhttp_simd.wasm', 'llhttp_simd-wasm.js')):
    wasm = (a.wasm_dir / binary).read_bytes()
    if not wasm.startswith(b'\0asm\x01\0\0\0'):
        raise ValueError('invalid WebAssembly module: ' + binary)
    encoded = base64.b64encode(wasm).decode('ascii')
    (a.output_dir / wrapper).write_text("""'use strict'

const { Buffer } = require('node:buffer')

const wasmBase64 = '%s'

let wasmBuffer

Object.defineProperty(module, 'exports', {
  get: () => {
    return wasmBuffer
      ? wasmBuffer
      : (wasmBuffer = Buffer.from(wasmBase64, 'base64'))
  }
})
""" % encoded, encoding='utf-8')
location = json.dumps(str(a.install_dir / 'loader.js'))
a.loader.write_text("""'use strict'
const flag = '__UNDICI_IS_NODE__'
const previous = Object.getOwnPropertyDescriptor(globalThis, flag)
try {
  Object.defineProperty(globalThis, flag, previous ? { value: true } : {
    value: true, writable: true, enumerable: true, configurable: true
  })
  module.exports = require('node:module').createRequire(%s)('./index-fetch.js')
} finally {
  if (previous) Object.defineProperty(globalThis, flag, previous)
  else delete globalThis[flag]
}
""" % location, encoding='utf-8')
