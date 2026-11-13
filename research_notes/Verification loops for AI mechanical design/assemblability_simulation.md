# Automated assemblability verification (assembly sequence planning, assembly simulation, tool access) — state as of November 2026

Source-quality note: in this session only github.com could be fetched directly. arxiv.org and huggingface.co failed to resolve, so every non-GitHub finding below comes from web-search summaries (marked "search summary"). Numbers from search summaries should be checked against the primary paper before being quoted in a final report. Three arXiv IDs surfaced by search (2607.05123, 2609.17263, 2609.21761) are 2026 preprints I could not open; they are flagged where used.

## 1. Assembly sequence planning (ASP) and disassembly-based methods: key works, code, inputs, runtimes, success rates

### Takeaway
The most directly reusable open code for a headless "do the parts come apart, and therefore go together" verifier is the MIT/Autodesk line: Assemble-Them-All (2022) and ASAP (2023/24), both MIT-licensed, taking only .obj meshes in the assembled pose and returning a disassembly order plus paths. Reported sequence-level success on a 240-assembly benchmark is about 82-86%, so "no plan found" is evidence, not proof, of unassemblability.

### Cited Findings

**Assemble Them All (Tian et al., SIGGRAPH Asia 2022)**
- Input is .obj meshes in the assembled state in one directory; `assets/process_mesh.py` rescales them (optional `--subdivide`); since a 03/2024 update no `translation.json` is needed and file names are arbitrary (fetched directly) — [GitHub: Assemble-Them-All](https://github.com/yunshengtian/Assemble-Them-All)
- Planners shipped: two-part physics-based `bfs` (authors' method) and `bk-rrt`; geometric baselines `rrt`, `rrt-connect`, `birrt`, `trrt`, `matevec-trrt`; multi-part sequence planners `random`, `queue`, `prog-queue` (authors' method) (fetched directly) — [GitHub: Assemble-Them-All](https://github.com/yunshengtian/Assemble-Them-All)
- Simulator is built on DiffRedMax; collision checking is point-based SDF (mesh vertices of one part tested against the SDF of the other), so the README recommends subdividing meshes for denser contact points (fetched directly) — [GitHub: Assemble-Them-All](https://github.com/yunshengtian/Assemble-Them-All)
- Default budgets: `--max-time` 120 s for two-part planning; multi-part `--seq-max-time` 3600 s and `--path-max-time` 120 s per path. Rotational motion requires `--rotation` (fetched directly) — [GitHub: Assemble-Them-All](https://github.com/yunshengtian/Assemble-Them-All)
- Install: conda `environment.yml`, then build the C++ simulation binding with `python setup.py install` (CMake > 3.16; `libgl1-mesa-dev xorg-dev` on Linux). README calls package versions "critical"; a community Docker image is linked. Code license MIT; dataset derived from Fusion 360 Gallery and subject to its license (fetched directly) — [GitHub: Assemble-Them-All](https://github.com/yunshengtian/Assemble-Them-All)
- Multi-part benchmark is binned Small 3-9, Medium 10-49, Large 50+ parts; a 53-part engine was fully disassembled in about 5 minutes versus hours for the MV+T-RRT baseline; abstract claims 80-part assemblies solved "within several minutes"; mean disassembly time per part reported as 25.6 s (Full BFS) and 6.7 s (Progressive BFS) overall, 30.6 s and 19.4 s on the Large bin (search summary; table extraction was described as ambiguous) — [arXiv 2211.03977](https://arxiv.org/pdf/2211.03977)

**ASAP (Tian et al., ICRA 2024)**
- Input identical in form: .obj meshes in assembled state under `assets/<dir>/<id>/`; same preprocessing and subdivision advice (fetched directly) — [GitHub: ASAP](https://github.com/yunshengtian/ASAP)
- Adds gravity and stability: each sub-assembly must be physically stable with a limited number of held parts and a support surface. CLI exposes `--max-gripper` (number of grippers holding/moving parts), `--max-pose`, `--pose-reuse`, `--base-part`, `--budget` (number of simulator feasibility evaluations), `--timeout`, `--plan-grasp`, `--plan-arm` (fetched directly) — [GitHub: ASAP](https://github.com/yunshengtian/ASAP)
- Example: `python plan_sequence/run_seq_plan.py --dir beam_assembly --id original --planner dfs --generator heur-out --max-gripper 2 --base-part 6 --log-dir logs/beam_seq --early-term`; outputs `setup.json`, `stats.json`, `tree.pkl`; `play_logged_plan.py --save-all` exports meshes, poses, paths and videos (fetched directly) — [GitHub: ASAP](https://github.com/yunshengtian/ASAP)
- Dataset: 1,906 training assemblies (591 MB) and 240 test assemblies (124 MB); MIT license; pip-installable Python deps (numpy, networkx, trimesh, torch, torch_geometric, ikpy, etc.) plus the compiled simulator (fetched directly) — [GitHub: ASAP](https://github.com/yunshengtian/ASAP)
- Poster claims roughly 30% higher success than baselines on hundreds of assemblies of up to 50 parts under fixed evaluation budgets; learned part selector is a 2-layer GATv2 with 8 heads (search summary) — [ASAP poster](https://asap.csail.mit.edu/static/poster.pdf); [arXiv 2309.16909](https://arxiv.org/pdf/2309.16909)

**Follow-ups 2025-2026**
- Fabrica (Tian et al., CoRL 2025, Outstanding Paper): hierarchical precedence, sequence, grasp and motion planning plus automated fixture generation, with RL policies for contact-rich steps; 80% successful steps zero-shot on real hardware; benchmark is only 7 assemblies of 5-9 parts (search summary) — [arXiv 2506.05168](https://arxiv.org/abs/2506.05168v1); [PMLR](https://proceedings.mlr.press/v305/tian25a.html)
- GLARE, "CAD-Based Relation Learning and Geometric-Symbolic Planning for Robotic Assembly" (2026 preprint): automatic relation extraction between components with optional human correction, geometric disassembly planner for collision-free per-part paths, then symbolic planner; reports 206/240 solved (85.83%) on the ASAP test set versus 82.08% for ASAP; residual failures attributed to no rotational motions, no subassembly planning, and interlocking assemblies (search summary; not opened) — [arXiv 2609.17263](https://arxiv.org/pdf/2609.17263)
- MERL AssemblyBench / AssemblyDyno (TR2026-076): a prior method scores nearly 30% worse on the new, harder dataset than on furniture datasets; AssemblyDyno reaches about 33% success in a physical trial; documented failure mode is a predicted motion leaving a part stuck in an intermediate position (search summary) — [MERL TR2026-076](https://www.merl.com/publications/docs/TR2026-076.pdf)
- "A Unified Framework for Automated Assembly Sequence and Production Line Planning using Graph-based Optimization" (Dec 2025 preprint) surfaced but was not examined (search summary) — [arXiv 2512.13219](https://arxiv.org/pdf/2512.13219)

**Open CAD-kernel-side frameworks**
- APLAN (Cramer, Kellens, Demeester, Procedia CIRP 127, 2024, pp. 56-61): open assembly-planning workbench for FreeCAD with automatic constraint detectors and an interactive assembly-graph viewer; must be compiled into FreeCAD via a `BUILD_APLAN` CMake option (search summary) — [GitHub: FreeCAD-APLAN](https://github.com/martcram/FreeCAD-APLAN); [KU Leuven record](https://lirias.kuleuven.be/4136527)
- A 2015 Revista Cubana de Ingenieria paper built a PythonOCC/OpenCascade tool that reads STEP assemblies and detects part collisions along disassembly directions (search summary) — [DOAJ record](https://doaj.org/article/30c2740dbfb84a3fbcab7eff8dae6b12)
- cadclaw (PyPI, MIT per a write-up): "automated check suite for STEP-based CAD assemblies" with a Disassembly gate providing sequenced part removal, radial exploded views and animation frame export; v0.4.7 on Zenodo April 2026, v0.8.0 on PyPI; project states it does not prove physical build conformance (search summary; internals unverified) — [PyPI: cadclaw](https://pypi.org/project/cadclaw/); [CI-for-CAD write-up](https://cadclaw.pages.dev/ci-for-cad/)

**Datasets and adjacent learning work**
- JoinABLe (Autodesk, CVPR 2022): predicts a parametric joint between two B-rep parts (link prediction over B-rep faces/edges, then pose search); 79.53% accuracy versus about 80% human; joint data j1.0.0 is 2.8 GB from the Fusion 360 Gallery Assembly Dataset (fetched directly) — [GitHub: JoinABLe](https://github.com/AutodeskAILab/JoinABLe)
- IKEA-Manual (NeurIPS 2022 D&B): 102 IKEA objects with parts, assembly plans and manual alignment; biased toward chairs and does not model connectors (search summary) — [arXiv 2302.01881](https://arxiv.org/pdf/2302.01881)
- FurnitureBench: real-world long-horizon benchmark with 5000+ demonstrations, 3D-printable furniture models and the FurnitureSim simulator (search summary) — [arXiv 2305.12821](https://arxiv.org/pdf/2305.12821)
- BrickGPT (Pun et al., ICCV 2025): StableText2Brick has 47,000+ brick structures; validity check plus physics-aware rollback during generation yields 100% validity and 98.8% stability; without rollback stability drops to 24.0%, without both checks to 37.2% validity / 12.8% stability; stability analysis is a force-equilibrium optimisation solved with commercial Gurobi (search summary; ablation and Gurobi detail from secondary summary sites) — [arXiv 2505.05469](https://arxiv.org/abs/2505.05469); [secondary summary](https://en.papernotes.org/ICCV2025/3d_vision/generating_physically_stable_and_buildable_brick_structures_from_text/)

### Inferences
- For a generate-verify-revise loop, ASAP/Assemble-Them-All are usable as-is: tessellate each build123d solid to .obj in assembled pose, subdivide, run with a time budget, parse `stats.json`. The compiled simulator and pinned dependencies argue for a prebuilt Docker image.
- Per-part costs of roughly 7-30 s imply a 20-part assembly check costs minutes, not seconds; this belongs behind cheaper geometric gates (section 3), not in every iteration.
- An 82-86% solve rate on valid assemblies means false "unassemblable" verdicts in roughly one case in six; the verifier should report "no plan found within budget" with the stuck part set, not a hard failure.
- BrickGPT is the cleanest published demonstration that an in-loop physical check with rollback transforms outcome quality (24% to 98.8% stable); it is the best analogy for the agent loop being built.
- Point-vs-SDF collision means thin features and sub-millimetre clearances are only resolved to mesh/SDF sampling density; nominal-contact (zero-clearance) CAD fits are likely to read as either stuck or free depending on tolerance settings.

### Gaps
- Exact per-bin success rates from Assemble-Them-All Table 3 and ASAP's own heuristic-vs-GNN table were not retrievable.
- "Breaking Bad" (fracture reassembly), Assembly101, NIST task boards and the neural 3D part-assembly literature were not researched within the call budget; they concern pose prediction/robot skill rather than feasibility of a designed product and are likely low relevance, but that is my judgement, not a sourced finding.
- No source found on classical non-directional blocking graph (Wilson and Latombe) open implementations; APLAN is the closest open home for such algorithms.
- Maximum practical part count for ASAP is not stated in the repo (dataset tops out around 50 parts).

## 2. Simulators for contact-rich insertion/assembly and their robustness at tight clearances

### Takeaway
Rigid-body simulators can now handle nut-and-bolt and sub-millimetre insertion using SDF or hydroelastic contact, but they are tuned per asset, sensitive to mesh/SDF resolution, and aimed at robot policy training rather than design verification. None of the sources shows a robust general treatment of press fits, snap fits or cables.

### Cited Findings
- Factory (NVIDIA, RSS 2022): high-quality nut-and-bolt meshes are 10k-50k triangles; naive contact generation gives about 1e6 contacts, a careful scheme about 1e4; realistic thread clearances matter for jamming and cross-threading (search summary) — [arXiv 2205.03532](https://arxiv.org/pdf/2205.03532v1.pdf)
- IndustReal (NVIDIA, RSS 2023): built on Factory in Isaac Gym; introduces a simulation-aware policy update because agents exploit inaccurate collision dynamics (interpenetration) to gain reward; notes prior work typically used clearances of 1 mm or more; an Isaac Lab port exists (search summary) — [arXiv 2305.17110](https://arxiv.org/pdf/2305.17110.pdf)
- AutoMate (NVIDIA, RSS 2024): dataset of 100 simulation- and real-compatible assemblies; specialist policies reach about 80%+ success on 80 assemblies and 90%+ on 55; real-world mean 86.5% over 20 assemblies (4.2% below sim); generalist 84.5% (search summary) — [arXiv 2407.08028](https://arxiv.org/abs/2407.08028); [NVIDIA blog](https://developer.nvidia.com/blog/training-sim-to-real-transferable-robotic-assembly-skills-over-diverse-geometries)
- Isaac Sim 6.x (Newton backend) documents a hydroelastic-contact walkthrough for a threaded nut-and-bolt: both shapes need the SDF collision API, SDF must be sized to resolve the helical thread, and hydroelastic contact is not supported for planes, heightfields or non-watertight meshes; the model is inspired by Drake's hydroelastic contact (search summary) — [Isaac Sim docs](https://docs.isaacsim.omniverse.nvidia.com/latest/physics/hydroelastic_contact_walkthrough.html)
- CRISP (2026 preprint): in a bolt-nut test, SDF-vs-SDF only modestly beat MuJoCo because SDF gradients are numerically differentiated, giving inaccurate contact points and normals; mesh-vs-SDF succeeded at moderate tolerances but failed at the tightest tolerance due to mesh discretisation (search summary; not opened) — [arXiv 2609.21761](https://arxiv.org/pdf/2609.21761)
- Assemble-Them-All/ASAP simulator: point-based SDF penalty contact on DiffRedMax, accuracy tied to vertex density (fetched directly) — [GitHub: Assemble-Them-All](https://github.com/yunshengtian/Assemble-Them-All)

### Inferences
- For design verification, dynamic simulation is the wrong first tool for threads, press fits and snap fits. Treat them symbolically: recognise the fastener/fit, replace it with a kinematic insertion direction plus a clearance/interference budget, and check the corridor geometrically.
- Mesh discretisation error (chordal tolerance) must be smaller than the clearance being tested; a 0.1 mm peg-in-hole needs tessellation deviation well under 0.05 mm or an exact B-rep distance query (OCCT `BRepExtrema`), otherwise results are noise.
- Physics simulation earns its place for one question that geometry cannot answer: gravity stability of partial assemblies and whether a part falls out before it is fastened (ASAP's use).

### Gaps
- No quantitative source found for simulator accuracy at 0.1 mm clearance specifically; IndustReal's exact clearances were not in the summaries.
- Nothing found on Project Chrono or Bullet for assembly verification, nor on snap-fit, press-fit, flexible-part or cable simulation in an automated verifier context. Commercial tools (IPS Cable Simulation from FCC is known to me but unsourced here) were not confirmed.
- MuJoCo's own SDF plugin documentation was not retrieved.

## 3. Cheap geometric heuristics to run first, and libraries on OCCT or meshes

### Takeaway
No maintained open library was found that packages fastener/tool-access checking; the building blocks (OCCT boolean/distance queries, mesh collision via trimesh/FCL) exist and the checks must be composed in-house. cadclaw and APLAN are the only open projects found that ship sequenced-removal or assembly-graph logic on STEP/OCCT.

### Cited Findings
- A targeted search found no ready-made open-source tool that checks screwdriver access to fasteners; the suggested construction is OCCT collision tests against a swept cylinder/cone model of the driver along each fastener axis (search summary, the absence is itself the finding) — [PyPI: cadclaw](https://pypi.org/project/cadclaw/0.8.0/)
- cadclaw offers sequenced part removal, radial exploded views and animation frame export for STEP assemblies, in a pytest-style "CI for mechanical design" workflow (search summary) — [CI-for-CAD write-up](https://cadclaw.pages.dev/ci-for-cad/); [Zenodo record](https://zenodo.org/records/19647391)
- CadPy: Python library on OCCT with a validation module for clash detection and a fastener class (search summary; unverified) — [PyPI: cadpy](https://pypi.org/project/cadpy/)
- PythonOCC-based directional collision detection from STEP for disassembly directions was demonstrated in 2015 (search summary) — [DOAJ record](https://doaj.org/article/30c2740dbfb84a3fbcab7eff8dae6b12)
- Research on fastener sequencing notes that disassembly-based work treats fasteners as one class and is inadequate for assembly-oriented fastener sequencing (search summary; originating paper not identified) — [KU Leuven APLAN paper](https://lirias.kuleuven.be/retrieve/744239)
- Assemble-Them-All's geometric baselines (straight-line and RRT-family path search on meshes) are available in the same repo and can be run without the physics planner (fetched directly) — [GitHub: Assemble-Them-All](https://github.com/yunshengtian/Assemble-Them-All)
- GLARE's residual failures (interlocking parts, need for rotation, need to move subassemblies together) show where translation-only single-part removal checks give false negatives (search summary) — [arXiv 2609.17263](https://arxiv.org/pdf/2609.17263)

### Inferences
Proposed tiered verifier (my synthesis; ordering by cost):
1. Static interference and clearance: pairwise boolean-common volume and minimum distance on B-rep (OCCT). Prerequisite for everything else.
2. Directional blocking matrix: for each part and each candidate direction (±X, ±Y, ±Z, plus joint/fastener/hole axes extracted from cylindrical faces), translate the part in steps to beyond the assembly bounding box and test collision against all others (mesh FCL via trimesh/python-fcl, or extrude the part's silhouette into a swept solid and intersect). Yields a part x direction x blocker table, i.e. a directional blocking graph.
3. Greedy disassembly peel: repeatedly remove any part with a free direction; the reversed order is an assembly sequence. Parts never freed are "trapped"; report their blockers. Add subassembly moves (remove a connected group together) before declaring failure.
4. Fastener corridor: for each screw, sweep head-diameter cylinder plus driver envelope (bit shank cylinder plus handle; socket plus ratchet swing sector; hex key L-sweep) outward along the axis for screw length plus tool length; intersect with all parts present at that step of the sequence.
5. Hand/finger access: coarse proxy volumes (for example a 25 mm sphere or 80-100 mm cylinder for a hand) at grasp locations; ray-cast visibility from outside the bounding hull as a cheap accessibility score.
6. Stability during build: with a chosen base part and gravity vector, check each partial assembly's parts are supported (contact normals opposing gravity, COM over support polygon), escalating to ASAP's simulator only on ambiguous cases.
7. Escalation: RRT/BFS path planning (Assemble-Them-All) only for parts that fail straight-line removal.
- Step 2-3 is equivalent to the classic principal-axis directional blocking graph; it is sound for "found a sequence" but incomplete (misses rotational, screw-motion and multi-step paths), so failures should be labelled "no straight-line removal" rather than "impossible".
- Threads and interference fits modelled at nominal size will collide along their own insertion axis; recognised fasteners/fits need to be exempted or shrunk by a small tolerance before sweeping.

### Gaps
- No open implementation found for tool-envelope libraries (standard driver/wrench/socket geometries with swing angles), hand-access volumes, or visibility-based accessibility on CAD. These appear to exist only inside commercial DMU tools.
- No source found addressing whether 3D-print supports or CNC setups block assembly; that sits in manufacturability checks rather than assembly literature.
- cadclaw's algorithm (directions tried, collision method, handling of fasteners) is undocumented in what I could see; needs a hands-on trial.

## 4. DFA scoring: methods, open implementations, LLM evaluators, commercial tools

### Takeaway
Boothroyd-Dewhurst DFA remains the reference metric and is simple enough to compute in-house once parts are classified, but no open implementation or peer-reviewed LLM-based DFA evaluator was found. Commercial assembly simulation (Siemens, Dassault, FCC IPS) automates collision-free assembly path finding; it is GUI/enterprise software, not a headless Python verifier.

### Cited Findings
- Boothroyd-Dewhurst analysis has two parts: determining the theoretical minimum number of parts, and estimating assembly times/costs. Minimum-part questions cover whether the part must move relative to others, must be a different/isolated material, or must be separate to permit assembly/disassembly; a part answering "no" to all is an elimination candidate. Design efficiency is EM = 3 x NM / TM (NM = theoretical minimum parts, TM = total estimated assembly time) (search summary of lecture material and a Clemson paper) — [Clemson DETC2011-47530](https://cecas.clemson.edu/cedar/wp-content/uploads/2017/03/DETC2011-47530.pdf); [B&D lecture notes](https://www.scribd.com/doc/4354891/Lecture-5-DFA-Boothro)
- Boothroyd Dewhurst's DFMA software computes handling and fastening penalties per part and the DFA Index; the vendor site advertises a "DFMA 2025B" release with 200,000+ costing data points across 22 countries (search summary; vendor claims) — [dfma.com](https://www.dfma.com/software/dfma-product-simplification.asp)
- The Clemson paper compares B&D with the Mathieson-Summers connective-complexity metric, an assembly-time estimate computed from the part connectivity graph rather than manual per-part classification (search summary) — [Clemson DETC2011-47530](https://cecas.clemson.edu/cedar/wp-content/uploads/2017/03/DETC2011-47530.pdf)
- Leo AI markets a tool that reads a CAD assembly and applies the Boothroyd-Dewhurst questions to every part to flag consolidation candidates, removable fasteners and hard-to-handle features (search summary; marketing blog, unverified) — [Leo AI blog](https://www.getleo.ai/blog/ai-design-for-assembly-dfa)
- No peer-reviewed paper applying LLMs to Boothroyd-Dewhurst scoring surfaced in a targeted search (search summary; absence finding) — [MIT "LLMs for CDaM" (2023) as nearest prior work](https://cfg.mit.edu/publications/llms-for-cdam)
- Siemens Process Simulate X Automatic Path Planner: add-on that automatically creates collision-free paths for product assembly/disassembly; built on the KineoWorks engine, which computes valid 3D assembly/disassembly paths for digital mock-up "in one click" (search summary; vendor claims) — [Siemens Process Simulate X APP](https://plm.sw.siemens.com/en-US/tecnomatix/products/process-simulate-x-automatic-path-planner); [KineoWorks](https://plm.sw.siemens.com/en-US/plm-components/kineo/kineoworks)
- Dassault DELMIA: "Assembly Path Optimization" computes collision-free assembly motions with user-adjustable bounding boxes and rotation limits (search summary) — [DELMIA community post](https://3dswym.3dexperience.3ds.com/post/delmia-process-engineering/assembly-path-optimization_rHv2TfaXRfavCbgQo9msJw)
- Fraunhofer-Chalmers IPS Path Planner: finds a path "for any object that can be freely assembled"; cites a tunnel-bracket case solved in under 2 minutes that could take an engineer days (search summary; vendor claim) — [FCC IPS Path Planner](https://fcc.chalmers.se/software/ips/ips-path-planner/)

### Inferences
- A lightweight DFA report is feasible for the agent: part count, fastener count and distinct fastener types, number of distinct insertion directions and reorientations in the found sequence (from section 3), theoretical-minimum-part candidates (LLM answers the three B&D questions per part with geometry/material context), and a connectivity-graph complexity score. This yields a comparable number across design revisions without licensing DFMA tables.
- B&D time tables (handling/insertion codes) are proprietary-in-practice lookup data; an LLM classifying parts into symmetry/size/handling categories is plausible but unvalidated.
- Commercial path planners confirm the industrial norm: feasibility is established by sampling-based collision-free path search on the DMU, which is what Assemble-Them-All offers openly.

### Gaps
- Nothing found on aPriori's assembly/DFA automation, the Lucas method, CENIT or Visual Components within budget.
- No open-source DFA calculator found.
- No independent evaluation of Leo AI or any LLM DFA reviewer.

## 5. LLM/VLM + assembly planning research 2024-2026 and work-instruction tools

### Takeaway
LLM/VLM assembly planning is still weak on geometry: published accuracies sit around 60% for plan/graph generation and drop sharply on harder benchmarks, with collision and fine geometry named as the failure points. The systems that work pair a language model with a geometric or physics checker; commercial work-instruction tools (Dirac) derive sequences from CAD and claim about 80% automation.

### Cited Findings
- Manual2Skill (arXiv 2502.10090, 2025): VLM reads IKEA manual images into a hierarchical assembly graph, evaluated on four real IKEA items; a later paper characterises it as achieving only 62% success on graph generation (F1 = 0.684), with failures from inaccurate diagram interpretation (search summary; the 62% is a secondary characterisation) — [arXiv 2502.10090](https://arxiv.org/html/2502.10090v3); [arXiv 2604.00913](https://arxiv.org/html/2604.00913v1)
- CADMate (ACL 2026): frames CAD assembly as predicting a 6-DoF transform per part from a reference image, using geometric chain-of-thought and spatial/physical rewards; authors note existing MLLMs struggle with fine-grained geometry and collision avoidance (search summary) — [ACL Anthology 2026.acl-long.834](https://aclanthology.org/2026.acl-long.834/)
- ASSEMCAD (2026 preprint): natural-language-to-CAD-assembly generation, reported to improve assembly preservation and physical validity over code-only CAD generation (search summary; ID flagged as unverified by the search tool) — [arXiv 2607.05123](https://arxiv.org/pdf/2607.05123)
- IDfRA, "Self-Verification for Iterative Design in Robotic Assembly" (Sept 2025): iterative design with self-verification, 86.9% construction success (search summary) — [aitopics record](https://aitopics.org/doc/arxivorg:4F463EF1)
- VLM text-driven multi-component robotic assembly with a conversational feedback loop for component assignment (NeurIPS 2025 Creative AI track) (search summary) — [arXiv 2511.02162](https://arxiv.org/pdf/2511.02162v4)
- LLM-enabled human-robot collaborative assembly sequencing from operator natural-language instructions (ASME, 2026) (search summary) — [arXiv 2603.11461](https://arxiv.org/pdf/2603.11461)
- MERL AssemblyBench: learned assembly-motion predictors lose nearly 30% on a harder dataset; parts get stuck mid-path (search summary) — [MERL TR2026-076](https://www.merl.com/publications/docs/TR2026-076.pdf)
- Dirac BuildOS: generates interactive step-by-step 3D work instructions from CAD; company says it automates about 80% with engineers editing the rest; Anduril deal (January 2026) cites authoring time cut from 12 hours to 90 minutes (90%); instructions update when CAD changes (search summary; vendor and press-release figures) — [Anduril/Dirac announcement](https://www.pulse.bot/ai/news/anduril-selects-dirac-to-power-ai-driven-work-instructions-across-its-factories-13c62722-9949-413c-a848-92b8f405c3ed/); [Dirac on Azure](https://www.webull.com/news/15429641241469952)
- Assembly Magazine covers AI for streamlining assembly planning (not examined) (search summary) — [Assembly Magazine](https://www.assemblymag.com/articles/97515-artificial-intelligence-helps-streamline-assembly)

### Inferences
- The agent should not be asked to assert assemblability from reasoning or renders alone; published evidence says LLM geometric judgement is the weak link. Its role is to propose (base part, sequence, subassembly grouping, fastener semantics) and let the geometric verifier accept or refute.
- LLM proposals can cut search: a proposed order checked step-by-step with straight-line sweeps is far cheaper than blind tree search, and failures localise to a specific step.

### Gaps
- No dedicated paper found on LLMs producing assembly sequences directly from STEP/B-rep with measured geometric-feasibility rates.
- Canvas GFX/Envision and Cadasio returned nothing; their automation level is unknown here.
- Dirac's sequencing method is not public in what was found.

## 6. Output design: reporting to the agent and to a human

### Takeaway
No source prescribes a report schema; existing tools emit a plan log (ASAP: `stats.json`, search tree, per-step paths, videos) or exploded views/animation frames (cadclaw). A structured, blocker-centric report is an inference from what those tools expose and where planners fail.

### Cited Findings
- ASAP logs `setup.json`, `stats.json`, `tree.pkl` per run and can replay a plan saving meshes, poses, paths and videos; batch success checking is a separate script (fetched directly) — [GitHub: ASAP](https://github.com/yunshengtian/ASAP)
- cadclaw's loop is "edit assembly spec, run check round, inspect report and review renders, repeat", with radial exploded views and animation frame export (search summary) — [CI-for-CAD write-up](https://cadclaw.pages.dev/ci-for-cad/)
- Dirac's human-facing output is interactive step-by-step 3D instructions tied to the CAD model (search summary) — [Anduril/Dirac announcement](https://www.pulse.bot/ai/news/anduril-selects-dirac-to-power-ai-driven-work-instructions-across-its-factories-13c62722-9949-413c-a848-92b8f405c3ed/)
- Planner failure classes worth distinguishing in a report: needs rotation, needs subassembly motion, interlocking, stuck at intermediate position (search summary) — [arXiv 2609.17263](https://arxiv.org/pdf/2609.17263); [MERL TR2026-076](https://www.merl.com/publications/docs/TR2026-076.pdf)

### Inferences
Suggested agent-facing JSON (my design):
- `status`: `sequence_found` | `no_sequence_within_budget` | `static_interference` (never a bare "fail").
- `method` and `completeness`: e.g. `straight_line_6dir` (incomplete) vs `rrt_se3_120s`, so the agent knows how much to trust a negative.
- `sequence`: ordered steps with part id, insertion direction vector, travel distance, required reorientation, parts that must be held.
- `trapped_parts`: for each, per direction the list of blocking part ids, first-contact distance, and a contact point/box, so the fix is localisable ("cover blocked in +Z by bracket after 3.2 mm").
- `fasteners`: per screw the driver type assumed, corridor clear length versus required length, obstructing parts, and the sequence step at which access is lost.
- `stability`: steps where the partial assembly is unsupported, with the unsupported part ids.
- `dfa`: part count, fastener count/types, number of insertion directions and reorientations, elimination candidates.
- Keep it terse and ranked by severity; include part names from the CAD script so the agent can map findings to code.
Human-facing: exploded view along the found removal directions (distance proportional to sequence depth), a step-through animation or frame strip of the reversed disassembly, and highlighted blocker pairs in a render for each failure.

### Gaps
- No empirical study found on which feedback format most improves LLM CAD revision for assembly defects.
- No open tool found that generates exploded views automatically from a computed disassembly sequence other than cadclaw (unverified).
