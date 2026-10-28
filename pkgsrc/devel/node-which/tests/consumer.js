// SPDX-License-Identifier: ISC
// Origin: EmberBSD (AI-assisted).
'use strict';
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const which = require(process.argv[2]);
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'which-test-'));
(async () => {
  try {
    const exe = path.join(dir, 'selected');
    fs.writeFileSync(exe, '#!/bin/sh\nexit 0\n', {mode: 0o755});
    const options = {path: dir};
    assert.equal(which.sync('selected', options), exe);
    assert.equal(await which('selected', options), exe);
    assert.equal(which.sync('absent', {...options, nothrow: true}), null);
    const cli = spawnSync(process.execPath, [process.argv[3], 'selected'],
                          {env: {...process.env, PATH: dir}, encoding: 'utf8'});
    assert.equal(cli.status, 0, cli.stderr);
    assert.equal(cli.stdout.trim(), exe);
    console.log('which shared isexe, API and CLI PASS');
  } finally {
    fs.rmSync(dir, {recursive: true, force: true});
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
