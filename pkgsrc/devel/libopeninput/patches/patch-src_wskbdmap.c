$NetBSD$

* Scan code 0x76 (wscons key 118) is F24 in scan code set 1.  Laptops
  send Control+Super+F24 for the touchpad toggle key, and xkeyboard-config
  maps that to XF86TouchpadToggle.  The XT map had KEY_RESERVED there.
* PC keyboards of many laptops send vendor scan codes that the XT map
  does not know.  Linux maps them with the KEYBOARD_KEY_ properties of the
  systemd hwdb; wscons sends them raw, so the backend dropped them.  The
  backend now reads the *.hwdb files of share/libinput/hwdb.d and then
  of etc/libinput/hwdb.d (see wskbd-hwdb.c) with the DMI modalias of the
  system (machdep.dmi on NetBSD, hw.vendor and hw.product on OpenBSD)
  and applies the matching records to the XT map of the PC keyboards.
* Tested on the host (tests/keyboard-hwdb.sh).

--- src/wskbdmap.c.orig
+++ src/wskbdmap.c
@@ -1,7 +1,11 @@
 #include <sys/ioctl.h>
 #include <sys/types.h>
 #include <sys/time.h>
+#include <sys/sysctl.h>
+#include <stdio.h>
+#include <string.h>
 #include "wscons.h"
+#include "wskbd-hwdb.h"
 #include "input-event-codes.h"
 
 static uint32_t wsUsbMap[] = {
@@ -366,7 +370,7 @@
 	/* 115 */ KEY_RESERVED,
 	/* 116 */ KEY_RESERVED,
 	/* 117 */ KEY_RESERVED,
-	/* 118 */ KEY_RESERVED,
+	/* 118 */ KEY_F24,	/* F24, scan code set 1 */
 	/* 119 */ KEY_RESERVED,
 	/* 120 */ KEY_RESERVED,
 	/* 121 */ KEY_RESERVED,
@@ -496,6 +500,108 @@
     wsXtMap
 };
 
+/*
+ * PC keyboards of many laptops send vendor scan codes.  Linux maps them with
+ * the KEYBOARD_KEY_ properties of the systemd hwdb, selected by the DMI
+ * modalias of the system.  The *.hwdb files of WSKBD_HWDB_DIR (the package
+ * files) and then of WSKBD_HWDB_ETCDIR (local files) give the same
+ * properties here: the XT map with them is used for the PC keyboards.
+ */
+#define WS_XT_HWDB_MAP_SIZE 256
+
+static uint32_t wsXtHwdbMap[WS_XT_HWDB_MAP_SIZE];
+
+static
+struct TransMapRec wsXtHwdb = {
+    0,
+    WS_XT_HWDB_MAP_SIZE,
+    wsXtHwdbMap
+};
+
+#define WSKBD_DMI_FIELDS 11
+#define WSKBD_DMI_LEN 128
+
+/* Read the DMI string NAME into BUF; return BUF, or NULL if not known. */
+static const char *
+wskbd_dmi(const char *name, char *buf)
+{
+	size_t len = WSKBD_DMI_LEN;
+
+#if defined(__NetBSD__)
+	char node[64];
+
+	snprintf(node, sizeof(node), "machdep.dmi.%s", name);
+	if (sysctlbyname(node, buf, &len, NULL, 0) == -1)
+		return NULL;
+#else
+	int mib[2] = { CTL_HW, 0 };
+
+	if (strcmp(name, "system-vendor") == 0)
+		mib[1] = HW_VENDOR;
+	else if (strcmp(name, "system-product") == 0)
+		mib[1] = HW_PRODUCT;
+	else
+		return NULL;
+	if (sysctl(mib, 2, buf, &len, NULL, 0) == -1)
+		return NULL;
+#endif
+	buf[WSKBD_DMI_LEN - 1] = '\0';
+	return buf;
+}
+
+static struct TransMapRec *
+wskbd_xt_map(struct libinput *libinput)
+{
+	static struct TransMapRec *selected;
+	static const char *const names[WSKBD_DMI_FIELDS] = {
+		"bios-vendor", "bios-version", "bios-date", "system-vendor",
+		"system-product", "system-version", "board-vendor",
+		"board-product", "board-version", "chassis-vendor",
+		"chassis-version",
+	};
+	char strings[WSKBD_DMI_FIELDS][WSKBD_DMI_LEN], date[11];
+	char modalias[sizeof(strings) + 64];
+	const char *value[WSKBD_DMI_FIELDS];
+	struct wskbd_hwdb_dmi dmi;
+	size_t i, n;
+
+	/* The system does not change: select the map once. */
+	if (selected != NULL)
+		return selected;
+	selected = &wsXt;
+
+	for (i = 0; i < WSKBD_DMI_FIELDS; i++)
+		value[i] = wskbd_dmi(names[i], strings[i]);
+	/* NetBSD gives YYYYMMDD; the modalias has MM/DD/YYYY. */
+	if (value[2] != NULL && strlen(value[2]) == 8) {
+		snprintf(date, sizeof(date), "%.2s/%.2s/%.4s", value[2] + 4,
+		    value[2] + 6, value[2]);
+		value[2] = date;
+	}
+	dmi = (struct wskbd_hwdb_dmi){
+		.bvn = value[0], .bvr = value[1], .bd = value[2],
+		.svn = value[3], .pn = value[4], .pvr = value[5],
+		.rvn = value[6], .rn = value[7], .rvr = value[8],
+		.cvn = value[9], .cvr = value[10],
+	};
+	if (wskbd_hwdb_modalias(&dmi, modalias, sizeof(modalias)) == -1)
+		return selected;
+
+	/* Codes past the XT map stay KEY_UNKNOWN. */
+	for (i = 0; i < WS_XT_HWDB_MAP_SIZE; i++)
+		wsXtHwdbMap[i] = i < WS_XT_MAP_SIZE ? wsXtMap[i] : KEY_UNKNOWN;
+	n = wskbd_hwdb_apply(WSKBD_HWDB_DIR, modalias, wsXtHwdbMap,
+	    WS_XT_HWDB_MAP_SIZE);
+	n += wskbd_hwdb_apply(WSKBD_HWDB_ETCDIR, modalias, wsXtHwdbMap,
+	    WS_XT_HWDB_MAP_SIZE);
+	if (n == 0)
+		return selected;
+	log_info(libinput, "%zu keyboard scan codes from hwdb for %s\n", n,
+	    modalias);
+	selected = &wsXtHwdb;
+	return selected;
+}
+
 static void
 printWsType(struct libinput *libinput, const char *name, const char *type)
 {
@@ -518,11 +624,11 @@
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
