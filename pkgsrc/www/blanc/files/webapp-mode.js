'use strict';
const path = require('path');
const layout = require('./webapp-layout.json');
const ID = /^[A-Za-z0-9_-]{1,64}$/;
function parseWebAppArgs(argv) {
  if (!Array.isArray(argv)) throw new TypeError('argv must be an array');
  const selected = argv.filter(x => typeof x === 'string' && x.startsWith('--webapp-'));
  if (!selected.length) return null;
  for (const arg of argv) {
    if (typeof arg === 'string' && arg.startsWith('--') && !arg.startsWith('--webapp-') && arg !== '--' && arg !== '--ozone-platform=x11' && arg !== '--in-process-gpu') throw new Error('unsupported webapp launch switch');
  }
  const values = {};
  for (const arg of selected) {
    const m = /^--webapp-(id|url|name)=(.*)$/s.exec(arg);
    if (arg === '--webapp-private') { if ('private' in values) throw new Error('duplicate private'); values.private = true; continue; }
    if (!m || Object.hasOwn(values,m[1])) throw new Error('invalid or duplicate webapp argument');
    values[m[1]]=m[2];
  }
  if (!ID.test(values.id || '')) throw new Error('invalid webapp id');
  if (typeof values.name !== 'string' || !values.name.trim() || [...values.name].length > 200 || /[\x00-\x1f\x7f]/.test(values.name)) throw new Error('invalid webapp name');
  if (typeof values.url !== 'string' || /[\x00-\x20\x7f]/.test(values.url)) throw new Error('invalid webapp URL');
  let url; try { url = new URL(values.url); } catch { throw new Error('invalid webapp URL'); }
  if (!['http:','https:'].includes(url.protocol) || !url.hostname || url.username || url.password) throw new Error('invalid webapp URL');
  return {id:values.id,url:url.href,name:values.name,private:values.private === true};
}
function userDataPath(appData,id,isPrivate = false) {
  if (!path.isAbsolute(appData) || !ID.test(id)) throw new Error('invalid webapp path');
  return path.join(appData,layout.application,isPrivate ? layout.private : layout.normal,id);
}
function initializeWebApp(app, fs, env, mode) {
  env.CHROME_DESKTOP = `WebApp-${mode.id}.desktop`;
  const profile = userDataPath(app.getPath('appData'), mode.id, mode.private);
  fs.mkdirSync(profile, { recursive: true, mode: 0o700 });
  app.setPath('userData', profile);
  app.setPath('sessionData', profile);
  return profile;
}
function sameWebApp(a,b) { return !!a && !!b && a.id===b.id && a.private===b.private; }
function effectivePrivate(mode,requested) { return mode?.private === true || requested === true; }
function webAppMenuModel(rows, activeId) {
  return rows.filter(row => row && row.id != null).map(row => ({
    id: row.id, label: String(row.title || row.url || 'Untitled').replace(/&/g, '&&').slice(0, 120),
    checked: row.id === activeId,
  }));
}
function fullPageLayout(layout,width,height) { return {...layout,pageBounds:{x:0,y:0,width,height}}; }
module.exports={parseWebAppArgs,userDataPath,initializeWebApp,sameWebApp,effectivePrivate,webAppMenuModel,fullPageLayout};
