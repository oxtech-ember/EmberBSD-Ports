# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; shared target options for host cross-build entry points.
# Source this file after defining usage(). It consumes leading options.
target=aarch64
mode=applications
target_seen=no
while [ "$#" -gt 0 ]; do
    case "$1" in
        --target)
            [ "$#" -ge 2 ] && [ -n "$2" ] && [ "$target_seen" = no ] || usage
            target=$2 target_seen=yes
            shift 2
            ;;
        --kernel)
            [ "${kernel_allowed:-no}" = yes ] && [ "$mode" = applications ] || usage
            mode=kernel
            shift
            ;;
        --*) echo 'Unknown build mode.' >&2; usage;;
        *) break;;
    esac
done
case "$target" in
    aarch64) triplet=aarch64--netbsd;;
    amd64) triplet=x86_64--netbsd;;
    *) echo "Unsupported target: $target" >&2; exit 2;;
esac
