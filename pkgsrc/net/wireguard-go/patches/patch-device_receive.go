From b3bc704ef0ee21a36298601a9e1e5ff90377ac52 Mon Sep 17 00:00:00 2001
From: "Jason A. Donenfeld" <Jason@zx2c4.com>
Date: Sun, 25 Oct 2026 00:09:52 +0200
Subject: device: don't overflow uint16 when adding v4 header length

Signed-off-by: Jason A. Donenfeld <Jason@zx2c4.com>
---
 device/receive.go | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

diff --git a/device/receive.go b/device/receive.go
index 1392957..6f9d90a 100644
--- device/receive.go
+++ device/receive.go
@@ -490,7 +490,7 @@ func (peer *Peer) RoutineSequentialReceiver(maxBatchSize int) {
 					continue
 				}
 				field := elem.packet[IPv6offsetPayloadLength : IPv6offsetPayloadLength+2]
-				length := binary.BigEndian.Uint16(field)
+				length := uint32(binary.BigEndian.Uint16(field))
 				length += ipv6.HeaderLen
 				if int(length) > len(elem.packet) {
 					continue
-- 
cgit v1.3-18-gd494

