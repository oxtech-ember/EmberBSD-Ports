The system STAILQ_ENTRY macro does not carry Clang nullability annotations.
Declare its standard link member explicitly so it remains nullable alongside
the annotated public API without weakening compiler diagnostics.

--- mDNSShared/utilities/mdns_addr_tailq.h.orig
+++ mDNSShared/utilities/mdns_addr_tailq.h
@@ -34,11 +34,16 @@
 
 typedef struct mdns_addr_with_port mdns_addr_with_port_t;
 struct mdns_addr_with_port {
-	STAILQ_ENTRY(mdns_addr_with_port) __entries;	// The entry used by STAILQ to form the linked list.
+	struct {
+		mdns_addr_with_port_t * NULLABLE stqe_next;
+	} __entries;
 	mDNSAddr address;								// IPv4 or IPv6 address.
 	mDNSIPPort port;								// The port number that is associated with the address above.
 };
 
 typedef struct mdns_addr_tailq mdns_addr_tailq_t;
 // The tail queue struct mdns_addr_tailq that contains struct mdns_addr_with_port.
-STAILQ_HEAD(mdns_addr_tailq, mdns_addr_with_port);
+struct mdns_addr_tailq {
+	mdns_addr_with_port_t * NULLABLE stqh_first;
+	mdns_addr_with_port_t * NULLABLE * NULLABLE stqh_last;
+};
