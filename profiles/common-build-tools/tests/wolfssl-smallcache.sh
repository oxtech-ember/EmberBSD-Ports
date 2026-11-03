#!/bin/sh
set -eu

: "${BMAKE:?set BMAKE to the selected native bmake}"
: "${PKGSRCDIR:?set PKGSRCDIR to the prepared pkgsrc tree}"
: "${MAKECONF:?set MAKECONF to the selected target make.conf}"

pkgdir=$PKGSRCDIR/security/wolfssl

target_options=$($BMAKE -C "$pkgdir" MAKECONF="$MAKECONF" \
    show-var VARNAME=PKG_OPTIONS)
target_args=$($BMAKE -C "$pkgdir" MAKECONF="$MAKECONF" \
    show-var VARNAME=CONFIGURE_ARGS)
target_cflags=$($BMAKE -C "$pkgdir" MAKECONF="$MAKECONF" \
    show-var VARNAME=CFLAGS)
case " $target_options " in
*' smallcache '*) ;;
*) echo 'target profile did not select the smallcache option' >&2; exit 1 ;;
esac
case " $target_args " in
*' --enable-smallcache '*) ;;
*) echo 'smallcache did not reach WolfSSL configure' >&2; exit 1 ;;
esac
case " $target_cflags " in
*' -ffunction-sections '*'-fdata-sections '*) ;;
*) echo 'target C flags do not preserve section granularity' >&2; exit 1 ;;
esac
case " $target_args " in
*' --disable-shared '*|*' --enable-shared '*) ;;
*) echo 'smallcache changed the target shared-library selection' >&2; exit 1 ;;
esac

default_args=$($BMAKE -C "$pkgdir" MAKECONF="$MAKECONF" \
    'PKG_OPTIONS.wolfssl=-shared -tests' show-var VARNAME=CONFIGURE_ARGS)
native_cflags=$($BMAKE -C "$pkgdir" MAKECONF="$MAKECONF" \
    USE_CROSS_COMPILE=no show-var VARNAME=CFLAGS)
case " $default_args " in
*' --enable-smallcache '*)
	echo 'smallcache changed the default WolfSSL configuration' >&2
	exit 1
	;;
esac
case " $native_cflags " in
*' -ffunction-sections '*|*' -fdata-sections '*)
	echo 'native C flags changed with the target-only section option' >&2
	exit 1
	;;
esac
