$NetBSD$

NetBSD has no struct ip_mreqn: use ip_mreq with the RFC 1724 interface index.

--- src/modules/module-rtp-source.c.orig
+++ src/modules/module-rtp-source.c
@@ -382,10 +382,18 @@
 			pw_log_debug("re-joined IPv6 multicast group successfully");
 		}
 	} else {
+#ifdef __NetBSD__
+		/* No ip_mreqn: RFC 1724 0.0.0.0/8 names the interface by index. */
+		struct ip_mreq mr4;
+		memset(&mr4, 0, sizeof(mr4));
+		mr4.imr_multiaddr = ((struct sockaddr_in*)&impl->igmp_recovery.mcast_addr)->sin_addr;
+		mr4.imr_interface.s_addr = htonl((uint32_t)impl->igmp_recovery.if_index);
+#else
 		struct ip_mreqn mr4;
 		memset(&mr4, 0, sizeof(mr4));
 		mr4.imr_multiaddr = ((struct sockaddr_in*)&impl->igmp_recovery.mcast_addr)->sin_addr;
 		mr4.imr_ifindex = impl->igmp_recovery.if_index;
+#endif
 
 		/* Leave the group first */
 		res = setsockopt(impl->igmp_recovery.socket_fd, IPPROTO_IP, IP_DROP_MEMBERSHIP,
@@ -516,10 +524,18 @@
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
 			pw_net_get_ip((struct sockaddr_storage*)sa, addr, sizeof(addr), NULL, NULL);
 			pw_log_info("join IPv4 group: %s", addr);
 			res = setsockopt(fd, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mr4, sizeof(mr4));
