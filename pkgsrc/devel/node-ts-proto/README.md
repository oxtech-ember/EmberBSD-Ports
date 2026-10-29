# Shared ts-proto

The npm `package.json` declares ISC, but the distributed `LICENSE` file is the
Apache-2.0 text. The recipe records the license text that the archive carries.
The declared `case-anything` range is `^2.1.13`. EmberBSD uses the newest
release 3.1.7: it exports the same case functions as an ES module, and
Node 22.12 and later load it through `require`.
