'use strict';
const assert = require('node:assert/strict');
const http = require('node:http');
const path = require('node:path');
const source = process.argv[2];
const undici = require(path.join(source, process.argv[3] || 'index.js'));
const server = http.createServer((_req, res) => {
  res.writeHead(200, {'content-type': 'text/plain'});
  res.end('common undici');
});
server.listen(0, '127.0.0.1', async () => {
  try {
    const url = `http://127.0.0.1:${server.address().port}/`;
    const response = await undici.fetch(url);
    assert.equal(response.status, 200);
    assert.equal(await response.text(), 'common undici');
    if (!process.argv[3]) {
      const data = await undici.request(url);
      assert.equal(data.statusCode, 200);
      assert.equal(await data.body.text(), 'common undici');
    }
    console.log('Undici HTTP consumer PASS');
  } catch (error) {
    console.error(error);
    process.exitCode = 1;
  } finally {
    server.close();
    await undici.getGlobalDispatcher().close();
  }
});
