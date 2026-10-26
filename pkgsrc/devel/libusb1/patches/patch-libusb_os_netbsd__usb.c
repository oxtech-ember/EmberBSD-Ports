$NetBSD$

Add explicit continuous BULK-IN read-ahead and repair endpoint ownership.
Origin: EmberBSD, local adaptation with Codex assistance.
Default transfers retain their synchronous behavior.

--- libusb/os/netbsd_usb.c.orig
+++ libusb/os/netbsd_usb.c
@@ -41,6 +41,8 @@
 
 struct handle_priv {
 	int endpoints[USB_MAX_ENDPOINTS];
+	uint16_t bulk_read_ahead;
+	uint16_t bulk_read_ahead_enabled;
 };
 
 /*
@@ -190,12 +192,62 @@
 	return _errno_to_libusb(err);
 }
 
+/* Parse once per handle; only explicitly selected continuous IN streams. */
+static int
+_parse_bulk_read_ahead(const char *value, uint16_t *mask)
+{
+	unsigned int endpoint;
+
+	*mask = 0;
+	if (value == NULL)
+		return LIBUSB_SUCCESS;
+	for (;;) {
+		if (value[0] != '8')
+			return LIBUSB_ERROR_INVALID_PARAM;
+		if (value[1] >= '1' && value[1] <= '9')
+			endpoint = (unsigned int)(value[1] - '0');
+		else if (value[1] >= 'a' && value[1] <= 'f')
+			endpoint = (unsigned int)(value[1] - 'a') + 10;
+		else if (value[1] >= 'A' && value[1] <= 'F')
+			endpoint = (unsigned int)(value[1] - 'A') + 10;
+		else
+			return LIBUSB_ERROR_INVALID_PARAM;
+		if (*mask & (1U << endpoint))
+			return LIBUSB_ERROR_INVALID_PARAM;
+		*mask |= (uint16_t)(1U << endpoint);
+		value += 2;
+		if (*value == '\0')
+			return LIBUSB_SUCCESS;
+		if (*value++ != ',')
+			return LIBUSB_ERROR_INVALID_PARAM;
+	}
+}
+
+static void
+_close_endpoints(struct handle_priv *hpriv)
+{
+	int i;
+
+	for (i = 0; i < USB_MAX_ENDPOINTS; i++) {
+		if (hpriv->endpoints[i] >= 0)
+			close(hpriv->endpoints[i]);
+		hpriv->endpoints[i] = -1;
+	}
+	hpriv->bulk_read_ahead_enabled = 0;
+}
+
 int
 netbsd_open(struct libusb_device_handle *handle)
 {
 	struct device_priv *dpriv = usbi_get_device_priv(handle->dev);
 	struct handle_priv *hpriv = usbi_get_device_handle_priv(handle);
-	int i;
+	int i, err;
+
+	err = _parse_bulk_read_ahead(getenv("LIBUSB_NETBSD_BULK_READAHEAD"),
+	    &hpriv->bulk_read_ahead);
+	if (err)
+		return err;
+	hpriv->bulk_read_ahead_enabled = 0;
 
 	dpriv->fd = open(dpriv->devnode, O_RDWR);
 	if (dpriv->fd < 0) {
@@ -219,7 +271,9 @@
 
 	usbi_dbg(HANDLE_CTX(handle), "close: fd %d", dpriv->fd);
 
-	close(dpriv->fd);
+	_close_endpoints(usbi_get_device_handle_priv(handle));
+	if (dpriv->fd >= 0)
+		close(dpriv->fd);
 	dpriv->fd = -1;
 }
 
@@ -308,12 +362,9 @@
 netbsd_claim_interface(struct libusb_device_handle *handle, uint8_t iface)
 {
 	struct handle_priv *hpriv = usbi_get_device_handle_priv(handle);
-	int i;
 
 	UNUSED(iface);
-
-	for (i = 0; i < USB_MAX_ENDPOINTS; i++)
-		hpriv->endpoints[i] = -1;
+	_close_endpoints(hpriv);
 
 	return LIBUSB_SUCCESS;
 }
@@ -322,13 +373,9 @@
 netbsd_release_interface(struct libusb_device_handle *handle, uint8_t iface)
 {
 	struct handle_priv *hpriv = usbi_get_device_handle_priv(handle);
-	int i;
 
 	UNUSED(iface);
-
-	for (i = 0; i < USB_MAX_ENDPOINTS; i++)
-		if (hpriv->endpoints[i] >= 0)
-			close(hpriv->endpoints[i]);
+	_close_endpoints(hpriv);
 
 	return LIBUSB_SUCCESS;
 }
@@ -572,14 +619,49 @@
 		snprintf(s, 4, ".%02d", endpt);
 
 		/* We may need to read/write to the same endpoint later. */
-		if (((fd = open(devnode, O_RDWR)) < 0) && (errno == ENXIO))
-			if ((fd = open(devnode, mode)) < 0)
-				return -1;
+		fd = open(devnode, O_RDWR);
+		if (fd < 0 && errno == ENXIO)
+			fd = open(devnode, mode);
+		if (fd < 0)
+			return -1;
 
 		hpriv->endpoints[endpt] = fd;
 	}
 
 	return hpriv->endpoints[endpt];
+}
+
+/* ugen read-ahead has byte-stream semantics, not USB packet boundaries. */
+static int
+_configure_bulk_read_ahead(struct libusb_transfer *transfer, int fd)
+{
+	struct handle_priv *hpriv;
+	struct usb_bulk_ra_wb_opt opt;
+	unsigned int endpoint;
+	uint16_t bit;
+	int enable = 1, error;
+
+	if (transfer->type != LIBUSB_TRANSFER_TYPE_BULK || !IS_XFERIN(transfer))
+		return 0;
+	hpriv = usbi_get_device_handle_priv(transfer->dev_handle);
+	endpoint = UE_GET_ADDR(transfer->endpoint);
+	bit = (uint16_t)(1U << endpoint);
+	if (!(hpriv->bulk_read_ahead & bit) ||
+	    (hpriv->bulk_read_ahead_enabled & bit))
+		return 0;
+	opt.ra_wb_buffer_size = 1024U * 1024U;
+	opt.ra_wb_request_size = 64U * 1024U;
+	if (ioctl(fd, USB_SET_BULK_RA_OPT, &opt) < 0 ||
+	    ioctl(fd, USB_SET_BULK_RA, &enable) < 0) {
+		error = errno;
+		close(fd);
+		hpriv->endpoints[endpoint] = -1;
+		hpriv->bulk_read_ahead_enabled &= (uint16_t)~bit;
+		errno = error;
+		return -1;
+	}
+	hpriv->bulk_read_ahead_enabled |= bit;
+	return 0;
 }
 
 int
@@ -596,6 +678,8 @@
 	 */
 	if ((fd = _access_endpoint(transfer)) < 0)
 		return _errno_to_libusb(errno);
+	if (_configure_bulk_read_ahead(transfer, fd) < 0)
+		return _errno_to_libusb(errno);
 
 	if (ioctl(fd, USB_SET_TIMEOUT, &transfer->timeout) < 0)
 		return _errno_to_libusb(errno);
