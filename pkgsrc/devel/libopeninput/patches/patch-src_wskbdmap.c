$NetBSD$

* Scan code 0x76 (wscons key 118) is F24 in scan code set 1.  Laptops
  send Control+Super+F24 for the touchpad toggle key, and xkeyboard-config
  maps that to XF86TouchpadToggle.  The XT map had KEY_RESERVED there.
* PC keyboards of some vendors send escaped scan codes that the XT map
  does not know.  Linux maps them through the systemd hwdb; wscons sends
  them raw, so the backend dropped them: codes 0x91 and 0xd7 gave
  KEY_RESERVED and 0xf1, past the end of the map, gave KEY_UNKNOWN.
  A small table, selected by the prefixes of the DMI system vendor and
  product (machdep.dmi.system-vendor and system-product on NetBSD,
  hw.vendor and hw.product on OpenBSD), now extends the XT map: on
  Micro-Star laptops Fn+F5 gives KEY_F20 (microphone mute, as in hwdb)
  and Fn+F7 KEY_CONFIG (MSI Center); on the Vector 17 HX AI Fn+F6 gives
  KEY_BLUETOOTH.  Other vendors and models keep the plain XT map.
* Tested on the host (tests/vendor-scan-codes.sh).

--- src/wskbdmap.c.orig
+++ src/wskbdmap.c
@@ -1,6 +1,9 @@
 #include <sys/ioctl.h>
 #include <sys/types.h>
 #include <sys/time.h>
+#include <sys/sysctl.h>
+#include <string.h>
+#include <strings.h>
 #include "wscons.h"
 #include "input-event-codes.h"
 
@@ -366,7 +369,7 @@
 	/* 115 */ KEY_RESERVED,
 	/* 116 */ KEY_RESERVED,
 	/* 117 */ KEY_RESERVED,
-	/* 118 */ KEY_RESERVED,
+	/* 118 */ KEY_F24,	/* F24, scan code set 1 */
 	/* 119 */ KEY_RESERVED,
 	/* 120 */ KEY_RESERVED,
 	/* 121 */ KEY_RESERVED,
@@ -496,6 +499,112 @@
     wsXtMap
 };
 
+/*
+ * Vendor scan codes of PC keyboards.  Linux applies the same codes through
+ * the systemd hwdb; wscons sends them raw, so the table is applied here.
+ * Each entry gives the prefixes of the DMI system vendor and product (any
+ * case; a NULL product matches every model), the wscons key (the escaped
+ * scan code with bit 7 set) and the evdev key.
+ */
+struct wskbd_xt_quirk {
+	const char *vendor;
+	const char *product;
+	int wskey;
+	uint32_t key;
+};
+
+static const struct wskbd_xt_quirk wsXtQuirks[] = {
+	/* Micro-Star laptops: Fn+F7 MSI Center, Fn+F5 microphone mute. */
+	{ "Micro-Star", NULL, 0x91, KEY_CONFIG },
+	{ "Micro-Star", NULL, 0xf1, KEY_F20 },
+	/* Vector 17 HX AI A2XW (product Vector 17 HX AI A2XWJG): Fn+F6. */
+	{ "Micro-Star", "Vector 17 HX AI", 0xd7, KEY_BLUETOOTH },
+};
+
+#define WS_XT_QUIRK_MAP_SIZE 256
+
+static uint32_t wsXtQuirkMap[WS_XT_QUIRK_MAP_SIZE];
+
+static
+struct TransMapRec wsXtQuirk = {
+    0,
+    WS_XT_QUIRK_MAP_SIZE,
+    wsXtQuirkMap
+};
+
+/*
+ * Fill MAP with the XT map and the entries of VENDOR and PRODUCT (NULL
+ * when unknown); codes past the XT map stay KEY_UNKNOWN.  Return the
+ * number of vendor entries; a map without them is not used.
+ */
+static size_t
+wskbd_xt_quirk_map(const char *vendor, const char *product, uint32_t *map,
+    size_t size)
+{
+	size_t i, n = 0;
+
+	for (i = 0; i < size; i++)
+		map[i] = i < WS_XT_MAP_SIZE ? wsXtMap[i] : KEY_UNKNOWN;
+	if (vendor == NULL)
+		return 0;
+	for (i = 0; i < sizeof(wsXtQuirks) / sizeof(*wsXtQuirks); i++) {
+		const struct wskbd_xt_quirk *q = &wsXtQuirks[i];
+
+		if (strncasecmp(vendor, q->vendor, strlen(q->vendor)) != 0)
+			continue;
+		if (q->product != NULL && (product == NULL ||
+		    strncasecmp(product, q->product, strlen(q->product)) != 0))
+			continue;
+		if (q->wskey < 0 || (size_t)q->wskey >= size)
+			continue;
+		map[q->wskey] = q->key;
+		n++;
+	}
+	return n;
+}
+
+static struct TransMapRec *
+wskbd_xt_map(struct libinput *libinput)
+{
+	static struct TransMapRec *selected;
+	char vendor[128], product[128];
+	size_t len = sizeof(vendor), plen = sizeof(product);
+	const char *have_product = product;
+
+	/* The vendor does not change: select the map once. */
+	if (selected != NULL)
+		return selected;
+	selected = &wsXt;
+
+#if defined(__NetBSD__)
+	if (sysctlbyname("machdep.dmi.system-vendor", vendor, &len,
+	    NULL, 0) == -1)
+		return selected;
+	if (sysctlbyname("machdep.dmi.system-product", product, &plen,
+	    NULL, 0) == -1)
+		have_product = NULL;
+#else
+	{
+		int mib[2] = { CTL_HW, HW_VENDOR };
+
+		if (sysctl(mib, 2, vendor, &len, NULL, 0) == -1)
+			return selected;
+		mib[1] = HW_PRODUCT;
+		if (sysctl(mib, 2, product, &plen, NULL, 0) == -1)
+			have_product = NULL;
+	}
+#endif
+	vendor[sizeof(vendor) - 1] = '\0';
+	product[sizeof(product) - 1] = '\0';
+	if (wskbd_xt_quirk_map(vendor, have_product, wsXtQuirkMap,
+	    WS_XT_QUIRK_MAP_SIZE) == 0)
+		return selected;
+	log_info(libinput, "Keyboard scan codes of vendor: %s, product: %s\n",
+	    vendor, have_product != NULL ? have_product : "(unknown)");
+	selected = &wsXtQuirk;
+	return selected;
+}
+
 static void
 printWsType(struct libinput *libinput, const char *name, const char *type)
 {
@@ -518,11 +627,11 @@
 	switch (type) {
 	case WSKBD_TYPE_PC_XT:
 		printWsType(libinput, libinput_device->devname, "XT");
-		device->scanCodeMap = &wsXt;
+		device->scanCodeMap = wskbd_xt_map(libinput);
 		break;
 	case WSKBD_TYPE_PC_AT:
 		printWsType(libinput, libinput_device->devname, "AT");
-		device->scanCodeMap = &wsXt;
+		device->scanCodeMap = wskbd_xt_map(libinput);
 		break;
 	case WSKBD_TYPE_USB:
 		printWsType(libinput, libinput_device->devname, "USB");
