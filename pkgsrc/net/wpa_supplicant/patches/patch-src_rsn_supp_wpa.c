--- src/rsn_supp/wpa.c.orig
+++ src/rsn_supp/wpa.c
@@ -3044,11 +3044,11 @@
 			goto failed;
 	}
 
+	/* Keep the controlled port closed until GTK/IGTK installation succeeds. */
 	if (key_info & WPA_KEY_INFO_SECURE) {
 		wpa_sm_mlme_setprotection(
 			sm, sm->bssid, MLME_SETPROTECTION_PROTECT_TYPE_RX,
 			MLME_SETPROTECTION_KEY_TYPE_PAIRWISE);
-		eapol_sm_notify_portValid(sm->eapol, true);
 	}
 	wpa_sm_set_state(sm, WPA_GROUP_HANDSHAKE);
 
