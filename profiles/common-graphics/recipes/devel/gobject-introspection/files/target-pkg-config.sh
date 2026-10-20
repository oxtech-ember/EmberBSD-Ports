#!/bin/sh

gi_scanner=no
gi_compiler=no
gi_package=no
for arg do
    case "$arg" in
        --variable=g_ir_scanner) gi_scanner=yes ;;
        --variable=g_ir_compiler) gi_compiler=yes ;;
        gobject-introspection-1.0) gi_package=yes ;;
    esac
done

if [ "$gi_package" = yes ]; then
    if [ "$gi_scanner" = yes ]; then
        printf '%s\n' '@GI_SCANNER@'
        exit 0
    fi
    if [ "$gi_compiler" = yes ]; then
        printf '%s\n' '@GI_COMPILER@'
        exit 0
    fi
fi

exec '@PKG_CONFIG@' "$@"
