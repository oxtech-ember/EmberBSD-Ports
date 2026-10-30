'use strict';
const Module = require('node:module');
Module.wrapper = [
  '(function(exports, require, module, __filename, __dirname, process, global, Buffer) { return function(exports, require, module, __filename, __dirname) { ',
  '\n}.call(this, exports, require, module, __filename, __dirname); })'
];
