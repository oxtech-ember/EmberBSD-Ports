# $NetBSD$
OPENSBI_BOARD= esp32s31
OPENSBI_PLATFORM= generic
OPENSBI_XLEN= 32
OPENSBI_ISA= rv32imac_zicsr_zifencei
OPENSBI_ABI= ilp32
OPENSBI_ENV+= PLATFORM_DEFCONFIG=esp32s31_defconfig OPENSBI_OPTIMIZE=-Oz
OPENSBI_BIN= fw_dynamic.bin

.include "../../sysutils/opensbi/opensbi.mk"
.include "../../mk/bsd.pkg.mk"
