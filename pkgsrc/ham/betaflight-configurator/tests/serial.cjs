// SPDX-License-Identifier: BSD-2-Clause
// EmberBSD Ports regression, developed with AI assistance.
const assert = require('node:assert/strict');
const {EventEmitter} = require('node:events');
const {installSerialSelection} = require(process.argv[2] || require('node:path').join(__dirname, '../files/serial.cjs'));
const flush=()=>new Promise(setImmediate);
function setup() {
 const s=new EventEmitter(); s.setPermissionRequestHandler=f=>s.request=f; s.setPermissionCheckHandler=f=>s.check=f; s.setDevicePermissionHandler=()=>{throw Error('blanket grant')};
 const c=new EventEmitter(); c.url='bfapp://./index.html'; c.dead=false; c.isDestroyed=()=>c.dead; c.getURL=()=>c.url;
 const w={isDestroyed:()=>false}; let resolve,reject, mode='promise', opts;
 const dialog={showMessageBox:(_p,o)=>{opts=o;if(mode==='throw')throw Error(); return new Promise((a,b)=>{resolve=a;reject=b})}};
 installSerialSelection(s,{BrowserWindow:{fromWebContents:x=>x===c?w:null},dialog});
 const request=(ports=[{portId:'a',portName:'/dev/a'},{portId:'b',portName:'/dev/b'}])=>{let prevented=false,results=[];s.emit('select-serial-port',{preventDefault(){prevented=true}},ports,c,x=>results.push(x));return {results,get prevented(){return prevented}}};
 return {s,c,request,resolve:x=>resolve({response:x}),reject:()=>reject(Error()),setMode:x=>mode=x,getOpts:()=>opts};
}
(async()=>{
 for(const [response,expected,ports] of [[2,'b',undefined],[0,'',undefined],[0,'',[]]]) {let x=setup(), q=x.request(ports);assert(q.prevented);x.resolve(response);await flush();assert.deepEqual(q.results,[expected]);assert.equal(x.s.listenerCount('serial-port-removed'),0)}
 {let x=setup(), result; x.s.request(x.c,'serial',v=>result=v,{requestingUrl:'bfapp://./index.html'});assert.equal(result,true);x.s.request(x.c,'serial',v=>result=v,{requestingUrl:'https://evil.test/'});assert.equal(result,false);assert.equal(x.s.check(x.c,'serial','https://evil.test'),false);assert.equal(x.s.check(x.c,'serial','bfapp://.'),true)}
 for (const event of ['destroyed','navigation']) {let x=setup(),q=x.request(); if(event==='destroyed'){x.c.dead=true;x.c.emit('destroyed')}else x.c.emit('did-start-navigation',{url:'https://evil.test',isSameDocument:false,isMainFrame:true});x.resolve(1);await flush();assert.deepEqual(q.results,['']);assert.equal(x.s.listenerCount('serial-port-removed'),0)}
 {let x=setup(),q=x.request();x.c.emit('did-start-navigation',{url:'bfapp://./frame.html',isSameDocument:false,isMainFrame:false});assert.deepEqual(q.results,[]);x.resolve(1);await flush();assert.deepEqual(q.results,['a'])}
 for (const mode of ['throw','reject']) {let x=setup();if(mode==='throw')x.setMode(mode);let q=x.request();if(mode==='reject')x.reject();await flush();assert.deepEqual(q.results,[''])}
 {let x=setup(),q=x.request();x.s.emit('serial-port-removed',{}, {portId:'a'},x.c);x.s.emit('serial-port-added',{}, {portId:'a'},x.c);x.resolve(1);await flush();assert.deepEqual(q.results,[''])}
 {let x=setup(),q=x.request(),second=x.request();assert.deepEqual(second.results,['']);x.resolve(1);await flush();assert.deepEqual(q.results,['a']);let third=x.request();x.resolve(2);await flush();assert.deepEqual(third.results,['b']);assert.equal(x.s.listenerCount('serial-port-removed'),0);assert.equal(x.c.listenerCount('destroyed'),0);assert.equal(x.c.listenerCount('did-start-navigation'),0)}
 console.log('PASS serial chooser lifecycle and permissions');
})().catch(e=>{console.error(e);process.exitCode=1});
