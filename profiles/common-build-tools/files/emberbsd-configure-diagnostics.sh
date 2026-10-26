# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Shared explicit SDK configure diagnostics.
# SDK admission binds the selected executable's bytes and provenance.
if test "${GCC_CONFIGURE_SDK+set}" = set; then
  if test "${EMBERBSD_CONFIGURE_SDK+set}" = set &&
     test "$EMBERBSD_CONFIGURE_SDK" != "$GCC_CONFIGURE_SDK"; then
    echo 'configure: conflicting SDK mode selectors' >&2
    exit 1
  fi
  EMBERBSD_CONFIGURE_SDK=$GCC_CONFIGURE_SDK
fi
if test "${GCC_CONFIGURE_UNAME+set}" = set; then
  if test "${EMBERBSD_CONFIGURE_UNAME+set}" = set &&
     test "$EMBERBSD_CONFIGURE_UNAME" != "$GCC_CONFIGURE_UNAME"; then
    echo 'configure: conflicting SDK uname selectors' >&2
    exit 1
  fi
  EMBERBSD_CONFIGURE_UNAME=$GCC_CONFIGURE_UNAME
fi
if test "${EMBERBSD_CONFIGURE_SDK-}" != yes; then
  echo 'configure: EMBERBSD_CONFIGURE_SDK must be yes when selected' >&2
  exit 1
fi
case ${EMBERBSD_CONFIGURE_UNAME-} in
  /usr/bin/uname | /bin/uname)
    echo 'configure: system uname is not a selected SDK input' >&2
    exit 1 ;;
  /*) if test ! -f "$EMBERBSD_CONFIGURE_UNAME" || test ! -x "$EMBERBSD_CONFIGURE_UNAME"; then
        echo 'configure: selected SDK uname must be executable' >&2
        exit 1
      fi ;;
  *) echo 'configure: select an absolute EMBERBSD_CONFIGURE_UNAME' >&2
     exit 1 ;;
esac
emberbsd_host_diagnostic ()
{
  case $1 in
    /usr/bin/uname | /bin/uname)
      shift
      if test "$#" = 1; then
        case $1 in
          -m | -n | -p | -r | -s | -v) "$EMBERBSD_CONFIGURE_UNAME" "$@"; return $? ;;
        esac
      fi ;;
  esac
  echo 'unavailable (selected SDK profile)'
  return 1
}
