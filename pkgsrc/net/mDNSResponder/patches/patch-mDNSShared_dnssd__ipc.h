# Lint preprocesses without __GNUC__, so the wire structures are not packed there.
# Keep the layout assertions for real compilers only, as the NetBSD base copy did.
--- mDNSShared/dnssd_ipc.h.orig
+++ mDNSShared/dnssd_ipc.h
@@ -255,8 +255,10 @@
 {
     // Check that the compiler generated our on-the-wire packet format structure definitions
     // properly packed, without adding padding bytes to align fields on 32-bit or 64-bit boundaries.
+#ifndef __lint__
     char assert0[(sizeof(client_context_t) ==  8) ? 1 : -1];
     char assert1[(sizeof(ipc_msg_hdr)      == 28) ? 1 : -1];
+#endif
 };
 
 #endif // DNSSD_IPC_H
