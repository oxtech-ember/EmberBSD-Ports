#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Source from build.sh; no target execution.
select_runtime_libraries() {
    runtime_libraries=libgcc,libstdc++
    runtime_sonames='libgcc_s.so.1 libstdc++.so.7'
    [ "$runtime_gomp" = no ] || {
        runtime_libraries=$runtime_libraries,libgomp
        runtime_sonames="$runtime_sonames libgomp.so.1"
    }
    [ "$runtime_atomic" = no ] || {
        runtime_libraries=$runtime_libraries,libatomic
        runtime_sonames="$runtime_sonames libatomic.so.3"
    }
}

check_runtime_libraries() {
    runtime_prior=$(sed -n 's/^runtime_libraries=//p' "$work/inputs.txt")
    runtime_claim_count=$(grep -c '^runtime_libraries=' "$work/inputs.txt" || :)
    [ "$runtime_claim_count" -le 1 ] || fail 'Duplicate runtime library selection.'
    # grep/sed accept an unterminated final line. A prior receipt must contain
    # the same complete newline-terminated selection that the builder writes.
    runtime_terminated_claims=0
    while IFS= read -r runtime_line; do
        case "$runtime_line" in runtime_libraries=*) runtime_terminated_claims=$((runtime_terminated_claims + 1));; esac
    done < "$work/inputs.txt"
    [ "$runtime_terminated_claims" -eq "$runtime_claim_count" ] || fail 'Unterminated prior runtime library selection.'
    # Receipts predating the optional runtimes describe only the original pair.
    [ "$runtime_claim_count" -ne 0 ] || runtime_prior=libgcc,libstdc++
    case "$runtime_prior" in
        libgcc,libstdc++|libgcc,libstdc++,libgomp|libgcc,libstdc++,libatomic|libgcc,libstdc++,libgomp,libatomic) ;;
        *) fail 'Unsupported prior runtime library selection.';;
    esac
    runtime_extension=no
    if [ "$runtime_libraries" != "$runtime_prior" ]; then
        [ "$resume" = runtime ] || fail 'Changing runtime libraries requires --resume-runtime.'
        for runtime_old in $(printf '%s' "$runtime_prior" | tr ',' ' '); do
            case ,$runtime_libraries, in
                *,"$runtime_old",*) ;;
                *) fail 'Runtime extension cannot remove an existing library.';;
            esac
        done
        runtime_extension=yes
    fi
}

verify_completed_stage() {
    for runtime_manifest in build-success stage.sha256 stage.symlinks; do
        [ -f "$work/$runtime_manifest" ] && [ ! -L "$work/$runtime_manifest" ] || fail 'Completed-stage receipts must be regular files.'
    done
    printf 'runtime-only-bootstrap\n' | cmp -s - "$work/build-success" || fail 'Invalid completed runtime marker.'
    [ -s "$work/stage.sha256" ] && [ -f "$work/stage.symlinks" ] || fail 'Missing completed-stage manifests.'
    # Compare the current regular-file/symlink inventory and bytes without changing the
    # completed stage, including during --check. Hashing listed files alone
    # would miss newly added files or links.
    runtime_current_files=$(cd "$work/stage" && find . -type f -exec shasum -a 256 {} + | LC_ALL=C sort)
    [ "$runtime_current_files" = "$(cat "$work/stage.sha256")" ] || fail 'Completed-stage file inventory or hashes changed.'
    runtime_current_links=$(cd "$work/stage" && find . -type l -exec sh -c 'for path do printf "%s\t%s\n" "$path" "$(readlink "$path")"; done' sh {} + | LC_ALL=C sort)
    [ "$runtime_current_links" = "$(cat "$work/stage.symlinks")" ] || fail 'Completed-stage symlink inventory changed.'
    [ -z "$(find "$work/stage" ! -type d ! -type f ! -type l -print)" ] || fail 'Special file in completed stage.'
}

record_runtime_libraries() {
    # The old receipt is already retained by the resume backup. Keep this
    # selection unique; earlier hashes and source provenance remain intact.
    sed '/^runtime_libraries=/d' "$work/inputs.txt" > "$resume_backup/inputs-current.txt"
    cat "$resume_backup/inputs-current.txt" > "$work/inputs.txt"
    printf 'runtime_libraries=%s\n' "$runtime_libraries" >> "$work/inputs.txt"
}
