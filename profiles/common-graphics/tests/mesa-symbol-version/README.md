# libgallium symbol versions

Mesa uses GNU `--default-symver` to version libgallium exports with its SONAME.
LLD does not implement that option. The upstream feature check then removes it.
An old consumer can still require the version in its ELF `VERNEED` table.

The NetBSD patch retains GNU's supported flag. If the flag is unavailable,
it names the existing version-script node with the same SONAME.
The exported symbol patterns do not change. LLD accepts the unquoted SONAME.
GNU's version-script grammar does not accept the hyphen in that name.
Quotes are not interchangeable: LLD retains them in the version identifier.

Run the cross regression from a clean Ports checkout:

```sh
ruby profiles/common-graphics/tests/mesa-symbol-version/run.rb \
  "$mesa_archive" "$gcc_tools" "$sysroot" "$lld_specs" \
  "$meson" "$ninja" "$new_output"
```

Use GCC16, the current LLD23 specs, and the EmberBSD sysroot.
The test extracts the pinned upstream Meson prefix and symbol map.
It applies the checked recipe patches and configures them with real Meson.
Small target libraries exercise GNU and LLD before and after the change.
The old LLD case must lack the version. Both fixed cases must retain it.
A consumer linked to the old GNU library must contain the matching `VERNEED`.
The test reads actual `VERDEF`, `VERNEED`, and default-versioned exports.
It does not execute target binaries and does not prove hardware operation.

The full package audit must also compare exported function, object, and TLS
symbols against the accepted package. Check SONAME and version definitions.
Do not discard version suffixes during the comparison.
GNU-only BSS/end linker-script markers are not Mesa API symbols.
Report their exact names separately when switching linkers.

`runtime-old-consumer.c` calls the real Mesa dispatch-table query.
Link it against the accepted old libgallium before updating the provider.
Keep that same ELF for execution after the package update.
A positive table size and exit zero confirm that this versioned import loads.
This small check supplements the full Mesa consumer and rendering tests.
