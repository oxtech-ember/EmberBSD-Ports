$NetBSD: patch-tun_tun__netbsd.go,v 1.1 2023/12/14 13:56:23 adam Exp $

Enable multi-af mode without changing the Go file descriptor to blocking.

--- tun/tun_netbsd.go.orig
+++ tun/tun_netbsd.go
@@ -25,7 +25,7 @@
 	Pad0 [12]byte
 }
 
-const _TUNSIFMODE = 0x8004745d
+const _TUNSIFHEAD = 0x80047442
 
 type NativeTun struct {
 	name        string
@@ -129,6 +129,30 @@
 	}
 
 	tun, err := CreateTUNFromFile(tunfile, mtu)
+
+	if err != nil {
+		return nil, err
+	}
+	// Fd() restores blocking mode on Go's pollable os.File. Use Control so
+	// the TUN read can be cancelled by Close without blocking shutdown.
+	raw, err := tunfile.SyscallConn()
+	if err != nil {
+		tun.Close()
+		return nil, err
+	}
+	ifheadmode := int32(1)
+	var ioctlErr syscall.Errno
+	err = raw.Control(func(fd uintptr) {
+		_, _, ioctlErr = unix.Syscall(unix.SYS_IOCTL, fd,
+			uintptr(_TUNSIFHEAD), uintptr(unsafe.Pointer(&ifheadmode)))
+	})
+	if err != nil || ioctlErr != 0 {
+		tun.Close()
+		if err != nil {
+			return nil, fmt.Errorf("TUN ioctl control: %w", err)
+		}
+		return nil, fmt.Errorf("enable TUN multi-af mode: %w", ioctlErr)
+	}
 
 	if err == nil && name == "tun" {
 		fname := os.Getenv("WG_TUN_NAME_FILE")
