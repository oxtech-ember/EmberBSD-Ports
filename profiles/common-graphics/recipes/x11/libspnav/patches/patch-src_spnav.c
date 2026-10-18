$NetBSD$

Origin: EmberBSD (AI-assisted). Allocate the event queue only after a successful socket connection. Preserve descriptor-zero event and close paths, and the disconnected/X11 state.

--- src/spnav.c.orig
+++ src/spnav.c
@@ -107,12 +107,6 @@
 		return -1;
 	}
 
-	if(!(ev_queue = malloc(sizeof *ev_queue))) {
-		return -1;
-	}
-	ev_queue->next = 0;
-	ev_queue_tail = ev_queue;
-
 	if((s = socket(PF_UNIX, SOCK_STREAM, 0)) == -1) {
 		return -1;
 	}
@@ -149,6 +143,13 @@
 	}
 
 success:
+	if(!(ev_queue = malloc(sizeof *ev_queue))) {
+		close(s);
+		return -1;
+	}
+	ev_queue->next = 0;
+	ev_queue_tail = ev_queue;
+
 	sock = s;
 	proto = 0;
 
@@ -202,7 +203,7 @@
 		return -1;
 	}
 
-	if(sock) {
+	if(sock >= 0) {
 		while(ev_queue) {
 			void *tmp = ev_queue;
 			ev_queue = ev_queue->next;
@@ -310,7 +311,7 @@
 	fval = sens;
 
 	if(proto == 0) {
-		if(sock) {
+		if(sock >= 0) {
 			ssize_t bytes;
 
 			while((bytes = write(sock, &fval, sizeof fval)) <= 0 && errno == EINTR);
@@ -478,7 +479,7 @@
 	}
 #endif
 
-	if(sock) {
+	if(sock >= 0) {
 		if(read_event(sock, event) > 0) {
 			return event->type;
 		}
@@ -500,7 +501,7 @@
 	}
 #endif
 
-	if(sock) {
+	if(sock >= 0) {
 		if(event_pending(sock)) {
 			if(read_event(sock, event) > 0) {
 				return event->type;
@@ -568,7 +569,7 @@
 	}
 #endif
 
-	if(sock) {
+	if(sock >= 0) {
 		struct event_node *tmplist, *tmptail;
 
 		if(!(tmplist = tmptail = malloc(sizeof *tmplist))) {
