# PowerVR compiler and CPU image sources

The shared producer extracts selected declarations and unchanged functions from
[Mesa 26.2.6](https://archive.mesa3d.org/mesa-26.2.6.tar.xz). The archive pin
and common downstream patches belong to `profiles/common-graphics` and the
MesaLib package. `compute-image/sources.tsv` pins the specific host inputs;
`compute-image/LICENSE` preserves the upstream MIT notices for the extracted
material. Local producer code carries its own SPDX and copyright notices.

The `a733-accelerators` compatibility paths refer to this shared producer.
The source-causal IDFWDF layout adjustment is in the common MesaLib patch; the
host shader and image producer both verify the same patched header. Neither
this producer nor its compiler evidence contains firmware or proves execution.
