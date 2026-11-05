# $NetBSD$

BUILDLINK_TREE+=	json-schema-validator

.if !defined(JSON_SCHEMA_VALIDATOR_BUILDLINK3_MK)
JSON_SCHEMA_VALIDATOR_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.json-schema-validator+=	json-schema-validator>=2.4.1
BUILDLINK_PKGSRCDIR.json-schema-validator?=	../../textproc/json-schema-validator
BUILDLINK_DEPMETHOD.json-schema-validator?=	build

.include "../../textproc/nlohmann-json/buildlink3.mk"
.endif

BUILDLINK_TREE+=	-json-schema-validator
