Preserve EmberBSD DHCP lease validation and IPv4LL cleanup.
Origin: EmberBSD 997342e2d9c9dd0765ecf16d52e6df34d3df3b88,
4da0c0fa0b299b228f7076bfa03026723f5af624, and
a6f115893c64a58452af50d89d0fd3dd84d8b9d4.

--- src/dhcp.c.orig
+++ src/dhcp.c
@@ -2113,14 +2113,21 @@
 {
 	struct dhcp_state *state = D_STATE(ifp);
 
-	if (state->state == DHS_BOUND)
+	/* DAD does not confirm a saved lease or a DHCP offer.
+	 * Wait for the server to acknowledge it. A lastlease fallback
+	 * can finish DAD while discovery continues. */
+	if (state->state == DHS_BOUND || state->state == DHS_REBOOT ||
+	    state->state == DHS_REQUEST ||
+	    (state->state == DHS_DISCOVER && !(state->added & STATE_EXPIRED)))
 		return;
 	if (state->offer == NULL || state->offer->yiaddr != ia->s_addr)
 		return;
 
 	logdebugx("%s: DAD completed for %s", ifp->name, inet_ntoa(*ia));
-	if (!(ifp->options->options & DHCPCD_INFORM))
+	if (!(ifp->options->options & DHCPCD_INFORM)) {
 		dhcp_bind(ifp);
+		return;
+	}
 #ifndef IN_IFF_DUPLICATED
 	else {
 		struct bootp *bootp;
@@ -2509,6 +2516,12 @@
 			}
 			return;
 		}
+#ifdef IPV4LL
+		/* The address can already be usable when a late ACK arrives. */
+		if (ifo->options & DHCPCD_IPV4LL &&
+		    !IN_LINKLOCAL(ntohl(lease->addr.s_addr)))
+			ipv4ll_drop(ifp);
+#endif
 	} else {
 		struct ipv4_addr *ia;
 
