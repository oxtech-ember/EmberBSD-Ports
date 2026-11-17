$NetBSD$

Use the channel-info mapper for the enum chan_width returned by
get_operation_channel_width().  The lower-level frequency mapper expects
enum oper_chan_width; passing CHAN_WIDTH_20 to it incorrectly selects the
80 MHz value and rejects 2.4 GHz Neighbor Report candidates.

Origin: EmberBSD contributors (AI-assisted).

--- wpa_supplicant/wnm_sta.c.orig
+++ wpa_supplicant/wnm_sta.c
@@ -890,7 +890,8 @@ static int wnm_nei_rep_add_bss(struct wpa_supplicant *wpa_s,
 			       u8 pref)
 {
 	u8 op_class, chan;
-	int sec_chan = 0, chanwidth = 0;
+	int sec_chan = 0;
+	enum chan_width chanwidth;
 	struct ieee802_11_elems elems;
 	struct ieee80211_ht_operation *ht_oper;
 	enum phy_type phy_type;
@@ -918,9 +919,8 @@ static int wnm_nei_rep_add_bss(struct wpa_supplicant *wpa_s,
 			sec_chan = -1;
 	}
 
-	if (ieee80211_freq_to_channel_ext(bss->freq, sec_chan, chanwidth,
-					  &op_class, &chan) ==
-	    NUM_HOSTAPD_MODES) {
+	if (ieee80211_chaninfo_to_channel(bss->freq, chanwidth, sec_chan,
+					&op_class, &chan) < 0) {
 		wpa_printf(MSG_DEBUG,
 			   "WNM: Cannot determine operating class and channel");
 		return -2;
