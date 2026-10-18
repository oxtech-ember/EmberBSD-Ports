#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Selection/preservation, not a GCC build.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
work=$(mktemp -d /tmp/ember-runtime-libraries.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
fail() { echo "$*" >&2; exit 2; }
. "$here/runtime-libraries.sh"
. "$here/resume-state.sh"
resume=runtime
triplet=aarch64--netbsd
mkdir -p "$work/stage/usr/pkg/gcc16/lib" "$work/build/gcc" "$work/build/$triplet/libatomic"
for runtime_gomp in no yes; do
    for runtime_atomic in no yes; do
        select_runtime_libraries
        printf 'scope=runtime-only-bootstrap\n' > "$work/inputs.txt"
        check_runtime_libraries
        if [ "$runtime_gomp$runtime_atomic" = nono ]; then
            [ "$runtime_extension" = no ]
        else
            [ "$runtime_extension" = yes ]
        fi
        printf 'runtime_libraries=%s\n' "$runtime_libraries" >> "$work/inputs.txt"
        check_runtime_libraries
        [ "$runtime_extension" = no ]
    done
done
reject() {
    if (check_runtime_libraries) > "$work/rejection.log" 2>&1; then
        fail "Accepted $1"
    fi
    grep -Fqx "$2" "$work/rejection.log"
}
printf 'runtime_libraries=libgcc,libstdc++,libgomp,libatomic\n' > "$work/inputs.txt"
runtime_gomp=no runtime_atomic=no
select_runtime_libraries
reject 'library removal' 'Runtime extension cannot remove an existing library.'
printf 'runtime_libraries=libgcc,libstdc++\nruntime_libraries=libgcc,libstdc++\n' > "$work/inputs.txt"
reject 'duplicate selection' 'Duplicate runtime library selection.'
printf 'runtime_libraries=libgcc,libstdc++' > "$work/inputs.txt"
reject 'unterminated prior selection' 'Unterminated prior runtime library selection.'
printf 'runtime_libraries=libgcc,libstdc++,libquadmath\n' > "$work/inputs.txt"
reject 'unknown library' 'Unsupported prior runtime library selection.'
printf 'scope=runtime-only-bootstrap\n' > "$work/inputs.txt"
runtime_gomp=yes runtime_atomic=yes
select_runtime_libraries
resume=yes
reject 'frontend resume extension' 'Changing runtime libraries requires --resume-runtime.'
resume=runtime
check_runtime_libraries
[ "$runtime_extension" = yes ]

# Exercise real filesystem receipts, preserving bytes and symlinks. The small
# text payload/frontend files deliberately do not represent target ELF code.
printf 'preserved stage bytes\n' > "$work/stage/usr/pkg/gcc16/lib/fixture"
ln -s fixture "$work/stage/usr/pkg/gcc16/lib/fixture-link"
printf 'runtime-only-bootstrap\n' > "$work/build-success"
(cd "$work/stage" && find . -type f -exec shasum -a 256 {} + | LC_ALL=C sort) > "$work/stage.sha256"
(cd "$work/stage" && find . -type l -exec sh -c 'for path do printf "%s\t%s\n" "$path" "$(readlink "$path")"; done' sh {} + | LC_ALL=C sort) > "$work/stage.symlinks"
verify_completed_stage
mv "$work/build-success" "$work/retained-success"
ln -s retained-success "$work/build-success"
if (verify_completed_stage) > "$work/marker-symlink.log" 2>&1; then fail 'Accepted symlinked completed marker'; fi
grep -Fxq 'Completed-stage receipts must be regular files.' "$work/marker-symlink.log"
rm "$work/build-success"
mv "$work/retained-success" "$work/build-success"
for mutation in changed added link special; do
    case "$mutation" in
        changed) printf 'changed\n' >> "$work/stage/usr/pkg/gcc16/lib/fixture";;
        added) printf 'unrecorded\n' > "$work/stage/extra";;
        link) ln -s fixture "$work/stage/usr/pkg/gcc16/lib/extra-link";;
        special) mkfifo "$work/stage/pipe";;
    esac
    if (verify_completed_stage) > "$work/$mutation.log" 2>&1; then fail "Accepted completed-stage $mutation"; fi
    case "$mutation" in
        changed) printf 'preserved stage bytes\n' > "$work/stage/usr/pkg/gcc16/lib/fixture";;
        added) rm "$work/stage/extra";;
        link) rm "$work/stage/usr/pkg/gcc16/lib/extra-link";;
        special) rm "$work/stage/pipe";;
    esac
done
verify_completed_stage
for file in $frontend_files; do printf 'preserved frontend fixture %s\n' "$file" > "$work/build/gcc/$file"; done
printf 'old target configure fixture\n' > "$work/build/$triplet/libatomic/Makefile"
backup_runtime_resume
verify_frontend_state
[ ! -e "$work/build-success" ]
grep -Fxq runtime-only-bootstrap "$resume_backup/build-success"
cmp "$resume_backup/original-stage.sha256" "$resume_backup/stage.sha256"
cmp "$resume_backup/original-stage.symlinks" "$resume_backup/stage.symlinks"
record_runtime_libraries
[ "$(grep -c '^runtime_libraries=' "$work/inputs.txt")" -eq 1 ]
grep -Fxq 'runtime_libraries=libgcc,libstdc++,libgomp,libatomic' "$work/inputs.txt"
! grep -q '^runtime_libraries=' "$resume_backup/inputs.txt"
grep -Fxq 'preserved stage bytes' "$resume_backup/stage/usr/pkg/gcc16/lib/fixture"
[ -z "$(find "$work/stage" -mindepth 1 -print)" ]
echo 'PASS: optional runtime selection, completed-stage drift refusal, preserved stage/receipt and immutable frontend; no GCC build or target execution'
