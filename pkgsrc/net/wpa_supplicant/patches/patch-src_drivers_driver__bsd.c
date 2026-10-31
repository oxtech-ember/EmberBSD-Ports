--- src/drivers/driver_bsd.c
+++ src/drivers/driver_bsd.c
@@ -1725,6 +1725,27 @@
 	return ireq.i_val;
 }
 
+#if defined(__NetBSD__) && defined(IEEE80211_IOC_STA_PORT)
+static int
+bsd_set_supp_port(void *priv, int authorized)
+{
+	struct bsd_driver_data *drv = priv;
+	struct ieee80211req ireq;
+
+	os_memset(&ireq, 0, sizeof(ireq));
+	os_strlcpy(ireq.i_name, drv->ifname, sizeof(ireq.i_name));
+	ireq.i_type = IEEE80211_IOC_STA_PORT;
+	if (ioctl(drv->global->sock, SIOCG80211, &ireq) < 0) {
+		if (errno == EOPNOTSUPP || errno == ENOTTY || errno == EINVAL)
+			return 0; /* Preserve behavior for older BSD drivers. */
+		return -1;
+	}
+	if (ireq.i_val != 1)
+		return -1;
+	return set80211param(drv, IEEE80211_IOC_STA_PORT, !!authorized);
+}
+#endif
+
 static int
 wpa_driver_bsd_get_bssid(void *priv, u8 *bssid)
 {
@@ -2535,6 +2556,9 @@
 	.deauthenticate		= wpa_driver_bsd_deauthenticate,
 	.associate		= wpa_driver_bsd_associate,
 	.get_capa		= wpa_driver_bsd_get_capa,
+#if defined(__NetBSD__) && defined(IEEE80211_IOC_STA_PORT)
+	.set_supp_port		= bsd_set_supp_port,
+#endif
 #if defined(__NetBSD__) && defined(IEEE80211_IOC_STA_MGMT)
 	.send_action = bsd_send_action,
 	.signal_poll = bsd_sta_signal_poll,
