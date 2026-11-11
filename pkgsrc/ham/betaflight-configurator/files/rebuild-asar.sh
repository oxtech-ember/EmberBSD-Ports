#!/bin/sh
# Rebuild the Ember asar from upstream tag 2026.6.2 (host Node 24+/26).
set -eu
TAG=2026.6.2
NODE=${NODE:-node}
NPM=${NPM:-npm}
ASAR=${ASAR:-asar}
WORKDIR=${WORKDIR:-/tmp/bf-ember-rebuild}
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"
git clone --depth 1 --branch "$TAG" https://github.com/betaflight/betaflight-configurator.git src
cd src
"$NPM" ci --ignore-scripts
"$NPM" run build
mkdir -p app
cp -R src/dist app/dist
cp "$1" app/main.cjs
printf '%s\n' '{"name":"betaflight-configurator","version":"'"$TAG"'","main":"main.cjs","private":true}' > app/package.json
"$ASAR" pack app "betaflight-configurator-${TAG}-ember1.asar"
echo "Wrote $WORKDIR/src/betaflight-configurator-${TAG}-ember1.asar"
