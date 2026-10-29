Keep const on read-only socket addresses.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- sockutils.c.orig
+++ sockutils.c
@@ -370,13 +370,13 @@
 {
 	if (saddr->sa_family == PF_INET)
 	{
-		struct sockaddr_in *saddr4 = (struct sockaddr_in *) saddr;
+		const struct sockaddr_in *saddr4 = (const struct sockaddr_in *) saddr;
 		if (IN_MULTICAST(ntohl(saddr4->sin_addr.s_addr))) return 0;
 		else return -1;
 	}
 	else
 	{
-		struct sockaddr_in6 *saddr6 = (struct sockaddr_in6 *) saddr;
+		const struct sockaddr_in6 *saddr6 = (const struct sockaddr_in6 *) saddr;
 		if (IN6_IS_ADDR_MULTICAST(&saddr6->sin6_addr)) return 0;
 		else return -1;
 	}
@@ -2005,7 +2005,7 @@
 	if ((flags & NI_NUMERICHOST) == 0)	/* Check that we want literal names */
 	{
 		if ((sockaddr->ss_family == AF_INET6) &&
-			(memcmp(&((struct sockaddr_in6 *) sockaddr)->sin6_addr, "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0", sizeof(struct in6_addr)) == 0))
+			(memcmp(&((const struct sockaddr_in6 *) sockaddr)->sin6_addr, "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0", sizeof(struct in6_addr)) == 0))
 		{
 			if (address)
 				pcapint_strlcpy(address, SOCKET_NAME_NULL_DAD, addrlen);
@@ -2013,7 +2013,7 @@
 		}
 	}
 
-	if (getnameinfo((struct sockaddr *) sockaddr, sockaddrlen, address, addrlen, port, portlen, flags) != 0)
+	if (getnameinfo((const struct sockaddr *) sockaddr, sockaddrlen, address, addrlen, port, portlen, flags) != 0)
 	{
 		/* If the user wants to receive an error message */
 		if (errbuf)
