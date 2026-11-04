$NetBSD$

Use the independent Ember Browser identity. Origin: EmberBSD (AI-assisted).

--- src/main/webauthn.js
+++ src/main/webauthn.js
@@ -32,7 +32,7 @@
     type: 'question',
     title: 'Choose a passkey',
     message: `Choose a passkey for ${relyingPartyId}`,
-    detail: 'This website has more than one passkey available in Blanc on this Mac.',
+    detail: 'This website has more than one passkey available in Ember Browser on this Mac.',
     buttons,
     cancelId,
     noLink: true,
@@ -53,12 +53,12 @@
  *
  * This deliberately does not request Apple's browser passkey entitlement: that
  * separate managed capability is required for iCloud/credential-provider
- * passkeys, while this feature stores device-bound passkeys in Blanc's own
+ * passkeys, while this feature stores device-bound passkeys in Ember Browser's own
  * Secure Enclave access group.
  *
  * Electron seals credential metadata with a per-session secret kept in the
  * session's prefs, so the in-memory private session mints a fresh secret every
- * launch: passkeys created in private tabs become unusable once Blanc quits,
+ * launch: passkeys created in private tabs become unusable once Ember Browser quits,
  * and normal-profile passkeys stay invisible to private tabs (spec D16).
  * The access group itself is app-global — Electron offers no per-session
  * opt-out, so private-tab ceremonies can't be selectively disabled.
