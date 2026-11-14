// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted). Diagnostic only; no application override.
'use strict';
const {app, BrowserWindow, protocol, session} = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const [versionArg, portArg] = process.argv.slice(-2);
if (!/^--expected-electron=\d+\.\d+\.\d+$/.test(versionArg ?? '') ||
    !/^--port=dtyU[0-9]+$/.test(portArg ?? '')) throw Error('select exact Electron version and observed dtyU port');
const expectedVersion = versionArg.split('=')[1];
const expectedPort = portArg.split('=')[1];
if (process.versions.electron !== expectedVersion) throw Error('unexpected Electron version');
const ORIGIN = 'mspdiag://probe';
const URL = ORIGIN + '/index.html';
protocol.registerSchemesAsPrivileged([{scheme:'mspdiag', privileges:{standard:true, secure:true, supportFetchAPI:true}}]);
let win, chosen = false;
app.whenReady().then(() => {
  const html = fs.readFileSync(path.join(__dirname, 'serial-msp-runtime.html'));
  protocol.handle('mspdiag', req => {
    if (req.url !== URL) return new Response('Not found', {status:404});
    return new Response(html, {headers:{'content-type':'text/html; charset=utf-8', 'content-security-policy':"default-src 'none'; script-src 'unsafe-inline'"}});
  });
  const ses = session.defaultSession;
  const trusted = contents => win && contents === win.webContents && !contents.isDestroyed() && contents.getURL() === URL;
  ses.setPermissionCheckHandler((contents, permission, origin) => { console.log(JSON.stringify({phase:'permission-check',permission,origin,trusted:Boolean(trusted(contents))})); return Boolean(trusted(contents) && permission === 'serial' && origin === ORIGIN + "/"); });
  ses.setPermissionRequestHandler((contents, permission, callback, details) => callback(Boolean(trusted(contents) && permission === 'serial' && details.requestingUrl === URL)));
  ses.on('select-serial-port', (event, ports, contents, callback) => {
    event.preventDefault();
    if (!trusted(contents) || chosen) { console.log(JSON.stringify({phase:'selection-rejected',trusted:Boolean(trusted(contents)),chosen})); callback(''); return; }
    const matching = ports.filter(p => p.vendorId === '1155' && p.productId === '22336' && p.portName === expectedPort);
    console.log(JSON.stringify({phase:'serial-selection', portCount:ports.length, matchingCount:matching.length,
      expectedPort, vendorId:'0483', productId:'5740'}));
    if (matching.length !== 1 || !matching[0].portId) { callback(''); return; }
    chosen = true;
    callback(matching[0].portId);
  });
  win = new BrowserWindow({width:700,height:400, webPreferences:{sandbox:true,contextIsolation:true,nodeIntegration:false}});
  win.loadURL(URL);
}).catch(error => { console.error('startup:', error.message); app.exit(1); });
app.on('window-all-closed', () => app.quit());
