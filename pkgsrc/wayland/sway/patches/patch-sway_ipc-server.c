$NetBSD$

Flush pending replies before display destruction closes IPC connections.
The exit command terminates the event loop before its writable callback
runs. Use the existing nonblocking write path once. A write failure can
remove the client, so disconnect it only if that path kept it alive.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- sway/ipc-server.c.orig
+++ sway/ipc-server.c
@@ -72,7 +72,15 @@ static void handle_display_destroy(struc
 	unlink(ipc_sockaddr->sun_path);
 
 	while (ipc_client_list->length) {
-		ipc_client_disconnect(ipc_client_list->items[ipc_client_list->length-1]);
+		int length = ipc_client_list->length;
+		struct ipc_client *client = ipc_client_list->items[length - 1];
+
+		/* The display loop cannot dispatch pending replies after exit. */
+		ipc_client_handle_writable(client->fd, WL_EVENT_WRITABLE, client);
+		/* A write error can already disconnect and free this client. */
+		if (ipc_client_list->length == length) {
+			ipc_client_disconnect(client);
+		}
 	}
 	list_free(ipc_client_list);
 
