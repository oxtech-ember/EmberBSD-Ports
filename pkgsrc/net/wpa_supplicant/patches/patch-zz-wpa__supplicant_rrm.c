$NetBSD$

The operating-class mapper reports failure as a negative status. Comparing
that status with NUM_HOSTAPD_MODES accepts invalid frequencies and leaves the
output fields unchanged.

--- wpa_supplicant/rrm.c.orig
+++ wpa_supplicant/rrm.c
@@ -775,7 +775,7 @@ int wpas_get_op_chan_phy(int freq, const u8 *ies, size_t ies_len,
 	}
 
 	if (ieee80211_chaninfo_to_channel(freq, chanwidth, sec_chan, op_class,
-					  chan) == NUM_HOSTAPD_MODES) {
+					  chan) < 0) {
 		wpa_printf(MSG_DEBUG,
 			   "Cannot determine operating class and channel");
 		return -1;
