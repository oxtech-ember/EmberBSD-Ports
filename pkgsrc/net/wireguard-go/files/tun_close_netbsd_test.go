// SPDX-License-Identifier: BSD-2-Clause
//go:build netbsd

package tun

import (
	"errors"
	"os"
	"testing"
	"time"
)

// Requires a disposable, already-created tunN interface with no traffic.
// Run with WIREGUARD_TEST_TUN=tunN go test -timeout 15s ./tun -run TestNetBSDReadClose.
func TestNetBSDReadClose(t *testing.T) {
	name := os.Getenv("WIREGUARD_TEST_TUN")
	if name == "" {
		t.Skip("WIREGUARD_TEST_TUN is not set")
	}
	dev, err := CreateTUN(name, 1420)
	if err != nil {
		t.Fatal(err)
	}
	readDone := make(chan error, 1)
	go func() {
		bufs := [][]byte{make([]byte, 2048)}
		sizes := make([]int, 1)
		_, err := dev.Read(bufs, sizes, 4)
		readDone <- err
	}()
	// No test traffic: allow Read to enter its wait before closing.
	time.Sleep(200 * time.Millisecond)
	select {
	case err := <-readDone:
		t.Fatalf("idle TUN read returned before Close: %v", err)
	default:
	}
	closeDone := make(chan error, 1)
	go func() { closeDone <- dev.Close() }()
	select {
	case err := <-closeDone:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(3 * time.Second):
		t.Fatal("Close blocked with an idle TUN read")
	}
	select {
	case err := <-readDone:
		if !errors.Is(err, os.ErrClosed) {
			t.Fatalf("TUN read after Close: got %v, want os.ErrClosed", err)
		}
	case <-time.After(3 * time.Second):
		t.Fatal("TUN read did not stop after Close")
	}
}
