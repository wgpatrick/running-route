# Integration, glue, infrastructure, licensing, risks and build order for an AI-driven mechanical engineering pipeline (state as of Nov 2026)

Researcher note on method and reliability: this session's network policy blocked direct page fetches (arxiv.org, simscale.com, themoonlight.io, zeli.app all failed to resolve). Every finding below therefore rests on search-result extracts of the cited pages, not on a full read of the page. Numbers from the Hephaestus-CCX paper were returned consistently by three separate searches; most other numbers were seen once. Items marked "vendor-reported" come from company blogs or press releases. Anything I could not source is under Gaps or labelled as inference.

## 1. Which projects already chain code-CAD + meshing + FEA/CFD + optimisation + CAM in one scripted or agentic pipeline, and what do they demonstrate vs claim?

### Takeaway
Nobody found has publicly demonstrated a full CAD -> simulation -> CAM loop run by an agent; what exists is (a) research pipelines covering CAD -> mesh -> FEA with poor strict-pass rates, (b) commercial agents covering one or two stages inside a vendor's own cloud (SimScale-in-Onshape, Autodesk Fusion MCP, Zoo), and (c) orchestration layers over incumbent tools (Synera). The best open evidence (Hephaestus-CCX, May 2026) says a CadQuery -> Gmsh -> CalculiX agent loop runs end to end but that frontier agents produced zero strict-passing designs in 400 first attempts.

### Cited Findings

Open / research pipelines (CAD -> mesh -> FEA)
- Hephaestus-CCX (arXiv 2605.17448, May 2026, preprint): agent writes a CadQuery program and exports STEP; an external controller meshes with Gmsh (HXT tetrahedral algorithm; Gmsh Python API fallback), runs CalculiX, and returns typed failures over stress, displacement, modal, buckling, contact and clearance requirements; up to 10 revision attempts. — [arXiv 2605.17448](https://arxiv.org/pdf/2605.17448)
- The same paper adds a text-only "blueprint" stage and a 21-view render inspection; the agent reads the images alongside deterministic measurements and emits a compact report (verdict, summary, issues, failure_category, primary_claim_id, retry_advice). — [arXiv 2605.17448 v2](https://arxiv.org/html/2605.17448v2)
- Benchmark: 50 single-part and multi-part engineering briefs paired with CalculiX evaluation kits and typed pass/fail checkers. Metrics: "strict pass" (every typed requirement passes) and "mean requirement pass" (average per-case pass fraction). — [arXiv 2605.17448 v1](https://arxiv.org/html/2605.17448v1)
- Results: in the main Codex (GPT-5.5, GPT-5.4) and Claude Code (Opus-4.7, Sonnet-4.6) sweep, 400 first attempts produced no strict-passing artifact; one FEA-feedback round added one strict pass across another 400 revised submissions; the best configuration met about 20% of typed requirements on average on first attempt. — [arXiv 2605.17448](https://arxiv.org/pdf/2605.17448)
- Repeated feedback helps: in one long GPT-5.5 run, mean requirement pass rose from 38.8% to 60.5%, with 9/50 strict passes, after an average of 68 minutes per item. — [arXiv 2605.17448 v2](https://arxiv.org/html/2605.17448v2)
- The authors ran no repeated trials and report no confidence intervals or significance tests. Code/assets are MIT; third-party tools keep their own licences (CadQuery Apache-2.0; CalculiX and Gmsh GPL, Gmsh with linking exception). — [arXiv 2605.17448 v2](https://arxiv.org/html/2605.17448v2)
- A community reproduction issue reports partially valid outputs, e.g. "36 valid solids but 38 intersecting pairs" and a case where a "homogeneous core proxy lacks effective material mapping; physics unverified"; it also notes H-CCX prompts ask for CAD without FEA. — [QiuYi111/Reify issue #37](https://github.com/QiuYi111/Reify/issues/37)
- FeaGPT (arXiv 2510.21993, Oct 2025): natural-language-to-FEA pipeline; Gmsh Python API for meshing from LLM-extracted parameters; structured JSON specs translated to CalculiX input files; evaluation centred on turbocharger components. — [arXiv 2510.21993](https://arxiv.org/pdf/2510.21993)
- A 2026 FEniCS-based system (arXiv 2606.10928) confines the LLM to three places: mapping prompt to structured spec, and generating Gmsh code only when geometry is not in a deterministic geometry catalogue. — [arXiv 2606.10928](https://arxiv.org/html/2606.10928)
- AutoFEA is cited in those papers as grounding LLM-generated CalculiX cards with GNN retrieval over a curated corpus. — [arXiv 2605.17448](https://arxiv.org/pdf/2605.17448)
- earthtojake/text-to-cad (MIT): a set of agent skills (SKILL.md workflows) for Claude Code and Codex; models are Python on build123d/OCP, exported to STEP/STL/DXF/GLB/URDF and inspected in a local React/Vite "CAD Explorer"; STEP-first validation before STL/3MF/GLB export; includes a SendCutSend skill. Sources disagree on skill count (7 vs 11). No FEA step was confirmed. — [GitHub](https://github.com/earthtojake/text-to-cad); [DEV write-up](https://dev.to/renolu/text-to-cad-ships-cad-agent-skills-that-run-from-a-prompt-to-a-bambu-lab-print-3nf)

FreeCAD-based agent wrappers
- No single project found combines MCP + headless FEM + CalculiX + CAM + Docker. — search across the listings below
- AnkusDrive drives FreeCAD's Python API via `freecadcmd` so LLMs design parts and run FEM; relies on the Python, ccx and gmsh bundled in FreeCAD installs. — [PyPI ankusdrive](https://pypi.org/project/ankusdrive/)
- proximile/FreeCAD-MCP runs FreeCAD in Docker headless (XML-RPC server, optional VNC), focused on CAD control rather than FEM/CAM. — [GitHub](https://github.com/proximile/FreeCAD-MCP)
- blwfish/freecad-mcp has CAM support, but CAM toolpath generation requires FreeCAD 1.2-dev because the Path/CAM workbench API changed incompatibly between 1.1 and 1.2. — [Glama listing](https://glama.ai/mcp/servers/blwfish/freecad-mcp)
- spkane's "Robust MCP Server" supports headless modelling, but its Docker image only supports xmlrpc/socket modes with FreeCAD on the host. — [GitHub](https://github.com/spkane/freecad-addon-robust-mcp-server)
- TESSA LABS freecad-mcp lists solver export for Elmer, CalculiX and OpenFOAM. — [LobeHub listing](https://lobehub.com/mcp/tessalabs-space-freecad-mcp)

Commercial: single-vendor cloud loops
- SimScale launched an "Engineering AI Agent" inside PTC Onshape (announced at IMTS, Sept 2026): from one prompt it proposes a simulation setup, prepares CAD geometry, runs the physics and explains results (vendor-reported). — [SimScale press](https://www.simscale.com/press/simscale-launches-engineering-ai-agent-for-onshape/)
- SimScale opened the agent to its community of 900,000+ users (Aug 2026), described as running from CAD clean-up to a validated report (vendor-reported). — [SimScale press](https://www.simscale.com/press/engineering-ai-agent-open-to-community/)
- Onshape has an AI Advisor (in-product assistance), says it is developing an MCP server toolkit for custom agents, and Onshape Labs publishes a FeatureScript MCP server for Claude/ChatGPT/Gemini clients (vendor-reported). — [Onshape blog](https://www.onshape.com/en/blog/ai-artificial-intelligence-cloud-native-cad-pdm-platform)
- Autodesk "Fusion Compute MCP": cloud-hosted MCP server exposing Fusion design, electronics and manufacturing to agents; Autodesk states it provides environment and tools, not the intelligence; CAM scope includes setup creation, machining operation setup and applying CAM templates. — [Autodesk blog](https://www.autodesk.com/products/fusion-360/blog/fusion-compute-mcp/); [Autodesk developer blog (JP)](https://blog.autodesk.io/fusion-compute-mcp-server/)
- Community Fusion MCP server (faust-machines) exposes ~80 tools including `cam_create_setup` and `cam_post_process` (posts for fanuc, grbl, haas). — [GitHub](https://github.com/faust-machines/fusion360-mcp-server)
- Zoo shipped "Zookeeper", a conversational CAD agent in Zoo Design Studio v1.1 (Jan 2026; press coverage dates it Feb 2026), available via an Agent API and a Zoo-MCP server; exports STEP/STL; recent additions include GD&T labels and DXF export; stated next step is image attachments. No simulation feature was found. — [Zoo research page](https://docs.zoo.dev/research/zookeeper); [Zoo press](https://zoo.dev/press/zoo-introduces-zookeeper); [Zoo roadmap](https://zoo.dev/roadmap)
- nTop Automate: official Linux container image running `ntopcl` against a notebook with JSON inputs/outputs; workflows must be authored in the Windows UI first; each running container needs its own licence; minimum 2 CPU cores. — [nTop docs](https://docs.ntop.com/help-articles/access-and-installation/system-requirements/ntop-automate-for-linux-container-image)

Commercial: orchestration over incumbent tools
- Synera (founded 2018): agentic platform orchestrating 80+ CAD and simulation tools (Altair, Autodesk, Hexagon, PTC, Siemens); raised $40M Series B in April 2026. — [SiliconANGLE](https://siliconangle.com/2026/04/14/german-startup-synera-lands-40-million-automate-engineering-workflows-ai-agents/); [TNW](https://thenextweb.com:443/news/synera-40m-series-b-agentic-ai-engineering)
- Synera announced (June 2026) use of NVIDIA's NemoClaw blueprint to orchestrate agents across CAD, meshing, manufacturing simulation and structural analysis; customer availability "anticipated" H2 2026. — [Synera press](https://www.synera.io/press/synera-nvidia-nemoclaw-ai-agents-design-simulation)
- Synera's own position: build deterministic workflow automation first, layer agents on top; RFQ example claims 3 days -> minutes (vendor-reported). — [Synera blog](https://www.synera.io/news/ai-agent-orchestration-engineering-use-cases)
- Dassault added role-based "Virtual Companions"/agents to 3DEXPERIENCE and upgraded its Aura copilot (Feb 2026); NVIDIA agentic tooling announcements (Mar 2026) covered Dassault, Siemens (a Fuse EDA agent, i.e. electronics), Cadence, Synopsys, and a PTC Onshape -> Isaac Sim robotics workflow. — [Develop3D](https://develop3d.com/cad/event-report-3dexperience-world-2026/); [Digital Engineering 24/7](https://www.digitalengineering247.com/article/nvidia-brings-agentic-ai-to-engineering-software/cad)
- Neural Concept "AI Design Copilot" (Jan 2026): generates CAD-ready geometry linked to multiphysics simulation (vendor-reported). — [Automotive Testing Technology Intl](https://www.automotivetestingtechnologyinternational.com/news/cae-simulation-modeling/ai-design-copilot-introduces-physics-aware-cad-ready-automation-for-engineers.html)

"AI mechanical engineer" startups
- P-1 AI ("Archie"): $23M seed (Apr 2025, Radical Ventures); self-described as at the level of a junior/entry-level design engineer; first deployments in data-centre cooling; no independent evaluation or 2026 benchmark found. — [yespress profile](https://yespress.io/p-1-ai); [job post](https://jobs.lererhippeau.com/companies/p-1-ai-2/jobs/78374856-ai-evals-lead)
- Foundation EGI (MIT CSAIL spinout): $7.6M seed (Apr 2025) and $23M (Jul 2025); domain LLM; initial focus is automating engineering documentation, not geometry or simulation. — [SiliconANGLE Apr 2025](https://siliconangle.com/2025/04/17/foundation-egi-raises-7-6m-transform-manufacturing-engineering-general-intelligence); [SiliconANGLE Jul 2025](https://siliconangle.com/2025/07/10/foundation-egi-raises-23m-series-expand-industrial-ai-platform/)
- Leo AI: $9.7M total; knowledge/search copilot over a company's CAD/PDM/PLM that reads B-rep; by its own account it does not generate new geometry and needs an engineer in the loop; 96% accuracy and 5+ h/week savings are vendor claims. — [Pulse 2.0](https://pulse2.com/leo-ai-9-7-million-raised-for-transforming-mechanical-engineering); [Leo blog](https://getleo.ai/blog/ai-cad-design-2026-whats-real)
- Navier AI: $5.6M seed (GV, HCVC, YC; dated Dec 2025 by one source); agent-driven engineering between CAD and validation, positioned on top of existing CAD/simulation tools; AFWERX Phase I SBIR in Aug 2026. — [Pulse 2.0](https://pulse2.com/navier-5-6-million-seed/)
- JuliaHub: $65M Series B (Apr 2026) for Dyad; CEO names hallucinations as a main challenge. — [SiliconANGLE](https://siliconangle.com/?p=744311)
- Hestus (YC S24): $1.5M seed (Jan 2025) for automating repetitive CAD tasks. — [mechanical-engineering.com](https://mechanical-engineering.com/prometheus-and-the-artificial-general-engineer/)
- One source reports Bezos-backed Prometheus raised $18.2B to build an "artificial general engineer" and acquired General Agents; the figure was not corroborated by a second source. — [mechanical-engineering.com](https://mechanical-engineering.com/prometheus-and-the-artificial-general-engineer/)

### Inferences
- The integration frontier in late 2026 is CAD -> FEA, not CAD -> FEA -> CAM. CAM appears only as tool exposure (Fusion MCP, FreeCAD MCP) with no published agent results.
- Funded startups cluster in three low-geometry-risk niches: knowledge/search (Leo), documentation (Foundation EGI), and orchestration of incumbent tools (Synera, Navier). That clustering is itself evidence that autonomous geometry + validated physics is still unsolved commercially.
- Synera's "automation first, agents on top" and the FEniCS paper's "LLM in three places only" converge on the same design rule: keep the LLM out of deterministic stages (meshing recipe, deck writing, post-processing) and give it typed, checkable interfaces.
- For a 1-3 person team, H-CCX is the closest reusable reference architecture (CadQuery -> STEP -> Gmsh -> CalculiX -> typed checkers -> retry) and a ready-made eval set; expect tens of minutes and many retries per hard case.

### Gaps
- Dirac, Hanomi, Camfer, Generative Engineering, Trace, Monumental, CDS, PhysicsX agent work: searches returned nothing usable; no claim can be made.
- No 2026 mechanical-CAD/CAE agent announcement from Ansys/Synopsys or from Siemens NX/Simcenter was found (only Siemens' EDA agent). Autodesk Assistant and generative-design automation details not found.
- SALOME / salome_meca / Code_Aster scripted or agentic pipelines: no results returned.
- H-CCX per-category failure breakdown and how it maps load/constraint faces from CadQuery into CalculiX sets could not be retrieved (arxiv.org blocked).
- No published end-to-end agent pipeline including optimisation and CAM was found; absence in search is not proof of absence.

## 2. Data-exchange glue and preserving face/edge identity (named selections) across CAD -> mesh -> solver -> CAM

### Takeaway
There is no standard, reliable carrier for face names across stages: STEP face names are vendor-dependent, Gmsh's STEP label reading is patchy, and Gmsh's INP export has several set-writing quirks. Working pipelines side-step file-borne names and re-derive selections geometrically or by tag-to-index matching inside one Python process (as the CadQuery assembly-mesh-plugin does).

### Cited Findings
- STEP: AP214 names are vendor-dependent and not standardised for robust CAE automation; even with AP242 behaviour depends on the exporter; many CAD tools ship with "export names" off; topology changes are a common cause of lost names. — [STEP standards explained (third-party guide)](https://takuto-na.github.io/step-standards-explained/docs/persistent-ids)
- Creo: no option to export persistent IDs to STEP (only names based on them); users were still asking for AP242 persistent UUIDs in Creo 11 in May 2026. — [PTC community](https://community.ptc.com/t5/3D-Part-Assembly-Design/Persistent-names-of-persistent-entities-in-STEP-export/m-p/603026)
- MBx-IF publishes a Recommended Practice for Persistent IDs (v1.7) and 2026 test suites covering persistent IDs for design iteration. — [MBx-IF rec. practice PID v1.7](https://www.mbx-if.org/home/wp-content/uploads/2025/10/rec_pracs_PID_v1.7.pdf)
- build123d's STEP exporter sets `TDataStd_Name` on the instance label and, where applicable, the referred shape label so STEP PRODUCT names persist (part/solid level). — [build123d exporters3d source](https://build123d-ja.readthedocs.io/ja/latest/_modules/exporters3d.html)
- CadQuery: found support is for assembly names and face-level colours via `Assembly.addSubshape(...)` and `exportStepMeta(...)`; no face-level names in STEP export were found. — [CadQuery basics, third-party guide](https://takuto-na.github.io/step-standards-explained/implementation/cadquery-basics)
- Gmsh can read STEP labels/colours via its OpenCASCADE kernel (demo `step_assembly.py`; `getEntityName`, `getColor`), but users report labels not showing or not retrievable. — [Gmsh issue 559](https://gitlab.onelab.info/gmsh/gmsh/-/issues/559); [Gmsh issue 2437](https://gitlab.onelab.info/gmsh/gmsh/-/issues/2437); [Gmsh list, STEP labels](https://onelab.info/pipermail/gmsh/2019/013036.html)
- In-memory handoff: passing a CadQuery/OCP shape to `gmsh.model.occ.importShapesNativePointer` is fragile; one report traced an OCCT `GeomAdaptor_Surface::UContinuity` exception to a pip-installed stack and fixed it with a clean conda install (gmsh 4.12.2); STEP export + `gmsh.merge` worked as fallback. — [CadQuery issue 1556](https://www.github.com/CadQuery/cadquery/issues/1556); [CadQuery Google group](https://groups.google.com/g/cadquery/c/pkoeRga94jA)
- `importShapesNativePointer` returned empty `outDimTags` on Windows while working on macOS. — [Gmsh issue 2122](https://gitlab.onelab.info/gmsh/gmsh/-/issues/2122)
- CadQuery `assembly-mesh-plugin`: turns CadQuery tags (e.g. `faces(">X").tag(...)`) into Gmsh physical groups via `getTaggedGmsh()`, matching tagged faces to Gmsh surfaces by their position in the CadQuery solid vs the Gmsh surface ID; every surface also gets its own physical group. — [PyPI assembly-mesh-plugin](https://pypi.org/project/assembly-mesh-plugin/)
- cad_to_dagmc uses Gmsh 3D physical groups automatically as material tags. — [cad_to_dagmc docs](https://fusion-energy.github.io/cad_to_dagmc/dev/inputs/gmsh_files.html)
- apeGmsh documents grouping faces by normal direction with a tolerance as an alternative to tagging. — [apeGmsh CAD import guide](https://nmorabowen.github.io/apeGmsh/internal_docs/guide_cad_import/)
- Gmsh -> CalculiX INP quirks: node sets for physical groups are only written with `Mesh.SaveGroupsOfNodes`; physical points may be written as `*ELSET` not `*NSET`; surface physical groups emit 2D elements CalculiX does not need and that must be cleaned; if any physical group is defined only elements in physical groups are saved; a `gmsh-inp-filter` script remaps surface element sets to volume-element faces. — [CalculiX discourse: missing nsets](https://calculix.discourse.group/t/gmsh-export-to-inp-missing-nsets/2641); [Gmsh issue 121](https://gitlab.onelab.info/gmsh/gmsh/-/issues/121); [Roland Smith, FEA from STEP with Gmsh and CalculiX](https://rsmith.home.xs4all.nl/engineering/fea-based-on-step-geometry-using-gmsh-and-calculix.html); [gmsh2ccx](https://github.imc.re/calculix/gmsh2ccx)
- One user reported that via the API, physical groups for edges/surfaces exported the geometric points rather than the mesh nodes on those entities. — [Gmsh issue 1456](https://gitlab.onelab.info/gmsh/gmsh/-/issues/1456)
- Editing by rebuilding: a 2026 CAD-agent primer reports that rebuilding a model from scratch instead of editing an imported STEP tends to introduce new errors, and that keeping local edits from disturbing the rest is the main challenge (CADGenBench best edit score about 0.635). — [Agent research primer](https://lehuili-cad-agent-intro.static.hf.space/index.html)
- Headless rendering: stock PyVista/VTK Linux wheels render off-screen without an X server, choosing EGL (GPU) or OSMesa (software) at run time; VTK 9.5+ selects `vtkEGLRenderWindow` automatically under the NVIDIA container runtime; `ghcr.io/pyvista/pyvista` images exist including a slim off-screen one; Xvfb + `PYVISTA_OFF_SCREEN=true` remains the legacy path. — [PyVista Docker docs](https://docs.pyvista.org/extras/docker); [PyVista building VTK](https://docs.pyvista.org/extras/building_vtk)
- CPU-only containers: install Mesa software EGL (`libegl1` on Debian/Ubuntu). — [Open3D headless docs](https://www.open3d.org/docs/latest/tutorial/visualization/headless_rendering.html)
- `pyvista-cad` provides STEP readers and build123d interop for visualising CAD in PyVista. — [pyvista-cad docs](https://cad.pyvista.org/user_guide/interop_with_build123d.html)

### Inferences
- Recommended identity strategy for a code-CAD pipeline: treat the CAD script as the single source of truth and keep selections as executable queries (e.g. "faces with normal +Z at z = h", "cylindrical faces of radius r"), re-evaluated on each rebuild, rather than as stored IDs. Resolve them to Gmsh surface tags in-process by geometric matching (centre of mass, area, bounding box, normal), then write solver sets yourself.
- Write the CalculiX deck from the Gmsh Python API (nodes, elements, per-surface node lists) with your own writer, or use a volume-only export plus self-built `*NSET`/`*SURFACE` cards; this avoids every INP-export quirk listed above.
- Add a mandatory "selection audit" artefact per run: for each named selection report face count, total area, centroid and a rendered highlight image. This is cheap and catches the wrong-face class of error before solve.
- STEP remains the right interchange for solids (and for hand-off to humans or CAM); colours are a more portable face-level side channel than names when a file boundary is unavoidable.
- The same query-based selections can drive CAM feature picks (pockets, holes, stock faces), so one selection layer can serve both FEA and CAM.

### Gaps
- No source was found demonstrating face-level names surviving build123d/CadQuery -> STEP -> Gmsh end to end; the chain is untested in the evidence.
- meshio's handling of INP sets, pygccx and cq-gmsh specifics, MED/XDMF/VTU conversion pitfalls, 3MF/glTF metadata, and ParaView batch (`pvbatch`) were not covered by any retrieved source.
- How FreeCAD's topological-naming fix (1.0+) behaves for FEM/CAM references under scripted regeneration was not researched here.
- No source found on carrying selections into CAM features in an open-source stack.

## 3. Practical infrastructure: containers, packages, install pain points, compute, runtime, sandboxing

### Takeaway
All core pieces are obtainable via conda-forge or existing images, and practitioners report that a single clean conda environment is more reliable than mixing pip wheels for OCP and Gmsh. FreeCAD headless is workable but has version and stdin traps, and its CAM API is unstable across 1.1/1.2.

### Cited Findings
- conda-forge ships `freecad` linux-64 v1.1.0. — [anaconda.org conda-forge/freecad](https://anaconda.org/conda-forge/freecad/manage)
- FreeCAD wiki documents a GUI-less Docker image (`amrit3701/freecad-cli`) started with `FreeCADCmd`; its FreeCAD version currency was not confirmed. — [FreeCAD wiki: Docker CLI mode](https://wiki.freecad.org/FreeCAD_Docker_CLI_mode)
- FreeCAD 1.1 introduced a refactored CalculiX solver object (enabled by a FEM preference) alongside the older ccxtools solver object; scripts that create solver objects must pick one. — [FreeCAD wiki: FEM SolverCalculixCcxtools](https://wiki.freecad.org/FEM_SolverCalculixCcxtools)
- Headless traps reported by an MCP project: run `freecadcmd` with stdin redirected from `/dev/null` or it waits on the console; running the AppImage without arguments tries to open the GUI and fails without a display; container paths break when FreeCAD runs on the host. — [AnkusDrive README](https://raw.githubusercontent.com/gchen19/ankusdrive/HEAD/README.md)
- FreeCAD CAM (Path) API changed incompatibly between 1.1 and 1.2-dev. — [blwfish/freecad-mcp listing](https://glama.ai/mcp/servers/blwfish/freecad-mcp)
- conda-forge `fenics-dolfinx`: 0.10.0 listed for linux-64, with 0.11.0 builds uploaded June 2026. — [anaconda.org fenics-dolfinx files](https://anaconda.org/conda-forge/fenics-dolfinx/files)
- pip-installed OCP + Gmsh stack produced an OCCT exception that vanished in a fresh conda install. — [CadQuery issue 1556](https://www.github.com/CadQuery/cadquery/issues/1556)
- Runtime data point: H-CCX reports an average of 68 minutes per item for a long multi-retry GPT-5.5 run (agent + mesh + CalculiX wall time combined, not solver time alone). — [arXiv 2605.17448 v2](https://arxiv.org/html/2605.17448v2)
- A cost-aware benchmark for LLM-automated physics simulation exists (SimulCost, arXiv 2603.20253). — [arXiv 2603.20253](https://arxiv.org/pdf/2603.20253)
- Commercial comparison point: nTop Automate needs a licence per running container and at least 2 cores. — [nTop docs](https://docs.ntop.com/help-articles/access-and-installation/system-requirements/ntop-automate-for-linux-container-image)

### Inferences
- Build one pinned conda/mamba (or pixi) environment image containing OCP/CadQuery or build123d, Gmsh, CalculiX, PyVista, meshio; keep FreeCAD (for CAM) and FEniCSx/OpenFOAM in separate images because their dependency stacks (OCCT, VTK, PETSc/MPI versions) are the likeliest to conflict. This is inference from the pip-vs-conda failure above, not a documented best practice.
- Pin FreeCAD to an exact version and wrap its FEM/CAM calls behind your own thin API; two breaking changes (solver object, CAM API) landed within one minor-version window.
- Agent sandboxes without GPUs should use VTK's OSMesa/EGL-on-llvmpipe path; no Xvfb needed for PyVista. Budget a display-free path for any FreeCAD rendering separately.
- In restricted-network sandboxes (like the one this research ran in), bake everything into the image; runtime `conda install` or model/asset downloads will fail.

### Gaps
- No sourced numbers for solver runtime or RAM of typical small analyses (e.g. 50k-500k-element linear static in CalculiX). This should be measured on the team's own reference bracket.
- conda-forge/Docker availability and current versions for CalculiX, Gmsh, OCP/CadQuery/build123d, `dolfinx/dolfinx` images and OpenCFD/Foundation OpenFOAM images were not returned by search; they are widely believed available but are uncited here.
- SALOME/Code_Aster container options, FreeCAD forum reports on conda-forge headless FEM, and reproducibility of meshes across Gmsh versions: not found.

## 4. Licensing risks: hosted product vs internal tool

### Takeaway
The open stack is LGPL/GPL-heavy but almost entirely usable as separate, unmodified executables or libraries, which is low-risk for an internal tool; the items needing legal review are linking Gmsh's API into closed code you distribute, shipping containers or on-prem builds to customers, and any AGPL slicer behind a network service.

### Cited Findings
- Gmsh is GPL-2.0-or-later with an exception permitting combination with named third-party code (the exception text lists OpenCASCADE, Netgen, METIS among others); people who modify Gmsh are not obliged to pass the exception on. — [SPDX Gmsh-exception](https://spdx.org/licenses/Gmsh-exception.html); [ScanCode gmsh-exception](https://scancode-licensedb.aboutcode.org/gmsh-exception.LICENSE)
- Gmsh list threads discuss API licensing; a maintainer indicated that tools which only generate `.geo` scripts interpreted by Gmsh do not link to it. — [Gmsh list: API licensing](https://onelab.info/pipermail/gmsh/2019/013344.html); [Gmsh list: licence exception question](https://onelab.info/pipermail/gmsh/2019/013215.html)
- Open CASCADE Technology is LGPL-2.1 with the "Open CASCADE Exception 1.0"; the LGPL-2.1-only status has been debated for GPL-3 compatibility. — [Fedora legal list](https://lists.fedoraproject.org/pipermail/legal/2013-December/002347.html); [OCCT exception text](https://licenses.nuget.org/OCCT-exception-1.0); [KiCad developers list](https://archive.lists.launchpad.net/kicad-developers/msg33569.html)
- H-CCX's asset table lists CadQuery as Apache-2.0 and CalculiX and Gmsh as GPL (Gmsh with linking exception). — [arXiv 2605.17448 v2](https://arxiv.org/html/2605.17448v2)
- PrusaSlicer is AGPL-3.0 and has a CLI; Bambu Studio and OrcaSlicer descend from it under AGPLv3. — [PrusaSlicer repo summary](https://awesome.ecosyste.ms/projects/github.com%2Fprusa3d%2FPrusaSlicer); [It's FOSS](https://itsfoss.com/news/bambu-lab-caught-violating-agplv3.md)
- AGPL enforcement is live: Bambu Lab is accused of AGPLv3 violations and the Software Freedom Conservancy became involved after a cease-and-desist against an OrcaSlicer fork (allegations, not rulings). — [Tom's Hardware](https://www.tomshardware.com/3d-printing/open-source-non-profit-claims-bambu-lab-violated-license-move-follows-cease-and-desist-demand-on-orcaslicer-fork-that-restored-cloud-printing-features-without-using-bambu-connect); [3D Printing Industry](https://3dprintingindustry.com/news/bambu-lab-now-under-formal-investigation-for-agplv3-violations-251645/)
- Commercial alternative cost shape: nTop Automate is licensed per running container. — [nTop docs](https://docs.ntop.com/help-articles/access-and-installation/system-requirements/ntop-automate-for-linux-container-image)

### Inferences (general licence reasoning, not legal advice and not from a cited source)
- Internal tool: GPL/LGPL/AGPL obligations are triggered by distribution (or, for AGPL, by offering a modified version over a network). Running unmodified CalculiX, Gmsh, OpenFOAM, Code_Aster, FreeCAD and slicers internally creates no source-release duty for your own agent code.
- Hosted product (SaaS): plain GPL has no network clause, so calling unmodified GPL solvers as subprocesses server-side is generally considered compatible with closed orchestration code. Keep process boundaries (CLI + files) for GPL tools; `import gmsh` in a closed Python service is a greyer area if that service is ever distributed, so isolate it in a separately licensed open worker.
- AGPL slicers: keep them unmodified and invoked as CLI; if you modify them and expose them over a network you must offer the modified source to users.
- Distribution cases (customer on-prem install, shipping Docker images, desktop app) trigger GPL/LGPL duties: provide source/offer for the GPL components, allow relinking for LGPL (OCCT), preserve notices. Shipping a container image counts as distribution.
- Agent-generated CAD scripts and outputs (STEP, meshes, G-code) are not derivative works of the tools in the ordinary reading; licence risk attaches to code, not artefacts.
- Practical hygiene: maintain an SBOM per image, do not patch GPL tools in private forks, and get counsel sign-off before any on-prem or image-shipping offering.

### Gaps
- CalculiX's exact licence text (commonly GPL-2.0-or-later), OpenFOAM (GPL-3.0), Code_Aster (GPL), FreeCAD (LGPL-2.1+), CuraEngine (AGPL) and build123d (Apache-2.0) were not confirmed by retrieved sources in this session; treat as needing verification.
- Whether Gmsh offers a commercial licence was only seen on a secondary site and should be confirmed with the Gmsh authors.
- Commercial kernel pricing/terms (Parasolid, ACIS, CGM, Zoo's engine) were not researched.

## 5. Technical risks and gaps reported by practitioners; where agents have a near-term win

### Takeaway
The dominant, well-evidenced risk is silent wrongness: runs that converge and look plausible but encode wrong physics, wrong selections or invalid geometry, combined with agents that argue for their wrong answer. Rendered-image feedback helps shape but not dimensions, so deterministic geometric and physical checks have to carry verification; user trust in AI-generated simulation setup is correspondingly low (17%).

### Cited Findings
Simulation setup and silent failure
- "False summit": a converged simulation that looks physically plausible but implements incorrect physics; "silent drift": unverified assumptions carried across stages. Studied for GPT and Claude on MOOSE under direct prompting and staged workflows; proposes an eight-category taxonomy and stage-gated workflow; reports agents producing sophisticated, internally consistent arguments defending incorrect results. — [arXiv 2606.21841](https://arxiv.org/pdf/2606.21841)
- The same paper notes earlier evaluations mostly catch syntactic errors (convergence failures, malformed inputs), which wrong units/BCs pass. — [arXiv 2606.21841](https://arxiv.org/pdf/2606.21841)
- A separate MOOSE benchmark reports up to 40% of runnable cases had misaligned simulation outputs. — [arXiv 2605.09360](https://arxiv.org/html/2605.09360)
- FEABench (NeurIPS 2024 workshop): best strategy produced executable API calls 88% of the time, yet no tested LLM/agent completely and correctly solved any problem. — [FEABench](https://neurips.cc/virtual/2024/100967)
- FEM-Bench (2026) attributes errors mainly to domain-knowledge deficits rather than generic reasoning. — [FEM-Bench review](https://www.themoonlight.io/review/fem-bench-a-structured-scientific-reasoning-benchmark-for-evaluating-code-generating-llms)
- AbaqusAgent flags "false simulations" from incorrect boundary conditions, load cases and solution variables. — [arXiv 2606.00138 summary](https://www.opentrain.ai/papers/a-multi-ai-agent-framework-enabling-end-to-end-finite-element-analysis-for-solid--arxiv-2606.00138/)
- PHITSBench (Jul 2026) describes an emerging consensus that LLMs can assist setup and execution when given retrieval, structured documentation and iterative self-correction. — [alphaXiv 2607.09789](https://www.alphaxiv.org/abs/2607.09789)

Geometry and spatial reasoning
- H-CCX: zero strict passes in 400 first attempts; multi-part outputs with intersecting solids reported in reproduction. — [arXiv 2605.17448](https://arxiv.org/pdf/2605.17448); [Reify issue #37](https://github.com/QiuYi111/Reify/issues/37)
- HN practitioners (2026): LLMs remain weak at spatial reasoning (one team added planning guidance to SKILL.md as a stopgap with Opus 4.7 + OpenSCAD); iterating on rotated rendered PNGs before export "works quite well"; build123d preferred over OpenSCAD for real B-rep; skills folders with Claude + build123d reported as satisfactory. — [HN thread 47970497](https://hn.svelte.dev/item/47970497); [HN thread 47183039](https://hn.nuxt.dev/item/47183039)
- CADSmith: visual feedback cannot resolve dimensional errors; pairs CadQuery generation with programmatic geometric validation. — [arXiv 2603.26512](https://arxiv.org/pdf/2603.26512)
- ExpConCAD: LLMs show insufficient understanding of the CadQuery library, with frequent syntax errors and semantic misuse. — [arXiv 2608.24760](https://arxiv.org/pdf/2608.24760)
- ModelRift benchmark headline: OpenSCAD beat CadQuery on the hardest task, "but both hide silent failures"; a commenter notes CadQuery output can be interrogated whereas OpenSCAD cannot. — [zeli.app summary](https://zeli.app/story/49676577)
- LLM4CAD-Editor: spatial grounding and feature alignment are hard when instructions leave spatial constraints implicit. — [arXiv 2606.20607](https://arxiv.org/pdf/2606.20607)
- BenchCAD: substantial out-of-distribution gaps on held-out industrial part families needing advanced operations and precise constraints. — [arXiv 2605.10865](https://arxiv.org/pdf/2605.10865)

CAM safety
- A study of ChatGPT optimising automotive machining code found it dropped a pocket-milling operation (about 31% of the program) and removed tool-length compensation (G43/H) and safe-return (G28) commands (secondary summary; verify against original). — [ownyourai.com](https://ownyourai.com/?p=41267)
- A May 2026 paper argues simulation alone does not prove G-code safety and proposes neuro-symbolic, separation-logic verification for collisions. — [arXiv 2605.10568](https://arxiv.org/pdf/2605.10568)
- CloudNC advises never running raw LLM G-code without review and verification (vendor guidance). — [CloudNC blog](https://www.cloudnc.com/blog/can-i-use-chatgpt-for-generating-g-code)
- No standardised benchmark for LLM CAM/toolpath agents was found. — search result, e.g. [GLLM review](https://www.themoonlight.io/de/review/gllm-self-corrective-g-code-generation-using-large-language-models-with-user-feedback)

Trust and evaluation
- IoT Analytics 2026 (120 manufacturers): only 17% trust AI-generated simulation inputs and auto-meshing; 87% expect AI embedded in core CAD/PLM/ALM; 61% say transparency/explainability would raise trust; aerospace most sceptical. — [IoT Analytics](https://iot-analytics.com/the-ai-trust-gap-in-design-and-engineering-software/)
- Omni Calculator 2026 (402 US engineers/students, self-selected): 86% use AI, about 6% trust it without hesitation, 89% check results, 52.4% default to a hand sanity calculation. — [Omni Calculator](https://www.omnicalculator.com/reports/ai-adoption-in-engineering)
- Benchmark-validity guidance: a task should be solvable if and only if the agent has the target capability (Agentic Benchmark Checklist). — [arXiv 2507.02825](https://arxiv.org/html/2507.02825v5)
- Leo AI's own blog: AI output that drives tooling cannot yet be trusted without engineer review. — [Leo blog](https://getleo.ai/blog/ai-cad-design-2026-whats-real)

### Inferences
- Verification layers to build, in order of value per effort: (1) geometric assertions on the B-rep (validity, volume, bounding box, hole counts/diameters, wall thickness, no interference); (2) selection audit (section 2); (3) physics sanity checks independent of the agent (reaction-force sum equals applied load, unit-system lint, hand-calc/beam-theory comparison within a tolerance, mesh-convergence delta); (4) multi-view renders for shape-level review. Items 1-3 are what catch "false summits"; item 4 does not.
- Have the checker, not the agent, own pass/fail (as H-CCX does with typed checkers), and never let the agent edit the evaluation deck; this limits self-justifying wrong answers.
- Mirror the survey behaviour: emit a hand-calc cross-check and a transparent report with every result, since 52% of engineers sanity-check by hand and 61% want explainability.
- Clear near-term wins (inference from where demonstrations succeed and where failure cost is low): parametric single parts (brackets, enclosures, fixtures, plates), 3D-printed parts, design-space sweeps over a human-approved parametric model and simulation template, automated report generation, and rule-based DFM checks. Weak areas: multi-part assemblies with contact, free-form surfacing, CNC G-code without simulation/verification, anything certification-bound.
- CNC should be gated: generate via a CAM kernel with templates (not LLM-written G-code), simulate material removal and collisions, require human sign-off before any machine run.

### Gaps
- Kernel-robustness statistics (OCCT boolean/fillet failure rates under agent-generated code) were not found.
- No sourced evidence on training-data scarcity for assemblies or on standards/knowledge access (ISO/ASME paywalls) surfaced, though both are commonly asserted.
- The original ModelRift benchmark numbers and the "False Summit" per-category counts could not be retrieved.
- No independent evaluation of any commercial agent (SimScale, Zookeeper, Synera, Archie) was found.

## 6. Milestone sequences and candidate demo/eval problems

### Takeaway
No source publishes a tested build-order roadmap; the sequence below is inferred from what demonstrably works (single-part code-CAD with render + assertion feedback), what demonstrably struggles (FEA-graded multi-part design), and what is unbenchmarked and dangerous (CAM). The evidence supports proceeding CAD -> checks/viewer -> FEA on single parts -> 3D-print -> sheet/2.5D CNC -> assemblies.

### Cited Findings
- Working pattern for stage 1: skills-packaged build123d agent with STEP-first validation, local viewer, and export to STL/3MF/GLB/DXF; includes a prompt-to-Bambu-print flow and a SendCutSend (laser/sheet service) skill. — [earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad); [DEV write-up](https://dev.to/renolu/text-to-cad-ships-cad-agent-skills-that-run-from-a-prompt-to-a-bambu-lab-print-3nf)
- Render-iterate loop before export reported effective by practitioners; dimensional correctness needs programmatic validation. — [HN thread 47183039](https://hn.nuxt.dev/item/47183039); [arXiv 2603.26512](https://arxiv.org/pdf/2603.26512)
- Stage 2 reference: CadQuery -> Gmsh -> CalculiX with typed requirement checkers and up to 10 retries; requirement types available as eval dimensions: stress, displacement, modal, buckling, contact, clearance; 50 ready-made briefs. — [arXiv 2605.17448](https://arxiv.org/pdf/2605.17448)
- Expected difficulty: single FEA-feedback round barely helps (1 extra strict pass in 400); many rounds reach 9/50 strict at about 68 min/item. — [arXiv 2605.17448 v2](https://arxiv.org/html/2605.17448v2)
- Deterministic-first principle from an orchestration vendor: build rule-based workflow automation first, then add agents. — [Synera blog](https://www.synera.io/news/ai-agent-orchestration-engineering-use-cases)
- Narrow-LLM principle: LLM maps prompt to structured spec; deterministic catalogue/geometry and solver templates do the rest. — [arXiv 2606.10928](https://arxiv.org/html/2606.10928)
- CAM tooling instability and risk: FreeCAD CAM API break 1.1 -> 1.2; LLM-edited G-code dropped operations and safety codes. — [blwfish/freecad-mcp](https://glama.ai/mcp/servers/blwfish/freecad-mcp); [ownyourai.com](https://ownyourai.com/?p=41267)
- Other public eval sets usable for regression: CADBench (CAD program generation), BenchCAD (industrial families, MIT), CADGenBench (build123d editing), CADWorld (long-horizon CAD computer use), FEABench/FEM-Bench (FEA reasoning). — [CADBench](https://arxiv.org/pdf/2605.10873); [BenchCAD](https://arxiv.org/pdf/2605.10865); [CADWorld](https://arxiv.org/pdf/2609.16251); [FEABench](https://neurips.cc/virtual/2024/100967)

### Inferences
Suggested build order for a 1-3 person team using Claude with headless open-source tools (inference, not a sourced roadmap):
1. M0 Infrastructure: pinned conda image (build123d or CadQuery/OCP, Gmsh, CalculiX, PyVista off-screen), artefact store, run manifest (tool versions, seeds, inputs) for reproducibility.
2. M1 Single-part code-CAD: skills/prompts, geometric assertion library, multi-view renders, web viewer, STEP/STL/3MF export. Eval: dimensioned brackets, plates, enclosures against assertion suites.
3. M2 Query-based named selections + selection audit; in-process Gmsh meshing; own CalculiX deck writer; linear static only; typed checkers; hand-calc cross-check; auto report. Eval: cantilever bracket with FoS target (closed-form beam check), plate with hole (stress concentration vs handbook Kt), pressure vessel (thin-wall hoop stress).
4. M3 Parameter sweeps/optimisation over a human-approved parametric model (mass minimisation under stress/deflection limits); add modal and buckling. Eval: drone arm (stiffness/mass, first mode), H-CCX subset.
5. M4 3D-print path: unmodified slicer CLI, printability checks (overhang, wall thickness, bed fit), print-time/material report. Eval: enclosure with snap fits, fixtures.
6. M5 Sheet/2D services (DXF) and 2.5D CNC through a CAM kernel with templates, toolpath simulation and mandatory human sign-off. Eval: fixture plates, simple pocketed housings.
7. M6 Thermal/CFD (heat sink) and assemblies with contact (gearbox housing): last, because evidence shows multi-part and contact cases are where agents fail most and BC identity is hardest.
- Use closed-form problems first precisely because they give an agent-independent oracle; they directly test for "false summit" behaviour.
- Track strict-pass and mean-requirement-pass per milestone plus wall time and token cost per solved case, mirroring H-CCX, so progress is comparable to published baselines.

### Gaps
- No practitioner post or talk was found that documents an actual milestone sequence and where it stalled; the roadmap above is this researcher's synthesis.
- No sourced examples of the specific demo problems (heat sink, gearbox housing, snap-fit enclosure) solved end to end by an agent were found; H-CCX's individual brief list was not retrievable.
- No cost data (tokens, compute) per solved engineering task beyond H-CCX's 68 min/item.
