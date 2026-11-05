# Graphene cross introspection

The common recipe retains pkgsrc's Graphene 1.10.8 and the shared GI launcher.
1.10.8 is the latest stable [upstream release](https://github.com/ebassi/graphene/releases).

The aarch64 dump was captured from the real Graphene library built with
Clang 23.1.4 and executed in an EmberBSD guest whose matching base and kernel
come from OS revision `2e5ec0754fdc95131d7b5de79b71526821be76c5`.
It contains target GType data, without a machine address or private path.

The normal cross build replays the stored dump and checks its platform,
package version, requested types and body hash. A changed release or type
list needs a new capture through the existing
[GI procedure](../../../profiles/common-graphics/cross/gi-dumps.md).
