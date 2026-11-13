# Scriptable CAM, process planning, DFM checking and quoting for an LLM-driven mechanical-engineering agent (state as of Nov 2026)

Method note for the report writer: this session used web search only (about 20 queries; the one direct page fetch, to aps.autodesk.com, was blocked by the session network policy). "Cited Findings" are restricted to what search results returned, and most were read as search-result summaries rather than full primary pages, so version numbers and vendor claims should be treated as "reported", not independently verified. Anything I know only from background knowledge (not confirmed this session) is placed under "Inferences" or "Gaps" and labelled as such.

## 1. Open-source CAM (FreeCAD CAM, OpenCAMLib, PyCAM, Kiri:Moto, Fabex, CAMotics, etc.)

### Takeaway
FreeCAD's CAM workbench (v1.1, March 2026) is the only open-source option found that combines STEP import, a Python job/operation API, Python post-processors and headless execution (`FreeCADCmd`); the wiki itself still describes the CAM scripting surface as early-stage. OpenCAMLib is a pip-installable 3-axis drop-cutter/waterline kernel, not a full CAM system, and CAMotics is a GUI-first 3-axis simulator with no confirmed headless mode.

### Cited Findings
- FreeCAD 1.1 was released 24 March 2026 (one outlet says 25 March). CAM changes: tool management replaced with "Better Tool Library" integration (new toolbit editor/selector, rebuilt library editor), "better multi-pass support and post-processors"; the wiki's CAM section otherwise only lists "Further CAM improvements". — [FreeCAD Release notes 1.1](https://wiki.freecad.org/Release_notes_1.1); [OSArch announcement](https://osarch.org/2026/03/25/freecad-1-1-released/); [Industry Insider](https://industryinsider.eu/3d-designing-and-simulation/freecad-1-1-improvements-following-the-latest-major-update/)
- FreeCAD runs without a GUI; `FreeCADCmd` executes a script and exits, which the wiki calls ideal for scripting. Not all workbench modules are automatically available in headless contexts. — [Headless FreeCAD](https://wiki.freecad.org/Headless_FreeCAD)
- The CAM workbench (renamed from Path) exposes a Python scripting interface for creating, manipulating and exporting toolpaths; the wiki page states the workbench is "in early development". — [CAM scripting](https://wiki.freecad.org/CAM_scripting); [CAM Workbench](https://wiki.freecad.org/CAM_Workbench)
- FreeCAD post-processors are plain Python files that implement at least `export(objectslist, filename, argstring)`; bundled posts include centroid, grbl, linuxcnc and mach3_mach4. Fusion `.cps` posts cannot be used directly. Syntax errors in a post can fail silently or with a generic "Failed to load". — [CAM Postprocessor Customization](https://wiki.freecad.org/CAM_Postprocessor_Customization); [Path Post](https://wiki.freecad.org/Path_Post); [post.md (community mirror of Mod/CAM docs)](https://git.polymech.info/polymech/freecad-cam/src/branch/master/Mod/CAM/docs/post.md)
- The CAM "Fixture" command is not available in FreeCAD 1.1 and above. — [CAM Workbench](https://wiki.freecad.org/CAM_Workbench)
- OpenCAMLib is a C++ library with Python bindings, published on PyPI as `opencamlib`; its core is axial and radial cutter-projection (drop-cutter / push-cutter) against triangulated surfaces. The PyPI release surfaced was 2022.12.17 with wheels for Python 3.7-3.11. — [PyPI opencamlib](https://pypi.org/project/opencamlib/); [opencamlib docs](https://opencamlib.readthedocs.io/)
- OpenCAMLib licence: repository mirrors state LGPL since August 2018; a third-party wiki lists GPLv3 (conflict; check the repo LICENSE). — [GitHub mirror](https://github.com/aticoder/opencamlib); contradicted by [CoMakingSpace wiki](https://wiki.comakingspace.de/OpenCAMLib)
- FreeCAD documents OpenCAMLib as an optional dependency for its 3D surfacing operations. — [FreeCAD OpenCamLib page](https://wiki.freecad.org/OpenCamLib)
- CAMotics is GPL open-source software that simulates 3-axis G-code, shows the cut workpiece and can export the cut workpiece as STL. — [LinuxLinks CAMotics](https://www.linuxlinks.com/camotics-3-axis-cnc-gcode-simulator/); [OpenBuilds CAMotics](https://openbuilds.com/projectresources/camotics.2/)
- No documented batch/headless CAMotics mode was found; a user-group question about command-line parameters had no answer. — [camotics-users group](https://groups.google.com/g/camotics-users)
- Other Python-native open CAM projects surfaced: `viaconstructor` (DXF to G-code, 2.5D, on PyPI) and `cq-cam` (CAM on CadQuery). — [viaconstructor](https://pypi.org/project/viaconstructor/0.5.2/); [cq-cam](https://github.com/giannissc/cq-cam)

### Inferences
- For a headless Linux container, FreeCAD CAM is the pragmatic open-source backbone: STEP in, `Path.Main.Job` plus operations (profile, pocket, drilling, adaptive, 3D surface via OCL) scripted in Python, G-code out through a Python post. The agent should emit a FreeCAD Python script rather than G-code directly. Expect to pin a FreeCAD version, because the CAM Python API changed across 0.21 / 1.0 / 1.1 (module rename Path to CAM, tool library rewrite).
- Background knowledge, not verified this session: FreeCAD CAM is in practice 2.5D and 3-axis with limited indexed (3+2) support and no simultaneous 5-axis; its Adaptive operation derives from libarea; PyCAM and HeeksCNC are effectively unmaintained; libactp is historical; Fabex is the renamed BlenderCAM (Blender add-on, 3-axis plus some 4/5-axis indexed, scriptable through Blender's Python in background mode); Kiri:Moto is a browser/JS slicer-CAM (FDM, laser, 3-axis CNC) under MIT licence with an embeddable engine API; LinuxCNC ships a standalone RS274NGC interpreter (`rs274`/"sai") usable for G-code parsing and limits checks. Treat all of these as leads to confirm.
- OpenCAMLib is useful as a library for custom 3-axis finishing passes on meshes, but the team would have to write linking, lead-ins, stock handling and posting themselves.

### Gaps
- Exact FreeCAD 1.1 CAM capability list (3+2, rotary, probing, turning add-on status) and whether CAM operations compute fully under `FreeCADCmd` without Gui imports: not confirmed; needs a hands-on test.
- Current maintenance state and latest release of OpenCAMLib, Fabex/BlenderCAM, Kiri:Moto, PyCAM, HeeksCNC: no 2025-2026 sources retrieved.
- Kiri:Moto headless/engine API: search returned nothing.

## 2. Commercial scriptable CAM (Fusion, Mastercam, hyperMILL, NX, SolidCAM, ESPRIT, Onshape CAM Studio, ModuleWorks)

### Takeaway
Autodesk Fusion is the most accessible commercial route for a small team: its CAM API can create setups and operations, generate toolpaths and post-process, and since 19 May 2025 the APS "Design Automation API for Fusion" is generally available as a cloud/headless execution path that explicitly covers subtractive CAM. Everything else surveyed is desktop-bound, enterprise-licensed, or has no evidence of a public CAM automation API.

### Cited Findings
- Fusion's desktop API exposes `CAM.generateToolpath`, which returns a `GenerateToolpathFuture` that scripts poll before post-processing; official samples cover a basic milling workflow, creating operations from templates, and an additive FFF workflow. — [CAM.generateToolpath](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/cam_CAM_generateToolpath.htm); [Basic Milling Workflow Sample](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BasicMillingWorkflowSample_Sample.htm); [Create CAM Operation From Template](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/New_Operation_Sample_Sample.htm); [Additive FFF sample](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/AdditiveFFFManufacturingSample_Sample.htm)
- Autodesk's Design Automation API for Fusion was announced as generally available on 19 May 2025; Autodesk describes it as covering nearly the whole design-to-manufacture workflow including subtractive CAM, pitched at PLM/MES integration and offloading toolpath generation and post-processing. Toolpath.com is named as an early adopter that built AI CAM and quoting on it. — [APS blog: GA announcement](https://aps.autodesk.com/blog/design-automation-api-fusion-now-generally-available); [APS blog, 27 Feb 2025](https://aps.autodesk.com/node/3599)
- A community "bare-bones" MCP server wraps APS Design Automation for Fusion using 2-legged OAuth and the workitems endpoint (unofficial example). — [autodesk-fusion-mcp-python](https://glama.ai/mcp/servers/@sockcymbal/autodesk-fusion-mcp-python/blob/a3398ac5c76baa252240f301167a4cba2fe6f5b8/fusion_mcp.py)
- Onshape CAM Studio offers 2.5- and 3-axis machining, tool and machine libraries, mill-turn and machine verification; it is included with Professional (reported USD 2,500 per user per year) and Enterprise; "CAM Studio Advanced" requires a separate licence, with price TBC in the source. — [Develop3D first look](https://develop3d.com/simulation/first-look-onshape-cam-studio/); [Onshape blog](https://www.onshape.com/en/blog/cam-studio-comprehensive-milling)
- ModuleWorks publishes no pricing. — [G2 ModuleWorks](https://www.g2.com/products/moduleworks/pricing)
- Mastercam 2026 (July 2025) introduced "AI-enabled CAM intelligence" with a Copilot early-adopter programme; 2026.R2 added GPU-accelerated simulation and made Copilot production, included with active CONNECT maintenance. — [Digital Engineering 24/7](https://www.digitalengineering247.com/article/mastercam-2026-features-ai-enabled-cam-intelligence/mastercam-cnc-software-inc); [Mastercam blog](https://www.mastercam.com/community/blog/mastercam-copilot-ai-that-actually-knows-your-software/)
- Siemens positions NX CAM Feature-Based Machining (recognise features, apply standard operations) as its established automation, alongside an NX X Manufacturing Copilot and the CloudNC CAM Assist integration. — [Siemens NX Manufacturing blog](https://blogs.sw.siemens.com/nx-manufacturing/how-ai-powered-cam-software-is-transforming-cnc-machining)

### Inferences
- Fusion via APS is the only commercial path found where "upload model, run script, get G-code" can run without a desktop seat on a Windows/macOS machine. Since the session could not fetch APS docs, the team must confirm: scripting language (background knowledge: TypeScript scripts in the cloud runtime versus Python on desktop), pricing/token model, which CAM strategies and posts are available, and whether machine simulation/collision results are returned.
- Background knowledge, not verified this session: Mastercam (.NET/NET-Hook), NX (NX Open in Python/C#/C++), SolidCAM, hyperMILL (Automation Center) and ESPRIT all have automation APIs but run only inside licensed Windows desktop seats with per-seat costs in the thousands to tens of thousands of USD per year; none is realistic for Linux containers. ModuleWorks is a B2B toolpath/simulation kernel licensed to CAM vendors (it underlies Onshape CAM Studio and many others) and is not sold to small teams off the shelf. MecSoft (RhinoCAM/VisualCAM) and Machining Cloud were not researched.

### Gaps
- APS Design Automation for Fusion: pricing, quotas, supported CAM operations, and limitations (could not fetch aps.autodesk.com; the host must be allowed in the session network settings to verify).
- Whether Onshape exposes CAM Studio through its REST API: no evidence found either way.
- No current sources retrieved for hyperMILL, SolidCAM, MecSoft, Machining Cloud API terms.

## 3. AI CAM products (CloudNC, Toolpath, Hexagon ProPlanAI, vendor copilots, startups)

### Takeaway
Commercial "AI CAM" in 2025-2026 is delivered as plug-ins inside incumbent CAM systems that automate feature recognition, strategy selection, tooling and feeds/speeds for 3-axis and 3+2 prismatic milling; headline savings are vendor-reported (about 75-80% of programming time), and no vendor was found to offer a public API an external agent could call.

### Cited Findings
- CloudNC CAM Assist targets 3-axis and 3+2 machining; CloudNC claims up to 80% programming time saved. A 2024 beta report cited an average of 68 minutes saved per 3-axis part; turning, mill-turn, CMM and fixture assistance were described as future work with milling the priority. — [Modern Machine Shop](https://www.mmsonline.com/products/cloudnc-ai-assisted-cam-software-accelerates-cnc-programming); [The Manufacturer](https://www.themanufacturer.com/articles/new-software-solution-to-accelerate-manual-cam-programming-time-by-80-enabling-manufacturers-to-be-more-productive/); [CloudNC blog](https://cloudnc.com/blog/ai-powered-cam-automation-cnc)
- CAM Assist is sold as an add-on for Autodesk Fusion, Siemens NX and GibbsCAM; a 2026 report on a USD 20 million raise lists Fusion, Mastercam, NX CAM, GibbsCAM and SolidCAM integrations and a "Quote Agent" scheduled for later in 2026. — [Autodesk marketplace listing](https://marketplace.autodesk.com/apps/301506fd-08a7-4f3e-b305-92a5fbefc4f9); [CloudNC GibbsCAM release](https://www.cloudnc.com/news-room/cam-assist-the-first-ai-plug-in-for-cam-is-now-available-for-gibbscam); [The Machine Maker: CloudNC raises $20M](https://themachinemaker.com/news/cloudnc-raises-20-million-to-expand-ai-powered-cnc-machining-solutions/)
- Toolpath (toolpath.com): USD 10M seed led by Leaders Fund (Sept 2024); a May 2025 round led by Kennametal with ModuleWorks took total funding to USD 20M; Autodesk made an undisclosed strategic investment in Aug 2025, stating the aim of closed-loop automated workflows in Fusion (manufacturability analysis, strategy planning, sending complete programs to Fusion). Toolpath has a Fusion add-on to import its program for refinement. — [Hypepotamus](https://hypepotamus.com/news/toolpath-secures-strategic-investment-cam-ai/); [Develop3D](https://develop3d.com/manufacture/toolpath-sees-further-investment-in-its-ai-cam-tools/); [Autodesk News](https://adsknews.autodesk.com/en/news/strategic-investment-toolpath/)
- Hexagon ProPlanAI: announced 2024 with a claimed 75% reduction in programming time; available to ESPRIT EDGE users from Q1 2025 as an add-on subscription; learns from a shop's past programs rather than hand-written rules. A later ESPRIT EDGE release (reported April 2026) extended it to turning, mill-turn and Swiss. Hexagon's separate Copilot is a product-help assistant that explicitly does not advise on feeds/speeds or process. — [Hexagon press release](https://hexagon.com/company/newsroom/press-releases/2024/hexagons-new-ai-powered-automation-slashes-machine-tool-programming-time-by-75-per-cent); [Hexagon ProPlanAI article](https://hexagon.com/resources/resource-library/hexagons-proplanai--new-artificial-intelligence-technology-is-the-next-step-in-the-evolution-of-cam-programming); [MMS](https://mmsonline.com/products/hexagon-ai-powered-cam-software-streamlines-part-programming)
- Mastercam Copilot (production in 2026.R2): help and command access, voice/text commands, feed-rate and spindle-speed adjustments; no feature recognition mentioned. — [Mastercam blog](https://www.mastercam.com/community/blog/mastercam-copilot-ai-that-actually-knows-your-software/)
- Sandvik and Microsoft announced a "Manufacturing Copilot" initially for Cimatron, GibbsCAM and SigmaNEST. — [Digital Engineering 24/7](https://www.digitalengineering247.com/article/sandvik-microsoft-launches-ai-in-cam-software/news)
- CloudNC publishes a 2026 guide defining the "CAM copilot" category (vendor-authored). — [CloudNC blog](https://www.cloudnc.com/blog/what-is-a-cam-copilot)

### Inferences
- Two product classes exist: (a) planning engines that output operations/toolpaths (CloudNC CAM Assist, Toolpath, ProPlanAI) and (b) chat assistants over product help and command execution (Mastercam Copilot, Hexagon Copilot, NX X Manufacturing Copilot). Only class (a) replaces programmer work, and all of it writes into a host CAM system for human review, which is the same human-in-the-loop pattern a new agent should adopt.
- For a small team, these are usable only as a paid plug-in on top of a Fusion seat; none is a callable building block. Their scope (3-axis and 3+2 prismatic aluminium/steel parts) is a market signal about what is tractable today.
- All time-saving numbers are vendor claims; no independent benchmark was found.

### Gaps
- No public API documentation found for CloudNC, Toolpath or ProPlanAI.
- No sources retrieved this session for Lambda Function, aiCAM, Up2parts, Limitless CNC, Harmoni, AdaOne or other 2025-2026 startups; not researched due to tool-call budget.
- Dates for the Sandvik Manufacturing Copilot and CloudNC's 2026 raise were not confirmed from primary pages.

## 4. Research on LLMs for CAM, G-code and process planning (2024-2026)

### Takeaway
Published work shows LLMs can write simple G-code and answer process-planning questions but fail on numeric grounding and long programs, so the literature converges on retrieval/knowledge-graph grounding plus external validators; machining feature recognition on synthetic B-rep benchmarks is near-saturated (about 99% accuracy on MFCAD++), with generalisation to real parts the open problem.

### Cited Findings
- GLLM (arXiv, Jan 2025): natural language to G-code using fine-tuned StarCoder-3B with RAG and a self-corrective loop; validation includes syntax checks, G-code-specific checks and functional correctness measured by Hausdorff distance. — [alphaXiv 2501.17584](https://alphaxiv.org/overview/2501.17584v1); [AITopics entry](https://aitopics.org/doc/arxivorg:8AE08FFC)
- Sket et al. (Advances in Production Engineering & Management, 2025) compared ChatGPT-3.5 and GPT-4o at generating ISO G-code for 3-axis milling, checking the output in a CAM application and assessing error recognition. — [APEM 20(2) 224-238](https://apem-journal.org/Archives/2025/Abstract-APEM20-2_224-238.html)
- A study in Machines (vol. 14, 2026) on ChatGPT G-code optimisation for automotive metal parts reported a failure where the model deleted the longest code block (31% of the program), attributed to token-minimisation bias and lack of semantic understanding. — surfaced via [AITopics g-code tag](https://aitopics.org/tag/g-code) (primary URL not retrieved)
- FDM-Bench benchmarks LLMs on additive-manufacturing tasks, including detecting defects/anomalies in FDM G-code. — [FDM-Bench review](https://www.themoonlight.io/review/fdm-bench-a-comprehensive-benchmark-for-evaluating-large-language-models-in-additive-manufacturing-tasks)
- ARKNESS (arXiv 2506.13026, June 2025): knowledge-graph-augmented LLM for CNC process planning questions (tool selection, feed-speed pairs, multi-axis routing); authors state LLMs "routinely hallucinate numeric values and provide no provenance"; reports +22.4 pp F1 and 8.1x ROUGE-L over baselines. It is QA/retrieval, not toolpath generation, and includes no collision evaluation. — [arXiv 2506.13026](https://arxiv.org/abs/2506.13026v1)
- LLM-MPKG (2025 journal paper): LLM-enabled construction of machining process knowledge graphs. — [XJTU scholar page](https://scholar.xjtu.edu.cn/en/publications/a-large-language-model-enabled-machining-process-knowledge-graph-/)
- Feature recognition: MFCAD++ has about 60,000 models with 3-10 machining features including non-planar faces; BRepNet was an early B-rep segmentation network. — [Geometric Deep Learning for CAD survey, arXiv 2402.17695](https://arxiv.org/pdf/2402.17695)
- AAGNet (graph neural network on a geometric attributed adjacency graph, multi-task: semantic, instance and bottom-face segmentation; introduced MFInstSeg) reports 99.29% accuracy / 98.64% IoU on MFCAD++ versus 99.22% / 97.75% for BRepNet, as tabulated in a 2025 transformer B-rep paper. — [arXiv 2504.07134](https://arxiv.org/pdf/2504.07134); [AAGNet summary](https://peeref.com/works/34020166)
- FeatureFox (arXiv 2604.26770, April 2026) recasts machining feature recognition as panoptic segmentation and reports high panoptic quality with far fewer training parts than AAGNet, while AAGNet remains slightly ahead with full training data. — [arXiv 2604.26770](https://arxiv.org/html/2604.26770)
- BrepMFR addresses domain adaptation from synthetic to real B-rep parts for feature recognition. — [BrepMFR](https://bohrium.dp.tech/paper/arxiv/b85511321954a2dfc932a0828816fc6a37a849cbd317af7e133e238556d68e91)

### Inferences
- The evidence supports an architecture where the LLM never emits final G-code: it selects features, operations, tools and parameters as structured data, a deterministic CAM kernel computes toolpaths, and independent validators (parser, limits, stock simulation, geometric comparison to target) gate output. GLLM's Hausdorff-distance check is a reusable idea: compare simulated cut stock against the design model.
- Feeds and speeds should come from a lookup (tool vendor data, material tables, a calculator) with the LLM choosing among sourced values, given the documented numeric hallucination.
- Rule-based feature recognition on the B-rep (holes, pockets, slots via OpenCascade face/edge adjacency) is likely sufficient for a v1 limited to prismatic parts; learned models such as AAGNet have public code but are trained on synthetic data and need domain adaptation.

### Gaps
- No dedicated benchmark of LLM-generated CNC toolpaths with collision/unsafe-motion metrics was found; this appears to be a genuine gap in the literature as searched, though the search was not exhaustive.
- No sources retrieved on LLM-driven fixture design or setup planning.
- Licences and code availability for AAGNet, BRepNet, UV-Net were not checked this session.

## 5. Additive manufacturing: scriptable slicers, orientation, printability

### Takeaway
FDM slicing is the easiest manufacturing output to automate headlessly: OrcaSlicer and PrusaSlicer both have documented CLIs, community Docker wrappers exist, and there are 2026 Python packages for end-to-end headless pipelines and B-rep printability analysis.

### Cited Findings
- OrcaSlicer's official wiki documents headless CLI mode to load, transform and slice models for automation and CI; setting keys map to flags by replacing underscores with hyphens (e.g. `--layer-height`). — [OrcaSlicer wiki: CLI mode](https://www.orcaslicer.com/wiki/cli/cli_mode)
- Third-party CLI references exist for OrcaSlicer and Bambu Studio; a Bambu forum thread reports the CLI could not apply external presets. — [Printago OrcaSlicer CLI reference](https://printago.io/blog/orca-slicer-cli-reference); [Printago Bambu Studio CLI reference](https://printago.io/blog/bambu-studio-cli-reference); [Bambu forum](https://forum.bambulab.com/t/cli-cannot-apply-external-presets/197842)
- PrusaSlicer advertises its CLI for batch slicing and pipeline integration; a PrusaSlicer 3.0.0-alpha13 preview was listed as released 2 Nov 2026. — [Prusa PrusaSlicer page](https://www.prusa3d.com/p/prusaslicer/index.md)
- `fabprint` (PyPI) is a headless 3D-print pipeline: arrange, orient, slice and send to printer from a TOML config. — [fabprint on PyPI](https://pypi.org/project/fabprint/0.1.86/)
- "Trident" is a community project running OrcaSlicer's slicing engine headless in Docker; the LinuxServer.io OrcaSlicer image is GUI-in-browser, not headless slicing. — [Trident](https://ca.unraid.net/apps/trident-0gnf5j41xhpclg); [linuxserver docker-orcaslicer](https://docs.linuxserver.io/images/docker-orcaslicer)
- An `orcaslicer-addon` npm package exists (Node binding to the slicer). — [libraries.io](https://libraries.io/npm/orcaslicer-addon)
- `augura` (PyPI, v0.1.x): B-rep-exact FDM printability analysis and print advice for build123d/STEP via OpenCascade: overhang angles, wall thickness (flags walls thinner than min_perimeters x nozzle) and contact footprint computed analytically rather than on a mesh. — [augura on PyPI](https://pypi.org/project/augura/)
- Fusion's API includes an additive FFF manufacturing sample. — [Autodesk sample](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/AdditiveFFFManufacturingSample_Sample.htm)

### Inferences
- Recommended v1 path: STEP to mesh (OpenCascade tessellation) to OrcaSlicer or PrusaSlicer CLI with pinned printer/filament/process profiles, then parse the slicer's G-code header for time and material as a cost proxy. Verification is cheap: slicer exit status and warnings, layer/extent checks against build volume, and printability checks (augura or custom overhang/thin-wall analysis).
- Background knowledge, not verified this session: CuraEngine is a standalone C++ CLI (AGPL-3.0) driven by JSON definition files; PrusaSlicer and OrcaSlicer are AGPL-3.0, which matters if the team redistributes or hosts a modified slicer; both slicers have built-in auto-orient and auto-arrange; Tweaker-3 is an open-source auto-orientation tool; metal AM build prep (Materialise Magics, Autodesk Netfabb, Oqton, Dyndrite with a Python API) is commercial and enterprise-priced.

### Gaps
- Current stable version numbers for OrcaSlicer, PrusaSlicer stable, and CuraEngine in late 2026 were not confirmed.
- No sources retrieved on metal AM tooling, support optimisation research, or SuperSlicer status.

## 6. Sheet metal, laser, waterjet: unfold, nesting, DXF

### Takeaway
FreeCAD's SheetMetal add-on is the main open-source unfold tool and exports DXF/SVG flat patterns, but its scripted/unattended use is poorly documented and it suffers from topological-naming fragility; no sourced evidence was found this session for nesting tools or build123d/CadQuery unfolding.

### Cited Findings
- FreeCAD SheetMetal's Unfold command works from a selected planar face and can export DXF or SVG; exported DXF includes bend lines, which must be separated/removed before sending to a cutter. — [SheetMetal Unfold](https://wiki.freecad.org/SheetMetal_Unfold)
- An "UnattendedUnfold" command exists but is not available by default (requires enabling "Engineering Mode" in preferences). — [SheetMetal UnattendedUnfold](https://wiki.freecad.org/SheetMetal_UnattendedUnfold)
- The workbench warns that editing earlier bends can renumber faces and break later bends (topological naming problem). — [SheetMetal Workbench](https://wiki.freecad.org/SheetMetal_Workbench)
- The add-on is developed at shaise/FreeCAD_SheetMetal; the changelog indexed showed releases through v0.4.18 (8 Jun 2024). — [GitHub: shaise/FreeCAD_SheetMetal](https://github.com/shaise/FreeCAD_SheetMetal)

### Inferences
- For v1, laser/waterjet parts that are already flat need no unfold: project the planar face of the STEP to 2D and write DXF (OpenCascade plus `ezdxf`), which is far more robust than bending workflows. Bent parts should be a later milestone, generated from a parametric sheet-metal definition (flat pattern computed from bend table/K-factor) rather than unfolding arbitrary solids.
- Background knowledge, not verified this session: Deepnest (Electron app, MIT/GPL mix, original repo dormant with community forks) and SVGnest (browser JS) are the usual open-source nesting options and are awkward headless; Python alternatives include `nest2D` (libnest2d bindings) and newer Rust nesters such as `sparrow`/`jagua-rs`. SendCutSend and similar services accept DXF/STEP uploads and do their own nesting, so nesting is only needed for in-house cutting.

### Gaps
- Nesting tools (Deepnest forks, SVGnest, others): no sources retrieved.
- build123d/CadQuery sheet-metal unfold approaches: no sources retrieved.
- Whether SheetMetal unfold runs under `FreeCADCmd` without the GUI: not documented in what was found; needs a test.

## 7. DFM checking, quoting and drawings

### Takeaway
No reliable public, self-serve instant-quote or DFM API from the major marketplaces (Xometry, Protolabs, Fictiv, SendCutSend) was confirmed; quoting is web-UI first, with APIs apparently reserved for enterprise/partner arrangements. Open-source DFM is fragmentary (thickness analysis, FDM printability), so a small team should expect to build its own rule checks on OpenCascade and treat marketplace quotes as a manual or browser-mediated step.

### Cited Findings
- Xometry's Instant Quoting Engine returns price and lead time from a CAD upload via its web UI and supplier network (reported as 4,000-5,000+ suppliers by different sources). — [Xometry EU: Instant Quoting Engine](https://xometry.eu/en/instant-quoting-engine/); [RapidDirect 2026 review](https://www.rapiddirect.com/blog/8-best-digital-manufacturing-platforms-with-instant-quotes-2026-review/)
- A third-party blog claims a Xometry Developer Portal with API keys and a DFM feedback endpoint; this could not be confirmed on Xometry's own pages and should be treated as unverified. — [third-party blog](https://www.topbubbleindex.com/blog/xometry-design-resources)
- Protolabs provides automated DFM analysis with quotes through its web platform (uploads up to 150 MB); sources conflict on whether its CNC quotes are instant. No developer API surfaced. — [Protolabs help: uploading CAD](https://protolabs.helpdocs.io/l/en/help-center/uploading-cad-files); [Protolabs UK platform blog](https://www.protolabs.co.uk/resources/blog/your-new-digital-manufacturing-platform-for-quoting-design-analysis-and-part-ordering/); [Fabcon comparison](https://fabcon.com/articles/precision-cnc-machining/best-instant-cnc-quote-platforms/)
- Protolabs Network (Hubs) offers instant quotes through its web platform. — [Hubs instant quotes](https://www.hubs.com/instant-quotes/)
- CNC24: no public developer API, SDKs or API docs published. — [apis.io CNC24](https://apis.io/providers/cnc24/)
- PartPacket: hosted MCP server and REST API comparing live FDM (STL) print estimates from Slant 3D and Craftcloud; no account needed to quote; no payments or orders; launch limits of 20 quote requests per IP per day and 100 service-wide. — [PartPacket](https://mcpservers.org/servers/partpacket-com-docs)
- goCAD offers REST microservices that analyse STEP files (volume, surface, bounding box, machining technology classification) for building one's own quoting. — [goCAD microservices](https://gocad.de/en/microservices)
- DigiFabster sells instant-quoting software to manufacturers (shop-side, not buyer-side). — [DigiFabster](https://digifabster.com/industry/on-demand-manufacturers/)
- Dassault 3DEXPERIENCE Make accepts STEP up to 50 MB and some sellers connect their own quote engines. — [3DEXPERIENCE Make](https://www.3ds.com/make)
- Open-source DFM building blocks: Analysis Situs (BSD-3, on OpenCascade) has ray-based thickness analysis, and its author notes a thickness field alone is insufficient for automatic DFM without interpretation. — [Analysis Situs blog: DFM analysis](https://quaoar.su/blog/category/dfm-analysis)
- `@casys/mcp-dfm` (JSR, v0.3.0): MCP server that takes STEP, tessellates with Gmsh and samples wall thickness; its docs state the method is not a proof of global minimum wall thickness. — [mcp-dfm](https://jsr.io/@casys/mcp-dfm)
- "DFM Studio" presents itself as free and open-source DFM analysis (web app; not evaluated). — [dfm-studio](https://dfm-studio.vercel.app/)
- CADEX Manufacturing Toolkit (commercial SDK) includes DFM rules such as undercut detection. — [CADEX MTK docs](https://docs.cadexsoft.com/mtk/mtk_news)
- A CloudNC "Quote Agent" is scheduled for later in 2026. — [The Machine Maker](https://themachinemaker.com/news/cloudnc-raises-20-million-to-expand-ai-powered-cnc-machining-solutions/)

### Inferences
- A practical v1 DFM layer is in-house rules over the B-rep with OpenCascade (pythonOCC / build123d / CadQuery): bounding box versus machine envelope, minimum internal corner radius versus tool radius, pocket depth-to-width and hole depth-to-diameter ratios, thin walls via ray casting, tool-access direction count (number of setups) via face-normal visibility, undercut detection per approach direction, and overhang/thin-wall checks for FDM. Each rule returns a structured finding the LLM can act on.
- Cost estimation in-house can be derived from the pipeline's own outputs (CAM cycle time from the simulator or post, stock volume, slicer time and filament mass) rather than a marketplace API. Marketplace quotes would be an optional human step.
- Commercial SDKs (CADEX MTK; background knowledge: also DFMPro, aPriori, CASTOR, Paperless Parts, which were not researched) are the route to production-grade DFM but carry enterprise licensing.

### Gaps
- Official API status for Xometry, Protolabs, Fictiv, SendCutSend, JLCCNC, PCBWay, Paperless Parts, aPriori, DFMPro, CASTOR: no primary API documentation was retrieved; absence of search hits is not proof that partner APIs do not exist. Direct vendor contact is needed.
- Tolerance/GD&T, STEP AP242 PMI and automated 2D drawing generation (FreeCAD TechDraw scripting, build123d/CadQuery drawing export): not researched this session due to tool-call budget.

## 8. Safety, verification and realistic first-version scope

### Takeaway
Open-source verification tooling is the weakest link: the only open material-removal simulator found (CAMotics) is 3-axis and has no confirmed headless mode, and no open Python library for stock simulation plus collision checking surfaced. Commercial AI CAM vendors themselves limit scope to 3-axis/3+2 prismatic milling with human review, which supports a v1 limited to FDM printing, flat laser/waterjet DXF, and 2.5D/3-axis milling with mandatory simulation and human sign-off.

### Cited Findings
- CAMotics simulates 3-axis G-code and can export the cut workpiece as STL (usable for comparison against the design), but no batch/headless mode is documented in the sources found. — [LinuxLinks](https://www.linuxlinks.com/camotics-3-axis-cnc-gcode-simulator/); [camotics-users group](https://groups.google.com/g/camotics-users)
- Research systems validate LLM G-code with layered checks: syntax, G-code-specific rules and geometric comparison (Hausdorff distance) to the intended shape. — [GLLM, alphaXiv 2501.17584](https://alphaxiv.org/overview/2501.17584v1)
- Documented LLM failure modes include hallucinated numeric process parameters without provenance and silently deleting large program sections. — [ARKNESS, arXiv 2506.13026](https://arxiv.org/abs/2506.13026v1); [AITopics g-code tag (Machines 2026 study)](https://aitopics.org/tag/g-code)
- Commercial AI CAM is scoped to 3-axis and 3+2 milling and outputs into a host CAM system where a programmer reviews it; Onshape CAM Studio and Mastercam 2026.R2 ship machine verification / GPU-accelerated simulation as the commercial verification path. — [MMS on CloudNC](https://www.mmsonline.com/products/cloudnc-ai-assisted-cam-software-accelerates-cnc-programming); [Develop3D on CAM Studio](https://develop3d.com/simulation/first-look-onshape-cam-studio/); [Digital Engineering 24/7 on Mastercam](https://www.digitalengineering247.com/article/mastercam-2026-features-ai-enabled-cam-intelligence/mastercam-cnc-software-inc)

### Inferences
- Suggested verification stack for v1 (design recommendation, not a sourced fact): (1) parse the emitted G-code with an independent interpreter and reject unknown codes; (2) check every move against machine travel limits, safe-Z rules, maximum feed/spindle and tool-length/holder reach; (3) run a stock-removal simulation (a simple in-house heightmap/dexel simulator is adequate for 3-axis, or CAMotics if a headless path is proven) and detect rapids into stock; (4) compare the simulated result with the target model for gouges and leftover material against tolerance; (5) check holder and fixture/vise collision with swept volumes; (6) require human approval plus a first-run procedure (single-block, reduced rapid override, air cut) before cutting metal.
- Realistic v1 scope: FDM printing (fully automatable, low consequence of failure), flat-part DXF for laser/waterjet services, and 2.5D/3-axis milling of prismatic parts in one or two vise setups using a fixed, pre-measured tool library on a hobby/prosumer machine (GRBL, LinuxCNC, Mach-class controllers that FreeCAD already posts for). Defer turning, 3+2 and 5-axis, automatic fixture design, and bent sheet metal.
- FreeCAD CAM in a container is the open path; Fusion via APS is the commercial fallback when toolpath quality or simulation matters more than licence freedom.

### Gaps
- No sourced open-source library for headless material-removal simulation with holder/fixture collision detection was found; background knowledge suggests FreeCAD has a built-in CAM simulator and LinuxCNC's interpreter can be run standalone, but neither was verified for headless use this session.
- No published incident data or benchmark quantifying unsafe-toolpath rates for LLM-generated CAM was found.
