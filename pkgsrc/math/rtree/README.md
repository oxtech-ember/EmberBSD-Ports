# RTree provider provenance

This package exports the generic `rtree::rtree` header-only target and
`<geometry/rtree.h>` include from KiCad 10.0.8's `thirdparty/rtree` subtree.
The exact source archive is pinned in `distinfo`, and extraction is restricted
to that subtree.

KiCad's versioned header preserves its GPLv3 additions: filtered range
iterators, visitor and completion-aware search overloads, `CalcStats`, and
`NearestNeighbors`. These APIs are used by KiCad's schematic and geometry
index wrappers. The current `nushoin/RTree` upstream is a distinct, newer
header-only API and does not provide this KiCad surface, so substituting it
would require consumer rewrites and would lose behavior. The packaged header
therefore carries KiCad's GPLv3-or-later terms; its upstream pointer is
`https://github.com/nushoin/RTree`.
