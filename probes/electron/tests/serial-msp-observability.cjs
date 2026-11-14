'use strict';
const fs=require('fs'), path=require('path'), vm=require('vm'), assert=require('assert');
const html=fs.readFileSync(path.join(__dirname,'serial-msp-runtime.html'),'utf8');
const source=html.match(/<script>([\s\S]*?)<\/script>/)[1];
async function test(mode) {
 let handler, report, code, phases=[], writes=[];
 const never=()=>new Promise(()=>{});
 const window={close(){}};
 const reader={read(){phases.push(window.fixturePhase); if(mode==='read') return never(); const checksum=mode==='parse' ? code^1 : code; return Promise.resolve({value:new Uint8Array([36,77,62,0,code,checksum]),done:false});},cancel(){return Promise.resolve()},releaseLock(){}};
 const writer={write(bytes){phases.push(window.fixturePhase);writes.push([...bytes]);code=bytes[4];return mode==='write'?never():Promise.resolve()},releaseLock(){}};
 const port={getInfo(){return {usbVendorId:0x0483,usbProductId:0x5740}},open(){phases.push(window.fixturePhase);return mode==='open'?never():Promise.resolve()},close(){phases.push(window.fixturePhase);return mode==='close'?never():Promise.resolve()},readable:{getReader(){return reader}},writable:{getWriter(){return writer}}};
 const button={addEventListener(_name,fn){handler=fn}}, result={};
 const sandbox={window,navigator:{userActivation:{isActive:true},serial:{requestPort(){return Promise.resolve(port)}}},document:{querySelector(q){return q==='#start'?button:result}},setTimeout(fn){return setTimeout(fn,2)},console:{log(line){report=JSON.parse(line.slice('MSP_DIAGNOSTIC_RESULT '.length))}},Uint8Array,Date,Promise,Error};
 vm.runInNewContext(source,sandbox);await handler({isTrusted:true,currentTarget:button});
 assert(report);assert.deepStrictEqual(writes.map(x=>x[4]),mode==='success'||mode==='close'?[1,2,3,4,101]:mode==='open'?[]:[1]);
 for(const x of writes)assert.deepStrictEqual(x,[36,77,60,0,x[4],x[4]]);
 if(mode==='success'){assert(report.passed);assert.equal(report.commands.length,5);assert.equal(report.closed,true)}
 if(mode==='open'){assert.equal(report.errorPhase,'port-open');assert.match(report.error,/port-open timeout/)}
 if(mode==='write'){assert.equal(report.errorPhase,'write:API_VERSION(1)');assert.match(report.error,/write:API_VERSION\(1\) timeout/)}
 if(mode==='read'){assert.equal(report.errorPhase,'read:API_VERSION(1)');assert.match(report.error,/read:API_VERSION\(1\) timeout/)}
 if(mode==='parse'){assert.equal(report.errorPhase,'parse:API_VERSION(1)');assert.match(report.error,/checksum mismatch/)}
 if(mode==='close'){assert(!report.passed);assert.equal(report.closeErrorPhase,'port-close');assert.match(report.closeError,/port-close timeout/)}
 assert.equal(phases[0],'port-open');if(mode!=='open') assert(phases.includes('write:API_VERSION(1)'));assert(phases.includes('port-close'));
}
(async()=>{for(const m of ['success','open','write','read','parse','close'])await test(m);console.log('PASS: success and open/write/read/parse/close failure phases')})().catch(e=>{console.error(e);process.exitCode=1});
