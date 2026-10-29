'use strict';
const fs = require('fs');
const path = require('path');
const addon = process.argv[2];
const work = process.argv[3];
fs.mkdirSync(work, { recursive: true });
const modulePath = path.join(work, 'dprint-node.node');
fs.copyFileSync(addon, modulePath);
const { format } = require(modulePath);
const cases = [
  ['arrows.ts', 'const a=(x:number)=>{/* open */return x+1;/* close */}; const b=(x:number)=>x+1;'],
  ['functions.ts', 'function f(this: Date,x:number):number{/* open */return x;/* close */} class A { constructor(x:number){/* inside */this.x=x} x:number; }'],
  ['accessors.ts', 'const x={get a(this:T):number{return 1},set a(this:T,v:number){this.v=v}};'],
  ['partial.ts', 'const x={get c(z){return z},set a(){},set b(a,b){}};'],
  ['comments-before.ts', 'function f(this // BEFORE\n : T) {}'],
  ['comments-after.ts', 'function f(this: // AFTER\n T) {}'],
  ['comments-block.ts', 'function f(this /* BEFORE */ : /* AFTER */ T) {}'],
  ['generic-getter.ts', 'const x={get a<T>(): T{return 1}};'],
  ['typed-setter.ts', 'const x={set a(v: number): void {}};'],
  ['unicode-entities.tsx', 'const el=<div>&#xD800; &#x1F63A; &amp; 🐱</div>;'],
  ['unicode.tsx', 'const el=<div>é 🐱 &amp; Привет</div>;'],
];
for (const [name, input] of cases) {
  const output = format(name, input, {});
  if (output !== format(name, output, {})) throw new Error(name + ' is not idempotent');
  if (name === 'functions.ts' && !output.includes('this: Date')) throw new Error('lost this parameter');
  if (name === 'accessors.ts' && (output.match(/this: T/g) || []).length !== 2) throw new Error('lost accessor this');
  if (name === 'partial.ts' && (!output.includes('set b(a, b)') || !output.includes('get c(z)'))) throw new Error('lost parameter');
  for (const comment of ['BEFORE', 'AFTER', 'inside']) {
    if (input.includes(comment) && !output.includes(comment)) throw new Error('comment lost: ' + comment);
  }
  if (input.includes('BEFORE') && output.indexOf('BEFORE') > output.indexOf(':')) throw new Error('comment moved after colon');
  if (input.includes('AFTER') && output.indexOf('AFTER') < output.indexOf(':')) throw new Error('comment moved before colon');
  if (name === 'generic-getter.ts' && !output.includes('<T>')) throw new Error('lost generic getter');
  if (name === 'typed-setter.ts' && !output.includes(': void')) throw new Error('lost setter return type');
  if (name === 'unicode-entities.tsx' && !output.includes('&#xD800; &#x1F63A; &amp; 🐱')) throw new Error('lost JSX escapes');
  if (name === 'unicode.tsx' && !output.includes('é 🐱 &amp; Привет')) throw new Error('lost JSX source');
  for (const comment of ['open', 'close']) if (input.includes(comment) && !output.includes(comment)) throw new Error('lost comment');
}
function configResult(value) {
  try { return 'ok:' + format('x.ts', 'const x=1;', { lineWidth: value }); }
  catch (error) { return 'err:' + error.message; }
}
for (const [actual, expected] of [[1.9,1],[-1.9,-1],[4294967297,1],[2147483648,-2147483648],[NaN,0],[Infinity,0],[-Infinity,0]]) {
  if (configResult(actual) !== configResult(expected)) throw new Error('N-API int32 behavior changed');
}
for (const value of [{}, null]) if (!configResult(value).includes('Unsupported type')) throw new Error('unsupported config accepted');
try {
  format('x.ts', 'const x=1;', Object.defineProperty({}, 'lineWidth', {enumerable:true, get() { throw Error('getter sentinel'); }}));
  throw new Error('getter failure swallowed');
} catch (error) { if (!error.message.includes('getter sentinel')) throw error; }
console.log('source-built dprint formatter: PASS');
