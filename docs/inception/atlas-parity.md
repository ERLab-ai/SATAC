# Atlas parity — owner-approved direction, 2026-11-27

v0.13 is the product/visual reference; v0.14 is the architectural reference. Acceptance requires restoring the legacy experience on the new architecture, not substituting a dashboard. Reference: baseline/v0.13 at 46a48ec5bd3656b2c514458d1637358a28664088, original archive src/atlas.html and docs/geology-preview.png, article.png, mobile.png. No phase closure implied.

| Feature | Current implementation / next acceptance |
|---|---|
| Dark teal/gold visual identity, map-first workspace | Implemented candidate; browser visual review still required |
| Floating controls, search and reader, mobile map-first | Implemented candidate; verify keyboard and responsive layout |
| Timeline | Bottom exact year navigation and playback, no year zero; restore legacy six era selectors after era mappings and data migration |
| Place symbols and names | Point labels for small datasets, generic markers; restore category-specific sigils; 91 geographic labels restored as scale-dependent reference labels |
| Map tools | Region/world, scale, zoom; synchronized minimap and world reset added; dedicated fullscreen pending |
| Layers and lenses | Location and geographic-label toggles; relief/ETOPO/flat/hex backdrop and reference river toggle; restore legacy atlas, historical places, density and thematic layers |
| Terrain, elevation/bathymetry, hex grid | Relief and ETOPO reference imagery reprojected to Web Mercator raster tiles; 37,209 original regional visual hexagons restored; relief residual texture, analytical cells, true DEM and finer detail pending |
| Encyclopedia | 50 main articles and original bibliography restored in candidate; thematic reader, search and editorial map anchors; legacy artwork and extended articles pending |
| Historical gazetteer and settlements | 190 historical and 323 modern source records restored in directory candidate; separate reference overlay; reconciliation and exact temporal extents pending |
| Relations, journeys, route network, historical political comparison | 13 editorial connections and 8 ordered thematic journeys restored as candidate; original route network and historical political comparison pending |
| Resources, geology, volcanism, cells | Pending original dataset migration and visualization |
| Offline use | Legacy standalone reference retained; new API requires server. Offline strategy pending |
| Engineering | Keep policy v1.2, stable identities, release-scoped public reads, spatial/temporal precision and regression tests |

No fake data, dummy buttons or historical boundary inference. Feature priority is not a change to formal P0/P1 gates. Require an explicit legacy-function regression matrix, comparable visual captures desktop/mobile, content inventory, API/database and browser tests before replacement release.

Route candidate: 145 original segments, 135 source graph nodes; source-weight Dijkstra and separate map overlay. Browser verification pending; previous directory cycle had four map initialization failures, corrected invalid match expression. Historical territories remain pending.

Historical snapshots candidate: 27 original polygons (five source years) and four original event points; explicit source-year temporal normalization, independent comparison and linked detail. No interpolated boundaries. Corrected prior release variable ordering build failure; browser validation pending.

Geology candidate: 44 original valid provinces and 12 volcanic sites, reference layers, original colors and filters, PostGIS point/polygon associations, retained source files. Cell intersection reader and resource metrics pending. No historical geological reconstruction.

Cell metric candidate: all 2480 original measured records, 1847 pinned geological links, four reference lenses, selectable cell reader and map overlay. Local source geometry cross-check passed; integration pending. Geosite stories and full parity review remain pending.

Extended topics: five original historical stories and two geosite articles, separate collection and original reference anchors, directory reader link; seven additional versioned works. 57 source topics in total. Legacy illustrations, era selectors and complete parity pending.

Visual/thematic candidate: restored all 11 original article SVG illustrations and 13 original category icon SVGs; six original thematic selectors shared by main article reader and map. Exact-year mode remains separate. Historical/modern directory and routes follow original thematic eligibility; editorial links require both endpoints and journeys require all stops to match selected theme. Extended markers gated by story/islamic and geosite/modern (original eligibility, not exact chronology). Eight original directory type glyphs restored in list/details; map type glyphs, full geographic borders/grid, texture, source-era precision, unified search and actual visual acceptance remain pending.

Cartographic candidate: original 458 global and 127 regional border paths (126 nondegenerate regional lines, one omitted zero-length), coarse outside-region fallback, 15-degree graticule, reprojected original alpha texture, relief fallback outside regional hex extent, and eight MapLibre historical type sprites with collision placement and circle fallback. Modern border toggle disabled in dated and historical thematic modes. Actual browser/visual verification pending. Unified search/layer controls, label parity and full-screen remain pending.

Integrated exploration candidate: single public release-consistent search for canonical names plus five reference views, with explicit separation from temporal matches, bounded reference list and type filter; centralized layer settings shared with specialist panels and map controls. Snapshot hits explicitly navigate to source year. No automatic entity merge. Search does not yet include route graph edges, cell metrics or full article body indexing. UI/performance acceptance pending.
