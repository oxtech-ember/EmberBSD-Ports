# Shared ts-poet

This package installs the upstream ts-poet JavaScript source from npm.
Upstream loads the native `dprint-node` formatter at module start. The npm
`dprint-node` archive contains only prebuilt binary add-ons, so EmberBSD does
not install it. The patches load the formatter only inside `maybePretty`.
When the formatter is not installed, ts-poet uses its own upstream fallback
and returns the unformatted TypeScript, which stays valid.
