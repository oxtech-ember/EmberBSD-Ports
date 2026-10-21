# Origin: EmberBSD (AI-assisted).
BUILDLINK_TREE+= pulseaudio-qt

.if !defined(PULSEAUDIO_QT_BUILDLINK3_MK)
PULSEAUDIO_QT_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.pulseaudio-qt+= pulseaudio-qt>=1.9.0
BUILDLINK_PKGSRCDIR.pulseaudio-qt?= ../../audio/pulseaudio-qt
# Cross KDE builds name these files relative to the buildlink prefix.
BUILDLINK_FILES.pulseaudio-qt+=	qt6/metatypes/qt6kf6pulseaudioqt_metatypes.json

.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif

BUILDLINK_TREE+= -pulseaudio-qt
