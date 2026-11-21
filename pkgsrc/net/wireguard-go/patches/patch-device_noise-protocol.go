From 2631ce99a06f27120d581611cf125d68bc6aa565 Mon Sep 17 00:00:00 2001
From: "Jason A. Donenfeld" <Jason@zx2c4.com>
Date: Tue, 6 Oct 2026 18:45:05 +0200
Subject: device: noise: reject response consumption after intermediate
 initiation

Two threads begin processing the identical response message, received
twice. The first thread, A, runs. While it's running, the second one, B,
gets partway through, and during that slow calculation, A completes and
then also a handshake initiation that's already been queued up runs in
thread C. The handshake initiation creation succeeds, and sets the state
back to waiting-for-response, at which point thread B resumes. Thread B
then copies the state back to the peer, and begins a new session, using
that state, which is the same session as the one made in thread A.

This seems basically impossible to hit in a meaningful way in practice,
but ensure that it absolutely cannot happen by comparing the ephemeral
private key that's on the stack with the latest one that the peer's
handshake state has.

Signed-off-by: Jason A. Donenfeld <Jason@zx2c4.com>
---
 device/noise-protocol.go | 27 ++++++++++++++++++---------
 1 file changed, 18 insertions(+), 9 deletions(-)

diff --git a/device/noise-protocol.go b/device/noise-protocol.go
index 5cf1702..a0aca36 100644
--- device/noise-protocol.go
+++ device/noise-protocol.go
@@ -509,7 +509,7 @@ func (device *Device) CreateMessageResponse(peer *Peer) (*MessageResponse, error
 	return &msg, nil
 }
 
-func (device *Device) ConsumeMessageResponse(msg *MessageResponse) *Peer {
+func (device *Device) ConsumeMessageResponse(msg *MessageResponse) (peer *Peer) {
 	if msg.Type != MessageResponseType {
 		return nil
 	}
@@ -523,8 +523,9 @@ func (device *Device) ConsumeMessageResponse(msg *MessageResponse) *Peer {
 	}
 
 	var (
-		hash     [blake2s.Size]byte
-		chainKey [blake2s.Size]byte
+		hash           [blake2s.Size]byte
+		chainKey       [blake2s.Size]byte
+		localEphemeral NoisePrivateKey
 	)
 
 	ok := func() bool {
@@ -582,6 +583,10 @@ func (device *Device) ConsumeMessageResponse(msg *MessageResponse) *Peer {
 			return false
 		}
 		mixHash(&hash, &hash, msg.Empty[:])
+
+		// allow unlocking temporarily
+		copy(localEphemeral[:], handshake.localEphemeral[:])
+
 		return true
 	}()
 
@@ -592,18 +597,22 @@ func (device *Device) ConsumeMessageResponse(msg *MessageResponse) *Peer {
 	// update handshake state
 
 	handshake.mutex.Lock()
-
-	handshake.hash = hash
-	handshake.chainKey = chainKey
-	handshake.remoteIndex = msg.Sender
-	handshake.state = handshakeResponseConsumed
+	if handshake.state == handshakeInitiationCreated &&
+		handshake.localEphemeral.Equals(localEphemeral) {
+		handshake.hash = hash
+		handshake.chainKey = chainKey
+		handshake.remoteIndex = msg.Sender
+		handshake.state = handshakeResponseConsumed
+		peer = lookup.peer
+	}
 
 	handshake.mutex.Unlock()
 
 	setZero(hash[:])
 	setZero(chainKey[:])
+	setZero(localEphemeral[:])
 
-	return lookup.peer
+	return
 }
 
 /* Derives a new keypair from the current handshake state
-- 
cgit v1.3-18-gd494

