BUILDLINK_TREE+= microsoft-gsl
.if !defined(MICROSOFT_GSL_BUILDLINK3_MK)
MICROSOFT_GSL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.microsoft-gsl+= microsoft-gsl>=5.0.1
BUILDLINK_PKGSRCDIR.microsoft-gsl?= ../../devel/microsoft-gsl
.endif
BUILDLINK_TREE+= -microsoft-gsl
