# $NetBSD$
BUILDLINK_TREE+= resonance-audio
.if !defined(RESONANCE_AUDIO_BUILDLINK3_MK)
RESONANCE_AUDIO_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.resonance-audio+= resonance-audio>=20220908
BUILDLINK_PKGSRCDIR.resonance-audio?= ../../audio/resonance-audio
.include "../../math/eigen3/buildlink3.mk"
.include "../../audio/pffft/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.endif
BUILDLINK_TREE+= -resonance-audio
