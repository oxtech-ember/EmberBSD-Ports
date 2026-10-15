# Origin: EmberBSD (AI-assisted).
BUILDLINK_TREE+= pulseaudio-qt

.if !defined(PULSEAUDIO_QT_BUILDLINK3_MK)
PULSEAUDIO_QT_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.pulseaudio-qt+= pulseaudio-qt>=1.9.0
BUILDLINK_PKGSRCDIR.pulseaudio-qt?= ../../audio/pulseaudio-qt

.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif

BUILDLINK_TREE+= -pulseaudio-qt
