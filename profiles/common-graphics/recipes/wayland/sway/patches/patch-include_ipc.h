$NetBSD$

Use unsigned shifts for the protocol event flag and subscription masks.
Signed 1 << 31 is undefined in C11. Preserve the existing 32-bit wire values.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- include/ipc.h.orig
+++ include/ipc.h
@@ -1,7 +1,7 @@
 #ifndef _SWAY_IPC_H
 #define _SWAY_IPC_H
 
-#define event_mask(ev) (1 << (ev & 0x7F))
+#define event_mask(ev) (1U << (ev & 0x7F))
 
 enum ipc_command_type {
 	// i3 command types - see i3's I3_REPLY_TYPE constants
@@ -24,18 +24,18 @@ enum ipc_command_type {
 	IPC_GET_SEATS = 101,
 
 	// Events sent from sway to clients. Events have the highest bits set.
-	IPC_EVENT_WORKSPACE = ((1<<31) | 0),
-	IPC_EVENT_OUTPUT = ((1<<31) | 1),
-	IPC_EVENT_MODE = ((1<<31) | 2),
-	IPC_EVENT_WINDOW = ((1<<31) | 3),
-	IPC_EVENT_BARCONFIG_UPDATE = ((1<<31) | 4),
-	IPC_EVENT_BINDING = ((1<<31) | 5),
-	IPC_EVENT_SHUTDOWN = ((1<<31) | 6),
-	IPC_EVENT_TICK = ((1<<31) | 7),
+	IPC_EVENT_WORKSPACE = ((1U << 31) | 0),
+	IPC_EVENT_OUTPUT = ((1U << 31) | 1),
+	IPC_EVENT_MODE = ((1U << 31) | 2),
+	IPC_EVENT_WINDOW = ((1U << 31) | 3),
+	IPC_EVENT_BARCONFIG_UPDATE = ((1U << 31) | 4),
+	IPC_EVENT_BINDING = ((1U << 31) | 5),
+	IPC_EVENT_SHUTDOWN = ((1U << 31) | 6),
+	IPC_EVENT_TICK = ((1U << 31) | 7),
 
 	// sway-specific event types
-	IPC_EVENT_BAR_STATE_UPDATE = ((1<<31) | 20),
-	IPC_EVENT_INPUT = ((1<<31) | 21),
+	IPC_EVENT_BAR_STATE_UPDATE = ((1U << 31) | 20),
+	IPC_EVENT_INPUT = ((1U << 31) | 21),
 };
 
 #endif
