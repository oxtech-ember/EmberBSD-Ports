// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
'use strict';
const fs = require('node:fs');
const readline = require('node:readline');
const {app, BrowserWindow} = require('electron');
const [fdA, fdB, expected] = process.argv.slice(-3);
const descriptors = [Number(fdA), Number(fdB)];
if (process.versions.electron !== expected || descriptors.some(fd => !Number.isInteger(fd) || fd < 3)) {
  throw new Error('invalid Electron version or descriptor arguments');
}
for (const fd of descriptors) {
  if (!fs.fstatSync(fd).isSocket()) throw new Error('inherited descriptor is not a socket: ' + fd);
}
let window;
app.whenReady().then(async () => {
  window = new BrowserWindow({show: false, webPreferences: {sandbox: true, contextIsolation: true, nodeIntegration: false}});
  await window.loadURL('data:text/html,<title>closefrom fixture</title><p>ready</p>');
  const rendererPID = window.webContents.getOSProcessId();
  if (!rendererPID) throw new Error('renderer PID unavailable');
  for (const fd of descriptors) fs.closeSync(fd);
  const send = record => process.stdout.write('EMBER_QA ' + JSON.stringify(record) + '\n');
  send({phase:'ready', mainPID:process.pid, rendererPID, fds:descriptors, electron:process.versions.electron});
  const input = readline.createInterface({input: process.stdin});
  let proved = false;
  let pending = Promise.resolve();
  input.on('line', line => {
    pending = pending.then(async () => {
      if (line === 'prove' && !proved) {
        const value = await window.webContents.executeJavaScript('true');
        if (window.webContents.getOSProcessId() !== rendererPID || value !== true) throw new Error('renderer changed or proof failed');
        proved = true;
        send({phase:'proof', mainPID:process.pid, rendererPID, value});
      } else if (line === 'quit' && proved) {
        input.close();
        app.quit();
      } else throw new Error('invalid supervisor command order');
    }).catch(error => {console.error(error); app.exit(1);});
  });
}).catch(error => {console.error(error); app.exit(1);});
