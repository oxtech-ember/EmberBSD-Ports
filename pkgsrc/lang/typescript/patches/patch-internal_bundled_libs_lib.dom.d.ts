$NetBSD$

Chromium-compatible Trusted Types DOM setters (Chromium
third_party/node/patches/typescript.patch) for every consumer.

--- internal/bundled/libs/lib.dom.d.ts.orig
+++ internal/bundled/libs/lib.dom.d.ts
@@ -13567,7 +13567,8 @@
      *
      * [MDN Reference](https://developer.mozilla.org/docs/Web/API/Element/innerHTML)
      */
-    innerHTML: string;
+    get innerHTML(): string;
+    set innerHTML(html: string|TrustedHTML);
     /**
      * The **`Element.localName`** read-only property returns the local part of the qualified name of an element.
      *
@@ -17768,7 +17769,7 @@
      *
      * [MDN Reference](https://developer.mozilla.org/docs/Web/API/HTMLElement/hidden)
      */
-    hidden: boolean | "until-found";
+    hidden: boolean;
     /**
      * The HTMLElement property **`inert`** reflects the value of the element's inert attribute. It is a boolean value that, when present, makes the browser "ignore" user input events for the element, including focus events and events from assistive technologies. The browser may also ignore page search and text selection in the element. This can be useful when building UIs such as modals where you would want to "trap" the focus inside the modal when it's visible.
      *
@@ -20440,7 +20441,8 @@
      *
      * [MDN Reference](https://developer.mozilla.org/docs/Web/API/HTMLScriptElement/src)
      */
-    src: string;
+    get src(): string;
+    set src(url: string|TrustedScriptURL);
     /**
      * The **`text`** property of the HTMLScriptElement interface represents the inline text content of the <script> element. It behaves in the same way as the textContent and innerText property.
      *
@@ -35294,7 +35296,8 @@
      *
      * [MDN Reference](https://developer.mozilla.org/docs/Web/API/ShadowRoot/innerHTML)
      */
-    innerHTML: string;
+    get innerHTML(): string;
+    set innerHTML(html: string|TrustedHTML);
     /**
      * The **`mode`** read-only property of the ShadowRoot specifies its mode — either open or closed. This defines whether or not the shadow root's internal features are accessible from JavaScript.
      *
@@ -45123,3 +45126,15 @@
     [Symbol.asyncIterator](options?: ReadableStreamIteratorOptions): ReadableStreamAsyncIterator<R>;
     values(options?: ReadableStreamIteratorOptions): ReadableStreamAsyncIterator<R>;
 }
+
+/**
+ * Trusted Types values accepted by the Chromium-compatible DOM setters.
+ * @types/trusted-types merges its branded declarations into these.
+ * The optional brands keep primitives and unrelated objects from matching.
+ */
+interface TrustedHTML {
+    readonly __emberbsdTrustedHTML?: never;
+}
+interface TrustedScriptURL {
+    readonly __emberbsdTrustedScriptURL?: never;
+}
