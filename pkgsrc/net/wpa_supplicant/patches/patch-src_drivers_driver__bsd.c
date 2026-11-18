$NetBSD$

Origin: EmberBSD BSD net80211 adapter; retains the OS SAE/key-epoch and platform lifecycle paths, with the shared WPA 2.12 RRM and controlled-port contract.

--- src/drivers/driver_bsd.c.orig
+++ src/drivers/driver_bsd.c
@@ -76,12 +76,27 @@
 	u32 sae_generation;
 	u8 sae_bssid[ETH_ALEN];
 	int sae_active;
+	int sae_configured;
+	int sae_blocked;
+#ifdef IEEE80211_SAE_CAP_KEY_EPOCH
+	int sae_key_epoch;
+#endif
 #ifdef IEEE80211_SAE_CAP_SA_QUERY
 	int sae_query;
 #endif
 #endif
+#if defined(__NetBSD__) && defined(IEEE80211_MLME_VERSION) && \
+    defined(IEEE80211_ASSOC_EVENT_VERSION)
+	uint64_t sta_assoc_epoch;
+	uint64_t sta_assoc_retired_epoch;
+	u8 sta_assoc_bssid[ETH_ALEN];
+	int sta_assoc_versioned;
+#endif
 #if !defined(HOSTAPD) && defined(__NetBSD__) && defined(IEEE80211_IOC_STA_MGMT)
 	int sta_btm;
+	int sta_nr;
+	int sta_rm_request_rx;
+	int sta_rm_report_tx;
 	int sta_rrm;
 	int sta_scan;
 	int sta_enabled;
@@ -105,7 +120,11 @@
 
 #if !defined(HOSTAPD) && defined(__NetBSD__) && defined(IEEE80211_IOC_STA_MGMT)
 static void bsd_sta_scan_clear(struct bsd_driver_data *);
-static void bsd_sta_tx_status(struct bsd_driver_data *, int, int);
+static void bsd_sta_tx_status(struct bsd_driver_data *, int, int, int, int);
+#endif
+#if defined(__NetBSD__) && defined(IEEE80211_MLME_VERSION) && \
+    defined(IEEE80211_ASSOC_EVENT_VERSION)
+static void bsd_sta_epoch_reset(struct bsd_driver_data *);
 #endif
 
 /* Generic functions for hostapd and wpa_supplicant */
@@ -197,6 +216,16 @@
 set80211var(struct bsd_driver_data *drv, int op, const void *arg, int arg_len)
 {
 	return bsd_set80211(drv, op, 0, arg, arg_len);
+}
+
+static int
+bsd_set_mlme(struct bsd_driver_data *drv, struct ieee80211req_mlme *mlme)
+{
+#if defined(__NetBSD__) && defined(IEEE80211_MLME_VERSION)
+	mlme->im_version = IEEE80211_MLME_VERSION;
+	mlme->im_assoc_epoch = 0;
+#endif
+	return bsd_set80211(drv, IEEE80211_IOC_MLME, 0, mlme, sizeof(*mlme));
 }
 
 static int
@@ -297,6 +326,16 @@
 	media = requested;
 	if (bsd_set_if_media(priv, media) < 0)
 		return -1;
+	return 0;
+}
+
+static int
+bsd_set_opmode(struct bsd_driver_data *drv, uint32_t media_mode,
+	    enum ieee80211_opmode opmode)
+{
+	if (bsd_set_mediaopt(drv, IFM_OMASK, media_mode) < 0)
+		return -1;
+	drv->opmode = opmode;
 	return 0;
 }
 
@@ -323,6 +362,54 @@
 }
 
 #ifndef HOSTAPD
+/* Keep the retiring token until the kernel acknowledges CONFIGURE-off. */
+static int
+bsd_sae_disable(struct bsd_driver_data *drv)
+{
+	u8 disabled = 0;
+
+	drv->sae_active = 0;
+	if (!drv->sae_configured)
+		return 0;
+	drv->sae_blocked = 1;
+	if (drv->ifindex && !drv->if_removed &&
+	    bsd_sae_request(drv, IEEE80211_SAE_CONFIGURE, &disabled, 1) < 0)
+		return -1;
+	drv->sae_configured = 0;
+	os_memset(drv->sae_bssid, 0, sizeof(drv->sae_bssid));
+	return 0;
+}
+
+static int
+bsd_sae_enable(struct bsd_driver_data *drv, const u8 *bssid)
+{
+	u32 generation;
+	u8 enabled = 1;
+	unsigned int i;
+
+	/* The equality token must not restart deterministically at one. A 32-bit
+	 * ABI still has a collision bound; kernel queue lifetimes use their own
+	 * serial. Never substitute a predictable token when entropy fails. */
+	for (i = 0; i < 8; i++) {
+		if (os_get_random((u8 *) &generation, sizeof(generation)) < 0)
+			return -1;
+		if (generation && generation != drv->sae_generation)
+			break;
+	}
+	if (i == 8)
+		return -1;
+	drv->sae_generation = generation;
+	os_memcpy(drv->sae_bssid, bssid, ETH_ALEN);
+	/* CONFIGURE-on is atomic: failure does not install this generation. */
+	if (bsd_sae_request(drv, IEEE80211_SAE_CONFIGURE, &enabled, 1) < 0) {
+		os_memset(drv->sae_bssid, 0, sizeof(drv->sae_bssid));
+		return -1;
+	}
+	drv->sae_configured = 1;
+	drv->sae_active = 1;
+	return 0;
+}
+
 static int
 bsd_sae_send_mlme(void *priv, const u8 *data, size_t len, int noack,
 		  unsigned int freq, const u16 *csa_offs, size_t csa_offs_len,
@@ -330,6 +417,11 @@
 {
 	struct bsd_driver_data *drv = priv;
 
+	(void) noack;
+	(void) freq;
+	(void) csa_offs;
+	(void) no_encrypt;
+	(void) wait;
 	if (!drv->sae_active || len < 30 || WPA_GET_LE16(data) != 0xb0 ||
 	    csa_offs_len || link_id >= 0)
 		return -1;
@@ -340,11 +432,21 @@
 static int
 bsd_sae_send_action(void *priv, unsigned int freq, unsigned int wait,
 		    const u8 *dst, const u8 *src, const u8 *bssid,
-		    const u8 *data, size_t data_len, int no_cck)
+		    const u8 *data, size_t data_len, int no_cck
+#ifdef WPA_DRIVER_FLAGS2_P2P_FEATURE_V2
+		    , int link_id
+#endif
+		    )
 {
 	struct bsd_driver_data *drv = priv;
 	u8 frame[28] = { 0xd0 };
 
+	(void) freq;
+	(void) no_cck;
+#ifdef WPA_DRIVER_FLAGS2_P2P_FEATURE_V2
+	if (link_id >= 0)
+		return -1;
+#endif
 	/* On-channel SA Query only; the kernel requires the current station PTK. */
 	if (!drv->sae_active || !drv->sae_query || wait || data_len != 4 ||
 	    data[0] != WLAN_ACTION_SA_QUERY || data[1] > 1 ||
@@ -382,12 +484,14 @@
 	struct ieee80211req_del_key wk;
 #if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
 	struct bsd_driver_data *drv = priv;
+	if (!drv->sae_active && drv->sae_blocked)
+		return -1;
 	if (key_idx == 4 || key_idx == 5) {
-		u8 index[2];
+		u8 key_id[2];
 		if (!drv->sae_active)
 			return 0;
-		WPA_PUT_LE16(index, key_idx);
-		return bsd_sae_request(drv, IEEE80211_SAE_DELETE_IGTK, index, sizeof(index));
+		WPA_PUT_LE16(key_id, key_idx);
+		return bsd_sae_request(drv, IEEE80211_SAE_DELETE_IGTK, key_id, sizeof(key_id));
 	}
 #endif
 
@@ -403,6 +507,12 @@
 		wk.idk_keyix = (u_int8_t) IEEE80211_KEYIX_NONE;	/* XXX */
 	}
 
+#if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE) && \
+    defined(IEEE80211_SAE_CAP_KEY_EPOCH)
+	if (drv->sae_active && drv->sae_key_epoch) {
+		return bsd_sae_request(drv, IEEE80211_SAE_DELETE_KEY, &wk, sizeof(wk));
+	}
+#endif
 	return set80211var(priv, IEEE80211_IOC_DELKEY, &wk, sizeof(wk));
 }
 
@@ -417,7 +527,7 @@
 	os_memcpy(mlme.im_macaddr, addr, IEEE80211_ADDR_LEN);
 	wpa_printf(MSG_DEBUG, "%s: op=%d reason=%d addr=" MACSTR, __func__,
 	    op, reason, MAC2STR(addr));
-	return set80211var(priv, IEEE80211_IOC_MLME, &mlme, sizeof(mlme));
+	return bsd_set_mlme(priv, &mlme);
 }
 
 static int
@@ -452,8 +562,23 @@
 	size_t seq_len = params->seq_len;
 	const u8 *key = params->key;
 	size_t key_len = params->key_len;
-
-	if (params->key_flag & KEY_FLAG_NEXT)
+	int ret;
+
+#if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
+	struct bsd_driver_data *sae_drv = priv;
+
+	if (!sae_drv->sae_active && sae_drv->sae_blocked)
+		return -1;
+#ifdef IEEE80211_SAE_CAP_KEY_EPOCH
+	if (sae_drv->sae_active && sae_drv->sae_key_epoch &&
+	    (params->link_id >= 0 ||
+	    (alg != WPA_ALG_NONE && alg != WPA_ALG_BIP_CMAC_128 &&
+	    (alg != WPA_ALG_CCMP || key_len != 16 || seq_len > 6))))
+		return -1;
+#endif
+#endif
+	if (key_len > sizeof(wk.ik_keydata) || seq_len > sizeof(wk.ik_keyrsc) ||
+	    (key_len && !key) || (seq_len && !seq))
 		return -1;
 
 	wpa_printf(MSG_DEBUG, "%s: alg=%d addr=%p key_idx=%d set_tx=%d "
@@ -471,9 +596,7 @@
 
 #if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
 	if (alg == WPA_ALG_BIP_CMAC_128) {
-		struct bsd_driver_data *sae_drv = priv;
 		u8 material[24];
-		int ret;
 
 		if (!sae_drv->sae_active || key_len != 16 || seq_len != 6 ||
 		    (key_idx != 4 && key_idx != 5))
@@ -554,7 +677,15 @@
 	}
 	os_memcpy(wk.ik_keydata, key, key_len);
 
-	return set80211var(priv, IEEE80211_IOC_WPAKEY, &wk, sizeof(wk));
+#if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE) && \
+    defined(IEEE80211_SAE_CAP_KEY_EPOCH)
+	if (sae_drv->sae_active && sae_drv->sae_key_epoch)
+		ret = bsd_sae_request(sae_drv, IEEE80211_SAE_SET_KEY, &wk, sizeof(wk));
+	else
+#endif
+		ret = set80211var(priv, IEEE80211_IOC_WPAKEY, &wk, sizeof(wk));
+	forced_memzero(&wk, sizeof(wk));
+	return ret;
 }
 
 static int
@@ -805,6 +936,10 @@
 			wpa_printf(MSG_DEBUG,
 				   "RTM_IFANNOUNCE: Interface '%s' added",
 				   drv->ifname);
+#if defined(__NetBSD__) && defined(IEEE80211_MLME_VERSION) && \
+    defined(IEEE80211_ASSOC_EVENT_VERSION)
+			bsd_sta_epoch_reset(drv);
+#endif
 			drv->ifindex = sdl->sdl_index;
 			drv->if_removed = 0;
 			event.interface_status.ievent = EVENT_INTERFACE_ADDED;
@@ -858,7 +993,7 @@
 				   drv->ifname);
 #if !defined(HOSTAPD) && defined(__NetBSD__) && defined(IEEE80211_IOC_STA_MGMT)
 			bsd_sta_scan_clear(drv);
-			bsd_sta_tx_status(drv, 0, 0);
+			bsd_sta_tx_status(drv, 0, 0, 0, 0);
 #endif
 			wpa_supplicant_event(drv->ctx, EVENT_INTERFACE_DISABLED,
 					     NULL);
@@ -959,7 +1094,8 @@
 static void bsd_sta_tx_timeout(void *eloop_ctx, void *timeout_ctx);
 
 static void
-bsd_sta_tx_status(struct bsd_driver_data *drv, int ack, int notify)
+bsd_sta_tx_status(struct bsd_driver_data *drv, int ack, int ack_known,
+                  int tx_error, int notify)
 {
 	union wpa_event_data event;
 	u8 *frame = drv->sta_tx_frame;
@@ -972,18 +1108,20 @@
 	drv->sta_tx_len = 0;
 	if (notify) {
 		wpa_printf(MSG_DEBUG,
-			   "BSD: STA TX status cookie=%u generation=%u freq=%u category=%d action=%d token=%d ack=%d",
+			   "BSD: STA TX status cookie=%u generation=%u freq=%u category=%d action=%d token=%d ack_known=%d ack=%d tx_error=%d",
 			   drv->sta_cookie, drv->sta_tx_generation, drv->sta_tx_freq,
 			   len >= 27 ? frame[24] : -1,
 			   len >= 27 ? frame[25] : -1,
-			   len >= 27 ? frame[26] : -1, ack);
+			   len >= 27 ? frame[26] : -1, ack_known, ack, tx_error);
 		os_memset(&event, 0, sizeof(event));
 		event.tx_status.type = WLAN_FC_TYPE_MGMT;
 		event.tx_status.stype = WLAN_FC_STYPE_ACTION;
 		event.tx_status.dst = frame + 4;
 		event.tx_status.data = frame;
 		event.tx_status.data_len = len;
-		event.tx_status.ack = ack;
+		event.tx_status.ack = ack_known && ack;
+		event.tx_status.ack_known = ack_known;
+		event.tx_status.tx_error = tx_error;
 		event.tx_status.link_id = -1;
 		wpa_supplicant_event(drv->ctx, EVENT_TX_STATUS, &event);
 	}
@@ -996,7 +1134,7 @@
 	union wpa_event_data event;
 	int aborted = drv->sta_scan_pending;
 
-	bsd_sta_tx_status(drv, 0, 0);
+	bsd_sta_tx_status(drv, 0, 0, 0, 0);
 	bsd_sta_scan_clear(drv);
 	wpa_supplicant_event(drv->ctx, EVENT_DISASSOC, NULL);
 	if (aborted) {
@@ -1021,7 +1159,7 @@
 	os_memcpy(req.bssid, drv->sta_tx_frame + 4, ETH_ALEN);
 	bsd_sta_set(drv, &req, IEEE80211_STA_CANCEL_TX);
 	wpa_printf(MSG_DEBUG, "BSD: station action TX completion timed out");
-	bsd_sta_tx_status(drv, 0, 1);
+	bsd_sta_tx_status(drv, 0, 0, ETIMEDOUT, 1);
 }
 
 static int
@@ -1034,30 +1172,39 @@
 		    (data[1] == WNM_BSS_TRANS_MGMT_QUERY ||
 		     (data[1] == WNM_BSS_TRANS_MGMT_RESP && len >= 5));
 	if (data[0] == WLAN_ACTION_RADIO_MEASUREMENT)
-		return drv->sta_rrm &&
-		    (data[1] == WLAN_RRM_NEIGHBOR_REPORT_REQUEST ||
-		     data[1] == WLAN_RRM_RADIO_MEASUREMENT_REPORT);
+		return (data[1] == WLAN_RRM_NEIGHBOR_REPORT_REQUEST &&
+			drv->sta_nr) ||
+		    (data[1] == WLAN_RRM_RADIO_MEASUREMENT_REPORT &&
+			drv->sta_rm_report_tx);
 	return 0;
 }
 
 static int
 bsd_send_action(void *priv, unsigned int freq, unsigned int wait,
 		const u8 *dst, const u8 *src, const u8 *bssid,
-		const u8 *data, size_t data_len, int no_cck, int link_id)
+		const u8 *data, size_t data_len, int no_cck
+#ifdef WPA_DRIVER_FLAGS2_P2P_FEATURE_V2
+		, int link_id
+#endif
+		)
 {
 	struct bsd_driver_data *drv = priv;
 	struct ieee80211req_sta_mgmt req;
 	u8 *frame;
 
-	/* This backend does not support multi-link operations. */
-	if (link_id != -1)
-		return -1;
-
+#ifdef WPA_DRIVER_FLAGS2_P2P_FEATURE_V2
+	if (link_id >= 0)
+		return -1;
+#endif
 #if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE) && \
     defined(IEEE80211_SAE_CAP_SA_QUERY)
 	if (data_len > 0 && data[0] == WLAN_ACTION_SA_QUERY)
 		return bsd_sae_send_action(priv, freq, wait, dst, src, bssid,
-					   data, data_len, no_cck);
+					   data, data_len, no_cck
+#ifdef WPA_DRIVER_FLAGS2_P2P_FEATURE_V2
+					   , link_id
+#endif
+					   );
 #endif
 	if (drv->sta_tx_frame || data_len > sizeof(req.data) ||
 	    !bsd_sta_tx_body(drv, data, data_len) ||
@@ -1091,7 +1238,7 @@
 	if (eloop_register_timeout(2, 0, bsd_sta_tx_timeout, drv, (void *) (uintptr_t) drv->sta_cookie) < 0) {
 		req.len = 0;
 		bsd_sta_set(drv, &req, IEEE80211_STA_CANCEL_TX);
-		bsd_sta_tx_status(drv, 0, 0);
+		bsd_sta_tx_status(drv, 0, 0, 0, 0);
 		return -1;
 	}
 	return 0;
@@ -1106,9 +1253,10 @@
 		return drv->sta_btm && len >= 7 &&
 		    data[1] == WNM_BSS_TRANS_MGMT_REQ;
 	if (data[0] == WLAN_ACTION_RADIO_MEASUREMENT)
-		return drv->sta_rrm &&
-		    (data[1] == WLAN_RRM_NEIGHBOR_REPORT_RESPONSE ||
-		     (data[1] == WLAN_RRM_RADIO_MEASUREMENT_REQUEST && len >= 5));
+		return (data[1] == WLAN_RRM_NEIGHBOR_REPORT_RESPONSE &&
+			drv->sta_nr) ||
+		    (data[1] == WLAN_RRM_RADIO_MEASUREMENT_REQUEST && len >= 5 &&
+			drv->sta_rm_request_rx);
 	return 0;
 }
 
@@ -1131,7 +1279,7 @@
 		return;
 	if (what == RTM_IEEE80211_STA_SCAN) {
 		if (!drv->sta_scan || !drv->sta_scan_pending ||
-		    req->op != IEEE80211_STA_SCAN || req->len ||
+		    req->op != IEEE80211_STA_SCAN || req->len || req->tx_error ||
 		    (req->flags & ~IEEE80211_STA_SCAN_ABORTED) ||
 		    req->cookie != drv->sta_scan_cookie ||
 		    req->generation != drv->sta_scan_epoch ||
@@ -1158,15 +1306,24 @@
 		return;
 	if (what == RTM_IEEE80211_STA_TX) {
 		if (req->op == IEEE80211_STA_TX && !req->len &&
-		    !(req->flags & ~IEEE80211_STA_TX_ACK) && drv->sta_tx_frame &&
+		    !(req->flags & ~(IEEE80211_STA_TX_ACK |
+				     IEEE80211_STA_TX_ACK_KNOWN)) &&
+		    (!(req->flags & IEEE80211_STA_TX_ACK) ||
+		     (req->flags & IEEE80211_STA_TX_ACK_KNOWN)) &&
+		    req->tx_error >= 0 &&
+		    (!req->tx_error || !req->flags) && drv->sta_tx_frame &&
 		    req->cookie == drv->sta_cookie &&
 		    req->generation == drv->sta_tx_generation &&
 		    req->freq == drv->sta_tx_freq &&
 		    !os_memcmp(req->bssid, drv->sta_tx_frame + 4, ETH_ALEN))
-			bsd_sta_tx_status(drv, !!(req->flags & IEEE80211_STA_TX_ACK), 1);
+			bsd_sta_tx_status(drv,
+				!!(req->flags & IEEE80211_STA_TX_ACK),
+				!!(req->flags & IEEE80211_STA_TX_ACK_KNOWN),
+				req->tx_error, 1);
 		return;
 	}
 	if (what != RTM_IEEE80211_STA_RX || req->op != IEEE80211_STA_GET ||
+	    req->tx_error ||
 	    req->cookie || req->flags ||
 	    !bsd_sta_rx_body(drv, req->data, req->len))
 		return;
@@ -1208,10 +1365,21 @@
 		drv->sta_extcap_mask[2] = 0x02;
 		wpa_printf(MSG_DEBUG, "BSD: host-managed BSS transitions available");
 	}
-	if (info.flags & IEEE80211_STA_CAP_RRM) {
-		drv->sta_rrm = 1;
+	drv->sta_nr = !!(info.flags & IEEE80211_STA_CAP_NR);
+	drv->sta_rm_request_rx =
+		!!(info.flags & IEEE80211_STA_CAP_RM_REQUEST_RX);
+	drv->sta_rm_report_tx =
+		!!(info.flags & IEEE80211_STA_CAP_RM_REPORT_TX);
+	drv->sta_rrm = drv->sta_nr || drv->sta_rm_request_rx ||
+		drv->sta_rm_report_tx;
+	if (drv->sta_nr)
 		drv->capa.rrm_flags |= WPA_DRIVER_FLAGS_SUPPORT_RRM |
-		    WPA_DRIVER_FLAGS_RRM_NEIGHBOR_REPORT_ONLY;
+			WPA_DRIVER_FLAGS_RRM_NEIGHBOR_REPORT;
+	if (drv->sta_rm_request_rx && drv->sta_rm_report_tx) {
+		drv->capa.rrm_flags |= WPA_DRIVER_FLAGS_SUPPORT_RRM;
+		wpa_printf(MSG_DEBUG, "BSD: host-managed radio measurement transport available");
+	} else if (drv->sta_nr) {
+		drv->capa.rrm_flags |= WPA_DRIVER_FLAGS_RRM_NEIGHBOR_REPORT_ONLY;
 		wpa_printf(MSG_DEBUG, "BSD: host-managed neighbor reports available");
 	}
 }
@@ -1257,7 +1425,7 @@
 	    (params->key_mgmt_suite == WPA_KEY_MGMT_PSK ||
 	     (params->key_mgmt_suite == WPA_KEY_MGMT_SAE &&
 	      params->mgmt_frame_protection == MGMT_FRAME_PROTECTION_REQUIRED));
-	bsd_sta_tx_status(drv, 0, 0);
+	bsd_sta_tx_status(drv, 0, 0, 0, 0);
 	bsd_sta_scan_clear(drv);
 	drv->sta_enabled = 0;
 	os_memset(&req, 0, sizeof(req));
@@ -1268,6 +1436,85 @@
 	return 0;
 }
 #endif /* __NetBSD__ && IEEE80211_IOC_STA_MGMT */
+
+#if defined(__NetBSD__) && defined(IEEE80211_MLME_VERSION) && \
+    defined(IEEE80211_ASSOC_EVENT_VERSION)
+static void
+bsd_sta_epoch_reset(struct bsd_driver_data *drv)
+{
+	drv->sta_assoc_epoch = 0;
+	drv->sta_assoc_retired_epoch = 0;
+	drv->sta_assoc_versioned = 0;
+	os_memset(drv->sta_assoc_bssid, 0, sizeof(drv->sta_assoc_bssid));
+}
+
+static int
+bsd_sta_assoc_event(struct bsd_driver_data *drv, const void *data, size_t len)
+{
+	struct ieee80211_assoc_event event;
+	const struct ieee80211_assoc_event *assoc = &event;
+	static const u8 zero_bssid[ETH_ALEN];
+
+	if (data == NULL || len != sizeof(event))
+		return 0;
+	os_memcpy(&event, data, sizeof(event));
+	if (assoc->iae_version != IEEE80211_ASSOC_EVENT_VERSION ||
+	    assoc->iae_reserved != 0 || assoc->iae_reserved2[0] != 0 ||
+	    assoc->iae_reserved2[1] != 0 || assoc->iae_assoc_epoch == 0 ||
+	    os_memcmp(assoc->iae_bssid, zero_bssid, ETH_ALEN) == 0 ||
+	    is_multicast_ether_addr(assoc->iae_bssid) ||
+	    assoc->iae_assoc_epoch <= drv->sta_assoc_retired_epoch ||
+	    assoc->iae_assoc_epoch < drv->sta_assoc_epoch ||
+	    (assoc->iae_assoc_epoch == drv->sta_assoc_epoch &&
+	     !is_zero_ether_addr(drv->sta_assoc_bssid) &&
+	     os_memcmp(assoc->iae_bssid, drv->sta_assoc_bssid, ETH_ALEN) != 0))
+		return 0;
+
+	drv->sta_assoc_versioned = 1;
+	drv->sta_assoc_epoch = assoc->iae_assoc_epoch;
+	os_memcpy(drv->sta_assoc_bssid, assoc->iae_bssid, ETH_ALEN);
+	return 1;
+}
+
+static int
+bsd_sta_disassoc_event(struct bsd_driver_data *drv, const void *data, size_t len)
+{
+	struct ieee80211_assoc_event event;
+	const struct ieee80211_assoc_event *disassoc = &event;
+	static const u8 zero_bssid[ETH_ALEN];
+	int had_current;
+
+	if (data == NULL || len != sizeof(event))
+		return 0;
+	os_memcpy(&event, data, sizeof(event));
+	if (disassoc->iae_version != IEEE80211_ASSOC_EVENT_VERSION ||
+	    disassoc->iae_reserved != 0 || disassoc->iae_reserved2[0] != 0 ||
+	    disassoc->iae_reserved2[1] != 0 || disassoc->iae_assoc_epoch == 0 ||
+	    os_memcmp(disassoc->iae_bssid, zero_bssid, ETH_ALEN) == 0 ||
+	    is_multicast_ether_addr(disassoc->iae_bssid) ||
+	    disassoc->iae_assoc_epoch <= drv->sta_assoc_retired_epoch ||
+	    disassoc->iae_assoc_epoch < drv->sta_assoc_epoch ||
+	    (disassoc->iae_assoc_epoch == drv->sta_assoc_epoch &&
+	     !is_zero_ether_addr(drv->sta_assoc_bssid) &&
+	     os_memcmp(disassoc->iae_bssid, drv->sta_assoc_bssid,
+		       ETH_ALEN) != 0))
+		return 0;
+
+	had_current = drv->sta_assoc_epoch != 0;
+	/* Retire before notifying the supplicant, which may reenter. */
+	drv->sta_assoc_retired_epoch = disassoc->iae_assoc_epoch;
+	drv->sta_assoc_versioned = 1;
+	drv->sta_assoc_epoch = 0;
+	os_memset(drv->sta_assoc_bssid, 0, sizeof(drv->sta_assoc_bssid));
+#if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
+	if (drv->sae_configured) {
+		drv->sae_active = 0;
+		drv->sae_blocked = 1;
+	}
+#endif
+	return had_current ? 1 : 2;
+}
+#endif
 
 static void
 bsd_wireless_event_receive(int sock, void *ctx, void *sock_ctx)
@@ -1376,6 +1623,13 @@
 		case RTM_IEEE80211_REASSOC:
 			if (drv->is_ap)
 				break;
+#if defined(__NetBSD__) && defined(IEEE80211_MLME_VERSION) && \
+    defined(IEEE80211_ASSOC_EVENT_VERSION)
+			if (drv->opmode == IEEE80211_M_STA &&
+			    !bsd_sta_assoc_event(drv, ifan + 1,
+			    n - sizeof(*ifan)))
+				break;
+#endif
 #if !defined(HOSTAPD) && defined(__NetBSD__) && defined(IEEE80211_IOC_STA_MGMT)
 			{
 				struct ieee80211req_sta_mgmt info;
@@ -1406,6 +1660,25 @@
 		case RTM_IEEE80211_DISASSOC:
 			if (drv->is_ap)
 				break;
+#if defined(__NetBSD__) && defined(IEEE80211_MLME_VERSION) && \
+    defined(IEEE80211_ASSOC_EVENT_VERSION)
+			if (drv->opmode == IEEE80211_M_STA) {
+				if (n == (int)sizeof(*ifan)) {
+					if (drv->sta_assoc_versioned)
+						break;
+				} else if (bsd_sta_disassoc_event(drv, ifan + 1,
+				    n - sizeof(*ifan)) != 1)
+					break;
+			}
+#endif
+#if !defined(HOSTAPD) && defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
+			/* The legacy event has no generation. Suppress local callbacks,
+			 * but only a later tagged retirement may change kernel state. */
+			if (drv->sae_configured) {
+				drv->sae_active = 0;
+				drv->sae_blocked = 1;
+			}
+#endif
 #if !defined(HOSTAPD) && defined(__NetBSD__) && defined(IEEE80211_IOC_STA_MGMT)
 			bsd_sta_disconnected(drv);
 #else
@@ -1465,6 +1738,11 @@
 		case IFAN_ARRIVAL:
 			drv = bsd_get_drvname(global, ifan->ifan_name);
 			if (drv) {
+#if defined(__NetBSD__) && defined(IEEE80211_MLME_VERSION) && \
+    defined(IEEE80211_ASSOC_EVENT_VERSION)
+				if (drv->ifindex != ifan->ifan_index || drv->if_removed)
+					bsd_sta_epoch_reset(drv);
+#endif
 				drv->ifindex = ifan->ifan_index;
 				drv->if_removed = 0;
 			}
@@ -1506,7 +1784,7 @@
 				   drv->ifname);
 #if !defined(HOSTAPD) && defined(__NetBSD__) && defined(IEEE80211_IOC_STA_MGMT)
 			bsd_sta_scan_clear(drv);
-			bsd_sta_tx_status(drv, 0, 0);
+			bsd_sta_tx_status(drv, 0, 0, 0, 0);
 #endif
 			wpa_supplicant_event(drv->ctx, EVENT_INTERFACE_DISABLED,
 					     NULL);
@@ -1635,8 +1913,17 @@
 
 static int
 bsd_sta_disassoc(void *priv, const u8 *own_addr, const u8 *addr,
-		 u16 reason_code, int link_id)
-{
+		 u16 reason_code
+#ifdef WPA_DRIVER_FLAGS2_P2P_FEATURE_V2
+		 , int link_id
+#endif
+		 )
+{
+	(void) own_addr;
+#ifdef WPA_DRIVER_FLAGS2_P2P_FEATURE_V2
+	if (link_id >= 0)
+		return -1;
+#endif
 	return bsd_send_mlme_param(priv, IEEE80211_MLME_DISASSOC, reason_code,
 				   addr);
 }
@@ -1681,7 +1968,8 @@
 	if (bsd_get_iface_flags(drv) < 0)
 		goto bad;
 
-	if (bsd_set_mediaopt(drv, IFM_OMASK, IFM_IEEE80211_HOSTAP) < 0) {
+	if (bsd_set_opmode(drv, IFM_IEEE80211_HOSTAP,
+	    IEEE80211_M_HOSTAP) < 0) {
 		wpa_printf(MSG_ERROR, "%s: failed to set operation mode",
 			   __func__);
 		goto bad;
@@ -1821,8 +2109,13 @@
 static int
 wpa_driver_bsd_deauthenticate(void *priv, const u8 *addr, u16 reason_code)
 {
-	return bsd_send_mlme_param(priv, IEEE80211_MLME_DEAUTH, reason_code,
-				   addr);
+	int ret = bsd_send_mlme_param(priv, IEEE80211_MLME_DEAUTH, reason_code,
+				     addr);
+#if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
+	if (bsd_sae_disable(priv) < 0)
+		ret = -1;
+#endif
+	return ret;
 }
 
 static int
@@ -1849,14 +2142,105 @@
 	drv_event_eapol_rx(drv->ctx, src_addr, buf, len);
 }
 
+#if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE) && \
+    defined(IEEE80211_SAE_CAP_KEY_EPOCH)
+static int
+bsd_sae_prepare_iface(struct bsd_driver_data *drv)
+{
+	struct ifreq ifr;
+
+	if (!drv->ifindex || drv->if_removed || bsd_get_iface_flags(drv) < 0)
+		return -1;
+	/* SDIO initialization can still be asynchronous after UP. Let the
+	 * supplicant retry once RUNNING is set; AUTH must not enter init work. */
+	if (drv->flags & IFF_UP)
+		return (drv->flags & IFF_RUNNING) ? 0 : -1;
+	os_memset(&ifr, 0, sizeof(ifr));
+	os_strlcpy(ifr.ifr_name, drv->ifname, sizeof(ifr.ifr_name));
+	ifr.ifr_flags = drv->flags | IFF_UP;
+	/* Native initialization starts with stop, which retires SAE. Finish it
+	 * before installing the new generation, never after CONFIGURE-on. */
+	if (ioctl(drv->global->sock, SIOCSIFFLAGS, &ifr) < 0 ||
+	    bsd_get_iface_flags(drv) < 0 ||
+	    (drv->flags & (IFF_UP | IFF_RUNNING)) != (IFF_UP | IFF_RUNNING))
+		return -1;
+	return 0;
+}
+#endif
+
+static int
+bsd_set_supp_port(void *priv, int authorized)
+{
+	struct bsd_driver_data *drv = priv;
+	u8 value;
+
+	if (authorized != 0 && authorized != 1)
+		return -1;
+	value = (u8) authorized;
+#if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
+	if (!drv->sae_active && drv->sae_blocked)
+		return -1;
+#ifdef IEEE80211_SAE_CAP_KEY_EPOCH
+	if (drv->sae_active && drv->sae_key_epoch)
+		return bsd_sae_request(drv, IEEE80211_SAE_SET_PORT,
+				       &value, sizeof(value));
+#endif
+#endif
+#ifdef IEEE80211_IOC_STA_PORT
+	{
+		struct ieee80211req req;
+
+		os_memset(&req, 0, sizeof(req));
+		os_strlcpy(req.i_name, drv->ifname, sizeof(req.i_name));
+		req.i_type = IEEE80211_IOC_STA_PORT;
+		if (ioctl(drv->global->sock, SIOCG80211, &req) < 0) {
+			if (errno == EOPNOTSUPP || errno == ENOTTY || errno == EINVAL)
+				return 0; /* Legacy operation is optional on older drivers. */
+			return -1;
+		}
+		if (req.i_val != 1)
+			return -1;
+		return set80211param(drv, IEEE80211_IOC_STA_PORT, value);
+	}
+#else
+	(void) drv;
+	return 0;
+#endif
+}
+
 static int
 wpa_driver_bsd_associate(void *priv, struct wpa_driver_associate_params *params)
 {
 	struct bsd_driver_data *drv = priv;
 	struct ieee80211req_mlme mlme;
+	enum ieee80211_opmode opmode;
 	u32 mode;
 	int privacy;
 	int ret = 0;
+	int sae = wpa_key_mgmt_sae(params->key_mgmt_suite);
+
+#if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
+	if (bsd_sae_disable(drv) < 0)
+		return -1;
+	if (sae) {
+		drv->sae_blocked = 1;
+		if (!(drv->capa.key_mgmt & WPA_DRIVER_CAPA_KEY_MGMT_SAE) ||
+		    params->key_mgmt_suite != WPA_KEY_MGMT_SAE ||
+		    params->mode != IEEE80211_MODE_INFRA ||
+		    params->mgmt_frame_protection != MGMT_FRAME_PROTECTION_REQUIRED ||
+		    params->pairwise_suite != WPA_CIPHER_CCMP ||
+		    params->group_suite != WPA_CIPHER_CCMP || !params->bssid ||
+		    is_multicast_ether_addr(params->bssid) ||
+		    is_zero_ether_addr(params->bssid))
+			return -1;
+	}
+#else
+	if (sae)
+		return -1;
+#endif
+	if (params->ssid_len > sizeof(mlme.im_ssid) ||
+	    (params->ssid_len && !params->ssid))
+		return -1;
 
 	wpa_printf(MSG_DEBUG,
 		"%s: ssid '%.*s' wpa ie len %u pairwise %u group %u key mgmt %u"
@@ -1871,18 +2255,21 @@
 	switch (params->mode) {
 	case IEEE80211_MODE_INFRA:
 		mode = 0 /* STA */;
+		opmode = IEEE80211_M_STA;
 		break;
 	case IEEE80211_MODE_IBSS:
 		mode = IFM_IEEE80211_IBSS;
+		opmode = IEEE80211_M_IBSS;
 		break;
 	case IEEE80211_MODE_AP:
 		mode = IFM_IEEE80211_HOSTAP;
+		opmode = IEEE80211_M_HOSTAP;
 		break;
 	default:
 		wpa_printf(MSG_ERROR, "%s: unknown operation mode", __func__);
 		return -1;
 	}
-	if (bsd_set_mediaopt(drv, IFM_OMASK, mode) < 0) {
+	if (bsd_set_opmode(drv, mode, opmode) < 0) {
 		wpa_printf(MSG_ERROR, "%s: failed to set operation mode",
 			   __func__);
 		return -1;
@@ -1899,12 +2286,11 @@
 
 	if (wpa_driver_bsd_set_drop_unencrypted(drv, params->drop_unencrypted)
 	    < 0)
-		ret = -1;
+		goto fail;
 	if (wpa_driver_bsd_set_auth_alg(drv, params->auth_alg) < 0)
-		ret = -1;
-	/* XXX error handling is wrong but unclear what to do... */
+		goto fail;
 	if (wpa_driver_bsd_set_wpa_ie(drv, params->wpa_ie, params->wpa_ie_len) < 0)
-		return -1;
+		goto fail;
 
 	privacy = !(params->pairwise_suite == WPA_CIPHER_NONE &&
 	    params->group_suite == WPA_CIPHER_NONE &&
@@ -1913,38 +2299,24 @@
 	wpa_printf(MSG_DEBUG, "%s: set PRIVACY %u", __func__, privacy);
 
 	if (set80211param(drv, IEEE80211_IOC_PRIVACY, privacy) < 0)
-		return -1;
+		goto fail;
 
 	if (params->wpa_ie_len &&
 	    set80211param(drv, IEEE80211_IOC_WPA,
 			  params->wpa_ie[0] == WLAN_EID_RSN ? 2 : 1) < 0)
-		return -1;
+		goto fail;
 
 #if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
-	if (drv->capa.key_mgmt & WPA_DRIVER_CAPA_KEY_MGMT_SAE) {
-		u8 enabled = params->key_mgmt_suite == WPA_KEY_MGMT_SAE;
-
-		if (enabled && (params->mgmt_frame_protection != MGMT_FRAME_PROTECTION_REQUIRED ||
-		    params->pairwise_suite != WPA_CIPHER_CCMP ||
-		    params->group_suite != WPA_CIPHER_CCMP || !params->bssid))
-			return -1;
-		if (++drv->sae_generation == 0)
-			drv->sae_generation++;
-		os_memset(drv->sae_bssid, 0, ETH_ALEN);
-		if (params->bssid)
-			os_memcpy(drv->sae_bssid, params->bssid, ETH_ALEN);
-		drv->sae_active = enabled;
-		if (bsd_sae_request(drv, IEEE80211_SAE_CONFIGURE, &enabled, 1) < 0) {
-			drv->sae_active = 0;
-			return -1;
-		}
-	}
-#endif
-	if (ret)
-		return ret;
+#ifdef IEEE80211_SAE_CAP_KEY_EPOCH
+	if (sae && drv->sae_key_epoch && bsd_sae_prepare_iface(drv) < 0)
+		goto fail;
+#endif
+	if (sae && bsd_sae_enable(drv, params->bssid) < 0)
+		goto fail;
+#endif
 #if defined(__NetBSD__) && defined(IEEE80211_IOC_STA_MGMT)
 	if (bsd_sta_associate(drv, params) < 0)
-		return -1;
+		goto fail;
 #endif
 	os_memset(&mlme, 0, sizeof(mlme));
 	mlme.im_op = IEEE80211_MLME_ASSOC;
@@ -1953,9 +2325,29 @@
 	mlme.im_ssid_len = params->ssid_len;
 	if (params->bssid != NULL)
 		os_memcpy(mlme.im_macaddr, params->bssid, IEEE80211_ADDR_LEN);
-	if (set80211var(drv, IEEE80211_IOC_MLME, &mlme, sizeof(mlme)) < 0)
-		return -1;
+	if (bsd_set_mlme(drv, &mlme) < 0)
+		goto fail;
+#if defined(__NetBSD__) && defined(IEEE80211_MLME_VERSION) && \
+    defined(IEEE80211_ASSOC_EVENT_VERSION)
+	if (params->mode == IEEE80211_MODE_INFRA) {
+		if (mlme.im_assoc_epoch == 0 ||
+		    mlme.im_assoc_epoch <= drv->sta_assoc_retired_epoch)
+			goto fail;
+		drv->sta_assoc_epoch = mlme.im_assoc_epoch;
+		drv->sta_assoc_versioned = 1;
+		os_memcpy(drv->sta_assoc_bssid, mlme.im_macaddr, ETH_ALEN);
+	}
+#endif
+#if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
+	if (!sae)
+		drv->sae_blocked = 0;
+#endif
 	return ret;
+fail:
+#if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
+	(void) bsd_sae_disable(drv);
+#endif
+	return -1;
 }
 
 static int
@@ -2012,7 +2404,7 @@
 	}
 #endif
 
-	if (bsd_set_mediaopt(drv, IFM_OMASK, 0 /* STA */) < 0) {
+	if (bsd_set_opmode(drv, 0 /* STA */, IEEE80211_M_STA) < 0) {
 		wpa_printf(MSG_ERROR, "%s: failed to set operation mode",
 			   __func__);
 		return -1;
@@ -2289,6 +2681,9 @@
 #ifdef IEEE80211_SAE_CAP_SA_QUERY
 			drv->sae_query = !!(req.i_val & IEEE80211_SAE_CAP_SA_QUERY);
 #endif
+#ifdef IEEE80211_SAE_CAP_KEY_EPOCH
+			drv->sae_key_epoch = !!(req.i_val & IEEE80211_SAE_CAP_KEY_EPOCH);
+#endif
 		}
 	}
 #endif
@@ -2326,14 +2721,20 @@
 }
 
 static void *
-wpa_driver_bsd_init(void *ctx, const char *ifname, void *priv,
-		    enum wpa_p2p_mode p2p_mode)
+wpa_driver_bsd_init(void *ctx, const char *ifname, void *priv
+#ifdef WPA_DRIVER_FLAGS2_P2P_FEATURE_V2
+		    , enum wpa_p2p_mode p2p_mode
+#endif
+		    )
 {
 #define	GETPARAM(drv, param, v) \
 	(((v) = get80211param(drv, param)) != -1)
 	struct bsd_driver_data *drv;
 	int i;
 
+#ifdef WPA_DRIVER_FLAGS2_P2P_FEATURE_V2
+	(void) p2p_mode;
+#endif
 	drv = os_zalloc(sizeof(*drv));
 	if (drv == NULL)
 		return NULL;
@@ -2400,9 +2801,14 @@
 {
 	struct bsd_driver_data *drv = priv;
 
+#if defined(IEEE80211_IOC_SAE) && defined(CONFIG_SAE)
+	if (bsd_sae_disable(drv) < 0)
+		wpa_printf(MSG_ERROR, "BSD: failed to retire external SAE session");
+#endif
+
 #if !defined(HOSTAPD) && defined(__NetBSD__) && defined(IEEE80211_IOC_STA_MGMT)
 	bsd_sta_scan_clear(drv);
-	bsd_sta_tx_status(drv, 0, 0);
+	bsd_sta_tx_status(drv, 0, 0, 0, 0);
 	if ((drv->sta_scan || drv->sta_btm || drv->sta_rrm) &&
 	    drv->ifindex != 0 && !drv->if_removed) {
 		struct ieee80211req_sta_mgmt req;
@@ -2463,22 +2869,9 @@
 
 	global->sock = socket(PF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
 	if (global->sock < 0) {
-		if (errno == EAFNOSUPPORT) {
-			wpa_printf(MSG_DEBUG,
-				   "INET not supported, trying INET6...");
-			global->sock = socket(PF_INET6,
-					      SOCK_DGRAM | SOCK_CLOEXEC, 0);
-			if (global->sock < 0) {
-				wpa_printf(MSG_ERROR,
-					   "socket[PF_INET6,SOCK_DGRAM]: %s",
-					   strerror(errno));
-				goto fail1;
-			}
-		} else {
-			wpa_printf(MSG_ERROR, "socket[PF_INET,SOCK_DGRAM]: %s",
-				   strerror(errno));
-			goto fail1;
-		}
+		wpa_printf(MSG_ERROR, "socket[PF_INET,SOCK_DGRAM]: %s",
+			   strerror(errno));
+		goto fail1;
 	}
 
 	global->route = socket(PF_ROUTE,
@@ -2554,6 +2947,7 @@
 	.deauthenticate		= wpa_driver_bsd_deauthenticate,
 	.associate		= wpa_driver_bsd_associate,
 	.get_capa		= wpa_driver_bsd_get_capa,
+	.set_supp_port		= bsd_set_supp_port,
 #if defined(__NetBSD__) && defined(IEEE80211_IOC_STA_MGMT)
 	.send_action = bsd_send_action,
 	.signal_poll = bsd_sta_signal_poll,
