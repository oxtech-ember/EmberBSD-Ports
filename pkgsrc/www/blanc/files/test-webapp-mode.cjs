'use strict';
const assert = require('node:assert/strict');
const {parseWebAppArgs:parse,userDataPath,initializeWebApp,sameWebApp,effectivePrivate,webAppMenuModel,fullPageLayout}=require('./webapp-mode.js');
const args=['--webapp-id=mail_1','--webapp-url=https://example.org/login?q=1','--webapp-name=Mail','--webapp-private'];
const mode=parse(args);
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'); const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'webapp-profile-')); try { const calls=[]; const env={CHROME_DESKTOP:'old.desktop',OTHER:'preserved'}; const app={getPath:n=>{assert.equal(n,'appData');return tmp;},setPath:(n,p)=>{assert(fs.statSync(p).isDirectory());calls.push([n,p]);}}; const profile=initializeWebApp(app,fs,env,mode); assert.deepEqual(calls,[['userData',profile],['sessionData',profile]]); assert.deepEqual(env,{CHROME_DESKTOP:'WebApp-mail_1.desktop',OTHER:'preserved'}); assert.equal(fs.statSync(profile).mode&0o777,0o700); } finally { fs.rmSync(tmp,{recursive:true,force:true}); }assert.deepEqual(mode,{id:'mail_1',url:'https://example.org/login?q=1',name:'Mail',private:true});
assert.equal(parse(['--ozone-platform=x11']),null);
assert.equal(userDataPath('/home/user/.config','mail_1'),'/home/user/.config/Ember Browser/webapps/mail_1');
for (const id of ['../bad','a/b','', '.','a'.repeat(65)]) assert.throws(()=>userDataPath('/tmp',id));
for (const bad of [
 ['--webapp-id=../bad','--webapp-url=https://a','--webapp-name=A'],
 ['--webapp-id=a','--webapp-url=file:///etc/passwd','--webapp-name=A'],
 ['--webapp-id=a','--webapp-url=https://u:p@a/','--webapp-name=A'],
 ['--webapp-id=a','--webapp-url=https://a/\n','--webapp-name=A'],
 ['--webapp-id=a','--webapp-url=https://a/','--webapp-name='+ 'x'.repeat(201)],
 ['--webapp-id=a','--webapp-url=https://a/','--webapp-name=A','--webapp-id=b'],
 ['--webapp-id=a','--webapp-url=https://a/','--webapp-name=A','--webapp-private=false'],
]) assert.throws(()=>parse(bad));
assert(sameWebApp(mode,parse(args)));assert(!sameWebApp(mode,parse(args.slice(0,-1))));assert(sameWebApp(mode,{...mode,url:'https://elsewhere.test/',name:'Changed'}));
assert.equal(userDataPath('/tmp','mail_1',true),'/tmp/Ember Browser/webapps-private/mail_1');
for (const name of ['Example','Пример почты','Firefox','xylophone']) assert.equal(parse(['--webapp-id=test','--webapp-url=https://example.com/path?q=a%20b','--webapp-name='+name]).name,name);
assert.throws(()=>parse(['--webapp-id=a','--webapp-url=https://a/','--webapp-name=A','--no-sandbox']));
assert(parse(['--ozone-platform=x11','--in-process-gpu','--webapp-id=a','--webapp-url=https://a/','--webapp-name=A']));
assert.equal(effectivePrivate(mode,false),true); assert.equal(effectivePrivate(mode,true),true); assert.equal(effectivePrivate(null,false),false);
assert.deepEqual(webAppMenuModel([{id:1,title:'A & B'},{id:2,url:'https://example.com/'}],2),[{id:1,label:'A && B',checked:false},{id:2,label:'https://example.com/',checked:true}]);
const original={pageBounds:{x:10,y:70,width:500,height:400},utilityBounds:{x:2}};const full=fullPageLayout(original,800,600);assert.deepEqual(full.pageBounds,{x:0,y:0,width:800,height:600});assert.deepEqual(original.pageBounds,{x:10,y:70,width:500,height:400});assert.deepEqual(full.utilityBounds,{x:2});
console.log('PASS webapp args, origin, ID traversal, isolation, private, same-instance and layout');
