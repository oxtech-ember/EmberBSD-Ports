# Origin: EmberBSD common profile, upstream lit tool/module dependency.
BUILDLINK_TREE+= py-llvm-lit
.if !defined(PY_LLVM_LIT_BUILDLINK3_MK)
PY_LLVM_LIT_BUILDLINK3_MK:=
.include "../../lang/python/pyversion.mk"
BUILDLINK_API_DEPENDS.py-llvm-lit+= ${PYPKGPREFIX}-llvm-lit>=23.1.3
BUILDLINK_PKGSRCDIR.py-llvm-lit?= ../../devel/py-llvm-lit
BUILDLINK_FILES.py-llvm-lit+= bin/llvm-lit
.endif
BUILDLINK_TREE+= -py-llvm-lit
