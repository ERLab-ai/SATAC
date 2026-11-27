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
| Historical gazetteer and settlements | Three-place sample only; migrate legacy collections with provenance |
| Relations, journeys, route network, historical political comparison | Pending legacy migration and interactive visualization |
| Resources, geology, volcanism, cells | Pending original dataset migration and visualization |
| Offline use | Legacy standalone reference retained; new API requires server. Offline strategy pending |
| Engineering | Keep policy v1.2, stable identities, release-scoped public reads, spatial/temporal precision and regression tests |

No fake data, dummy buttons or historical boundary inference. Feature priority is not a change to formal P0/P1 gates. Require an explicit legacy-function regression matrix, comparable visual captures desktop/mobile, content inventory, API/database and browser tests before replacement release.
