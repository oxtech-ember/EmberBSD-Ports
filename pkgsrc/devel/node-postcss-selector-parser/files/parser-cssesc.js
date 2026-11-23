'use strict';

var cssesc = require('cssesc');
var defaults = {
    escapeEverything: false,
    isIdentifier: false,
    quotes: 'single',
    wrap: false
};

// Keep the parser defaults independent of the public cssesc.options object.
Object.defineProperty(exports, '__esModule', { value: true });
exports.default = function escapeSelector(value, options) {
    return cssesc(value, Object.assign({}, defaults, options));
};
