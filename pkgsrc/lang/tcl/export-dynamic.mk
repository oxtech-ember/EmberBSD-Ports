# Pass the ELF export flag to the linker through the compiler driver.
SUBST_CLASSES+=		export-dynamic
SUBST_STAGE.export-dynamic=	pre-configure
SUBST_FILES.export-dynamic=	unix/configure
SUBST_SED.export-dynamic=	-e 's|LDFLAGS="$$LDFLAGS -export-dynamic"|LDFLAGS="$$LDFLAGS -Wl,-export-dynamic"|'
