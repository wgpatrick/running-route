# earthtojake's repositories (text-to-cad) and the other open-source closed-loop CAD agent harnesses — first-hand study, fetched 2026-11-13

**How this was gathered (applies to every section).** All dates and counts are as of the fetch date, 2026-11-13.
- READ DIRECTLY (git clone via the session proxy, files read locally): `earthtojake/text-to-cad` at commit `8ea2434` (2026-11-12, VERSION 0.11.9, last 60 commits of history only), `earthtojake/ccx`, `kicode`, `cad-skill`, `urdf-skill`, `sendcutsend-skill`, `cad-viewer`, `armcade`, `step.parts` (tree + README + notices), `jdilla1277/agentcad`, `pzfreo/build123d-mcp`, `huggingface/cadgenbench`, `Adam-CAD/CADAM`, `neka-nat/freecad-mcp`, `KittyCAD/zoo-mcp`, `partcad/partcad`, `Kamel773/CAD_Code_Generation` (CADCodeVerify).
- READ VIA github.com HTML (summarised by the fetch tool): the earthtojake repository list, star/fork/issue counts, the text-to-cad issues and releases pages.
- SEARCH SUMMARIES ONLY (labelled where used): Hephaestus-CCX, CADSmith, CADGenBench leaderboard numbers.
- COULD NOT FETCH: `arxiv.org` and `huggingface.co` both failed DNS in this session (not on the allowed-hosts list, contrary to the brief); `docs.zoo.dev` was not fetched; the GitHub REST API is blocked for non-session repos. `earthtojake/cadgen` cloned as an empty repository.

Source URLs below point at the file on the default branch; the content cited is what that file held on 2026-11-13.

---

## 1. All of earthtojake's public repos

### Takeaway
The profile lists 20 public repos; one of them matters far more than the rest: `text-to-cad` (26.2k stars, MIT, pushed daily). The older standalone `cad-skill`, `urdf-skill`, `sendcutsend-skill` and `cad-viewer` are archived and were folded into text-to-cad; `ccx` and `kicode` are packaging repos that feed it; `step.parts` is a separate MIT parts-catalogue service.

### Cited Findings
- Profile: bio "beep booping", 581 followers, 20 repositories, no pagination (complete list). — [github.com/earthtojake?tab=repositories](https://github.com/earthtojake?tab=repositories) (HTML fetch, 2026-11-13)
- Repo table as shown on that page (a dash = field not displayed, not zero):

| Repo | Description (page) | Lang | Stars | Licence | Last updated | Relevance |
|---|---|---|---|---|---|---|
| text-to-cad | "Designing physical products with AI" | Python | 26,203 (2,485 forks) | MIT | 2026-11-12 | CORE |
| ccx | (none) — CalculiX `ccx` as a Python wheel `cad-ccx` | Python | — | "Other" (GPL-2.0 per text-to-cad's pyproject comment) | 2026-11-08 | FEA solver packaging |
| kicode | (none) — KiCad `kicad-cli` + KiPy in one package | Python | — | GPL-3.0 | 2026-11-08 | PCB (not mech) |
| earthtojake.com | personal site | TS | 9 | — | 2026-08-27 | no |
| cad-viewer (archived) | "Browser-based viewer for many CAD and robotics file formats" | JS | 105 | MIT | 2026-08-26 | viewer, superseded |
| cadgen | (none) | — | — | — | 2026-08-12 | empty repo on clone; `cadgen` is now a deprecated alias package inside text-to-cad |
| touchgrass | — | TS | — | MIT | 2026-07-03 | no |
| armcade | robot-teleop arcade (TOM arm, LiveKit) | Python | — | MIT | 2026-07-03 | robotics, not CAD |
| lerobot (fork) | fork of HF LeRobot | Python | 6 | Apache-2.0 | 2026-06-26 | robotics |
| step.parts | "Open source STEP part library (12,000+ parts)" (README now says 16,000+) | TS | 410 | MIT (+ third-party model licences) | 2026-06-13 | standard parts |
| muesli | local meeting transcriber | — | 2 | — | 2026-06-06 | no |
| implicit.js | implicit 3D modelling library | JS | 65 | MIT | 2026-06-03 | marginal |
| urdf-skill (archived) | "URDF generation and validation for robot models" | Python | 14 | MIT | 2026-05-19 | superseded |
| cad-skill (archived) | "Script-driven CAD generation, inspection, and validation" | JS | 42 | MIT | 2026-05-19 | superseded |
| sendcutsend-skill (archived) | DXF/STEP checks vs SendCutSend guidelines | Python | 15 | MIT | 2026-05-19 | superseded |
| remotehost-skill | dev-server ports via Tailscale | Shell | 15 | — | 2026-05-19 | no |
| emoji-face, daoism, robot-arm, 20q | old projects | — | 0–22 | — | 2017–2022 | no |

  — [github.com/earthtojake?tab=repositories](https://github.com/earthtojake?tab=repositories)
- `cad-skill`, `urdf-skill`, `sendcutsend-skill` READMEs each read "Moved to text-to-cad … This repo has been deprecated"; last commits 2026-05-19. — [cad-skill README](https://github.com/earthtojake/cad-skill/blob/main/README.md), [urdf-skill README](https://github.com/earthtojake/urdf-skill/blob/main/README.md)
- The archived `cad-skill` was a much smaller thing: `requirements.txt` = build123d, ezdxf, numpy, pillow, playwright, trimesh, vtk; script folders `common/ dxf/ inspect/ render/ step/` plus an `explorer`. — [cad-skill/requirements.txt](https://github.com/earthtojake/cad-skill/blob/main/requirements.txt)
- `cad-viewer` last commit: "Sync CAD Viewer 0.4.28 from earthtojake/text-to-cad@8f9a7d7" (2026-08-26); it opened STEP/STL/3MF/GLB/DXF/URDF/SRDF/SDF with face/edge picking and "copied CAD references", plus optional MoveIt2 websocket IK controls. — [cad-viewer README](https://github.com/earthtojake/cad-viewer/blob/main/README.md)
- `ccx` = `cad-ccx`: "CalculiX's finite-element solver, `ccx`, packaged as a Python wheel … conda-forge's build of the CalculiX source, unmodified", `pip install cad-ccx`, `ccx -v` → 2.23, wheels for Linux x86_64 and aarch64 (manylinux_2_17) among others; `cad_ccx.run("beam.inp")` runs single-threaded. — [earthtojake/ccx README](https://github.com/earthtojake/ccx/blob/main/README.md)
- `step.parts`: Next.js app, "16,000+ open source STEP parts"; categories fasteners, extrusion/stock, bearings/gears/pulleys/linear motion, electronics, servos/motors/actuators/reducers; public API `https://api.step.parts/v1/parts?q=M3&tag=screw`, filters `category`, `family`, `standard=ISO 4762`, OpenAPI at `/v1/openapi.json`; repo still carries `skills/step-parts/SKILL.md` and `scripts/download_step_part.py`. — [step.parts README](https://github.com/earthtojake/step.parts/blob/main/README.md)
- step.parts licensing: MIT for original material only; KiCad-derived STEP files are CC-BY-SA-4.0 with KiCad-libraries-exception, FreeCAD-library-derived CC-BY-3.0, SparkFun CC-BY-4.0 / CC-BY-SA-4.0, Adafruit MIT. — [THIRD_PARTY_NOTICES.md](https://github.com/earthtojake/step.parts/blob/main/THIRD_PARTY_NOTICES.md)

### Inferences
- The profile page's "12,000+" vs the README's "16,000+" for step.parts is a stale description, not a conflict of substance.
- The licence holder in text-to-cad's LICENSE is "Thompson Labs LLC", so this is a company-backed project despite the personal account.

### Gaps
- Stars/licence for `ccx`, `kicode`, `armcade`, `cadgen`, `touchgrass` were not displayed on the list page and the REST API is blocked; not fetched individually.
- No blog/X/HN posts by or about earthtojake were read (x.com and HN are not reachable hosts here); nothing in these notes rests on them.

---

## 2. text-to-cad in depth

### Takeaway
text-to-cad 0.11.9 is no longer "a CAD skill with scripts": it is a full local engine (`cad` CLI + warm build server + browser viewer + thin MCP shim) with eight skills, and as of the week of 7–12 Nov 2026 it already ships exact-B-rep assembly interference at named poses, joint-stop sweeps, per-process DFM with a three-state verdict, CalculiX linear-static FEA with bonded assemblies, and MJCF/URDF generation from build123d joints with a MuJoCo compile-and-health check. What it does not ship is a dynamic simulation run as a verifier, a closed-loop kinematic solver, assemblability/insertion checks, contact/bolt FEA, or tolerance analysis.

### Cited Findings

**Traction, cadence, licence**
- 26.2k stars, 2.5k forks, 109 watchers, 5 open issues, 31 open PRs, 1,510 commits on `main`; topics agents, ai-agents, cad, mechanical-engineering, robotics, step, stl, text-to-cad. — [github.com/earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad) (HTML fetch, 2026-11-13)
- Ten releases v0.11.0 → v0.11.9 between 7 and 11 Nov 2026 (two on several days); e.g. v0.11.3 stress studies/CalculiX, v0.11.7 manufacturing checks on exact geometry, v0.11.8 MuJoCo + robot descriptions from CAD, v0.11.9 `cad model interference`, `snapshot --preview`, poses along a motion, the galatea humanoid. — [releases](https://github.com/earthtojake/text-to-cad/releases); commit log read locally confirms the same subjects
- MIT, "Copyright (c) 2026 Thompson Labs LLC"; every skill folder carries its own MIT LICENSE. — [LICENSE](https://github.com/earthtojake/text-to-cad/blob/main/LICENSE)
- Telemetry is on by default ("sends usage stats and crash reports, tagged with a random ID and never including your files, paths or prompts"); `install.sh … --no-telemetry` turns it off. — [README](https://github.com/earthtojake/text-to-cad/blob/main/README.md), [docs/install.md](https://github.com/earthtojake/text-to-cad/blob/main/docs/install.md)
- Open issues are all upstream-kernel trackers (OCCT 8.0.x periodic-surface workaround #822, F1 airbox loft Boolean instability #703, free-form bounds/extrema #702, sweep distortion #701) plus one glTF-for-Gazebo question #681. — [issues](https://github.com/earthtojake/text-to-cad/issues)

**Repo structure (read locally)**
- Top level: `skills/` (8 skills), `packages/` (`cad` library, `cad-server`, `cad-mcp`, `core` and `ui` TypeScript, `aliases/cadgen`), `apps/` (`web`, `api`, `docs`, `mcp`), `models/` (example gallery), `scripts/` (install, release, bench, test), `tests/` (python + browser), per-agent manifests (`.claude-plugin`, `.codex-plugin`, `.cursor-plugin`, `.grok-plugin`, `gemini-extension.json`, `plugin.json`, `mcp.json`, `skills.sh.json`), `AGENTS.md` (26 KB), `docs/` (install, 5 migration guides, contributing: adding-a-document-type / adding-an-integration / testing / writing-a-skill). — [repo tree](https://github.com/earthtojake/text-to-cad)
- Skills and sizes: `cad` (SKILL.md 38 KB + 16 references ≈ 235 KB), `robot-simulation` (35 KB + 18 references), `fea` (19 KB + 3 refs), `pcb` (23 KB + 10 refs), `sendcutsend` (15 KB), `render` (13 KB), `engineering-drawing` (8 KB), `print3d` (7.5 KB + `scripts/orca_presets.py`). Total skill text ≈ 724 KB. — [skills/](https://github.com/earthtojake/text-to-cad/tree/main/skills)
- Skill consolidation in 0.11: "The twelve skills are six, each an outcome rather than a file format": `urdf`,`srdf`,`sdf` → `robot-simulation`; `dxf` → `cad`; `dfm`,`dfam-check` → `cad`'s "Can it be made?"; `gcode`,`bambu-labs` → `print3d`; **`step-parts` and `download_step_part.py` → "gone: step.parts stays a service of its own"**; new `pcb`. — [docs/migrations/migrating-0.10-to-next.md](https://github.com/earthtojake/text-to-cad/blob/main/docs/migrations/migrating-0.10-to-next.md)

**Libraries and versions (packages/cad/pyproject.toml, v0.11.9)**
- Python ≥ 3.13 (launchers use uv-managed 3.14); base dependency numpy only; extra `build123d`: `build123d>=0.13.0,<0.14`, `cadquery-ocp-novtk>=8.0,<8.1` (OCCT 8), `bd_materials`, ezdxf, shapely, scipy, matplotlib, pillow. The upper bound is deliberate: "the library does not merely CALL build123d, it reaches into it: the engine's determinism settings shadow `set` in its topology modules and replace `Vertex.__hash__`, and its memo wraps the kernel's constructors". — [packages/cad/pyproject.toml](https://github.com/earthtojake/text-to-cad/blob/main/packages/cad/pyproject.toml)
- Extras: `netgen` (`netgen-mesher>=6.2.2608,<6.3`, LGPL-2.1, macOS / Linux x86_64 / Windows x86_64 only — a solve refuses on Linux ARM); `calculix` (`cad-ccx==2.23.0`, GPL-2.0, "run as a separate program and never linked"); `trimesh>=4.6,<6` + rtree + networkx for DFM ray casts; `mujoco` (`mujoco-core>=4.0,<5`, `mujoco-studio>=4.0,<5` — headless, no GL); `coacd` 1.0.x for convex decomposition; `kicad` (`kicode==10.99.0.dev20261106`). Meshing is **netgen, not Gmsh**. — [packages/cad/pyproject.toml](https://github.com/earthtojake/text-to-cad/blob/main/packages/cad/pyproject.toml)

**The loop (cad skill)**
- A model is a parameterless Python function decorated `@model` returning a build123d shape; `cad run src/bracket.py` (a wrapper over `uv run`) builds it in a warm per-script worker of one long-lived local server and prints a bounded text report: build time, cache hits/misses, "parts 1 · bounds 40 × 20 × 6 mm · joints 0 · sequences 0", a stable document `id:` (derived from script path + function name) and a `view:` URL. "Running the script is the rebuild. It writes no file." — [skills/cad/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/SKILL.md)
- Incremental rebuild: "the worker keeps every kernel operation its models ran, keyed by its inputs and the body that ran it … So an edit costs what it changed, and an element keeps the name its feature history gave it"; shapes made by raw OCP calls are reported as `uncached`. Example line: cold 2.61 s, warm 0.01 s. — [references/model-contract.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/references/model-contract.md)
- "Check each change" table: read the run's delta first; a number the person gave → `assert` inside the model body or `cad model inspect`; a derived number → a check script that calls the model; an assembly change → `cad model interference "$ID"` with a `--pose` per mechanism state; new parts/placements → snapshots; a part with a named process → its `cad model dfm` check, whose flags are recorded in the module docstring (`Check: cad model dfm "$ID" --tools 3,6,10`) so later sessions rerun the same check. — [skills/cad/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/SKILL.md)
- Explicit loop rules: "A number is never read off a picture: a snapshot shows arrangement and appearance, not dimensions"; "A check that fails or cannot decide has shown nothing about the design"; "A retry that leaves out or shrinks a specified feature … builds a different design from the one asked for"; "A check is trusted once it has been seen to fail: plant what it guards against"; "Report what a check cannot see beside what it passed". — [skills/cad/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/SKILL.md)
- No retry cap is written into the skill; the DFM loop says "Repeat until no error remains". — [skills/cad/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/SKILL.md)

**Stable references and code provenance**
- Every face/edge/vertex is named by feature history (`f:plate.body.3;M:plate.relief`); a dimension edit keeps names. `cad model inspect "$ID" "bracket/face 7"` returns JSON with `ref`, `kind`, `area`, `centroid`, `surface`, `radius` and `made_by: {operation: "cut", function, file, line}` — the source line that created the face. A deleted element "fails, naming it … never guessing". — [references/inspection-and-validation.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/references/inspection-and-validation.md)
- Geometry diagnostics exposed as library calls: `shape.is_valid`, `is_sound` (BRepAlgoAPI_Check), `topology_errors`, `boundary_edges`, `self_intersections`; "An inconclusive check raises `GeometryError` rather than passing"; `inspect` flags inside-out solids (`inverted`). Measurements: `closest_points`, `overlap_volume` (exact intersection volume), `mass_properties` (mass, CoM, inertia). — [references/inspection-and-validation.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/references/inspection-and-validation.md)

**Assembly interference (new in v0.11.9)**
- `cad model interference "$ID" [--pose crouch] [--pose walk@0.6] [--pose '{"l_knee": 90}'] [--fit 'bearing*' housing]`: "The verdict is the kernel's, exact, on the parts' own solids, so a plate through a 2.6 mm skin is found … A mesh only rules out the pairs with air between them". Exit status 0 clear / 1 overlap / 3 "none found but a pair could not be measured, which is no pass". Intended overlaps must be declared (`--fit`), "never inferred". `--json` gives `measurements.overlaps/.fits/.unmeasured`. — [references/inspection-and-validation.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/references/inspection-and-validation.md)
- Cost and caching: per-pair answers are cached by the two geometries and relative placement, a timed-out check resumes, a pose re-measures only moving pairs; a per-pair Boolean limit of five minutes and twenty for the whole check; "a 700-part humanoid: ten minutes the first time on four cores, most of it eight such pairs". It "checks the poses it is given, and chooses none" and cannot see a time between two sampled poses. — same file

**Kinematics and motion**
- Joints are build123d's (`RevoluteJoint`, `LinearJoint`, `CylindricalJoint`, `BallJoint`, `RigidJoint` + `connect_to`); `cad.build123d` adds `mechanism_state`, `gear_pair`, `rack_and_pinion_pair`, `screw_pair`, `configuration_sequence`, `posed`, named after STEP AP242 entities. — [references/kinematics.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/references/kinematics.md)
- Closed loops are stored but not solved: "a loop's pairs are not posed (there is no solver), so a mechanism state or a configuration sequence that moves one is refused or left out, and `cad model ranges` sweeps none of them." — same file
- `cad model ranges "$ID"` sweeps each revolute/linear joint alone, 1° or 1 mm per step, until child meets parent; reports stops, the two parts that met, and "clashes" with other links; 0.3 mm default clearance, gap accuracy "within 0.6 mm over the true one, never under"; single core; "an arm of a few hundred small parts and six joints takes tens of seconds". The command writes nothing — the agent copies the stops into `angular_range`. — [skills/cad/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/SKILL.md)
- "A pose or a motion shows movement; it does not measure it." Motion is reviewed by posed snapshots (`--pose walk@0.6`, batch JSON job lists) and by the viewer's playbar; measurement is interference at chosen poses. — [references/kinematics.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/references/kinematics.md)

**Robot descriptions and MuJoCo (robot-simulation skill)**
- Scope line: "Robot and world descriptions (URDF, SRDF, MJCF) … Not the CAD part itself … **nor a simulation run**." `cad model export <id> robot.xml|.urdf` generates MJCF/URDF from joints, materials and declarations `frame()`, `body()`, `limits()`, `mass()`, `point_mass()`, `free()`, `link()`; couplings become MJCF `<equality><joint>` / URDF `<mimic>`; closed loops become MJCF `connect` equalities and are dropped (with a log line) in URDF. — [skills/robot-simulation/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/robot-simulation/SKILL.md), [references/kinematics.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/references/kinematics.md)
- `cad mujoco check scene.xml [--strict --json]` compiles with MuJoCo and runs static "model health" rules at `qpos0` and the `home` key: `contacts_at_rest` (>0.1 mm penetration), `visual_geoms_collide`, `inertia_from_visuals`, `scale_suspect`, `joint_limits_at_rest`, `defaults_not_recommended`, `mass_summary`. JSON shape `{"ok","path","findings":[{"severity","code","message","location","hint"}],"summary"}`; exit 1 fail, 2 command refused. — [references/mjcf-checks.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/robot-simulation/references/mjcf-checks.md)
- Human review of dynamics is MuJoCo Studio's web viewer (`cad run mujoco-studio --model scene.xml`); "Visual review cannot prove planning correctness or dynamics; the viewer does not play a simulation." A flipped joint sign is caught only by a viewer sweep or posed snapshots. — [skills/robot-simulation/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/robot-simulation/SKILL.md)
- A 35 KB recipe exists for turning a vendor STEP of an arm into links/joints (`references/from-a-vendor-step.md`). — [skills/robot-simulation/references](https://github.com/earthtojake/text-to-cad/tree/main/skills/robot-simulation/references)

**FEA (fea skill, v0.11.3+)**
- Linear static only: netgen quadratic tets, CalculiX 2.23, isotropic material below yield, rigid fixtures; units fixed mm/N/MPa. "Vibration, buckling, heat, flow, fatigue, impact and parts that slide on each other are not in this version." "It is a first-pass engineering check, not a certification." — [skills/fea/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/fea/SKILL.md)
- Workflow: `cad step solve part.step` (no study) lists faces with hints (`plane, normal -Z, largest`); the agent writes a JSON study (`fixtures`, `loads`, `margin` default 2, optional displacement `checks`); `cad step solve … --study study.json --out DIR --json` writes `result.json`, `stress.png`, `displacement.png`, `result.glb`, `result.vtu`, optional `ccx.inp`. — same file
- Built-in guards: automatic re-mesh at half element size when safety factor < 3; malformed studies refused before meshing; under-constrained parts refused; "so is a solve whose reactions do not balance the applied load"; deterministic single-thread solve. — same file
- Assemblies: touching parts are auto-bonded into one conforming mesh (0.1 mm contact tolerance); the setup listing prints each pair as `bonded` / `not connected` / `overlapping · N mm³`; "Connections are `bonded` or `free`: parts that press and slide on each other, and bolts, are not in this version." — same file

**DFM ("Can it be made?", v0.11.7+)**
- `cad model dfm "$ID" --process cnc|sheet|molding|printing …` on exact geometry (meshes only for printing). Three-state verdict by exit status: `OK` 0, `FAILED` 1, `NOT CHECKED` 3 ("Never read it as a pass"), usage 2. JSON findings carry `rule`, `value`, `limit`, `unit`, `op`, `source`, `refs` — "read those, never the message, and take the next edit from them (the feature at `refs[0]`, moved from `value` past `limit`)". Redesigns are compared by matching failures on `xyz` position because face numbers change. — [skills/cad/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/SKILL.md)
- Checks only run when a process is named or implied; rules are "general practice, no shop's". `sendcutsend` and `print3d` (OrcaSlicer, Bambu hand-off; "Never starts a print") cover named services. — same file; [skills/print3d/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/print3d/SKILL.md)

**Viewer and human review**
- The CAD Viewer is served by the same local server, updates live on each run, is explicitly read-only ("Changing a design belongs to the agent and the code"), and offers Select, Measure, Annotate, Quick Edit, filters, joint sliders, mechanism-state presets and a motion playbar. Picked entities are copied as stable refs; a Quick Edit prompt arrives with `File:`, `References:` and a snapshot packet with the person's ink, which the agent re-renders with `--annotation … --camera authored`. — [packages/ui/README.md](https://github.com/earthtojake/text-to-cad/blob/main/packages/ui/README.md), [skills/cad/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/SKILL.md)
- Agent-side images come from `cad model snapshot` (OCCT-rendered PNG; `--camera`, `--display hidden-line`, `--pose`, clipped views, `--preview`); "Never screenshot the viewer to check your own work". — [skills/cad/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/SKILL.md)

**Tool surface and supported agents**
- The agent surface is CLI + skills, not MCP tools. `cad-mcp` is a stdlib-only stdio shim that "holds no tool, view or document: the server does"; under Claude Code the session "lists no tools: there CAD is the cad skill and the `cad` command". Its one user-facing tool is `cad_show` (viewer cards in Claude Desktop). — [packages/cad-mcp/README.md](https://github.com/earthtojake/text-to-cad/blob/main/packages/cad-mcp/README.md)
- Install: `curl -fsSL https://texttocad.dev/install.sh | sh`; per-app sections for Claude Code (`claude plugin marketplace add earthtojake/text-to-cad#latest`; `claude plugin install text-to-cad@earthtojake`), Claude Desktop, Codex, Cursor, Grok Build, Gemini CLI, and "Other agents" via the Skills CLI. First start downloads the runtime and needs network. — [docs/install.md](https://github.com/earthtojake/text-to-cad/blob/main/docs/install.md)

**Standard / off-the-shelf parts**
- In 0.11.9 there is no parts-catalogue skill in the plugin (removed; see migration row above). Vendor geometry enters through `step.read`, `xbf.read`, `stl.read` in the model body; a vendor STEP is converted once to the native `.xbf` ("many times faster than parsing the STEP"). A grep of the repo for `bd_warehouse` returned nothing. — [skills/cad/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/SKILL.md); local grep, 2026-11-13

**Examples, benchmarks, dog-fooding**
- `models/` gallery: falcon_heavy, moonwatch, f14d, lyra and juno (with URDF/SRDF), w16, galatea (700–850-part humanoid with `sim/`), motorbike, f1, radial (nine-cylinder engine), hypercar, tendon_hand, qdd_actuator, dfm-process-comparison, mujoco, eight KiCad boards. — [models/](https://github.com/earthtojake/text-to-cad/tree/main/models)
- `scripts/bench` holds engine performance benchmarks only (cold/noop/edit/restart/mesh/snapshot timings over ten corpus models); "None of them runs in CI". There is no task-accuracy benchmark or CADGenBench result in the repo. — [scripts/bench/README.md](https://github.com/earthtojake/text-to-cad/blob/main/scripts/bench/README.md)
- `models/galatea/FEEDBACK.md` is an agent's post-mortem: rails cut through a shin guard "in a model I had reported as checked three times over. A person saw it in the first renders", because (1) the part was never reviewed alone and (2) the home-made interference check sampled mesh points, so "a plate passing through a skin scored nothing". The exact re-check found 190 mm³, 10 mm³ and 2,677 mm³ overlaps. This directly produced the `cad model interference` command and the "trusted once it has been seen to fail" rule. — [models/galatea/FEEDBACK.md](https://github.com/earthtojake/text-to-cad/blob/main/models/galatea/FEEDBACK.md)
- `models/radial/GAUNTLET.md` documents a blind A/B visual critic: a fresh-context critic sees the render and a museum photo in random order, asked "which is more beautiful?", and names one largest gap that is routed back to the part's owner. — [models/radial/GAUNTLET.md](https://github.com/earthtojake/text-to-cad/blob/main/models/radial/GAUNTLET.md)

### Inferences
- The verifier set was built in roughly one week (FEA 8 Nov, DFM 10 Nov, MuJoCo 10–11 Nov, interference 11 Nov). It is fresh code with no published accuracy evidence, and interfaces changed across 0.8 → 0.10 → 0.11 (five migration guides), so anything built on it should pin a version.
- The design is strongly opinionated toward a person at a desktop: persistent local server, live browser viewer, auto-update, telemetry. A headless Linux sandbox is supported in pieces (MuJoCo headless by design; FEA pictures "left out … Linux with no display"), but the server/door/token model and first-run downloads add friction in ephemeral containers.
- Python ≥ 3.13 and build123d 0.13/OCP 8 are hard floors; a team sandbox on an older build123d cannot import the `cad` library alongside it.
- Removing the step-parts skill means standard-part sourcing is currently outside the plugin; the step.parts API still exists and is trivially callable.

### Gaps
- No roadmap document was found in the repo; direction is only visible through release notes and open PR count (31).
- Full commit history and contributor count were not obtained (shallow clone, API blocked).
- The Discord and texttocad.dev docs site were not read.
- I did not run the software; all behaviour above is as documented in the skill files, not observed.

---

## 3. The other harnesses, read directly

### Takeaway
Two other actively developed, permissively licensed build123d harnesses exist — agentcad (CLI-first, versioned builds and diffs, review comments) and build123d-mcp (MCP-first, validity gate, spec verification, parameter audit) — and both publish CADGenBench numbers showing the harness improves the same model. Everything else is either a different kernel (FreeCAD, KCL, OpenSCAD), a benchmark, or a paper without code I could read.

### Cited Findings

| Project | Stars (2026-11-13) | Licence | Last commit | Kernel | Surface |
|---|---|---|---|---|---|
| jdilla1277/agentcad | 213 | Apache-2.0 | 2026-11-12 (v0.8.0) | build123d 0.10.x / OCP 7.8 (CadQuery optional) | CLI, JSON on stdout; also MCP |
| pzfreo/build123d-mcp | 151 | Apache-2.0 | 2026-11-11 (v0.3.92.dev0) | build123d ≥0.10,<0.14 | MCP (stdio/HTTP) |
| huggingface/cadgenbench | 153 | Apache-2.0 | 2026-07-17 | tool-agnostic (STEP in) | benchmark + baseline agent |
| Adam-CAD/CADAM | 5.4k | GPL-3.0 | 2026-10-14 | OpenSCAD WASM | web app |
| neka-nat/freecad-mcp | 3.3k | MIT | 2026-11-12 (v0.1.31) | FreeCAD | MCP → FreeCAD addon RPC |
| KittyCAD/zoo-mcp | 11 | MIT | 2026-11-12 | Zoo engine / KCL (cloud, account) | MCP |
| partcad/partcad | 530 | Apache-2.0 | 2026-11-13 (v0.10.18) | many (build123d, CadQuery, OpenSCAD, STEP…) | CLI `pc`, MCP `pc mcp`, 15 skills |

  — star counts from each repo's GitHub page; licences, versions and dates from local clones: [agentcad](https://github.com/jdilla1277/agentcad), [build123d-mcp](https://github.com/pzfreo/build123d-mcp), [cadgenbench](https://github.com/huggingface/cadgenbench), [CADAM](https://github.com/Adam-CAD/CADAM), [freecad-mcp](https://github.com/neka-nat/freecad-mcp), [zoo-mcp](https://github.com/KittyCAD/zoo-mcp), [partcad](https://github.com/partcad/partcad)

**agentcad**
- "Each command's final response is structured JSON on stdout"; progress goes to stderr. Required workflow installed by `agentcad init`: "Inspect → Specify → Build → Validate → Deliver … If a check fails, return to the earliest incorrect stage and iterate." — [agentcad README](https://github.com/jdilla1277/agentcad/blob/main/README.md)
- Commands: `run script.py --label L` (versioned STEP + metrics; `--preview` four-view PNG), `inspect` (bounded topology, addressable IDs, edit risk), `measure`, `render --view top,front,right,iso`, `check-spec output.step spec.json`, `diff 1 2` (shared / reference-only / candidate-only volume), `view old.step new.step` (A/B), `import supplier.step --init`, `parts list/show`, `export`. — same README
- Human review: live local viewer on 127.0.0.1 with side-by-side/overlay of previous vs current, and spatial review comments pinned to a surface and named part, stored as local JSON under `.agentcad/reviews`; the agent reads them with `agentcad review list --status open` and can reply/resolve. — same README
- Bounded responses are a first-class feature: `--response-budget`, `--response-text-budget`, `--image-budget`; an over-budget response returns `delivery.status=budget_unavailable` and a reference to "a complete pre-budget snapshot". — [docs/inspection-budgets.md](https://github.com/jdilla1277/agentcad/blob/main/docs/inspection-budgets.md)
- Evidence (project's own CADGenBench runs, 81 fixtures, GPT-5 Nano): published baseline 0.184 overall / 82.7% valid (67/81); Candidate K (19 reliability fixes) 0.217 / 96.3%; Candidate L (plus five-stage workflow text, ~29% more words) 0.245 / 98.8% (80/81). Editing was initially worse with the harness than without (0.249 vs 0.279 direct build123d) and rose to 0.353. Claude Opus 5.5 with standard agentcad: 0.447 overall, 0.593 editing. — [docs/product-plans/agentcad-performance-evidence.md](https://github.com/jdilla1277/agentcad/blob/main/docs/product-plans/agentcad-performance-evidence.md)
- Diagnosis from transcript review: agents "often had a sound geometric plan and still failed because they guessed an API, lost output capture, selected the wrong runtime, applied a global operation, or treated a structurally valid STEP as proof that the requested edit was correct." — [docs/product-plans/agentcad-performance-next-steps.md](https://github.com/jdilla1277/agentcad/blob/main/docs/product-plans/agentcad-performance-next-steps.md)

**build123d-mcp**
- Tools (from `server.py`): `execute`, `execute_file` (persistent session), `render_view`, `measure`, `validate`, `locate_gate_defects`, `design_audit`, `verify_spec`, `suggest_spec`, `analyze_printability`, `cross_sections`, `mesh_section`, `mesh_holes`, `inspect_part`, `interference`, `export`, `bank_candidate`, drawing tools; `install_skill(target="claude"|"agents-md"|…, skill="modeling"|"drawing"|"repair")`. — [src/build123d_mcp/server.py](https://github.com/pzfreo/build123d-mcp/blob/main/src/build123d_mcp/server.py), [README](https://github.com/pzfreo/build123d-mcp/blob/main/README.md)
- `validate` returns "a `PASS`/`FAIL` line plus JSON: `passes_gate`, `n_solids`, `volume`, `watertight_manifold`, `open_edges`, `nonmanifold_edges`, `brep_valid`, `reasons`, `warnings`". `design_audit` nudges each named parameter ±epsilon, rebuilds and re-runs the gate, "out of process, hard-bounded by the op budget", returning a partial report rather than timing out. `verify_spec` is "the 'did I build what was requested?' gate". `interference` returns `interferes`, overlap `volume`, `bounds` for a pair. — [llms.md](https://github.com/pzfreo/build123d-mcp/blob/main/llms.md)
- Ships a `bd_warehouse` resource module and sandboxing (`security.py`); heavy operations run in subprocess workers. — [src/build123d_mcp](https://github.com/pzfreo/build123d-mcp/tree/main/src/build123d_mcp)
- Evidence (project's own claim): "On the public CADGenBench leaderboard in June 2026, using build123d-mcp raised the same model's score from 0.360 to 0.457 and CAD validity from 88% to 100%." — [README](https://github.com/pzfreo/build123d-mcp/blob/main/README.md)

**CADGenBench**
- Two tasks (generation from an engineering drawing; editing a STEP per change request); submission is one `output.step` per sample; four axes — Validity (watertight gate that zeroes the rest), Shape similarity (surface-distance F1, volume IoU), Interface match (authored keep-in/keep-out sub-volumes), Topology match (Betti numbers); private ground truth; rows publish as "unvalidated" until a methodology review. Includes a reference baseline that "iteratively writes CAD code, validates the artifact, and repeats until valid". — [cadgenbench README](https://github.com/huggingface/cadgenbench/blob/main/README.md)
- Single parts only: nothing in the metric list covers assemblies, motion, strength or manufacturability. — same README

**CADAM (Adam)** — browser app generating parametric OpenSCAD (WASM) with BOSL/BOSL2/MCAD, slider parameters, STL/SCAD/DXF export; its "benchmarks" folder is a showcase of 13 prompt→model examples, not a scored evaluation. No verifier loop is described in the README. — [CADAM README](https://github.com/Adam-CAD/CADAM/blob/master/README.md)

**neka-nat/freecad-mcp** — 17 tools incl. `execute_code`, `execute_code_headless` (separate `freecadcmd` process), `get_view` (screenshot, `include_screenshot=false` for text-only), `insert_part_from_library` / `get_parts_list` (FreeCAD parts library), `run_fem_analysis` ("Run CalculiX on an existing analysis and return summary results"). It is a remote control for a running FreeCAD, with no prescribed check loop. — [docs/tools.md](https://github.com/neka-nat/freecad-mcp/blob/main/docs/tools.md)

**Zoo MCP** — requires a Zoo account/API token; tools include `execute_kcl`, `mock_execute_kcl`, `lint_and_fix_kcl`, `format_kcl`, `snapshot`, `calculate_mass/volume/surface_area/center_of_mass`, `calculate_bounding_box_cad`, `entity_distance`, `get_sketch_constraint_status`, `convert_cad_file`, KCL doc and sample search. — [zoo-mcp server.py](https://github.com/KittyCAD/zoo-mcp/blob/main/src/zoo_mcp/server.py), [README](https://github.com/KittyCAD/zoo-mcp/blob/main/README.md)

**PartCAD** — README lists "FEA, modal, thermal and CFD analysis (`pc cae`), simulation in MuJoCo or Gazebo (`pc qual test --simulation`), 2.5D toolpaths (`pc cam`)", assemblies with "interfaces and mating as objects", a "Build vs Buy decision per line item", and "Agent Skills for Claude Code and Cursor, an MCP server (`pc mcp`)". Skills: add-interfaces, convert, describe, export, gen, gen-assembly, gen-part, gen-scene, gen-sketch, init, render, search, setup, **sim-assembly-fea**, **validate**. — [partcad README](https://github.com/partcad/partcad/blob/devel/README.md), [ai-agents/](https://github.com/partcad/partcad/tree/devel/ai-agents)
- `validate` skill: check an object "against the requirements its `requirements:` section declares — run `pc qual test` for the ports, interfaces and physics PartCAD measures, run every simulation and every engineering analysis scenario, render it from every angle that matters". `sim-assembly-fea`: run a declared assembly simulation, "read the forces and moments acting on the body the part is welded into at the end of the run … and add the part a new named FEA scenario". — [validate/SKILL.md](https://github.com/partcad/partcad/blob/devel/ai-agents/common/skills/validate/SKILL.md), [sim-assembly-fea/SKILL.md](https://github.com/partcad/partcad/blob/devel/ai-agents/common/skills/sim-assembly-fea/SKILL.md)

**CADCodeVerify** — the public repo holds the CADPrompt dataset and figures only (last commit 2025-02-28); no harness code. — [Kamel773/CAD_Code_Generation](https://github.com/Kamel773/CAD_Code_Generation)

**Hephaestus-CCX (SEARCH SUMMARY ONLY, not read)** — arXiv 2605.17448: agent writes CadQuery, up to 10 attempts; a deterministic controller meshes with gmsh, runs CalculiX against typed pass/fail requirement checkers and returns failed requirements and margins; 50 briefs; "400 first attempts yield no strict-passing artifacts"; multi-view feedback raised GPT-5.5's mean requirement pass rate from 19.4% to 29.3%. No GitHub repo surfaced. — [arxiv.org/html/2605.17448v2](https://arxiv.org/html/2605.17448v2) (search snippet)

**CADSmith (SEARCH SUMMARY ONLY, not read)** — arXiv 2603.26512: Planner/Coder/Executor/Validator/Refiner over CadQuery with two correction loops and a stronger model as judge; reported median IoU 0.8085 → 0.9629 and mean Chamfer distance 28.37 → 0.74 on 100 examples. No code repo surfaced. — [arxiv.org/abs/2603.26512](https://arxiv.org/abs/2603.26512) (search snippet)

### Inferences
- PartCAD is the only project read whose documentation describes chaining a mechanism simulation into part-level FEA loads. I read only its README and skill front-matter, not the implementation, so maturity is unverified.
- agentcad pins build123d <0.11 (OCP 7.8) while text-to-cad requires 0.13 (OCP 8): the two cannot share one Python environment. build123d-mcp spans 0.10–0.13 and can.

### Gaps
- The CADGenBench leaderboard itself (huggingface.co) could not be fetched; current top scores are unverified. Search snippets disagree (≈0.39, 0.387, 0.444).
- docs.zoo.dev / Zookeeper were not read; only the zoo-mcp repo was.
- No other "Claude Code for CAD" plugins were surveyed beyond those named; search surfaced Forgent3D and a CalculiX MCP in "CAE-Agent-Hub" by name only.
- Star counts are rounded by GitHub's UI for the larger repos.

---

## 4. Cross-cutting: verifier types, bounding the loop, feedback format, evidence

### Takeaway
Single-part validity, measurement, renders and DFM are well covered and reusable today; pose-sampled assembly interference and static FEA exist in text-to-cad only since November 2026. Dynamic motion simulation as a pass/fail verifier, closed-loop kinematics, assemblability, contact/bolted FEA and tolerance analysis are absent from every harness whose code I read (PartCAD claims some in its README).

### Cited Findings

**Verifier coverage (from the files cited in sections 2–3)**

| Verifier | text-to-cad 0.11.9 | agentcad 0.8 | build123d-mcp 0.3.9x | PartCAD (README claims) |
|---|---|---|---|---|
| B-rep validity / watertight | library calls + `inspect` | validation on export | `validate` gate | — |
| Dimensions, mass, CoM | `inspect`, check scripts | `measure`, metrics | `measure` | — |
| Requested-vs-built spec | asserts in model body | `spec.json` + `check-spec` | `verify_spec` / `suggest_spec` | `requirements:` + `pc qual test` |
| Version diff | cached rebuild delta line | `diff`, A/B viewer | session snapshots | — |
| Renders | OCCT `snapshot`, poses, sections | four-view PNG, turntable | `render_view`, cross-sections | render skill |
| Static assembly interference | exact, all pairs, cached | not seen | pairwise `interference` | — |
| Interference at poses | yes, poses chosen by agent | no | no | — |
| Joint range from geometry | `cad model ranges` | no | no | — |
| Closed-loop kinematics | no solver | no | no | not read |
| Dynamic simulation run | no (compile + rest-state health only) | no | no | `pc qual test --simulation` |
| Assemblability / insertion path | no | no | no | not read |
| FEA | linear static, bonded | no | no | `pc cae` (FEA, modal, thermal, CFD) |
| DFM | CNC, sheet, molding, printing | no | `analyze_printability` | materials/methods in BOM |
| Tolerance stack-up | no | no | no | not read |
| Parameter robustness | no | edit-risk report | `design_audit` | — |

- text-to-cad's own statement of the motion gap: "A pose or a motion shows movement; it does not measure it … a part that clears there can still pass through another mid-motion." — [references/kinematics.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/references/kinematics.md)

**Keeping loops fast and bounded**
- text-to-cad: warm worker + per-kernel-operation memo (0.01 s warm vs 2.61 s cold in the skill's example); per-pair interference cache with resume; mesh prefilter then exact Boolean; hard limits (5 min/pair, 20 min/check) that surface as status 3 rather than a pass; `--joint` / `--occurrence` to narrow scope; process-gated DFM ("with none, no check"). — [skills/cad/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/SKILL.md), [inspection-and-validation.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/references/inspection-and-validation.md)
- agentcad: token/image response budgets with a saved full snapshot; versioned build directories; 120 s command and 900 s trial timeouts in its benchmark runs. — [inspection-budgets.md](https://github.com/jdilla1277/agentcad/blob/main/docs/inspection-budgets.md), [performance-evidence.md](https://github.com/jdilla1277/agentcad/blob/main/docs/product-plans/agentcad-performance-evidence.md)
- build123d-mcp: subprocess workers with an op budget; partial reports instead of timeouts; mesh-estimate fallback flagged as such. — [llms.md](https://github.com/pzfreo/build123d-mcp/blob/main/llms.md)
- Explicit attempt caps appear only in the benchmark-style systems: H-CCX "up to 10 attempts" (search summary). text-to-cad's skills set none.

**Feedback format to the model**
- text-to-cad: findings as `{severity, code, message, location, hint}` with stable codes; DFM adds `rule/value/limit/unit/op/refs`; four exit codes (0 ok, 1 failed, 2 usage, 3 not checked); refs resolve to source file and line via `made_by`. — [skills/cad/SKILL.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/cad/SKILL.md), [mjcf-checks.md](https://github.com/earthtojake/text-to-cad/blob/main/skills/robot-simulation/references/mjcf-checks.md)
- agentcad: JSON on stdout, prose on stderr. build123d-mcp: `PASS`/`FAIL` line plus JSON with `reasons` vs `warnings`. — READMEs cited above

**Evidence that the loop helps (all self-reported or from search summaries)**
- build123d-mcp: 0.360 → 0.457 CAD Score, validity 88% → 100%, same model. — [README](https://github.com/pzfreo/build123d-mcp/blob/main/README.md)
- agentcad: 0.184 → 0.245 overall and 67/81 → 80/81 valid across two iterations; workflow text alone K→L +0.028 on Nano, +0.011 on GPT-6 Luna (0.329 → 0.340). — [performance-evidence.md](https://github.com/jdilla1277/agentcad/blob/main/docs/product-plans/agentcad-performance-evidence.md)
- H-CCX: 19.4% → 29.3% requirement pass rate with multi-view feedback; zero strict passes on first attempts (search summary). — [arxiv.org/html/2605.17448v2](https://arxiv.org/html/2605.17448v2)
- text-to-cad: no quantitative evidence; one documented qualitative failure where a mesh-sampled check reported "0 interferences" three times on a model with real overlaps. — [galatea/FEEDBACK.md](https://github.com/earthtojake/text-to-cad/blob/main/models/galatea/FEEDBACK.md)

### Inferences
- Harness gains are largest on validity (near-100%) and modest on correctness; the absolute scores (0.25–0.46) show geometry correctness from drawings remains unsolved even with a loop.
- agentcad's K→L result suggests reliability fixes to the tool surface mattered about as much as workflow instructions, and that workflow text helps weaker models more than stronger ones. Single runs, no variance reported.
- The three-state verdict (pass / fail / not checked) recurs independently in text-to-cad's DFM, interference and FEA and is the clearest shared design pattern.

### Gaps
- No benchmark read covers assemblies, mechanisms or FEA requirements with public code; H-CCX's kit could not be located.
- No project publishes loop-iteration counts or cost-per-fix distributions.

---

## 5. Recommendation inputs: adopt, fork, build

### Takeaway
text-to-cad is the closest match to the team's stack (build123d, Linux, CLI + skills, MIT) and covers more of the target verifier list than anything else; the realistic choice is between running it as-is beside custom verifiers or lifting its patterns, with the dynamic-motion, assemblability and loop-control layers left for the team to build.

### Cited Findings
- Adoptable as-is under MIT: the whole plugin via `claude plugin marketplace add earthtojake/text-to-cad#latest`, giving `cad run`, `inspect`, `snapshot`, `interference`, `ranges`, `dfm`, `step solve`, `model export robot.xml`, `mujoco check`. — [docs/install.md](https://github.com/earthtojake/text-to-cad/blob/main/docs/install.md)
- Constraints on adoption: Python ≥ 3.13, build123d 0.13 / OCP 8.0 pinned; netgen wheels absent on Linux ARM; GPL-2.0 CalculiX and GPL-3.0 KiCad are invoked as separate programs; telemetry default-on; first run needs network. — [packages/cad/pyproject.toml](https://github.com/earthtojake/text-to-cad/blob/main/packages/cad/pyproject.toml), [README](https://github.com/earthtojake/text-to-cad/blob/main/README.md)
- Extension points are documented: `docs/contributing/writing-a-skill.md`, `adding-an-integration.md`, `adding-a-document-type.md`; "a new skill … goes in `skills/`". — [docs/contributing](https://github.com/earthtojake/text-to-cad/tree/main/docs/contributing)
- Independently reusable pieces: `cad-ccx` (pip-installable CalculiX 2.23 for Linux x86_64/aarch64); the step.parts API (16,000+ STEP parts, mixed CC-BY / CC-BY-SA model licences); agentcad's `diff` and review-comment model (Apache-2.0); build123d-mcp's `validate`, `verify_spec`, `design_audit` (Apache-2.0); CADGenBench's scoring engine and local `sanity_check_submission.py` (Apache-2.0). — sources as cited in sections 1 and 3

### Inferences
- **Adopt as-is (candidate):** text-to-cad's `cad` CLI and the `cad`, `fea`, `robot-simulation` skills as the base generate→inspect loop, version-pinned. Worth a spike in the team's actual sandbox first, since headless/ephemeral behaviour was not tested here.
- **Borrow as patterns rather than code:** exit-code 3 "not checked ≠ pass"; findings with `rule/value/limit/refs`; `made_by` source-line provenance; declared fits instead of inferred overlaps; check flags recorded in the model docstring; "plant a failure before trusting a check"; review part → link → joint at both travel ends → assembly; agentcad's response budgets and version diffs; build123d-mcp's parameter-perturbation audit.
- **Fork/extend candidates:** add skills to text-to-cad for the missing verifiers so they share its refs, poses and JSON conventions; agentcad if a lighter, daemon-optional CLI with built-in versioning is preferred (but it is on an older build123d).
- **Gaps the team would need to build:**
  1. A dynamic motion verifier: run MuJoCo (or similar) on the exported MJCF and return pass/fail on reach, collisions during motion, torque/force limits, stability — text-to-cad stops at compile and rest-state health.
  2. Swept/continuous interference along a motion, not only at agent-chosen poses.
  3. A closed-loop kinematic solver (four-bars, slider-cranks, parallel grippers cannot be posed or range-swept today).
  4. Assemblability: insertion directions, assembly sequence, tool/fastener access, trapped parts.
  5. FEA beyond bonded linear static: contact, bolted joints with preload, buckling, modal, fatigue; and loads derived from the motion simulation (PartCAD describes this hand-off).
  6. Tolerance and fit analysis (stack-ups, ISO fits) — only nominal geometry is checked anywhere.
  7. A requirements/spec artefact that drives which verifiers run and records verdicts (agentcad `spec.json` and PartCAD `requirements:` are the nearest models).
  8. Loop control: iteration caps, tiering of cheap vs expensive checks, stop conditions, and a "no silent feature-dropping" guard — text-to-cad leaves all of this to prose instructions.
  9. Standard-parts sourcing inside the loop (catalogue search → STEP → mass/interface metadata), since text-to-cad removed its step-parts skill.
  10. An assembly/mechanism benchmark to measure whether the loop helps; public benchmarks read here are single-part.

### Gaps
- None of the adopt/fork judgements were validated by installing or running the tools; they rest on documentation and source layout.
- Whether text-to-cad's maintainers accept external verifier skills upstream is unknown (31 open PRs, no contribution-acceptance data read).
