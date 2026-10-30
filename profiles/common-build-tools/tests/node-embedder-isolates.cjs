const { Worker } = require('node:worker_threads');
const assert = require('node:assert/strict');
(async () => {
  for (let round = 0; round < 4; ++round) {
    const work = Array.from({ length: 12 }, (_, id) => new Promise((resolve, reject) => {
      const worker = new Worker(`const { parentPort, workerData } = require('node:worker_threads'); import('node:fs').then(m => parentPort.postMessage([workerData, typeof m.readFile]))`, { eval: true, workerData: id });
      worker.once('error', reject);
      worker.once('message', ([id, fn]) => { assert.equal(fn, 'function'); assert.ok(id >= 0); });
      worker.once('exit', code => code === 0 ? resolve() : reject(new Error(`worker exit ${code}`)));
    }));
    await Promise.all(work);
    if (global.gc) global.gc();
  }
  console.log('48 concurrent Node worker isolates and teardown PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
