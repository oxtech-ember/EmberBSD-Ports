'use strict';
const fs = require('node:fs');
const { WASI } = require('node:wasi');
(async () => {
  const wasi = new WASI({ version: 'preview1', args: [], env: {}, preopens: {} });
  const module = await WebAssembly.compile(fs.readFileSync(process.argv[2]));
  const instance = await WebAssembly.instantiate(module, wasi.getImportObject());
  wasi.initialize(instance);
  if (instance.exports.run() !== 42) throw new Error('unexpected result');
  console.log('WASI reactor malloc/free PASS');
})();
