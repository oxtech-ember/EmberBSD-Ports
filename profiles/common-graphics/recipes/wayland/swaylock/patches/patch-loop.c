$NetBSD$

Check allocation results before dereferencing or replacing owned pointers.
Preserve image and event-loop state when allocation fails.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- loop.c.orig
+++ loop.c
@@ -41,6 +41,11 @@
 	}
 	loop->fd_capacity = 10;
 	loop->fds = malloc(sizeof(struct pollfd) * loop->fd_capacity);
+	if (!loop->fds) {
+		swaylock_log_errno(LOG_ERROR, "Unable to allocate memory for file descriptors");
+		free(loop);
+		return NULL;
+	}
 	wl_list_init(&loop->fd_events);
 	wl_list_init(&loop->timers);
 	return loop;
@@ -135,16 +140,23 @@
 	}
 	event->callback = callback;
 	event->data = data;
-	wl_list_insert(loop->fd_events.prev, &event->link);
 
 	struct pollfd pfd = {fd, mask, 0};
 
 	if (loop->fd_length == loop->fd_capacity) {
-		loop->fd_capacity += 10;
-		loop->fds = realloc(loop->fds,
-				sizeof(struct pollfd) * loop->fd_capacity);
+		int capacity = loop->fd_capacity + 10;
+		struct pollfd *fds = realloc(loop->fds,
+				sizeof(struct pollfd) * capacity);
+		if (!fds) {
+			swaylock_log_errno(LOG_ERROR, "Unable to grow file descriptor list");
+			free(event);
+			return;
+		}
+		loop->fds = fds;
+		loop->fd_capacity = capacity;
 	}
 
+	wl_list_insert(loop->fd_events.prev, &event->link);
 	loop->fds[loop->fd_length++] = pfd;
 }
 
