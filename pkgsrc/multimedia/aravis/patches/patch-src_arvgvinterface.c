$NetBSD$

Send discovery to an interface without broadcast, such as the BSD loopback,
at the address it records as broadcast address.

--- src/arvgvinterface.c.orig
+++ src/arvgvinterface.c
@@ -184,6 +184,26 @@
 	for (iter = socket_list->sockets; iter != NULL; iter = iter->next) {
 		ArvGvDiscoverSocket *discover_socket = iter->data;
 		GError *error = NULL;
+
+		/* An interface without broadcast, such as the BSD loopback,
+		 * records its own address as broadcast address. A limited
+		 * broadcast does not reach it, so send to that address. */
+		if (g_inet_address_equal (g_inet_socket_address_get_address
+					  (G_INET_SOCKET_ADDRESS (discover_socket->interface_address)),
+					  g_inet_socket_address_get_address
+					  (G_INET_SOCKET_ADDRESS (discover_socket->broadcast_address)))) {
+			g_socket_send_to (discover_socket->socket,
+					  discover_socket->broadcast_address,
+					  (const char *) packet, size,
+					  NULL, &error);
+			if (error != NULL) {
+				arv_warning_interface ("[ArvGVInterface::send_discover_packet] "
+						       "Error sending packet to interface address: %s",
+						       error->message);
+				g_clear_error (&error);
+			}
+			continue;
+		}
 
                 arv_gv_discover_socket_set_broadcast (discover_socket, TRUE);
 
