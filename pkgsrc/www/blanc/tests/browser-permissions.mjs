import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
const [base, initialURL, out, phase, expectedElectron] = process.argv.slice(2);
assert(['initial','restart'].includes(phase) && expectedElectron, 'phase and Electron version required');
const ep = new URL(base), origin = new URL(initialURL).origin;
assert(ep.protocol === 'http:' && ep.hostname === '127.0.0.1');
assert(new URL(initialURL).hostname === '127.0.0.1');
assert.equal(process.versions.electron, expectedElectron);
const sleep = ms => new Promise(r=>setTimeout(r,ms));
const clients = new Map();
const report = {phase, checks:[]};
let step = 'startup';
async function list() {
  const r = await fetch(new URL('/json/list',ep),{signal:AbortSignal.timeout(5000)});
  assert(r.ok); return (await r.json()).filter(t=>t.type==='page');
}
async function connect(t) {
  if(clients.has(t.id)) return clients.get(t.id);
  const u=new URL(t.webSocketDebuggerUrl);
  assert(u.protocol==='ws:' && u.hostname==='127.0.0.1' && u.port===ep.port);
  const ws=new WebSocket(u); const pending=new Map(); let id=0;
  ws.addEventListener('message',e=>{const m=JSON.parse(e.data),p=pending.get(m.id);if(!p)return;clearTimeout(p.timer);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);});
  ws.addEventListener('close',()=>{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('target closed'));}pending.clear();});
  await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('socket timeout')),10000);ws.addEventListener('open',()=>{clearTimeout(timer);resolve();},{once:true});ws.addEventListener('error',()=>{clearTimeout(timer);reject(Error('socket error'));},{once:true});});
  function call(method,params={}){return new Promise((resolve,reject)=>{const key=++id;const timer=setTimeout(()=>{pending.delete(key);reject(Error(method+' timeout'));},10000);pending.set(key,{resolve,reject,timer});ws.send(JSON.stringify({id:key,method,params}));});}
  async function ev(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});assert(!r.exceptionDetails,JSON.stringify(r.exceptionDetails));return r.result.value;}
  const c={call,ev,ws,id:t.id};clients.set(t.id,c);return c;
}
async function until(fn, label, ms=15000){let last;for(const end=Date.now()+ms;Date.now()<end;){last=await fn();if(last)return last;await sleep(150);}throw Error('timeout: '+label);}
async function targetURL(url){return until(async()=>{const ts=(await list()).filter(t=>t.url===url);assert(ts.length<=1,'ambiguous target '+url);if(!ts[0])return null;const c=await connect(ts[0]);return await c.ev('location.href === '+JSON.stringify(url)+" && document.readyState === 'complete'") ? c : null;},url,30000);}
async function bySelector(selector){return until(async()=>{const matches=[];for(const t of await list()){if(!t.url.startsWith('blanc-chrome:'))continue;const c=await connect(t);if(await c.ev('Boolean(document.querySelector('+JSON.stringify(selector)+'))'))matches.push(c);}assert(matches.length<=1,'ambiguous UI');return matches[0];},selector);}
async function click(c,selector){const p=await until(()=>c.ev(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e||e.disabled)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e),x=r.x+r.width/2,y=r.y+r.height/2,h=document.elementFromPoint(x,y);return r.width&&r.height&&s.visibility==='visible'&&s.display!=='none'&&(h===e||e.contains(h))?{x,y}:null;})()`),selector);for(const type of ['mousePressed','mouseReleased'])await c.call('Input.dispatchMouseEvent',{type,...p,button:'left',clickCount:1});}
async function key(c,key,code,modifiers=0){for(const type of ['keyDown','keyUp'])await c.call('Input.dispatchKeyEvent',{type,key,windowsVirtualKeyCode:code,modifiers});}
async function openPanel(){
  const state=await until(()=>overlay.ev("(()=>{const mode=document.body.dataset.mode;return mode==='panel'?'open':(!mode&&document.querySelector('#panelAnchor').hidden?'closed':null);})()"),'stable overlay');
  if(state==='closed')await click(shell,'#pillDomain');
  await until(()=>overlay.ev("document.body.dataset.mode==='panel' && !document.querySelector('#panelAnchor').hidden && document.querySelector('#addressInput').getBoundingClientRect().width>0"),'panel shown');
}
async function navigate(url){await openPanel();await click(overlay,'#addressInput');await key(overlay,'a',65,2);await overlay.call('Input.insertText',{text:url});await key(overlay,'Enter',13);return targetURL(url);}
async function quit(c){const done=new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(Error('quit timeout')),20000);c.ws.addEventListener('close',()=>{clearTimeout(t);resolve();},{once:true});});c.ws.send(JSON.stringify({id:900000,method:'Browser.close'}));await done;}
let shell,overlay;
try {
  shell=await bySelector('#islandPill');overlay=await bySelector('#addressInput');
  const page=await targetURL(initialURL);
  async function requestAndBlock(c){

    await click(c,'#permission');const prompt=await bySelector('#permBlockBtn');
    await until(()=>prompt.ev("!document.querySelector('#permissionBar').hidden"),'permission prompt');
    assert.deepEqual(await prompt.ev("[...document.querySelectorAll('#permissionBar .permission-host')].map(e=>e.title)"),[new URL(initialURL).host],'exact single permission origin displayed');
    await click(prompt,'#permBlockBtn');await until(()=>c.ev("window.permissionResult==='denied'"),'permission denial');

  }
  if(phase==='initial'){
    step='normal permission deny';await requestAndBlock(page);report.checks.push('normal geolocation prompt/deny');
    step='remember deny';const normalCount=await page.ev('window.permissionRequests');await click(page,'#permission');await until(()=>page.ev(`window.permissionRequests===${normalCount+1} && window.permissionResult==='denied'`),'remembered denial');
    step='private permission';await openPanel();await click(overlay,'#footerNewPrivate');const priv=await navigate(origin+'/private-policy.html');
    await requestAndBlock(priv);report.checks.push('private permission does not inherit normal decision');
    await click(shell,'#pillPrivateChip');await until(async()=>!(await list()).some(t=>t.id===priv.id),'private target gone');
    await quit(page);
  }else{
    step='normal persisted permission';const normalCount=await page.ev('window.permissionRequests');await click(page,'#permission');await until(()=>page.ev(`window.permissionRequests===${normalCount+1} && window.permissionResult==='denied'`),'persisted denial');report.checks.push('normal denial persisted after normal quit');
    step='private permission cleared';await openPanel();await click(overlay,'#footerNewPrivate');const priv=await navigate(origin+'/private-policy.html');
    await requestAndBlock(priv);report.checks.push('private decision cleared after normal quit');await quit(priv);
  }
  report.passed=true;
}catch(e){report.error=String(e);report.step=step;try { const t=(await list()).find(t=>t.url===initialURL);if(t)report.permissionState=await (await connect(t)).ev("({result:window.permissionResult,secure:window.isSecureContext,media:typeof navigator.mediaDevices})");report.targets=(await list()).map(x=>x.url); }catch{}process.exitCode=1;}
finally{for(const c of clients.values())c.ws.close();await writeFile(out+'/'+phase+'-flows.json',JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report));}
