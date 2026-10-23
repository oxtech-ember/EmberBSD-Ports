$NetBSD$

Return IPC startup failures without invoking a callback that can return or send
shutdown events before IPC exists. Roll back owned resources and register the
display listener only after preparation succeeds. Initialize cleanup state
before the first startup error jump.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- sway/ipc-server.c.orig
+++ sway/ipc-server.c
@@ -67,8 +67,10 @@
 static void handle_display_destroy(struct wl_listener *listener, void *data) {
 	if (ipc_event_source) {
 		wl_event_source_remove(ipc_event_source);
+		ipc_event_source = NULL;
 	}
 	close(ipc_socket);
+	ipc_socket = -1;
 	unlink(ipc_sockaddr->sun_path);
 
 	while (ipc_client_list->length) {
@@ -83,25 +85,34 @@
 		}
 	}
 	list_free(ipc_client_list);
+	ipc_client_list = NULL;
 
 	free(ipc_sockaddr);
+	ipc_sockaddr = NULL;
 
 	wl_list_remove(&ipc_display_destroy.link);
 }
 
-void ipc_init(struct sway_server *server) {
+bool ipc_init(struct sway_server *server) {
+	bool bound = false;
 	ipc_socket = socket(AF_UNIX, SOCK_STREAM, 0);
 	if (ipc_socket == -1) {
-		sway_abort("Unable to create IPC socket");
+		sway_log_errno(SWAY_ERROR, "Unable to create IPC socket");
+		return false;
 	}
 	if (fcntl(ipc_socket, F_SETFD, FD_CLOEXEC) == -1) {
-		sway_abort("Unable to set CLOEXEC on IPC socket");
+		sway_log_errno(SWAY_ERROR, "Unable to set CLOEXEC on IPC socket");
+		goto error;
 	}
 	if (fcntl(ipc_socket, F_SETFL, O_NONBLOCK) == -1) {
-		sway_abort("Unable to set NONBLOCK on IPC socket");
+		sway_log_errno(SWAY_ERROR, "Unable to set NONBLOCK on IPC socket");
+		goto error;
 	}
 
 	ipc_sockaddr = ipc_user_sockaddr();
+	if (!ipc_sockaddr) {
+		goto error;
+	}
 
 	// We want to use socket name set by user, not existing socket from another sway instance.
 	if (getenv("SWAYSOCK") != NULL && access(getenv("SWAYSOCK"), F_OK) == -1) {
@@ -111,30 +122,59 @@
 
 	unlink(ipc_sockaddr->sun_path);
 	if (bind(ipc_socket, (struct sockaddr *)ipc_sockaddr, sizeof(*ipc_sockaddr)) == -1) {
-		sway_abort("Unable to bind IPC socket");
-	}
-
+		sway_log_errno(SWAY_ERROR, "Unable to bind IPC socket");
+		goto error;
+	}
+	bound = true;
 	if (listen(ipc_socket, 3) == -1) {
-		sway_abort("Unable to listen on IPC socket");
-	}
-
-	// Set i3 IPC socket path so that i3-msg works out of the box
-	setenv("I3SOCK", ipc_sockaddr->sun_path, 1);
-	setenv("SWAYSOCK", ipc_sockaddr->sun_path, 1);
+		sway_log_errno(SWAY_ERROR, "Unable to listen on IPC socket");
+		goto error;
+	}
 
 	ipc_client_list = create_list();
-
+	if (!ipc_client_list || !ipc_client_list->items) {
+		sway_log(SWAY_ERROR, "Unable to allocate IPC client list");
+		goto error;
+	}
+	ipc_event_source = wl_event_loop_add_fd(server->wl_event_loop, ipc_socket,
+			WL_EVENT_READABLE, ipc_handle_connection, server);
+	if (!ipc_event_source) {
+		sway_log(SWAY_ERROR, "Unable to add IPC socket event source");
+		goto error;
+	}
+
+	// Publish the socket only after its resources are ready.
+	if (setenv("I3SOCK", ipc_sockaddr->sun_path, 1) == -1 ||
+			setenv("SWAYSOCK", ipc_sockaddr->sun_path, 1) == -1) {
+		sway_log_errno(SWAY_ERROR, "Unable to publish IPC socket path");
+		goto error;
+	}
 	ipc_display_destroy.notify = handle_display_destroy;
 	wl_display_add_destroy_listener(server->wl_display, &ipc_display_destroy);
-
-	ipc_event_source = wl_event_loop_add_fd(server->wl_event_loop, ipc_socket,
-			WL_EVENT_READABLE, ipc_handle_connection, server);
+	return true;
+
+error:
+	if (ipc_event_source) {
+		wl_event_source_remove(ipc_event_source);
+		ipc_event_source = NULL;
+	}
+	list_free(ipc_client_list);
+	ipc_client_list = NULL;
+	if (bound) {
+		unlink(ipc_sockaddr->sun_path);
+	}
+	free(ipc_sockaddr);
+	ipc_sockaddr = NULL;
+	close(ipc_socket);
+	ipc_socket = -1;
+	return false;
 }
 
 struct sockaddr_un *ipc_user_sockaddr(void) {
 	struct sockaddr_un *ipc_sockaddr = malloc(sizeof(struct sockaddr_un));
 	if (ipc_sockaddr == NULL) {
-		sway_abort("Can't allocate ipc_sockaddr");
+		sway_log(SWAY_ERROR, "Can't allocate ipc_sockaddr");
+		return NULL;
 	}
 
 	ipc_sockaddr->sun_family = AF_UNIX;
@@ -147,7 +187,9 @@
 	}
 	if (path_size <= snprintf(ipc_sockaddr->sun_path, path_size,
 			"%s/sway-ipc.%u.%i.sock", dir, getuid(), getpid())) {
-		sway_abort("Socket path won't fit into ipc_sockaddr->sun_path");
+		sway_log(SWAY_ERROR, "Socket path won't fit into ipc_sockaddr->sun_path");
+		free(ipc_sockaddr);
+		return NULL;
 	}
 
 	return ipc_sockaddr;
@@ -273,6 +315,9 @@
 }
 
 static bool ipc_has_event_listeners(enum ipc_command_type event) {
+	if (!ipc_client_list) {
+		return false;
+	}
 	for (int i = 0; i < ipc_client_list->length; i++) {
 		struct ipc_client *client = ipc_client_list->items[i];
 		if ((client->subscribed_events & event_mask(event)) != 0) {
--- sway/main.c.orig
+++ sway/main.c
@@ -353,7 +353,11 @@
 		return valid ? 0 : 1;
 	}
 
-	ipc_init(&server);
+	struct swaynag_instance nag_gpu = {0};
+	if (!ipc_init(&server)) {
+		exit_value = EXIT_FAILURE;
+		goto shutdown;
+	}
 
 	setenv("WAYLAND_DISPLAY", server.socket, true);
 	if (!load_main_config(config_path, false, false)) {
@@ -379,7 +383,7 @@
 		swaynag_show(&config->swaynag_config_errors);
 	}
 
-	struct swaynag_instance nag_gpu = (struct swaynag_instance){
+	nag_gpu = (struct swaynag_instance){
 		.args = "--type error "
 			"--message 'Proprietary GPU drivers are not supported by sway. Do not report issues.' "
 			"--detailed-message",
--- include/sway/ipc-server.h.orig
+++ include/sway/ipc-server.h
@@ -1,5 +1,6 @@
 #ifndef _SWAY_IPC_SERVER_H
 #define _SWAY_IPC_SERVER_H
+#include <stdbool.h>
 #include <sys/socket.h>
 #include "sway/config.h"
 #include "sway/input/input-manager.h"
@@ -8,8 +9,9 @@
 
 struct sway_server;
 
-void ipc_init(struct sway_server *server);
+bool ipc_init(struct sway_server *server);
 
+// Returns NULL if allocation or socket path construction fails.
 struct sockaddr_un *ipc_user_sockaddr(void);
 
 void ipc_event_workspace(struct sway_workspace *old,
