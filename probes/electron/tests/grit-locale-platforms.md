# Locale platform conditions

The NetBSD overlay extends GRIT's `is_linux` condition to BSD targets.
Seven font translation files also replace `is_linux` with `is_posix`.
The latter condition includes macOS, iOS and ChromeOS.
It selects a second `IDS_WEB_FONT_FAMILY` translation on those platforms.
The production gather then fails the duplicate-translation assertion in
`MessageClique.AddTranslation`.

`grit-locale-platform-exclusivity.patch` restores `is_linux` in those seven
files. The existing BSD extension in GRIT remains unchanged.
All translation IDs, font strings and other platform branches remain unchanged.
Android and SunOS return to the upstream selection, which has no Linux font
translation for those targets.

The condition matches the [pinned upstream translation](https://github.com/chromium/chromium/blob/dd78960ccd8a03a2fe1f629543d27783885b78e9/ui/strings/translations/app_locale_settings_ja.xtb).
The [NetBSD GRIT patch](https://github.com/NetBSD/pkgsrc/blob/trunk/www/chromium/patches/patch-tools_grit_grit_node_base.py)
already includes BSD in `is_linux`. Keep that existing overlay when applying
this correction.

Run the regression with the selected host Python and the patched source tree:

```sh
python3 probes/electron/tests/grit-locale-platforms.py \
  --source /absolute/patched-chromium \
  --output /absolute/new-work/locale-result.json
```

The output file must not exist. Its parent directory must exist.
The test imports GRIT from the selected source tree.
It calls the production `grd_reader.Parse` and `RunGatherers` methods with
validation and gender translation enabled.
It checks 12 platform strings, including `netbsd` and `netbsd11`.
It also checks all seven font values for the five Linux/BSD platform strings.

Before the correction, macOS, iOS and ChromeOS fail at the duplicate-translation
assertion. The other nine strings pass. After the correction, all 12 pass.
As a negative control, replace the Japanese `is_linux` condition with `False`.
The five Linux/BSD cases must fail because the Japanese font is missing.
Restore the condition after the control.

This test checks the production gather stage. It does not validate generated
resource packs, installed fonts or rendered text.
