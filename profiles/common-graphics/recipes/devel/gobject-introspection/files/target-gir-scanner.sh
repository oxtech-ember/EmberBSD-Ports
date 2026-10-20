#!/bin/sh
exec '@GI_SCANNER@' --use-ldd-wrapper='@GI_LDD_WRAPPER@' "$@"
