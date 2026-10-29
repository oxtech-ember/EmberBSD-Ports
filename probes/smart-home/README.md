# Smart-home source ports

EmberBSD Ports owns these original-source preparations, local portability
patches and checks. The intended workflow connects sensors through MQTT,
Zigbee and Thread to an automation controller. These are source probes,
not a finished installable smart-home image.

## Current evidence

The stable releases below were checked on 2026-10-07. An archive preparation
or a host test does not establish native EmberBSD runtime support.

| Project | Selected release | Verified boundary |
| --- | --- | --- |
| [Eclipse Mosquitto](../mosquitto/README.md) | 2.1.2 | Installed AArch64/NetBSD VM candidate passes 12 MQTT/TLS/authentication/ACL/persistence checks. Separate owner recipe. |
| [Zigbee2MQTT](ZIGBEE2MQTT.md) | 2.14.2 | Frozen dependency installation, build, 842 upstream tests, 5 serial-list contracts and real onboarding HTTP/API pass on macOS/arm64 with Node 24.21.0. Native Node/addons and radios remain unverified. |
| [OpenThread Border Router](OTBR.md) | v2026.10.0 | Native REST/RCP configuration, adapted infra_if object and a real NetBSD ICMPv6 socket contract pass. netif multicast API, agent build, launch, ingress filtering and routing remain unverified. |
| Domoticz | 2026.4 (source build 2026.18387) | Original complete release archive verifies and extracts. Native build and HTTP/MQTT/automation workflow remain unverified. |
| [Home Assistant Core](HOME-ASSISTANT.md) | 2026.9.4 | Source/dependency inventory prepared. Host UI starts, but shutdown crashes during Python finalization; runtime check is not accepted. Native Python/Rust closure and startup remain unverified. |

## Original sources

The [source manifests](sources) record upstream URLs, exact versions and
SHA256. Preparation rejects an existing work directory and verifies every
archive for a component before extracting any, including OTBR submodules.
It preserves upstream source and license files. No downloaded archive or
binary is stored in this repository.

```sh
sh prepare.sh domoticz /absolute/new-domoticz /absolute/archive-cache
sh prepare.sh home-assistant /absolute/new-ha /absolute/archive-cache
sh test-prepare.sh /absolute/archive-cache /absolute/new-contract-work
```

Omit the final cache argument to download directly from the recorded upstream
locations. The work directory must be absolute, new, and use letters,
digits, `_`, `.`, `/` or `-`. Its parent must exist. The source contract
checks existing-work preservation and a corrupted last nested archive.
Checksums are provenance pins, not independent author signatures.

Local helpers and patches are AI-assisted EmberBSD adaptations. Patch headers
state their original source and submission status; none is claimed accepted
upstream. pnpm remains the upstream Zigbee2MQTT dependency installer, not a
new EmberBSD package manager. Installable recipes should follow pkgsrc after
the native workflows are validated.

## Common dependencies

Use one selected version of each shared dependency. Do not install an old
interpreter alongside the common stack to make an application build.

- GCC 16.2 is the current C/C++ compiler candidate. C++ dependencies must use
  its runtime; the existing VM's older Boost build cannot silently be mixed
  into a GCC 16 Domoticz executable.
- Node 26.12.1 is the common `lang/nodejs` selection. Zigbee2MQTT 2.14.2
  declares Node `^22.2.0 || ^24 || <=26.2`, so its upstream startup warning
  remains visible on Node 26.12.1. This is not a claim of upstream support.
- Python 3.14.8 comes from the [common build tools](../../profiles/common-build-tools/README.md)
  selection. Home Assistant requires at least 3.14.2. The VM's current 3.13
  is not an acceptable application runtime. Upstream Python build generators
  remain actual dependencies; no project-owned helper is written in Python.
- Mosquitto's cJSON 1.7.19 and the [shared SQLite 3.53.4 selection](../sqlite/README.md)
  are reused. OTBR uses this cJSON rather than building its older submodule.
- Domoticz needs current Boost::thread, curl, OpenSSL, Lua and Python
  development files. Its upstream Lua search prefers 5.3; migration must select
  the common Lua 5.5.1 candidate and validate existing awesome/EFL consumers.
  A private, permanent Lua 5.3 workaround is not accepted.

## Remaining application gates

Domoticz must retain Lua/dzVents and Python scripting, use the shared database
and MQTT client, and disable its binary self-updater in a package-managed
installation. Its release archive includes the bundled subprojects, so
Git submodule updating is unnecessary. Linux I2C/SPI code must not be
represented as a working NetBSD hardware backend. Acceptance needs the real
HTTP interface, a virtual device, an automation/MQTT exchange and persistence
after restart.

Home Assistant is a maintained Core source port under EmberBSD's
responsibility; it is not an upstream Home Assistant OS/container installation.
Core currently rejects NetBSD in `validate_os()`. Simply removing that guard
is insufficient: its pinned native Python/Rust packages, including `uv`,
`cryptography`, `orjson` and `psutil-home-assistant`, need native verification.
The initial useful profile includes the UI/API, MQTT, automation, recorder
and the OTBR REST client. Linux Bluetooth or Supervisor behavior must not be
silently stubbed. Acceptance requires actual onboarding, MQTT automation and
state recovery with the common Python runtime.

Zigbee pairing and Thread routing additionally require identified real radios
or a separately documented upstream radio simulation. Device-node enumeration,
a running HTTP page or an `otbr-agent` process alone does not establish them.
