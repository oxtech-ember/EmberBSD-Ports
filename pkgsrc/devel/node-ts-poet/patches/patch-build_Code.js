$NetBSD$

Load the native dprint-node formatter only when it is installed.
Without it, ts-poet keeps the unformatted, valid TypeScript output.

--- build/Code.js.orig
+++ build/Code.js
@@ -9,7 +9,6 @@
 const is_plain_object_1 = require("./is-plain-object");
 const ConditionalOutput_1 = require("./ConditionalOutput");
 const index_1 = require("./index");
-const dprint_node_1 = __importDefault(require("dprint-node"));
 class Code extends Node_1.Node {
     constructor(literals, placeholders) {
         super();
@@ -246,6 +245,8 @@
 };
 function maybePretty(input, options) {
     try {
+        // EmberBSD: load the optional native formatter only when it is installed.
+        const dprint_node_1 = __importDefault(require("dprint-node"));
         return dprint_node_1.default.format("file.ts", input.trim(), { ...baseOptions, ...options });
     }
     catch (e) {
