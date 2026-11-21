// SPDX-License-Identifier: BSD-2-Clause
package device

import (
	"encoding/hex"
	"testing"
	"time"
)

// diagnosticBeforeResponseCommit is injected only into the throw-away test copy.
func TestResponseAfterNewInitiation(t *testing.T) {
	a, b := randDevice(t), randDevice(t)
	defer a.Close()
	defer b.Close()
	pb, err := b.NewPeer(a.staticIdentity.privateKey.publicKey())
	if err != nil {
		t.Fatal(err)
	}
	pa, err := a.NewPeer(b.staticIdentity.privateKey.publicKey())
	if err != nil {
		t.Fatal(err)
	}
	pb.Start()
	pa.Start()
	init, err := a.CreateMessageInitiation(pa)
	if err != nil {
		t.Fatal(err)
	}
	if b.ConsumeMessageInitiation(init) == nil {
		t.Fatal("initiation rejected")
	}
	response, err := b.CreateMessageResponse(pb)
	if err != nil {
		t.Fatal(err)
	}
	diagnosticBeforeResponseCommit = func() {
		diagnosticBeforeResponseCommit = nil
		if _, err := a.CreateMessageInitiation(pa); err != nil {
			t.Fatal(err)
		}
	}
	defer func() { diagnosticBeforeResponseCommit = nil }()
	if a.ConsumeMessageResponse(response) != nil {
		t.Fatal("stale response consumed after new initiation")
	}
	if pa.handshake.state != handshakeInitiationCreated {
		t.Fatal("new handshake was overwritten")
	}
}

func TestIPv6OversizedPayloadRejected(t *testing.T) {
	pair := genTestPair(t, false)
	for i := range pair {
		var peer NoisePublicKey
		for k := range pair[i].dev.peers.keyMap {
			peer = k
			break
		}
		if err := pair[i].dev.IpcSet(uapiCfg("public_key", hex.EncodeToString(peer[:]), "allowed_ip", "2001:db8::/32")); err != nil {
			t.Fatal(err)
		}
	}
	pair.Send(t, Ping, nil)
	pkt := make([]byte, 40)
	pkt[0] = 0x60
	pkt[4] = 0xff
	pkt[5] = 0xff
	copy(pkt[8:24], []byte{0x20, 0x01, 0x0d, 0xb8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1})
	copy(pkt[24:40], []byte{0x20, 0x01, 0x0d, 0xb8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2})
	pair[0].tun.Outbound <- pkt
	select {
	case got := <-pair[1].tun.Inbound:
		t.Fatalf("malformed IPv6 packet delivered: %x", got)
	case <-time.After(time.Second):
	}
}
