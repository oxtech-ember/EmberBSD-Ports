$NetBSD$

Check dictionary pointer addresses before calculating a match distance. The
non-deterministic path can receive an entry outside the input object. Avoid
forming an out-of-bounds pointer before rejecting that entry. Packaging is
AI-assisted.

--- src/lzo_dict.h.orig
+++ src/lzo_dict.h
@@ -269,10 +269,9 @@
 /* m_pos may point anywhere... */
 #define LZO_CHECK_MPOS_NON_DET(m_pos,m_off,in,ip,max_offset) \
     (BOUNDS_CHECKING_OFF_IN_EXPR(( \
-        m_pos = ip - (lzo_uint) PTR_DIFF(ip,m_pos), \
         PTR_LT(m_pos,in) || \
-        (m_off = (lzo_uint) PTR_DIFF(ip,m_pos)) == 0 || \
-         m_off > max_offset )))
+        PTR_GE(m_pos,ip) || \
+        (m_off = (lzo_uint) PTR_DIFF(ip,m_pos)) > max_offset )))
 
 #else
 
