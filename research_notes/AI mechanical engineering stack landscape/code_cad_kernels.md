# Programmable (code-CAD) geometry kernels, libraries and APIs for an LLM-driven mechanical CAD agent (state as of Nov 2026)

Method note for the report writer: in this session only github.com could be fetched directly. arxiv.org, zoo.dev and buildcad.ai were blocked by the network allowlist, so paper numbers, Zoo pricing and MCP-guide details below come from search-result summaries of those pages, not from reading the pages. They are marked "(search summary)". Anything I could not source is in Gaps or is labelled as unsourced background in Inferences.

## 1. Trade-offs between B-rep, mesh/CSG and implicit/SDF representations for a pipeline that must feed simulation and CAM

### Takeaway
B-rep (in practice OCCT for open source) is the only representation that natively produces the STEP/trimmed-NURBS solids that CAM and CAE tools expect; implicit kernels cannot export STEP directly and mesh/CSG kernels output only tessellations. The price of B-rep is weaker robustness (fillets, booleans, face identity).

### Cited Findings
- Fidget's author states it does not support STEP export "because STEP files use a completely different underlying representation. Most STEP files represent shapes as a set of surfaces (e.g. trimmed NURBS)" (search summary of HN thread) — [HN: Fidget](https://news.ycombinator.com/item?id=42634624)
- Fidget meshes using manifold dual contouring, and its meshing is described as much less battle-tested than libfive's (search summary) — [HN: Fidget](https://news.ycombinator.com/item?id=42634624); background talk: [Keeter, "Fidget: Yet Another Implicit Kernel", July 2024](https://www.mattkeeter.com/research/fidget-2024.pdf)
- nTop (proprietary implicit kernel) can export implicit or mesh parts to STEP or Parasolid through a quad-mesh conversion route, but its documentation says that route should not be used for lattices or TPMS structures; a separate implicit-to-CAD block for those is still labelled Beta. Support guidance says the mesh-based route works reliably only on fairly simple models such as topology-optimisation results (search summary) — [nTop: How to export geometry as a CAD part](https://support.ntop.com/hc/en-us/articles/7323484481555-How-to-export-geometry-as-a-CAD-part-STEP-or-Parasolid); [nTop: Conversion to CAD with Quadrangulate Mesh](https://learn.ntop.com/lessons/conversion-to-cad-with-quadrangulate-mesh/)
- nTop 5.0 introduced a new implicit modelling kernel; the vendor says better CAD body export and meshing are planned (search summary) — [nTop 5.0 release note](https://support.ntop.com/hc/en-us/articles/26062971882131-nTop-5-0-New-Implicit-Modeling-Kernel)
- Manifold (mesh boolean kernel) became OpenSCAD's default backend in August 2025; CGAL remains available with `--backend=cgal` (search summary) — [OpenSCAD commits](https://github.com/openscad/openscad/commits/master/)
- OCCT's fillet is geometric and "automatically extended to all edges in a smooth continuity with the original edge", which is one reason a selection can fillet more edges than intended (search summary) — [OCCT Modeling Algorithms guide](https://occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html)
- OCCT 8.0.0 final was announced in May 2026 after five release candidates and three betas, with more than 500 changes since 7.9.0; it requires C++17; 8.0.1 is the first maintenance release and 8.0.0p1 a hot patch. It adds BRepGraph, a topology-geometry graph layer described as a new way to work with B-rep topology (search summary) — [OCCT 8.0.0 release discussion](https://github.com/Open-Cascade-SAS/OCCT/discussions/1275); [OCCT releases](https://github.com/Open-Cascade-SAS/OCCT/releases)
- Zoo describes its engine as a custom "GPU-native Geometry Engine" built from the ground up (search summary) — [Zoo Design API](https://zoo.dev/design-api)

### Inferences
- For an agent that must hand geometry to CAM and FEA, B-rep is the safe primary representation: STEP out is native, and faces/edges remain analytic (planes, cylinders) so CAM feature recognition and CAE boundary-condition selection work. Mesh/CSG (OpenSCAD, Manifold, JSCAD) is robust for booleans but yields STL/3MF only, so it suits 3D printing but not machining or drawing workflows. Implicit/SDF is strongest for lattices, offsets and blends that break B-rep kernels, but reaching STEP needs a lossy conversion.
- Unsourced background (my general knowledge, not verified in this session): Parasolid (Siemens) and ACIS (Dassault/Spatial) are proprietary, commercially licensed kernels generally regarded as more robust than OCCT for fillets/shelling; they are reachable for a small team mainly indirectly via Onshape (Parasolid), SolidWorks (Parasolid) or Fusion (Autodesk ShapeManager, an ACIS derivative). Treat as background to verify.
- A hybrid is plausible: B-rep for the prismatic "engineering" body, mesh or implicit only for regions that need it, accepting that those regions will not export as clean STEP.

### Gaps
- No source found on how CAM tools handle implicit or mesh-derived geometry versus B-rep (search returned nothing).
- No quantitative robustness comparison (fillet/boolean/shell failure rates) between OCCT, Parasolid, ACIS and Zoo's engine was found.
- Whether OCCT 8.0 improved fillet or boolean robustness specifically was not found; the 8.0.0 release notes need to be read directly.
- Parasolid/ACIS licensing terms and prices for a small team were not researched.

## 2. Comparison of libraries, kernels and APIs: headless Linux operation, licences, activity and versions

### Takeaway
The open-source OCCT-based Python stack (build123d, CadQuery, OCP, FreeCAD) is the most active option that runs fully in a Linux container, and all of it moved to or toward OCCT 8.0 during 2026. Commercial options are either cloud APIs with metering (Zoo, Onshape, Fusion Automation) or desktop-bound; of the Rust kernels, Fornjot was shut down in June 2026.

### Cited Findings

**build123d (Python, OCCT via OCP)**
- Releases shown on GitHub (page gives day/month only; years inferred from sequence): v0.10.0 (5 Nov), v0.11.0 (17 Jun) which dropped the transitive VTK dependency by moving to cadquery-ocp-novtk 7.9 and added Python 3.14 support, v0.11.1 (2 Jul), v0.12.0 (18 Sep) adding materials, UV texture coordinates with `export_obj()` and breaking API changes (e.g. `add()` renamed `insert()`, tangent arc/line classes replaced by `ConstrainedArcs`/`ConstrainedLines`), and v0.13.0 (21 Sep) which upgraded the kernel to OCP 8.0.1 — [build123d releases](https://github.com/gumyr/build123d/releases)
- The roadmap's goal for 1.0.0 is a stable API; 1.0 had not been reached (search summary) — [build123d Roadmap](https://scour.ing/p/https://github.com/gumyr/build123d/wiki/Roadmap)
- A September 2026 blog reports about 2,645 GitHub stars and active development (secondary source) — [brightcoding blog](https://blog.brightcoding.dev/2026/09/21/gumyrbuild123d-pythonic-cad-for-parametric-3d-modeling)
- build123d is described as an evolution of CadQuery in which the fluent method-chaining API is replaced by stateful context managers (search summary) — [build123d on PyPI](https://pypi.org/p/build123d)

**CadQuery / OCP (Python, OCCT)**
- Releases shown on GitHub (day/month only): 2.5.0–2.5.2 (2–3 Jan), 2.6.0 (6 Oct), 2.6.1 (28 Oct), 2.7.0 (13 Feb), 2.8.0 (20 Jun, marked Latest) — [CadQuery releases](https://github.com/CadQuery/cadquery/releases)
- CadQuery 2.7.0 metadata pins `cadquery-ocp<7.9,>=7.8.1`, i.e. OCCT 7.8.x (search summary of a package metadata file) — [cadquery 2.7.0 METADATA](https://zimaos.tailde1d02.ts.net/.local/lib/python3.12/site-packages/cadquery-2.7.0.dist-info/METADATA)
- OCP 7.9 wheels exist: stubs package 7.9.3.0 dated 3 Jan 2026 and novtk/wasm builds 7.9.3.1 from May 2026; CadQuery docs PDF is titled 2.9.0.dev0, dated 22 Jun 2026 (search summary) — [cadquery-ocp on PyPI](https://pypi.org/project/cadquery-ocp); [CadQuery docs PDF](https://cadquery.readthedocs.io/_/downloads/en/latest/pdf/)

**pythonOCC**
- GitHub README lists 7.9.0 (April 2025) as latest release; a FreshPorts entry shows an 8.0.0.a build dated 15 Aug 2026 (apparently a pre-release); licence is LGPL v3 (search summary) — [pythonocc-core](https://github.com/tpaviot/pythonocc-core); [FreshPorts](https://freshports.org/cad/pythonocc-core/)

**FreeCAD (Python API, headless)**
- FreeCAD 1.1 was released on 24 March 2026 (wiki; one article says 25 March), after RC1 in Nov 2025 and RC3 in Feb 2026; 1.1.1 followed on 15 April 2026 — [Release notes 1.1](https://wiki.freecad.org/Release_notes_1.1); [FreeCAD 1.1.1 released](https://blog.freecad.org/2026/04/15/freecad-1-1-1-released/); [RC1 post](https://blog.freecad.org/2025/11/26/the-first-release-candidate-of-freecad-1-1-is-out/)
- The 1.1 release notes describe "continued improvements to topological naming mitigation"; the naming algorithm first shipped in 1.0 and the wiki says it will be applied to more parts of FreeCAD with more repair tooling later (search summary) — [FreeCAD 1.1 release page](https://freecad.github.io/Website/download/releases/1-1/); [Topological naming problem wiki](https://wiki.freecad.org/Topological_naming_problem/en)
- FreeCAD 1.0 (Nov 2024) added a built-in Assembly workbench and TNP fixes — [AlternativeTo news](https://alternativeto.net/news/2024/11/freecad-1-0-launches-with-enhanced-ui-ux-built-in-assembly-workbench-and-tnp-fixes/)

**OpenSCAD / Manifold**
- Latest OpenSCAD pre-release found is openscad-2026.11-RC0 (published 7 Nov); no 2026 stable release was found, and a third-party issue states the last tagged stable is still 2021.01 (conflict unresolved; verify on the releases page) — [OpenSCAD releases](https://github.com/openscad/openscad/releases); [third-party issue](https://github.com/catduckgnaf/print-handy/issues/1050)
- OpenSCAD's Manifold submodule was bumped to v3.5.4 (merged 25 Oct 2026); the newest manifold3d on PyPI is reported as 3.5.3 (7 Sep 2026) (search summary) — [OpenSCAD PR #7100](https://github.com/openscad/openscad/pull/7100); [manifold3d on PyPI](https://pypi.org/project/manifold3d/2.5.0/)

**Zoo / KittyCAD (KCL, Design API, Zookeeper)**
- Zoo's FAQ says its CAD geometry engine is not open source; the Design Studio app (KittyCAD/modeling-app) is open source and its repo lists an MIT licence (search summary) — [Zoo FAQ](https://zoo.dev/docs/faq); [KittyCAD/modeling-app](https://github.com/kittycad/modeling-app)
- API rate is about $0.0083 per second (about $0.50 per minute) after a free allowance; one page version says 40 free minutes, an older one 20 free minutes ($10 balance). The FAQ says usage is charged by the second and failed calls are not charged; a third-party guide claiming round-up to one minute conflicts with this (search summary) — [Zoo Design API](https://zoo.dev/design-api); [Zoo FAQ](https://zoo.dev/docs/faq); contradicted on rounding by [third-party guide](https://artificial-intelligence-wiki.com/ai-tools/ai-design-tools/zoo-dev-kittycad-guide/)
- Text-to-CAD returns STEP and glTF as the initial output at no extra charge; converting to other formats such as STL is billed as extra server time (search summary) — [Turning on billing for Text-to-CAD](https://zoo.dev/blog/turning-on-billing-for-text-to-cad)
- Zookeeper is Zoo's conversational CAD agent built into Design Studio, sold in Free/Plus/Pro tiers; Zookeeper reasoning and billable API activity "direct or via Zoo MCP" draw from the same monthly usage credit, while manual CAD modelling in Design Studio stays unlimited (search summary) — [Announcing Zookeeper](https://zoo.dev/blog/announcing-zookeeper); [Pricing](https://kittycad.io/pricing)
- Zoo Design Studio reached v1 (search summary; date not captured) — [Zoo Design Studio v1 blog](https://zoo.dev/blog/zoo-design-studio-v1)

**Onshape (REST API + FeatureScript)**
- Onshape enforces annual API call limits by account type at company level; once exhausted, requests return HTTP 402. Per-endpoint rate limits return 429 and exact values are not published — [Onshape API Limits](https://onshape-public.github.io/docs/auth/limits/)
- Third-party figures: Free/Standard/EDU 2,500 calls per user per year, Professional 5,000, Enterprise 10,000 (secondary; verify) — [onshape-api-toolkit rate-limit notes](https://github.com/SergeyMokhov/onshape-api-toolkit/blob/main/docs/08-rate-limits-and-errors.md); [checkthat.ai pricing summary](https://checkthat.ai/brands/onshape/pricing)
- Practitioners hit 429 errors in automated pipelines (e.g. onshape-to-robot) — [onshape-to-robot issue #170](https://github.com/Rhoban/onshape-to-robot/issues/170)

**Autodesk Fusion (APS Automation API)**
- Automation API for Fusion became generally available on 19 May 2025; it runs Fusion scripting API tasks in the cloud without user interaction, priced at 3.0 Flex tokens per processing hour at launch (open beta from Feb 2025 was free) (search summary; re-check current rate) — [APS blog: Automation API for Fusion GA](https://aps.autodesk.com/blog/design-automation-api-fusion-now-generally-available)
- A separate Fusion Operations API was in public beta as of 18 May 2026 — [APS blog](https://aps.autodesk.com/blog/fusion-operations-api-now-available-whats-new-and-what-it-means-you)

**Replicad / OpenCascade.js / JSCAD (JavaScript)**
- OpenCascade.js is LGPL; replicad-opencascadejs (replicad's custom OCCT wasm build) is at 0.23.0 with an MIT licence; @jscad/web changelog shows 2.6.13 dated 22 Feb 2026 (search summary) — [OpenCascade.js about](https://ocjs.org/docs/about); [replicad-opencascadejs](https://www.jsdelivr.com/package/npm/replicad-opencascadejs?tab=files); [JSCAD changelog](https://cdn.jsdelivr.net/npm/@jscad/web@2.6.13/CHANGELOG.md)

**Rust kernels**
- Fornjot was shut down: the GitHub repo was archived on 19 June 2026 and the README says the project's goals were never reached; last versions were 0.49.0 — [hannobraun/fornjot](https://github.com/hannobraun/fornjot)

### Summary table (sourced cells cite the findings above; cells marked * are unsourced background from my general knowledge and should be verified)

| Option | Representation / kernel | Headless Linux container | Licence | Latest version found | Notes |
|---|---|---|---|---|---|
| build123d | B-rep, OCCT 8.0.1 via OCP | Yes* (pip wheel) | Apache-2.0* | v0.13.0 (Sep 2026) | Pre-1.0, frequent breaking changes |
| CadQuery | B-rep, OCCT 7.8.x via OCP (2.7.0) | Yes* (pip/conda) | Apache-2.0* | 2.8.0 (Jun 2026) | Largest LLM benchmark corpus (section 3) |
| OCP | Raw OCCT bindings | Yes* | Apache-2.0 bindings over LGPL OCCT* | 7.9.3.x wheels; 8.0.1 used by build123d | Verbose, full kernel access |
| pythonOCC | Raw OCCT bindings (SWIG) | Yes* (conda) | LGPL v3 | 7.9.0 (Apr 2025); 8.0.0 alpha seen | Slower release cadence |
| FreeCAD Python | B-rep, OCCT; feature tree, sketcher, Assembly, TechDraw, FEM, CAM | Yes* (`freecadcmd`) | LGPL* | 1.1.1 (15 Apr 2026) | Only open option with history tree + TNP mitigation |
| OpenSCAD | Mesh CSG, Manifold default | Yes* (CLI) | GPL* | 2026.11-RC0; stable status unclear | No STEP, no fillets as first-class ops* |
| Manifold | Mesh boolean library | Yes* (manifold3d wheel) | Apache-2.0* (not confirmed) | 3.5.4 | Guaranteed-manifold booleans* |
| JSCAD | Mesh CSG in JS | Yes* (Node) | MIT* (not confirmed) | 2.6.13 (Feb 2026) | No STEP* |
| Replicad | B-rep, OCCT wasm | Yes* (Node) | MIT (wasm build pkg); core not confirmed | 0.23.0 (wasm pkg) | Browser-friendly |
| Zoo KCL / Design API | Proprietary GPU B-rep engine, cloud | Client is headless; engine is a remote service | Engine proprietary; app MIT | Design Studio v1 | ~$0.50/min metered |
| Onshape API + FeatureScript | Parasolid*, cloud | Client is headless; SaaS | Proprietary subscription | n/a | Annual API call caps |
| Fusion Automation API | Autodesk kernel, cloud | Yes (cloud job) | Proprietary; Flex tokens | GA May 2025 | 3.0 Flex tokens/hr at launch |
| SolidWorks API | Parasolid*, desktop | No* (Windows COM) | Proprietary | not researched | See Gaps |
| Rhino.Compute | NURBS surface modeller | Not confirmed | Proprietary | not researched | See Gaps |
| truck (Rust) | B-rep | not researched | not researched | not researched | See Gaps |
| Fornjot (Rust) | B-rep | n/a | n/a | 0.49.0, archived 19 Jun 2026 | Dead |
| libfive / Fidget | Implicit | Yes* | not confirmed | not researched | No STEP export |

### Inferences
- OCCT 8.0 adoption is uneven as of late 2026: build123d is on OCP 8.0.1 while the last CadQuery release whose pin I saw (2.7.0) targets 7.8.x. A team mixing both libraries in one environment should check the OCP pin of CadQuery 2.8.0 first.
- build123d's release cadence (four releases Jun–Sep 2026, each with breaking changes) means LLM training data lags the API; pinning a version and supplying current docs in context is needed.
- Zoo's metering (per compute-second) and Onshape's annual call caps (thousands of calls per user per year) both constrain a high-iteration agent loop that rebuilds geometry hundreds of times per task; a local OCCT stack has no such marginal cost.
- For a small team prioritising headless Linux, the practical shortlist is build123d or CadQuery (code-first B-rep), FreeCAD (when a feature tree, assemblies, drawings or built-in FEM/CAM are needed), and Zoo or Onshape as a commercial-kernel fallback for geometry OCCT cannot build.

### Gaps
- truck (Rust): no information found in this session on status, version or features.
- SolidWorks API and Rhino.Compute/Grasshopper: searches returned nothing; headless/Linux status, licensing and versions are unverified.
- Licences for build123d, CadQuery, OCP, OpenSCAD, Manifold, JSCAD, FreeCAD, libfive and Fidget were not confirmed from sources in this session (table cells marked *).
- KCL's own licence is unclear: Zoo's blog calls KCL open source while the FAQ only calls it Zoo's scripting language.
- Current Zoo subscription tier prices (Free/Plus/Pro) and any self-hosted engine option were not retrieved (zoo.dev blocked).
- OpenSCAD stable-release status in 2026 is unresolved (RC seen, no stable confirmed).
- GitHub star counts and commit activity were only obtained for build123d (secondary source).
- "Newer kernels 2024-2026": apart from OCCT 8.0's BRepGraph and Zoo's engine, I found no new open-source B-rep kernel; I did not run a dedicated search, so absence is not established.
- Export format matrix (STEP/IGES/STL/3MF per tool) was not confirmed per tool from sources.

## 3. Evidence on which CAD language LLMs generate most reliably

### Takeaway
There is no single head-to-head study across CadQuery, OpenSCAD, build123d and KCL. Most 2026 benchmarks are CadQuery-only; they agree that executability is a poor proxy for correct geometry and that models fail on sweeps, lofts and shells. One agent paper found build123d gave the highest Pass@1, and one multimodal benchmark found a larger drop on CadQuery than on OpenSCAD.

### Cited Findings
- CADDesigner ran CadQuery and build123d inside the same agent framework on 200 test models; build123d attained the highest Pass@1 and shortest latency. The authors note simpler APIs can improve early success and reduce execution time but may compromise geometric accuracy (search summary) — [CADDesigner, arXiv 2508.01031](https://arxiv.org/pdf/2508.01031)
- P3D-Bench evaluates the same multimodal models on CadQuery and OpenSCAD; the reported drop in its geometry score is larger on CadQuery (-0.057 on average) than on OpenSCAD (-0.023). This is a score drop, not a success rate, and build123d is not included (search summary) — [P3D-Bench, arXiv 2606.11152](https://arxiv.org/html/2606.11152v1)
- Text2CAD-Bench (600 examples, three difficulty levels) scores LLM-generated CadQuery by invalidity rate, Chamfer Distance and IoU. Its leaderboard lists GPT-5.2 first on L2 with invalidity 30.6% and IoU 0.45, then Claude-4.5-Sonnet with invalidity 41.3% and IoU 0.43. The domain-specific Text2CAD model is almost always executable (7.0% invalid) but has IoU 0.05. All models degrade at L3 (sweeps, lofts, shells). Paper text and leaderboard numbers differ, so verify against the paper (search summary) — [Text2CAD-Bench, arXiv 2605.18430](https://arxiv.org/html/2605.18430v1); [HF dataset/leaderboard](https://huggingface.co/datasets/AICAD/Text2CAD-Bench)
- Text2CAD-Bench ablations: Python CadQuery representations significantly outperform DeepCAD-style command sequences on execution validity and geometric accuracy; executability, geometric precision and design-intent understanding often do not correlate (search summary) — [Text2CAD-Bench review](https://www.themoonlight.io/fr/review/text2cad-bench-a-benchmark-for-llm-based-text-to-parametric-cad-generation)
- BenchCAD contains 17,900 execution-verified CadQuery programs across 106 industrial part families; reported execution rates range from 67.5% to 99.0% depending on model (models not identified in the summary); models recover coarse shape but systematically replace sweeps, lofts and twist-extrudes with simpler operations (search summary) — [BenchCAD, arXiv 2605.10865](https://arxiv.org/pdf/2605.10865)
- MUSE reports current LLMs for text-to-CAD "remain far from producing usable designs", with a failure cascade from executable code to valid geometry to engineering-ready design (search summary) — [MUSE, arXiv 2605.28579](https://arxiv.org/pdf/2605.28579)
- Unverified practitioner claims: a blog reports OpenSCAD producing about 3 errors against 40 for build123d (citing a secondary source, no paper); a GitHub issue reports a build123d MCP raising a "CADGenBench" score from 0.360 to 0.457, self-reported on a small set. Neither is an established result — [torno issue #42](https://github.com/luisg0nc/torno/issues/42)

### Inferences
- CadQuery has by far the most benchmark and training-data coverage, which makes it the lowest-risk target for raw LLM generation; build123d has one favourable agent-loop result but is under-represented in benchmarks and changes API often.
- OpenSCAD's small, stable language probably explains its lower error/drop figures, but those benchmarks score shape similarity and do not penalise the lack of STEP output or fillets, so "more reliable" there does not mean more useful for mechanical work.
- Because executability does not track geometric correctness, an agent needs geometric verification in the loop (volume, bounding box, rendered views, feature checks) regardless of language.
- Benchmark model names (GPT-5.2, Claude-4.5-Sonnet) are a generation or more behind late-2026 frontier models, so absolute rates are likely pessimistic for current models; relative findings about hard operations are more durable.

### Gaps
- No benchmark including KCL was found; Zoo has not, as far as I could find, published comparative success rates.
- No study directly comparing all of CadQuery, build123d, OpenSCAD and FreeCAD Python under identical conditions was found.
- Exact CADDesigner Pass@1 figures and the LLMs used were not retrieved (arxiv.org blocked).
- No benchmark results for assemblies beyond the title of ASSEMCAD (arXiv 2607.05123), which I did not read.

## 4. Known pain points: topological naming, fillets, selection, tolerances, STEP fidelity, assemblies, GD&T/PMI, drawings

### Takeaway
Face/edge identity is the central unsolved problem in code-CAD on OCCT: build123d and CadQuery have no persistent naming, and FreeCAD only mitigates it. OCCT can read and write AP242 GD&T through XDE, but users report that exported PMI is not always recognised by other tools, and the Python code-CAD libraries do not expose it at a high level.

### Cited Findings
- A build123d issue proposing persistent tags on sub-shapes lists the known failure cases: a tagged face that splits gives its tag to both halves, merged faces must reconcile tags, and a tag on a face consumed by a fillet is lost — [build123d issue #1454](https://github.com/gumyr/build123d/issues/1454)
- A Hacker News commenter on build123d reports "zero mitigation for toponaming" and calls index-based selection extremely brittle, though still used when composing a selector is too awkward; another notes that not all STEP importers are robust with files from OCCT-based packages (anecdotal) — [HN: build123d](https://news.ycombinator.com/item?id=47567242)
- A third-party project proposes naming faces/edges from construction history using OCCT's Generated/Modified history with fallback to geometric similarity, showing the usual workaround design — [BetterCad issue #47](https://github.com/kevinmcaleer/BetterCad/issues/47)
- FreeCAD's TNP algorithm shipped in 1.0 and 1.1 continues "mitigation" rather than claiming a full fix — [FreeCAD TNP wiki](https://wiki.freecad.org/Topological_naming_problem/en); [FreeCAD 1.1 release page](https://freecad.github.io/Website/download/releases/1-1/)
- OCCT fillets propagate automatically along tangent-continuous edges — [OCCT Modeling Algorithms guide](https://occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html)
- build123d reworked 2D filleting in 2026: `fillet_2d` handles fillets that consume whole edges and the OCCT ChFi2d algorithm was replaced, indicating the upstream algorithm was a source of failures (search summary) — [build123d releases](https://github.com/gumyr/build123d/releases)
- OCCT's XDE can read and write several types of GD&T data; writing PMI requires AP242 schema, `write.stepcaf.annot` and `SetDimTolMode(true)` on the STEPCAF writer — [OCCT XDE user guide](https://dev.opencascade.org/doc/overview/html/occt_user_guides__xde.html); [OCCT forum: writing STEP with GD&T](https://dev.opencascade.org/content/how-do-i-write-step-gdts)
- Users report exported graphical PMI not being recognised by the NIST STEP viewer or Autodesk Inventor, and difficulty linking semantic GD&T entities to shape aspects when reading AP242 — [OCCT forum: exported PMI not picked up](https://dev.opencascade.org/content/exported-pmi-graphical-presentation-step-not-picked-other-cad-tools); [OCCT forum: missing presentation PMI](https://dev.opencascade.org/content/missing-presentation-pmi-step-export-stepcafcontrolwriter)
- A community package, build123d-drafting-helpers, was released in May 2026, indicating drawing/drafting support in build123d is an add-on area — [PyPI feed](https://pypi.org/rss/project/build123d-drafting-helpers/releases.xml)

### Inferences
- For an LLM agent the practical mitigation is to regenerate the whole model from source each time and select faces/edges by geometric predicates (position, normal, type, size) rather than by index, then verify the selection count before applying fillets or chamfers.
- Fillet/chamfer/shell steps should be applied late and wrapped in try/fallback logic (smaller radius, fewer edges), since they are the operations benchmarks show models avoid and that OCCT is most likely to reject.
- GD&T/PMI and 2D drawings are the weakest part of the open stack: achievable via raw OCCT XDE or FreeCAD TechDraw, but with interoperability risk; a commercial tool (Onshape, Fusion, SolidWorks) is the likely route if release-quality drawings or MBD are required.

### Gaps
- No sources found on PMI/GD&T support in CadQuery or build123d, nor on FreeCAD TechDraw running headless.
- No sourced data on OCCT tolerance problems, shelling failures or boolean failure rates; fillet-failure evidence is indirect.
- Assembly constraint/mate support in CadQuery (assembly solver), build123d (joints) and FreeCAD Assembly workbench was not verified from sources in this session.
- STEP round-trip fidelity between OCCT and commercial kernels: only one anecdotal comment found.
- No information retrieved on drawing generation in Zoo, Onshape API or Fusion Automation.

## 5. Existing MCP servers and agent tool integrations for CAD and their maturity

### Takeaway
By late 2026 Autodesk and PTC both ship vendor-backed MCP servers (Fusion built in locally; Onshape hosted and FeatureScript-focused), Zoo exposes an MCP that bills against API credit, and FreeCAD is served by community projects led by neka-nat/freecad-mcp. No well-maintained CadQuery MCP was identified, and most detail here comes from third-party guides that disagree on specifics.

### Cited Findings
- Fusion: a guide reports an Autodesk-built MCP server included in Fusion desktop since May 2026, enabled under Preferences > General > API and listening on http://127.0.0.1:27182/mcp while Fusion is open; a separate Fusion Data server handles project-level data, not design geometry; community Fusion servers also exist (one with 27 tools) (secondary sources, not checked against Autodesk docs) — [Leo AI: CAD MCP comparison 2026](https://www.getleo.ai/blog/cad-mcp-server-comparison-2026); [TechDraw AI: CAD MCP servers](https://techdrawai.com/blog/cad-mcp-servers)
- Autodesk also lists a "Fusion Automation MCP Beta" feedback programme — [Autodesk feedback portal](https://feedback.autodesk.com/key/FusionAutomationMCP)
- Onshape: PTC's MCP server is distributed through Onshape Labs, hosted, in early access, and focused on writing FeatureScript custom features rather than drawing geometry directly; access reportedly needs a subscription and admin permission (secondary) — [TechDraw AI: Connect Claude to Onshape](https://techdrawai.com/blog/connect-claude-to-onshape); [Leo AI comparison](https://www.getleo.ai/blog/cad-mcp-server-comparison-2026)
- FreeCAD: neka-nat/freecad-mcp is the most-starred community server; star counts vary by source (about 2,900 in Oct 2026 in one guide, 1,709 in another). It requires installing an add-on inside FreeCAD and running its RPC server. One guide warns these community projects sit on an older version of the MCP specification, so maintenance should be checked (secondary) — [buildcad.ai guide](https://buildcad.ai/guides/cad-mcp-servers); [ChatForest review](https://chatforest.com/reviews/cad-3d-modeling-mcp-servers/)
- CadQuery: one guide says it found no maintained CadQuery MCP server worth listing (secondary) — [buildcad.ai guide](https://buildcad.ai/guides/cad-mcp-servers)
- Zoo: the pricing page refers to billable API activity "direct or via Zoo MCP"; the FAQ says an MCP tool call is not itself the billing unit because a tool may run locally or make one or more API calls (search summary) — [Pricing](https://kittycad.io/pricing); [Zoo FAQ](https://zoo.dev/docs/faq)
- build123d: a community "build123d-mcp" exists with self-reported benchmark gains (unverified) — [torno issue #42](https://github.com/luisg0nc/torno/issues/42)
- Other round-ups list MCP servers for Blender, AutoCAD, KiCad, SolidWorks and OpenSCAD — [Snyk: 9 MCP servers for CAD](https://snyk.io/articles/9-mcp-servers-for-computer-aided-drafting-cad-with-ai/); [ChatForest review](https://chatforest.com/reviews/cad-3d-modeling-mcp-servers/)

### Inferences
- The vendor MCP servers are tied to a running desktop app (Fusion) or a hosted subscription (Onshape), so neither is a drop-in for a containerised Linux agent; the FreeCAD community server also assumes a running GUI instance with an add-on.
- For code-CAD libraries an MCP layer adds little: an agent with a Python sandbox can call build123d or CadQuery directly, which likely explains the absence of a mature CadQuery MCP. A thin in-house tool (execute script, return errors, metrics and rendered views) is the more common pattern.
- Maturity ranking by evidence found: Fusion (vendor, shipped in product) > Onshape (vendor, early access) and Zoo (vendor) > FreeCAD community servers > others.

### Gaps
- None of the MCP details were verified against Autodesk, PTC or Zoo primary documentation; buildcad.ai and zoo.dev could not be fetched.
- Tool lists, version numbers and last-commit dates for individual MCP servers were not obtained.
- No information found on a SolidWorks MCP's maturity or on Blender MCP's relevance to mechanical CAD beyond listing.
- No evaluation data comparing agent performance with and without these MCP servers, other than one self-reported figure.
