# Simulation tools for an LLM-driven mechanical-engineering agent (state as of Nov 2026)

Method note for the report writer: ~22 web searches were run on 2026-11-13. Cited findings come from search-result summaries of the linked pages; the primary pages were NOT individually opened and read in full, so exact figures (success rates, dates, prices) should be treated as "reported by source, lightly verified". Anything under "Inferences" marked [BK] is researcher background knowledge (training data up to mid-2026) that was not re-verified in this session and has no URL; it is included because the search budget did not cover every tool named in the brief. Tools with no finding at all are listed under Gaps.

## 1. Meshing (Gmsh, Netgen, TetGen, fTetWild, snappyHexMesh, cfMesh, MeshLib, Cubit)

### Takeaway
Gmsh (4.15.x, pip-installable, OpenCASCADE kernel built in, STEP import via `gmsh.model.occ.importShapes`) is the default headless mesher for clean B-rep; fTetWild is the robustness fallback for dirty/triangle-soup input at the cost of speed and loss of exact CAD-face association. No sourced head-to-head on real CAD robustness for Gmsh was found.

### Cited Findings
- Gmsh 4.15.0 is dated 26 Oct 2025; the official reference manual is labelled 4.15.2, implying later patch releases. — [Gmsh manual](https://gmsh.info/doc/texinfo/gmsh.html); [GitLab tags](https://gitlab.onelab.info/gmsh/gmsh/-/tags)
- Gmsh is installable headless with `pip install --upgrade gmsh` (PyPI wheel 4.15.0). — [PyPI gmsh 4.15.0](https://pypi.org/project/gmsh/4.15.0/)
- Gmsh has two default CAD kernels: built-in and OpenCASCADE; STEP import requires OCC support compiled in. — [Gmsh manual](https://gmsh.info/doc/texinfo/gmsh.html); [PyVista CAD-to-FEA example](https://cad.pyvista.org/examples/05_workflows/cad_to_fea_tet_mesh.html)
- PyVista's documented CAD-to-FEA workflow imports a STEP/OCC shape into Gmsh via `gmsh.model.occ.importShapes` and tet-meshes the volume — a minimal reference for the STEP-to-mesh step. — [PyVista CAD-to-FEA example](https://cad.pyvista.org/examples/05_workflows/cad_to_fea_tet_mesh.html)
- fTetWild's authors report the algorithm always succeeds in inserting all input triangles on Thingi10k; robustness to imperfect input is the design goal. — [fTetWild paper, arXiv 1908.03581](https://arxiv.org/abs/1908.03581v2)
- TetGen fails to produce a constrained Delaunay tetrahedralization on ~8.5% of valid Thingi10k models (another summary: 91.4% success). — [2023 CDT paper, NYU GCL](https://cims.nyu.edu/gcl/papers/2023-CDT.pdf)
- Average time per model in one comparison: TetGen 2 s, CGAL 19 s, fTetWild 38 s, TetWild 137 s. — [Convex polyhedral meshing paper, arXiv 2109.14434](https://arxiv.org/pdf/2109.14434)
- pyccx advertises "cleaning and merging of CAD assemblies" through Gmsh's internal functionality as part of its Gmsh+CalculiX pipeline. — [pyccx docs](https://pyccx.readthedocs.io)
- A long-standing practitioner write-up of STEP -> Gmsh -> CalculiX notes a Python script is needed to filter the Gmsh-exported mesh so it suits CalculiX (e.g. removing lower-dimensional elements). — [Roland Smith's blog](https://rsmith.home.xs4all.nl/engineering/fea-based-on-step-geometry-using-gmsh-and-calculix.html)
- OpenFOAM v2606 release notes include a "pre-processing" section (snappyHexMesh etc. ships with OpenFOAM). — [OpenFOAM v2606 pre-processing](https://www.openfoam.com/node/681)

### Inferences
- Thingi10k results are for STL triangle meshes, not B-rep; they show the relative ordering (fTetWild > CGAL/TetGen on robustness, TetGen >> fTetWild on speed) but do not directly predict Gmsh behaviour on STEP.
- Practical agent strategy: (1) Gmsh OCC import + `occ.healShapes`/fragment, 2nd-order tets (C3D10); (2) on meshing failure, tessellate to STL and fall back to fTetWild or Gmsh's surface-remesh path, accepting loss of CAD face IDs (BC assignment must then be done geometrically, e.g. by bounding box/normal). [BK]
- [BK] Gmsh licence is GPL-2+ (with linking exception options sold commercially); calling it as a subprocess/Python module in a server pipeline is fine, embedding in a closed-source distributed product needs care. Netgen/NGSolve is LGPL with a pip wheel and its own OCC STEP import; TetGen is AGPL (commercial licence available); fTetWild is MPL-2; MeshLib is dual-licensed (free non-commercial, paid commercial) and is a surface-mesh/healing library rather than an FE volume mesher; Coreform Cubit is commercial (free "Learn" tier with element caps) and is the strongest option for automated-ish hex meshing with a Python API.
- [BK] Hex vs tet: fully automatic all-hex meshing of arbitrary CAD is still unsolved; for structural work quadratic tets (C3D10) are the accepted automatic default, linear tets (C3D4) are too stiff and must be avoided. For CFD, snappyHexMesh (hex-dominant, STL-driven, tolerant of dirty geometry but poor feature-edge/layer quality) and cfMesh (cartesianMesh, simpler dictionary, GPL, in ESI distribution) are the automatic options.
- [BK] Shell/beam idealisation (mid-surfacing) is not reliably automatable with open tools; an agent should default to solids with >=2-3 quadratic elements through thickness and flag thin-walled parts as a known accuracy/cost risk.

### Gaps
- No sourced robustness/failure-rate numbers for Gmsh or Netgen on real-world STEP files (e.g. ABC dataset). No 2026 version/status information found for Netgen/NGSolve, TetGen, cfMesh, MeshLib, or Coreform Cubit (pricing, API) — not searched within budget.
- No sourced recipe for automated mesh-convergence loops in Gmsh (size fields, `Mesh.MeshSizeFactor` sweeps) — standard practice but uncited here.

## 2. Structural FEA solvers and the pragmatic default

### Takeaway
CalculiX (ccx 2.23, Oct 2025, still current Nov 2026) driven by a Gmsh-generated mesh and a generated `.inp` deck is the pragmatic default for automated linear static/modal/buckling/thermal analysis of a part from STEP: Abaqus-like keyword input that LLMs know well, single binary, and several existing Python wrappers and LLM pipelines (pygccx, pyccx, FeaGPT, FreeCAD FEM). FEniCSx/DOLFINx (0.10 -> 0.11) is the choice when custom PDEs/adjoints are needed; OpenRadioss's status needs checking (reported shut down Oct 2026).

### Cited Findings
- CalculiX stable release is 2.23, released 19 Oct 2025; calculix.de / dhondt.de list 2.23 as current, and a Nov 2026 forum thread still discusses 2.23 issues (no 2.24 found). — [Wikipedia: Calculix](https://en.wikipedia.org/wiki/Calculix); [calculix.de](https://calculix.de); [CalculiX forum](https://calculix.discourse.group)
- CalculiX 2.23 does not allow rigid body constraints with 2D elements even in nonlinear analyses; next version expected to lift this; releases typically land Q3/Q4 (informal forum expectation). — [PrePoMax forum](https://prepomax.discourse.group/t/calculix-2-23-has-released/3626)
- pygccx: Python framework for building, solving and post-processing FE models using Gmsh and CalculiX; limited to 3D solid elements (no shells or beams). — [pygccx (fork mirror)](https://github.com/QiangF/pygccx)
- pyccx: "Simulation FEA environment for Python built upon Calculix and GMSH", uses the Gmsh SDK for meshing. — [PyCCX on PyPI](https://pypi.org/project/PyCCX); [pyccx docs](https://pyccx.readthedocs.io)
- pycalculix targets 2D/axisymmetric models only (not suitable for 3D STEP parts). — [pycalculix on PyPI](https://pypi.org/project/pycalculix/1.1.2)
- FreeCAD 1.1 was released 25 Mar 2026; FEM workbench uses CalculiX as default solver for structural and thermo-mechanical analysis, communicating by writing/reading text files; 1.1 added box/elliptical beam sections and an electromagnetic analysis type for the refactored CalculiX solver object. — [FreeCAD blog: FEM in 1.1](https://blog.freecad.org/2025/09/09/what-is-new-in-fem-for-freecad-1-1/); [FreeCAD wiki FEM CalculiX](https://wiki.freecad.org/FEM_CalculiX); [AlternativeTo news](https://alternativeto.net/news/2026/3/freecad-1-1-adds-three-point-lighting-part-design-previews-and-major-fem-upgrades)
- Headless FreeCAD: `FreeCADCmd` runs a script and exits; script-file execution is the recommended approach; not all workbench modules are automatically available in headless mode. — [FreeCAD wiki: Headless FreeCAD](https://wiki.freecad.org/Headless_FreeCAD)
- Third-party FreeCAD MCP servers exist (e.g. on Glama; "AnkusDrive" claims a FreeCAD 1.1 MCP driver that runs CalculiX solves) — maturity unverified. — [Glama FreeCAD MCP](https://glama.ai/mcp/servers/ddu9vehrbp); [ankusdrive on PyPI](https://pypi.org/project/ankusdrive/)
- DOLFINx 0.10.0 (311 merged PRs from 25 contributors since 0.9.0; adds blocked-problem support in `dolfinx.fem.petsc.LinearProblem`); docs now list v0.11.0 (177 PRs from 27 contributors since 0.10) and a 0.12 draft. API still changes every release. — [DOLFINx 0.10 announcement](https://fenicsproject.discourse.group/t/v0-10-0-of-dolfinx/18297); [DOLFINx release notes](https://docs.fenicsproject.org/dolfinx/main/python/release_notes.html)
- code_aster: 37 years of development, >4,600 verification test cases, ~1M lines of code (project self-description). — [code_aster via OSArch wiki](https://wiki.osarch.org/index.php/Code_Aster)
- OpenRadioss: an It's FOSS article dated 5 Oct 2026 reports the owning company shut down the OpenRadioss project at the start of October 2026, removing the repository; a community fork "OpenCourant" under AGPLv3 has been set up. SINGLE SOURCE — must be confirmed before relying on it. — [It's FOSS](https://itsfoss.com/news/siemens-openradioss-fork.md)
- MOOSE: monthly INL newsletters through mid-2026; July 2026 covers Kokkos acceleration for linear FV solvers and C++20 builds (active development, rolling releases). — [MOOSE Newsletter July 2026](https://mooseframework.inl.gov/newsletter/2026/2026_07.html)
- SU2 8.5.0 (27 Apr 2026) includes "fully functional thermo-elasticity coupling" (SU2 also has a structural FEA module). — [SU2 v8.5.0 release](https://newreleases.io/project/github/su2code/SU2/release/v8.5.0)

### Inferences
- Why CalculiX as default: (a) input is a single declarative text deck in Abaqus dialect — heavily represented in LLM training data and easy to template/validate; (b) one static binary, trivially containerised (apt `calculix-ccx` or conda-forge) [BK]; (c) covers linear static, modal (`*FREQUENCY`), linear buckling (`*BUCKLE`), nonlinear geometry/material, contact, steady/transient thermal and coupled thermo-mechanical [BK]; (d) results in `.frd`/`.dat` are parseable (`.dat` gives reaction-force totals via `*NODE PRINT, TOTALS=YES`) [BK]; (e) at least one published LLM pipeline (FeaGPT) and FreeCAD/PrePoMax ecosystems already target it. Weaknesses: GPL-2 [BK]; single maintainer cadence (one release/year); contact convergence is fiddly; shell/beam elements are internally expanded to solids; no built-in fatigue (needs external post-processing) [BK].
- Recommended reference architecture: CadQuery/OCP or build123d for STEP handling -> Gmsh Python API (physical groups from CAD faces) -> own thin `.inp` writer (or pygccx) -> `ccx` subprocess -> parse `.frd` with meshio/ccx2paraview/pyvista -> checks. Writing your own thin deck generator is low-risk because pygccx/pyccx are small, lightly maintained projects (maintenance status not verified).
- [BK] Comparative positioning (not verified this session):
  - Code_Aster (GPL-3, EDF): most capable open structural solver (nonlinear, contact, fatigue, fracture, shells/beams, >4,600 validation cases) with Python command files (`.comm`) and MED mesh format; heavier install (official Singularity/Docker images of salome_meca), steeper syntax, docs partly French/machine-translated — best "second backend" when CalculiX limits are hit (fatigue, shells, advanced contact).
  - FEniCSx/DOLFINx (LGPL-3; official `dolfinx/dolfinx` Docker images; conda): weak-form programming in Python (UFL); ideal for custom physics, topology optimisation and adjoints; no built-in contact/elements library like a general-purpose code; API churn between 0.x releases breaks LLM-written code.
  - Elmer (GPL/LGPL, CSC): multiphysics (thermal, EM, structural, flow), `.sif` text input, ElmerGrid converts Gmsh meshes; good for coupled thermal/EM, less used for pure structures.
  - MOOSE (LGPL-2.1, INL): HIT `.i` input files, strong multiphysics/nonlinear, conda/Docker/Apptainer installs, heavy build; LLM agents exist (MooseAgent).
  - Kratos (BSD-4), MFEM (BSD-3), deal.II (LGPL -> Apache-2 transition), SfePy (BSD), scikit-fem (BSD-3, pure Python, pip): libraries/frameworks; scikit-fem and SfePy are easiest to pip-install for small linear problems; deal.II/MFEM are C++-first. FEBio (MIT) is biomechanics-focused, strong nonlinear/contact, XML `.feb` input. OpenRadioss was explicit-dynamics/crash (AGPL) — see status caveat above.
  - PrePoMax: Windows GUI pre/post for CalculiX (.NET), not a headless Linux option; useful for human review of agent-generated `.inp`. pyNastran (BSD-3): reader/writer for Nastran BDF/OP2, not a solver — relevant only if targeting MSC/NX/Optistruct or the open MYSTRAN solver.
  - FreeCAD FEM: complete STEP -> Gmsh -> CalculiX pipeline scriptable via `FreeCADCmd`, but adds a large dependency and document-object indirection; best used as reference/fallback or via MCP rather than as the core.

### Gaps
- Versions/dates as of late 2026 not found for: code_aster (17.x?), Elmer, Kratos, MFEM, deal.II, SfePy, scikit-fem, FEBio, PrePoMax, pyNastran; licences and Docker availability in the table above are background knowledge, not sourced this session.
- OpenRadioss shutdown/OpenCourant fork rests on one news article; not cross-checked against GitHub.
- No sourced benchmark comparing solver accuracy/performance (CalculiX vs Code_Aster vs commercial) was retrieved.

## 3. CFD and multibody/dynamics

### Takeaway
OpenFOAM remains the open CFD default (ESI v2606, June 2026 — adds first GPU offloading and `pybFoam` Python bindings; Foundation v14, July 2026) but automated case setup is the hard part: the best LLM agents reach ~84-88% "runs successfully" on tutorial-like cases and far less on physical correctness. For mechanisms, MuJoCo (3.14, Sep 2026) and Project Chrono (10.0.0, Mar 2026) are the actively released options.

### Cited Findings
- OpenFOAM v2606 (ESI/OpenCFD) released 26 Jun 2026 (Wikipedia says 19 Jun): new GEKO RANS model; first release with GPU offloading via C++17/20 std::execution policies (community contribution); multi-area finite-area; new `pybFoam` Python bindings; initial VTK-HDF export (`foamToVTKHDF`). — [OpenFOAM v2606 news](https://www.openfoam.com/news/main-news/openfoam-v2606); [OpenFOAM download](https://www.openfoam.com/download)
- OpenFOAM Foundation v13 released 8 Jul 2025; v14 released 14 Jul 2026 (field functions for case initialisation, units as a standard feature, overhaul of coded file input, new XiFluid solver). The two lines are separate projects with diverging dictionaries/solver names. — [OpenFOAM 13 release](https://openfoam.org/release/13/); [openfoam.org v14](https://openfoam.org/14); [Wikipedia: OpenFOAM](https://en.wikipedia.org/wiki/OpenFOAM)
- SU2 stable is 8.5.0 (27 Apr 2026): multigrid improvements, new grey-area mitigation for DES, thermo-elasticity coupling; v8.0.0 "Harrier" completely reworked the Python wrapper. — [SU2 v8.5.0](https://newreleases.io/project/github/su2code/SU2/release/v8.5.0); [SU2 v8.0.0](https://newreleases.io/project/github/su2code/SU2/release/v8.0.0); [Wikipedia: SU2 code](https://en.wikipedia.org/wiki/SU2_code)
- FluidX3D (GPU lattice-Boltzmann, OpenCL) released v3.7 in May 2026; listed as free for non-commercial use with a custom ("other") licence — commercial use needs a separate arrangement; verify LICENSE.md upstream. — [Phoronix](https://phoronix.com/news/fluidx3d-3.7-released); [ecosyste.ms listing](https://awesome.ecosyste.ms/projects/github.com%2FProjectPhysX%2FFluidX3D)
- code_saturne v9.2 has been released (EDF's open CFD code; surfaced incidentally). — [code_saturne news](https://code-saturne.org/en/news/release-note-version-920)
- CFDLLMBench: best model achieves only 14% on CFDCodeBench and 34% on FoamBench, where success = fraction of cases producing physically accurate results; FoamBench has 110 basic + 16 advanced OpenFOAM tasks; CFDQuery has 90 MCQs. — [CFDLLMBench, arXiv 2509.20374](https://arxiv.org/abs/2509.20374v2)
- Project Chrono stable release 10.0.0 dated 27 Mar 2026; PyChrono is its SWIG-based Python binding. — [Wikipedia: Project Chrono](https://en.wikipedia.org/wiki/Project_Chrono)
- MuJoCo 3.14.0 released 22 Sep 2026 (3.11.0 on 27 Jul 2026 — roughly monthly cadence); pip-installable. — [Wikipedia: MuJoCo](https://en.wikipedia.org/wiki/MuJoCo); [MuJoCo changelog](https://mujoco.readthedocs.io/en/3.11.0/changelog.html)

### Inferences
- The ESI/Foundation split is itself an automation hazard: LLMs mix dictionary syntax and solver names (e.g. Foundation's modular `foamRun -solver incompressibleFluid` vs ESI's `simpleFoam`) [BK]. Pin one line (most LLM-agent papers and Foam-Agent use Foundation v10-style or ESI cases; check which) and feed the agent that version's tutorials via retrieval.
- Automated CFD case setup difficulty ranking [BK]: external/internal incompressible steady RANS on a single STL with snappyHexMesh is templatable; conjugate heat transfer, multiphase, rotating machinery and anything needing boundary-layer-resolved meshes are much harder to make robust. A Lattice-Boltzmann code (FluidX3D, OpenLB [GPL-2], Palabos [AGPL-3]) removes the body-fitted-meshing step (voxelise STL), which makes fully automatic transient external-flow setup much easier at the cost of wall-modelling accuracy and (for FluidX3D) licence restrictions.
- [BK] Multibody choices: Project Chrono (BSD-3; rigid+flexible bodies, FEA beams/shells, vehicles, granular, SWIG PyChrono via conda) is the closest to engineering MBD; MuJoCo (Apache-2; fast generalized-coordinate contact dynamics, MJCF/URDF, soft-contact model tuned for robotics/control rather than certified mechanism loads); Drake (BSD-3; rigorous multibody + hydroelastic contact + optimisation, pip `drake`); PyBullet (zlib; effectively in maintenance mode); MBDyn (GPL; aerospace-grade DAE multibody with text input, small community). For mechanism kinematics/joint loads from CAD assemblies, Chrono or Drake are the stronger fits; MuJoCo if the downstream use is control/RL.

### Gaps
- No 2026 data found for Nek5000/NekRS, Basilisk, Palabos, OpenLB, Drake (latest version), PyBullet, MBDyn — not searched within budget.
- No sourced maturity assessment of `pybFoam` or v2606 GPU offloading (both first-release features).

## 4. Commercial / API-accessible options and pricing realities

### Takeaway
Only Luminary Cloud publishes usable API pricing ($5/credit tier includes API/SDK access); SimScale's API is effectively an Enterprise, quote-only feature; Ansys PyAnsys libraries are free MIT clients but require a licensed Ansys solver instance behind them. For a small team, commercial APIs mean sales conversations and per-seat/per-credit costs rather than self-serve.

### Cited Findings
- Luminary Cloud: pricing page lists a $5-per-credit tier (Starter/Professional, on-demand, GCP US) that includes API/SDK access, and $8.50 per credit for the ITAR/dedicated-support tier; prepaid credits are discounted per order form; some features are "Early Access" with preliminary pricing. — [Luminary pricing](https://www.luminarycloud.com/pricing/); [Luminary consumption table](https://legal.luminarycloud.com/consumption.html)
- SimScale: paid tiers are quote-based; official pricing page ties "dedicated API support", Engineering AI/Physics AI and custom integrations to the Enterprise plan; a pricing-change tracker reports API access was removed from lower tiers' listing in early 2026; free Community plan's included core hours reportedly dropped from 3000 to 2000 in early Oct 2026. Whether API keys work on the free plan is unconfirmed. — [SimScale pricing](https://www.simscale.com/product/pricing/); [PricingSaaS SimScale tracker](https://pricingsaas.com/companies/simscale); [Capterra](https://capterra.com/p/145960/SimScale/pricing)
- PyAnsys/PyMAPDL in containers: you containerise MAPDL (the licensed solver), not PyMAPDL; PyMAPDL is a gRPC client. — [PyMAPDL discussion mirror](https://git.tdem.in/ansys/pymapdl/discussions/3027)
- Ansys licensing terms require a licence for each user accessing the program "directly or indirectly"; the Ansys Startup Program is offered as bundles and its licences can be checked out on Rescale. — [Ansys product codes PDF](https://ansys.com/content/dam/legal/ansys-product-codes-january-2025.pdf); [Rescale: Ansys Startup Program licensing](https://rescale.com/documentation/main/ansys-resources/licensing/ansys-startup-program/)
- Ansys 2026 R1 was launched by Synopsys on 11 Mar 2026 (Ansys is now part of Synopsys): first agentic capabilities (Discovery Validation Agent, early customer evaluation, flags setup issues), SimAI split into SimAI Premium (cloud) and SimAI Pro (desktop training/prediction), Engineering Copilot extended to more products, GeomAI concept exploration. — [Synopsys press release](https://news.synopsys.com/2026-03-11-Synopsys-Launches-Ansys-2026-R1-to-Re-Engineer-Engineering-with-Joint-Solutions-and-AI-Powered-Products)

### Inferences
- "Indirect access" licensing language is a real risk for agent products: an LLM agent serving multiple end users through one Ansys/Abaqus/COMSOL seat likely violates standard terms; an OEM/embedded agreement would be needed. Open-source solvers avoid this entirely.
- [BK] Other commercial routes (unverified this session): Abaqus has mature Python scripting (`abaqus cae noGUI=script.py`) but token-based licensing in the tens of k$/yr; COMSOL is automatable via Java API/`mph` Python package and LiveLink, per-seat licence, used by FEABench; Onshape exposes simulation only through its UI/limited REST and Fusion's simulation has limited API coverage; Altair (now Siemens) units-based licensing; nTop has `ntopcl` command-line automation with field-driven design and built-in FEA; Flexcompute (Flow360 CFD, Python client, FlexCredit pay-per-use) and Luminary are GPU-native cloud CFD with Python SDKs; Rescale is an HPC orchestration layer (API + bring-your-own-licence), not a solver.
- Pragmatic pattern for a small team: open-source stack (Gmsh + CalculiX + OpenFOAM) as primary; one pay-per-use GPU CFD cloud (Luminary or Flexcompute) if high-fidelity external aero is core; defer Ansys/Abaqus until a customer requires solver pedigree.

### Gaps
- No sourced pricing found for: Ansys Startup Program (historically a few k$/yr bundle; unverified), Abaqus, COMSOL, Flexcompute FlexCredits, Rescale, nTop, Altair, Onshape Simulation, Fusion simulation — searches returned nothing or were not run.
- Could not confirm whether SimScale's Python SDK remains publicly maintained or usable outside Enterprise.

## 5. LLM agents for simulation (2024-2026): success rates and failure modes

### Takeaway
Published agents report high "executes without error" rates (84-100% on author-chosen tasks) but independent benchmarks show low physical-correctness rates (FEABench: 0 problems fully solved; CFDLLMBench: best 34% on FoamBench, 14% on CFDCodeBench). Design consensus is moving toward constraining the LLM (structured JSON specs, templated decks, retrieval of tutorials, reviewer/error-fix loops) rather than free-form solver-code generation.

### Cited Findings
- Foam-Agent v1: 83.6% success with Claude 3.5 Sonnet on 110 OpenFOAM cases (11 physics scenarios) vs 55.5% MetaOpenFOAM and 37.3% OpenFOAM-GPT; success = case ran successfully through the framework. The original OpenFOAMGPT code was unavailable, so the 37.3% is for a re-implementation ("OpenFOAMGPT-Alt"). — [Foam-Agent, arXiv 2505.04997](https://arxiv.org/abs/2505.04997v1)
- Foam-Agent 2.0: 88.2% on the same 110 tasks; six specialised agents; Reviewer agent drives error recovery; composable (exposed as tools/MCP-style). — [Foam-Agent 2.0, arXiv 2509.18178](https://arxiv.org/html/2509.18178v2)
- CFDLLMBench (NREL): best model only 34% on FoamBench and 14% on CFDCodeBench when success requires physically accurate results. — [arXiv 2509.20374](https://arxiv.org/abs/2509.20374v2)
- FEABench (Google, COMSOL via API): best strategy generates executable API calls 88% of the time, but no model completely and correctly solved any problem; FEABench Gold = 15 verified problems, FEABench Large = 200 parsed from tutorials. — [FEABench, arXiv 2504.06260](https://arxiv.org/abs/2504.06260v1); [Google Research](https://research.google/pubs/feabench-evaluating-language-models-on-real-world-physics-reasoning-ability/)
- MooseAgent: abstract claims 93% average success; per-case (v1): steady heat conduction, linear elasticity, phase field 100%; transient heat 80%; plasticity and porous flow 60%; thermo-mechanical coupling 40%. Figures across versions do not obviously reconcile. — [MooseAgent, arXiv 2504.08621](https://arxiv.org/abs/2504.08621)
- MCP-SIM (engrXiv preprint; six agents with shared memory, generates FEniCS code): claims 100% success on 12 tasks (elasticity, heat transfer, multiphysics, fracture) — small author-selected set, unreviewed. — [MCP-SIM preprint](https://engrxiv.org/preprint/download/4723/8144/6739)
- FeaGPT (Oct 2025): LLM pipeline turning structured JSON specifications into CalculiX input and running the solver; demonstrated on 432 NACA4412 wing configurations and a turbocharger case. — [FeaGPT, arXiv 2510.21993](https://arxiv.org/pdf/2510.21993.pdf)
- ALL-FEM (early 2026): fine-tuned open-weight models on FEniCS scripts in a multi-agent workflow; best model produces correct code on 71.79% of benchmark problems. — [ALL-FEM, arXiv 2603.21011](https://arxiv.org/html/2603.21011v2)
- A 2026 FEniCS paper deliberately keeps the LLM from writing solver code (constrained natural-language interface to variational forms), citing MCP-SIM as the code-generation alternative. — [arXiv 2606.10928](https://arxiv.org/pdf/2606.10928)
- AbaqusAgent (mid-2026): multi-agent decomposition into interpreter, architect, input writer, runner, reviewer, visualiser. — [AbaqusAgent, arXiv 2606.00138](https://huggingface.co/papers/2606.00138)
- VFEAgent (May 2026): multimodal (drawings + text) end-to-end FEA validated on Abaqus with a solver-agnostic intermediate representation; future work to target OpenSees and CalculiX. — [VFEAgent, arXiv 2605.28978](https://arxiv.org/html/2605.28978v1)
- Vendor side: Ansys 2026 R1 Discovery Validation Agent "proactively identifies setup issues"; Engineering Copilot is an in-product assistant (help/training/in-context support), not an autonomous solver driver. — [Synopsys press release](https://news.synopsys.com/2026-03-11-Synopsys-Launches-Ansys-2026-R1-to-Re-Engineer-Engineering-with-Joint-Solutions-and-AI-Powered-Products); [Ansys Discovery updates](https://www.ansys.com/products/3d-design/ansys-discovery/product-updates)

### Inferences
- The gap between "ran" (84-100%) and "physically correct" (0-34%) is the central finding: executability is nearly solved by error-feedback loops; correctness is not, and self-reported agent success rates mostly measure the former on tutorial-derived tasks.
- Success degrades with coupling/nonlinearity (MooseAgent: 100% linear -> 40% thermo-mechanical), supporting a product scope that starts with linear static/modal/steady thermal.
- Failure modes implied by these designs (reviewer agents, validation agents, JSON intermediates, RAG over tutorials): wrong/hallucinated keywords and API calls, misplaced or missing boundary conditions, inconsistent units, and plausible-looking but unverified outputs. [BK: units are especially dangerous with CalculiX/Abaqus, which are unitless — mm-tonne-s-MPa vs SI mix-ups give errors of 1e3-1e9 without any solver warning; the pipeline should fix one unit system in code, not let the LLM choose.]
- Architecture recommendation: LLM emits a schema-validated analysis spec (materials from a database, loads/BCs bound to CAD face selectors, analysis type); deterministic code writes the deck, runs it, and performs checks; LLM only interprets structured check results. This matches FeaGPT and the constrained-FEniCS paper and avoids the FEABench failure pattern.

### Gaps
- Detailed failure-mode taxonomies (share of failures due to BCs vs units vs convergence vs hallucination) were not retrieved from the papers — only headline numbers from search summaries. MetaOpenFOAM and OpenFOAMGPT primary papers were not opened.
- No independent replication of any agent's self-reported success rate was found; no benchmark found for STEP-to-result structural agents specifically (CAD-in, stress-out).
- Ansys SimAI/Engineering Copilot API accessibility and pricing not found.

## 6. AI surrogates and physics foundation models

### Takeaway
Geometry-aware surrogates (DoMINO in NVIDIA PhysicsNeMo, Transolver-3, GINO) are production-relevant mainly for automotive/aero external aerodynamics where large CFD datasets (e.g. DrivAerML) exist; general PDE foundation models (Poseidon, Walrus) remain research artefacts on mostly Cartesian domains. For one-off part-level FEA that solves in seconds-minutes, a surrogate is not worth it.

### Cited Findings
- PhysicsNeMo (NVIDIA, formerly Modulus) docs at versions 25.08-26.05 ship a DoMINO recipe trained on DrivAerML, domain-parallel training, and a fine-tuning recipe for the DoMINO-Automotive-Aero NIM (predictor-corrector). — [PhysicsNeMo DoMINO docs 26.05](https://docs.nvidia.com/physicsnemo/26.05/physicsnemo/examples/cfd/external_aerodynamics/domino/README.html)
- SAE paper 2026-01-0600 evaluates DoMINO on a production GM mid-size SUV dataset, predicting surface pressure/flow fields to estimate drag and lift. — [SAE 2026-01-0600](https://saemobilus.sae.org/papers/automotive-aerodynamics-surrogate-modeling-using-nvidia-physicsnemo-mid-sized-suv-gm-dataset-2026-01-0600)
- Transolver-3 (Feb 2026) scales transformer solvers to meshes with >160 million cells on aircraft and automotive benchmarks; GINO (GNO + Geo-FNO) is used as a baseline. — [Transolver-3, arXiv 2602.04940](https://arxiv.org/html/2602.04940v1)
- NVIDIA published a benchmarking framework for automotive-aero AI surrogates in PhysicsNeMo-CFD (Jul 2025). — [arXiv 2507.10747](https://arxiv.org/pdf/2507.10747v1)
- Ansys SimAI (2026 R1): SimAI Premium (cloud-scale) and SimAI Pro (desktop local training/prediction); optiSLang connectors automate training-data generation -> training -> optimisation. — [Synopsys press release](https://news.synopsys.com/2026-03-11-Synopsys-Launches-Ansys-2026-R1-to-Re-Engineer-Engineering-with-Joint-Solutions-and-AI-Powered-Products)
- Walrus (Polymathic AI, Nov 2025): 1.3B-parameter transformer for continuum dynamics, pretrained on 19 scenarios, MIT-licensed on Hugging Face; beats prior foundation models on most tasks but Poseidon still wins in some domains; code tightly coupled to The Well data format. — [Walrus, arXiv 2511.15684](https://arxiv.org/pdf/2511.15684); [HF model card](https://huggingface.co/polymathic-ai/walrus/blob/main/README.md)
- Poseidon (NeurIPS 2024, ETH): pretrained on fluid equations, evaluated on 15 downstream tasks; stated limitations are narrow pretraining physics and mostly simple Cartesian domains with standard BCs. — [Poseidon, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/84e1b1ec17bb11c57234e96433022a9a-Abstract.html)

### Inferences
- When a surrogate is worth it: (1) a narrow design family evaluated thousands of times (optimisation, interactive design feedback, real-time/digital twin); (2) each solve is expensive (hours of transient/turbulent CFD, crash) so 10^2-10^3 training solves amortise; (3) you can afford a solver-in-the-loop check on the final candidates. Not worth it: arbitrary customer parts, linear static FEA (already seconds-minutes), safety-relevant sign-off, or when geometry/topology varies outside training distribution. [BK-informed judgement]
- For an agent, surrogates are a later optimisation: the solver pipeline must exist anyway to generate training data and to verify surrogate predictions. Foundation models (Walrus/Poseidon) operate on gridded fields, not unstructured CAD-derived meshes, so they do not plug into a STEP workflow today.
- MeshGraphNets, FNO/neural operators and Transolver/GINO are available as open implementations in PhysicsNeMo (Apache-2) [BK], making it the natural open framework if a surrogate is later needed.

### Gaps
- No findings retrieved on PhysicsX, Neural Concept, or Navier AI (products, 2026 funding, APIs, pricing) — search returned nothing relevant.
- No sourced quantitative accuracy numbers (e.g. drag error %) for DoMINO/Transolver-3 on DrivAerML were retrieved; no sourced cost/benefit study of surrogate vs solver.
- No structural-mechanics-specific surrogate benchmark found (most evidence is external aero).

## 7. Verification and topology optimisation

### Takeaway
Automated sanity checks should be deterministic code, not LLM judgement: global reaction-vs-applied-load balance (~1% tolerance cited), >=3-level mesh convergence with Richardson extrapolation (guarding against non-monotonic convergence), and regression against NAFEMS/analytical benchmarks. Open topology-optimisation options are research-grade (FEniTop on FEniCSx, DL4TO on PyTorch; ToPy is effectively legacy).

### Cited Findings
- Recommended convergence practice: refine by halving element size until key results change <~5%, then Richardson-extrapolate. — [Skill-Lync V&V course](https://resources.skill-lync.com/courses/fea-fundamentals/validation-verification)
- Richardson extrapolation assumes monotonic convergence; non-monotonic convergence leads to spurious observed order and no reliable error estimate. — [SAE 2005-01-1774](https://saemobilus.sae.org/papers/solution-verification-linked-model-validation-reliability-confidence-2005-01-1774)
- A 2026 trade article proposes global force balance imbalance <=1% of applied load and mesh convergence shown across at least three refinement levels (secondary source; threshold not traced to a NAFEMS document). — [Robotics & Automation News, May 2026](https://roboticsandautomationnews.com/2026/05/06/how-fea-software-improves-structural-design-accuracy/101216/)
- NAFEMS publication R0135 demonstrates code verification via observed order of accuracy from solutions on multiple mesh resolutions, including 3D solid examples. — [NAFEMS R0135](https://www.nafems.org/publications/resource_center/r0135/)
- NAFEMS standard linear-elastic benchmarks (e.g. LE10 thick plate under pressure) have published reference solutions; a vendor guide tabulates them. — [ESRD: Standard NAFEMS Benchmarks](https://www.esrd.com/resource-library/product/standard-nafems-benchmarks-linear-elastic-tests)
- code_aster ships >4,600 verification test cases, usable as a cross-solver reference suite. — [OSArch wiki: Code_Aster](https://wiki.osarch.org/index.php/Code_Aster)
- FEniTop: 2D/3D topology optimisation in Python on FEniCSx with parallel computing and ParaView export; code at missionlab/fenitop. — [FEniTop paper, SMO 2024](https://link.springer.com/article/10.1007/s00158-024-03818-7)
- DL4TO: PyTorch library for 3D topology optimisation (SIMP with differentiable physics, deep-learning integration), Apache licence. — [DL4TO GitHub](https://github.com/dl4to/dl4to)
- ToPy: stable v0.4.1 targets Python 2 with Pysparse; Python 3 master branch is unstable. — [ToPy docs index](https://docsearch.algolia.com/mcp/docs/repo/williamhunter/topy)
- scikit-topt: JOSS-published Python topology-optimisation library (2025-26). — [JOSS paper](https://joss.theoj.org/papers/10.21105/joss.09092.pdf)
- dolfinx-adjoint has a Zenodo release dated 26 Feb 2026 tested against DOLFINx 0.10.0. — [Zenodo record](https://zenodo.org/records/18785543)

### Inferences
- Minimum automated check suite for a CalculiX-based agent [BK-informed]: (1) pre-solve: mesh quality (min scaled Jacobian/aspect ratio), all physical groups non-empty, mass from mesh x density vs CAD volume x density (catches unit errors), rigid-body-mode check (unconstrained model -> 6 zero-frequency modes in a modal run); (2) post-solve: sum of reactions = sum of applied loads within ~1%, max displacement small vs part size for linear analysis, max von Mises vs yield (flag nonlinearity), stress singularities at sharp re-entrant corners/point constraints detected via non-convergence under refinement; (3) convergence: 3 mesh levels on the quantity of interest, report Richardson estimate and GCI, refuse to report if non-monotonic; (4) independent estimate: beam/plate hand-calc or closed-form where the agent can idealise, order-of-magnitude agreement required; (5) CI regression on NAFEMS LE1/LE10/FV32-type cases whenever the pipeline changes.
- Because LLM agents "hallucinate" plausible results (Section 5), every number in a report should be traceable to a parsed solver output file, with the check results attached.
- For topology optimisation in production, CalculiX itself has sensitivity/optimisation steps and FreeCAD-adjacent tools (BESO) exist [BK], but FEniTop/dolfinx-adjoint on DOLFINx is the more maintainable open route; pyOptSparse is an optimiser wrapper (SNOPT/IPOPT/SLSQP), not a TO code [BK].

### Gaps
- Actual NAFEMS reference values (e.g. LE10 target stress) not retrieved; no sourced example of an automated verification harness for CalculiX/code_aster.
- No findings for pyOptSparse or "TopOpt in FreeCAD"; no head-to-head benchmark of TO tools; no sourced data on manufacturability-constrained open TO.
