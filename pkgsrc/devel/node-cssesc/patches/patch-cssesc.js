$NetBSD$

Use the space-removal implementation from postcss-selector-parser 7.2.1,
dist/util/cssesc.js (Mathias Bynens, MIT). Keep the cssesc options and CLI.

--- cssesc.js.orig
+++ cssesc.js
@@ -19,8 +19,64 @@
 var regexAnySingleEscape = /[ -,\.\/:-@\[-\^`\{-~]/;
 var regexSingleEscape = /[ -,\.\/:-@\[\]\^`\{-~]/;
 var regexAlwaysEscape = /['"\\]/;
-var regexExcessiveSpaces = /(^|\\+)?(\\[A-F0-9]{1,6})\x20(?![a-fA-F0-9\x20])/g;
-
+var BACKSLASH = 0x5c;
+var SPACE = 0x20;
+function isUpperHex(code) {
+    return (code >= 0x30 && code <= 0x39) || (code >= 0x41 && code <= 0x46);
+}
+function isHexOrSpace(code) {
+    return isUpperHex(code) || (code >= 0x61 && code <= 0x66) || code === SPACE;
+}
+/**
+ * Remove spaces after `\HEX` escapes that are not followed by a hex digit or a
+ * space, since they are redundant. This is only possible if the escape is not
+ * preceded by an odd number of backslashes, which would make its own backslash
+ * an escaped one.
+ *
+ * Same result as cssesc 3.0.0's
+ * `output.replace(/(^|\\+)?(\\[A-F0-9]{1,6})\x20(?![a-fA-F0-9\x20])/g, ...)`:
+ * a match can only start at the beginning of a run of backslashes and only
+ * its last backslash can open the escape, so each run is measured once
+ * instead of being re-scanned from every position inside it.
+ */
+function removeExcessiveSpaces(output) {
+    var length = output.length;
+    var result = "";
+    var copied = 0;
+    var i = 0;
+    while (i < length) {
+        if (output.charCodeAt(i) !== BACKSLASH) {
+            i++;
+            continue;
+        }
+        var runEnd = i + 1;
+        while (runEnd < length && output.charCodeAt(runEnd) === BACKSLASH) {
+            runEnd++;
+        }
+        // Look at up to 7 hex digits: more than 6 can never be followed directly
+        // by the space.
+        var hexEnd = runEnd;
+        while (hexEnd < length && hexEnd - runEnd < 7 && isUpperHex(output.charCodeAt(hexEnd))) {
+            hexEnd++;
+        }
+        var hexLength = hexEnd - runEnd;
+        if (hexLength >= 1 &&
+            hexLength <= 6 &&
+            output.charCodeAt(hexEnd) === SPACE &&
+            !isHexOrSpace(output.charCodeAt(hexEnd + 1))) {
+            // Backslashes preceding the one that opens the escape.
+            if ((runEnd - i - 1) % 2 === 0) {
+                result += output.slice(copied, hexEnd);
+                copied = hexEnd + 1;
+            }
+            i = hexEnd + 1;
+        }
+        else {
+            i = runEnd;
+        }
+    }
+    return copied === 0 ? output : result + output.slice(copied);
+}
 // https://mathiasbynens.be/notes/css-escapes#css
 var cssesc = function cssesc(string, options) {
 	options = merge(options, cssesc.options);
@@ -79,17 +135,7 @@
 		}
 	}
 
-	// Remove spaces after `\HEX` escapes that are not followed by a hex digit,
-	// since they’re redundant. Note that this is only possible if the escape
-	// sequence isn’t preceded by an odd number of backslashes.
-	output = output.replace(regexExcessiveSpaces, function ($0, $1, $2) {
-		if ($1 && $1.length % 2) {
-			// It’s not safe to remove the space, so don’t.
-			return $0;
-		}
-		// Strip the space.
-		return ($1 || '') + $2;
-	});
+	output = removeExcessiveSpaces(output);
 
 	if (!isIdentifier && options.wrap) {
 		return quote + output + quote;
