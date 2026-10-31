$NetBSD$

NetBSD has no struct ip_mreqn: use ip_mreq with the RFC 1724 interface index.

--- src/modules/module-vban-recv.c.orig
+++ src/modules/module-vban-recv.c
@@ -243,10 +243,18 @@
 		static const uint32_t ipv4_mcast_mask = 0xe0000000;
 		struct sockaddr_in *sa4 = (struct sockaddr_in*)sa;
 		if ((ntohl(sa4->sin_addr.s_addr) & ipv4_mcast_mask) == ipv4_mcast_mask) {
+#ifdef __NetBSD__
+			/* No ip_mreqn: RFC 1724 0.0.0.0/8 names the interface by index. */
+			struct ip_mreq mr4;
+			memset(&mr4, 0, sizeof(mr4));
+			mr4.imr_multiaddr = sa4->sin_addr;
+			mr4.imr_interface.s_addr = htonl((uint32_t)req.ifr_ifindex);
+#else
 			struct ip_mreqn mr4;
 			memset(&mr4, 0, sizeof(mr4));
 			mr4.imr_multiaddr = sa4->sin_addr;
 			mr4.imr_ifindex = req.ifr_ifindex;
+#endif
 			res = setsockopt(fd, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mr4, sizeof(mr4));
 		} else {
 			sa4->sin_addr.s_addr = INADDR_ANY;
