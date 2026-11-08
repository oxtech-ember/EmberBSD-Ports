$NetBSD$

NetBSD has no linux/input.h. The portal keycodes are the evdev values.

--- plugins/mousepad/waylandremoteinput.cpp.orig	2025-11-01 21:19:03.000000000 +0300
+++ plugins/mousepad/waylandremoteinput.cpp	2026-11-08 13:58:44.312148092 +0300
@@ -15,7 +15,45 @@
 #include <KSharedConfig>
 #include <QDBusPendingCallWatcher>
 
-#include <linux/input.h>
+/* evdev codes from linux/input-event-codes.h. NetBSD has no linux/input.h.
+ * These are the keycodes the remote-desktop portal expects. */
+#ifndef KEY_ESC
+#define KEY_ESC 1
+#define KEY_ENTER 28
+#define KEY_LEFTCTRL 29
+#define KEY_LEFTSHIFT 42
+#define KEY_LEFTALT 56
+#define KEY_F1 59
+#define KEY_F2 60
+#define KEY_F3 61
+#define KEY_F4 62
+#define KEY_F5 63
+#define KEY_F6 64
+#define KEY_F7 65
+#define KEY_F8 66
+#define KEY_F9 67
+#define KEY_F10 68
+#define KEY_SCROLLLOCK 70
+#define KEY_F11 87
+#define KEY_F12 88
+#define KEY_SYSRQ 99
+#define KEY_LINEFEED 101
+#define KEY_HOME 102
+#define KEY_UP 103
+#define KEY_PAGEUP 104
+#define KEY_LEFT 105
+#define KEY_RIGHT 106
+#define KEY_END 107
+#define KEY_DOWN 108
+#define KEY_PAGEDOWN 109
+#define KEY_DELETE 111
+#define KEY_LEFTMETA 125
+#define KEY_BACKSPACE 14
+#define KEY_TAB 15
+#define BTN_LEFT 0x110
+#define BTN_RIGHT 0x111
+#define BTN_MIDDLE 0x112
+#endif
 #include <xkbcommon/xkbcommon.h>
 
 namespace
