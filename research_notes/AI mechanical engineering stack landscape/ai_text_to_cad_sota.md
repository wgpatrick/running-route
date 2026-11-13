# AI/LLM-driven CAD generation: state of the art, 2023 to Nov 2026

Method note (read first): research was done 2026-11-13. Direct page fetches were blocked in this session (arxiv.org, docs.zoo.dev, wevolver.com all unreachable), so every finding below comes from web-search result summaries of the cited pages, not from reading the full papers. Numbers were not checked against the original tables. Where a search summary itself flagged a discrepancy, it is repeated here. Items I could only recall from background knowledge are confined to the Gaps sections and labelled "unverified".

## 1. Key papers: approaches, representations, metrics, numbers

### Takeaway
The field moved from bespoke command-sequence transformers (DeepCAD, Text2CAD, 2021-2024) to fine-tuned small LLMs/VLMs that emit CadQuery Python (CAD-Recode, cadrille, CAD-Coder, CADEvolve, 2025-2026), with RL on geometric reward and large synthetic datasets giving the biggest measured gains; on the sketch-extrude benchmarks these specialists reach roughly 85-92% IoU with under 1% invalid outputs. From 2026 the frontier is agentic generate-execute-critique loops and benchmarks that test function, manufacturability and assemblies, where scores are far lower.

### Cited Findings

Representations and metrics
- Standard reconstruction metrics are Chamfer Distance (CD), IoU and Invalidity Ratio (IR); cadrille follows CAD-Recode in normalizing ground truth and reports median CD on 8,192 points because invalid models bias the mean — [cadrille, arXiv 2505.22914](https://arxiv.org/pdf/2505.22914)
- Reported numbers for the same model differ across papers because of normalization, alignment and mean-vs-median CD; e.g. CADFit's table (which rigidly aligns and rescales predictions before scoring) gives CAD-Recode IoU 0.818 / CD 0.027 / IR 0.000 on DeepCAD and 0.761 / 0.027 / 0.003 on Fusion360, and cadrille 0.872 / 0.020 / 0.007 and 0.817 / 0.019 / 0.003 — [CADFit, arXiv 2605.01171](https://arxiv.org/pdf/2605.01171)
- The ACM Computing Surveys survey (arXiv May 2025, journal Feb 2026) finds CAD code generation is the most prominent LLM-for-CAD application and GPT-4o the most frequently used model; code generation pipelines typically include a debugger loop that refines code until it executes — [LLMs for CAD: A Survey, arXiv 2505.08137](https://arxiv.org/html/2505.08137v2)
- A 2026 critical review organizes the area by representations, LLMs and agentic design systems for "engineering-grade parametric CAD" — [Machines 14(10):1206](https://doi.org/10.3390/machines14101206)

Command-sequence era
- Text2CAD (Khan et al., NeurIPS 2024): first large-scale text-CAD dataset, built by adding descriptions to DeepCAD models; a Transformer decoder maps text to command sequences; about 660,000 annotations covering all DeepCAD samples, but descriptions are template-generated from the command sequences and lack linguistic diversity — [Text2CAD-Bench, arXiv 2605.18430](https://arxiv.org/html/2605.18430v1); [Text2CAD NeurIPS paper](https://proceedings.neurips.cc/paper_files/paper/2024/file/0e5b96f97c1813bb75f6c28532c2ecc7-Paper-Conference.pdf)
- CAD-Llama (2025): LLM adapted to parametric command sequences; reports 84.72 ACC_T vs Text2CAD's 69.91, about 14 points over CAD-Translator and Text2CAD — [CAD-Llama, arXiv 2505.04481](https://arxiv.org/pdf/2505.04481)
- CADFusion (2025): LLM backbone that alternates a sequential-learning stage with a visual-feedback stage (rendered outputs used as training signal) — [CADFusion, arXiv 2501.19054](https://arxiv.org/pdf/2501.19054)
- CADmium (2025): fine-tunes code language models for text-driven sequential CAD design — [CADmium, arXiv 2507.09792](https://arxiv.org/pdf/2507.09792)

CadQuery-code era (fine-tuned specialists)
- CAD-Recode (ICCV 2025): Qwen2-1.5B plus a lightweight point-cloud projector, outputs CadQuery Python, trained on 1M procedurally generated CAD sequences — [CAD-Recode, arXiv 2412.14042](https://arxiv.org/pdf/2412.14042)
- CAD-Recode claims 10x lower mean CD than prior SOTA on DeepCAD and Fusion360: mean CD 3.43 to 0.30 and IoU 77.6% to 92.0% vs CAD-SIGNet; a summary gives DeepCAD IoU 92.0% / median CD 0.16 and Fusion360 IoU 87.8% / median CD 0.15; invalidity below 1% on DeepCAD, Fusion360 and real-world CC3D — [CAD-Recode ICCV paper](https://openaccess.thecvf.com/content/ICCV2025/papers/Rukhovich_CAD-Recode_Reverse_Engineering_CAD_Code_from_Point_Clouds_ICCV_2025_paper.pdf); [HF paper page](https://huggingface.co/papers/2412.14042)
- Most of CAD-Recode's gain comes from synthetic data: the same model trained on only the 160k DeepCAD subset gets CD 0.89 / IoU 86.2 on DeepCAD. arXiv v1 reports different numbers (e.g. CD 4.76), so the version cited matters — [CAD-Recode, arXiv 2412.14042](https://arxiv.org/pdf/2412.14042)
- cadrille (2025): one VLM handling point cloud, multi-view image and text inputs, CadQuery output, supervised fine-tuning then RL; online RL (Dr. CPPO) beats offline DPO across metrics and datasets — [cadrille on alphaXiv](https://www.alphaxiv.org/abs/2505.22914v2)
- cadrille RL results: image-input IoU up 3-6 points over SFT to 90.2% on DeepCAD and 85.0% on Fusion360; CC3D CD from 0.81 to 0.57; invalidity 0.0% on DeepCAD/Fusion360 images and 0.1-0.2% on CC3D; under cadrille's protocol CAD-Recode scores CD 0.18 / IoU 87.1 on DeepCAD — [cadrille review](https://liner.com/review/cadrille-multimodal-cad-reconstruction-with-reinforcement-learning); [cadrille, arXiv 2505.22914](https://arxiv.org/html/2505.22914)
- CAD-Coder (NeurIPS 2025): text to CadQuery with chain-of-thought and GRPO using a CAD-specific reward that includes a Chamfer-distance geometric term — [CAD-Coder NeurIPS paper](https://proceedings.neurips.cc/paper_files/paper/2025/file/564a224e88f2490f3c1deaae877d37e3-Paper-Conference.pdf)
- Text-to-CadQuery (Xie and Ju, 2025): fine-tuning LLMs on 170K text-CadQuery pairs gives consistent improvement with model scale — [Text2CAD-Bench, arXiv 2605.18430](https://arxiv.org/html/2605.18430v1)
- CADEvolve (Feb 2026): starts from 46 hand-written CadQuery primitives; a VLM edits and extends them into 8k complex parametric generators, augmented to about 1.3M scripts with renders (tiers G/P/C); described as the first open CAD sequence dataset covering the full CadQuery operator set with multi-operation histories. Fine-tuned VLM CADEvolve-M claims SOTA Image2CAD on DeepCAD, Fusion 360 and MCB; code, data and model released — [CADEvolve, arXiv 2602.16317](https://arxiv.org/abs/2602.16317)
- Zero-to-CAD (Apr 2026): agentic synthesis of interpretable CAD programs at million scale without real data — [arXiv 2604.24479](https://arxiv.org/pdf/2604.24479)
- Pointer-CAD (Mar 2026): unifies B-rep and command sequences with pointer-based edge and face selection (targets operations such as fillet/chamfer that must reference existing topology) — [arXiv 2603.04337](https://arxiv.org/pdf/2603.04337)
- UniCAD (Jun 2026): unified benchmark and universal model for multi-modal, multi-task CAD — [arXiv 2606.05058](https://arxiv.org/pdf/2606.05058)

Prompted general-purpose models with verification loops
- CADCodeVerify ("Generating CAD Code with Vision-Language Models for 3D Designs", ICLR 2025): a VLM generates and answers validation questions about rendered output and feeds corrections back; with GPT-4 it reports a 7.30% reduction in point-cloud distance and a 5.5% compile-rate gain over prior work (another listing says 5.0% success-rate gain). A secondary summary says removing few-shot examples raised point-cloud distance from 0.126 to 0.141 — [arXiv 2410.05340](https://arxiv.org/html/2410.05340v2); [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/file/81a934cd364e18ea6fdeaf57a93c17d4-Paper-Conference.pdf)

Agentic systems (2026)
- CADSmith (CMU, Mar 2026): multi-agent generation combining OpenCASCADE kernel measurements with VLM judgment of multi-view renders; authors report visual context mattered most for complex parts — [CADSmith on alphaXiv](https://www.alphaxiv.org/abs/2603.26512v1)
- IterCAD (Jun 2026): multimodal agent that checks generated code against a reference engineering drawing in a sandbox and revises; feedback goes beyond compiler/runtime errors — [IterCAD on alphaXiv](https://www.alphaxiv.org/abs/2606.13368)
- RA-CAD (Aug 2026): generate-execute-critique-rewrite loop where the critique step is trained by RL against terminal CAD-quality reward instead of external visual reviewers — [arXiv 2608.05714](https://arxiv.org/pdf/2608.05714)
- TraceCAD (Aug 2026): repair across attempts by tying failure evidence to specific modeling steps — [arXiv 2608.03062](https://arxiv.org/pdf/2608.03062)
- CADIR (Aug 2026): cross-backend editable intermediate representation for agentic CAD — [arXiv 2608.00891](https://arxiv.org/pdf/2608.00891)
- Self-improving CAD agents with FEA feedback (May 2026): blueprint stage, rich-view visual inspection and finite-element feedback, up to 10 revision attempts — [arXiv 2605.17448](https://arxiv.org/pdf/2605.17448)
- Physics-in-the-Loop (IJCAI 2026): VLM generate-simulate-refine loop, ablating visual-only vs physics feedback — [IJCAI 2026](https://ijcai.org/proceedings/2026/714)
- AssemCAD (Jul 2026): generates executable assemblies with valid structure and articulated joints from text — [arXiv 2607.05123](https://arxiv.org/html/2607.05123v1)
- CADENA (Aug 2026): stepwise CAD reverse engineering; CADFit (May 2026): mesh-to-CAD program generation with hybrid optimization — [CADENA](https://arxiv.org/pdf/2608.00799); [CADFit](https://arxiv.org/pdf/2605.01171)

### Inferences
- CadQuery (and build123d in practitioner tooling) has become the de facto output language: it is executable, STEP-exportable, in-distribution for LLMs, and gives a free validity check via the OpenCASCADE kernel.
- The two levers with the clearest measured effect are (a) scale and diversity of synthetic training programs (CAD-Recode: IoU 86.2 to 92.0 from data alone) and (b) RL on execution-based geometric reward (cadrille, CAD-Coder), which mainly drives invalidity toward zero.
- Near-saturated numbers on DeepCAD/Fusion360 say little about real parts; see sections 2 and 3.
- Cross-paper number comparison is unsafe. A team should re-run baselines under one protocol.

### Gaps
- Not verified this session (no source retrieved): DeepCAD (ICCV 2021) and SkexGen (ICML 2022) original numbers; CAD-GPT (AAAI 2025); CAD-MLLM; FlexCAD (ICLR 2025); GenCAD; Img2CAD; LLM4CAD; Query2CAD; 3D-PreMise; BlenderLLM; CAD-Assistant. Unverified background recollection: these span command-sequence autoregressive/diffusion models (DeepCAD, SkexGen, GenCAD), fine-tuned LLMs for controllable sequence infill/editing (FlexCAD), multimodal LLMs (CAD-GPT, CAD-MLLM), GPT-4-class prompting with self-refinement (Query2CAD, 3D-PreMise, LLM4CAD), Blender-script generation (BlenderLLM, mesh-oriented), and a tool-augmented VLLM planner over FreeCAD (CAD-Assistant). The report writer should not cite numbers for these from this note.
- A separate MIT "CAD-Coder" (image to CadQuery VLM, GenCAD-Code dataset) exists by recollection, but the search found no source tying the name to MIT or to a 163k dataset; the NeurIPS 2025 CAD-Coder cited above is the text-to-CadQuery GRPO paper. Name collision should be flagged.
- Exact cadrille, CADEvolve-M and CADCodeVerify per-setting tables could not be read; only headline figures are given.
- B-rep direct generation (BrepGen, HoLa-BRep and successors): no findings retrieved.

## 2. Datasets and benchmarks, and their limitations

### Takeaway
The legacy training corpora are small-vocabulary: DeepCAD and Fusion 360 Gallery are sketch-and-extrude only and ABC has no construction history. 2026 brought a wave of benchmarks (BenchCAD, Text2CAD-Bench, MUSE, RealCADBench, CADEngBench, P3D-Bench, CADBench, EngDesign) that add industrial part families, edits, assemblies, manufacturability and simulation, and they show large headroom.

### Cited Findings

Legacy datasets
- DeepCAD: sketch and extrude operations only; size cited variously as 176,017 or 178,238 models, and its ~178k sequences reduce to 114,985 after deduplication — [Text2CAD-Bench, arXiv 2605.18430](https://arxiv.org/html/2605.18430v1); [CADmium, arXiv 2507.09792](https://arxiv.org/pdf/2507.09792)
- Fusion 360 Gallery: 8,625 human design sequences, limited to sketch-and-extrude — [Text2CAD-Bench, arXiv 2605.18430](https://arxiv.org/html/2605.18430v1)
- ABC: about one million CAD models with parametric surfaces but no construction sequences — [Text2CAD-Bench, arXiv 2605.18430](https://arxiv.org/html/2605.18430v1)
- SketchGraphs: millions of sketch-and-constraint graphs, but no 3D solid modeling operations — [Text2CAD-Bench, arXiv 2605.18430](https://arxiv.org/html/2605.18430v1)
- Text2CAD: ~660k template-generated annotations on DeepCAD, so it inherits DeepCAD's geometry limits and has low linguistic diversity — [Text2CAD-Bench, arXiv 2605.18430](https://arxiv.org/html/2605.18430v1)
- CADPrompt (2024): 200 objects, each with a natural-language prompt and expert-written Python CAD code; described by its authors as the first benchmark for CAD code generation — [arXiv 2410.05340](https://arxiv.org/html/2410.05340v2)
- CAD-Recode dataset: 1M procedurally generated CadQuery programs — [arXiv 2412.14042](https://arxiv.org/pdf/2412.14042)
- CADEvolve-3L: 8k generators, ~1.3M scripts, full CadQuery operator set, single parts only (no assemblies mentioned) — [arXiv 2602.16317](https://arxiv.org/abs/2602.16317)

2026 benchmarks
- BenchCAD (May 2026): 17,900 execution-verified CadQuery programs across 106 industrial part families; tests visual recognition, CAD-operation understanding, parametric abstraction, spatial-code reasoning, plus an edit track — [BenchCAD, arXiv 2605.10865](https://arxiv.org/pdf/2605.10865)
- CADBench (May 2026): 18,000 evaluation samples in six families derived from DeepCAD, Fusion 360, ABC, MCB and Objaverse — [CADBENCH, arXiv 2605.10873](https://arxiv.org/pdf/2605.10873)
- Text2CAD-Bench (May 2026): 600 human-verified instances; explicitly does not cover sheet metal, multi-part assemblies, or parametric families with complex constraints, and its VLM-based scoring is limited for internal structures, precise dimensions and inter-part relationships — [arXiv 2605.18430](https://arxiv.org/html/2605.18430v1); [HF dataset](https://huggingface.co/datasets/AICAD/Text2CAD-Bench)
- MUSE (May 2026): benchmarks manufacturable, functional and assemblable text-to-CAD; notes prior benchmarks do not represent industrial products with joint relations and assembly constraints, and that scarcity of annotated complex-assembly data is a major bottleneck — [MUSE, arXiv 2605.28579](https://arxiv.org/html/2605.28579v1)
- P3D-Bench (Jun 2026): evaluates MLLMs and text-only LLMs producing CadQuery, OpenSCAD, JSON and Three.js; full assemblies are substantially harder than single parts because spatial relations must be right — [arXiv 2606.11152](https://arxiv.org/html/2606.11152v2)
- CADEngBench (Aug 2026): "It looks like CAD, but does it work?" Evaluates parametric design, assembly reasoning and physics simulation — [arXiv 2608.09296](https://arxiv.org/pdf/2608.09296)
- RealCADBench (Sep 2026): parametric CAD modeling from industrial design intents, with Part and Assembly tracks — [arXiv 2609.03773](https://arxiv.org/html/2609.03773v1); [GitHub](https://github.com/joyindustrial/RealCADBench)
- EngDesign (NeurIPS 2025 Datasets and Benchmarks): 101 design tasks across 9 engineering domains (incl. mechanical, structural, control, analog/digital hardware), 473 gradable items; simulation-based evaluation with iterative feedback; 34 tasks need tools such as MATLAB or Cadence. A third-party summary lists GPT-4o at 15.7 overall pass rate — [EngDesign, arXiv 2509.16204](https://arxiv.org/html/2509.16204v2); [NeurIPS page](https://papers.neurips.cc/paper_files/paper/2025/hash/664f777548205fb6e0cbb0965e8d2e16-Abstract-Datasets_and_Benchmarks_Track.html)

### Inferences
- Anything trained or evaluated only on DeepCAD/Fusion360/Text2CAD has not been tested on fillets, chamfers, revolves, sweeps, lofts, shells, patterns, holes with standards, sheet metal or assemblies.
- The synthetic-program datasets (CAD-Recode, CADEvolve, Zero-to-CAD) widen operator coverage but are still single-part and carry no functional requirements, tolerances or manufacturing context.
- For a product team, MUSE, RealCADBench and CADEngBench are the most decision-relevant public evals; BenchCAD is the best public test of operator coverage.

### Gaps
- No verified details retrieved for Omni-CAD (CAD-MLLM), MCB (Mechanical Components Benchmark) internals, or a benchmark named "MechBench". Unverified recollection: Omni-CAD is roughly 450k multimodal instances; MCB is a mesh classification set of mechanical parts used here as an out-of-distribution geometry target.
- SketchGraphs' exact size (commonly quoted as 15M sketches) was not confirmed by the search.
- No FEA-specific LLM benchmark was found beyond CADEngBench's simulation track and the FEA-in-the-loop agent papers.
- EngDesign scores for 2026 frontier models were not retrieved.

## 3. Frontier general-purpose LLMs vs fine-tuned specialists; spatial reasoning and visual feedback

### Takeaway
Zero-shot frontier models write executable CAD code most of the time (execution rate ~0.93 for the best) but geometric fidelity and engineering correctness are mediocre: best solid IoU ~0.43 on RealCADBench parts, ~0.40 best total on BenchCAD at release, and 19-21% on MUSE's fine-grained functional/manufacturable/assemblable criteria in the paper. Fine-tuned specialists win on in-distribution reconstruction but under-cover real operations; tools and feedback loops raise frontier scores markedly, and no single vendor leads across capabilities.

### Cited Findings
- BenchCAD, paper-era (May 2026): best frontier total ~0.397 (Gemini 3.1 Pro with thinking); Claude Opus 4.7 ~0.383 without thinking and 0.378 with thinking. The specialist CADEvolve v3 reaches 0.6014 but with weak essential-operation coverage (0.3715) — [BenchCAD, arXiv 2605.10865](https://arxiv.org/pdf/2605.10865)
- BenchCAD operation recall: GPT-5.3 has 25.2% macro recall on advanced operations, near zero on chamfer, revolve, fillet, cboreHole and shell; models replace sweeps, lofts and twist-extrudes with plain sketch-and-extrude — [BenchCAD, arXiv 2605.10865](https://arxiv.org/html/2605.10865v1)
- BenchCAD modality gap: giving the model CadQuery code instead of images lifts scores a lot (best Code QA ~0.838 vs Gemini's 0.587 on Vision QA). On BenchCAD-Edit, GPT-5.3 thinking 0.865, Opus 4.7 thinking 0.853, Gemini 3.1 Pro thinking 0.837 — [BenchCAD, arXiv 2605.10865](https://arxiv.org/pdf/2605.10865)
- Later third-party leaderboard rows (not comparable to the paper; different subsets, resolutions and harnesses): Claude Opus 5.5 at 0.730 total on a 1,000-file subset at 256 px; Opus 5 at 0.497, and a separate Opus 5 row at voxel IoU 0.821 with tools — [Klu.ai BenchCAD](https://klu.ai/benchmarks/benchcad); [benchmarklist.com](https://benchmarklist.com/benchmarks/benchcad/). These aggregator pages also show GPT-5.3 totals (~0.21-0.22) that conflict with the paper, so treat them as low-reliability.
- RealCADBench Part Track (Sep 2026): Gemini 3.1 Pro Preview top regime-balanced PA 0.5507 and highest solid IoU 0.4291; GPT-5.5 PA 0.5478, execution rate 0.9311, IoU 0.3829, Judge 73.79; Claude Opus 4.8 PA 0.5316, Judge 68.31. Assembly Track: GPT-5.5 top Judge 76.33, Claude Opus 4.8 lowest of four at 60.24 — [RealCADBench, arXiv 2609.03773](https://arxiv.org/html/2609.03773v1)
- MUSE: paper reports the best closed-source models at only ~19-21% on functionality, manufacturability and assemblability, open-source models at 3-4%; executable code often still yields invalid assemblies — [MUSE, arXiv 2605.28579](https://arxiv.org/html/2605.28579v1). A later self-reported leaderboard lists GPT-5.5 at 67.14 Final Score, Gemini 3.1 Pro 53.93, Claude Opus 4.7 53.46 (Opus 4.7 has 76.42% sandbox success but lower geometry/functionality), with fine-grained engineering criteria around 50-55% for the best model — [benchmarklist MUSE](https://benchmarklist.com/benchmarks/muse_benchmarking_manufacturable_functional_and_assemblable_text_to_cad_generation/). The two sets of figures use different aggregates/model generations and should not be merged.
- CADEngBench (Aug 2026): Gemini leads engineering-requirement satisfaction, functional editing, matched FEA and assembly retrieval; Claude leads executability, parametric behavior and L3 simulation reach; differences are not statistically separable (Holm-corrected McNemar); capabilities are only weakly correlated, so no single score describes a model. Executable code can violate design intent, parameter families can diverge from reference structural response, and plausible assembly predictions can miss the recorded mate — [CADEngBench, arXiv 2608.09296](https://arxiv.org/pdf/2608.09296)
- Text2CAD-Bench: compares GPT-5.2 and Claude 4.5 Sonnet; Claude has the lowest CD on the hardest L3-Geo tier (70.13 vs 93.46) but trails on simpler tiers; the HF leaderboard ranks GPT-5.2 ahead overall — [arXiv 2605.18430](https://arxiv.org/html/2605.18430v1)
- P3D-Bench: assemblies are much harder than parts for all MLLMs because of spatial-relation errors — [arXiv 2606.11152](https://arxiv.org/html/2606.11152v2)
- Visual and kernel feedback: CADCodeVerify's render-and-question loop gave GPT-4 a 7.30% point-cloud-distance reduction and ~5.5% compile-rate gain — [arXiv 2410.05340](https://arxiv.org/html/2410.05340v2). CADSmith pairs exact kernel measurements with multi-view renders and finds visual context matters most on complex parts — [CADSmith](https://www.alphaxiv.org/abs/2603.26512v1). AssemCAD argues visual perception gives limited guidance for assembly-level reasoning and that Chamfer distance is unreliable for assemblies — [AssemCAD, arXiv 2607.05123](https://arxiv.org/html/2607.05123v1)
- Practitioner tooling: earthtojake/text-to-cad is an MIT-licensed plugin for Claude Code, Codex, Cursor, Gemini and Grok in which the agent writes build123d on OpenCASCADE and exports STEP/STL/3MF/GLB, with drawings, manufacturability checks and a skill for finding off-the-shelf STEP parts; a blog post cites ~9.3k GitHub stars (unconfirmed) — [devpik overview](https://www.devpik.com/open-source/text-to-cad); [andrew.ooo review](https://andrew.ooo/posts/text-to-cad-review-agent-cad-plugin/); [aomway post](https://www.aomway.com/post/2404.html). The same post says tolerance fit, assembly verification and manufacturability assessment remain the user's job (anecdotal).

### Inferences
- Compile/execution rate is solved enough to stop being a differentiator; the binding constraint is whether geometry matches intent and whether the right operations are used.
- Frontier models edit existing CAD code far better (~0.85) than they create from images (~0.4). Products built around code-in-context editing and parametric changes are on firmer ground than image-to-CAD from scratch.
- The jump on BenchCAD leaderboards from ~0.4 (mid-2026 models, bare) to 0.73-0.82 (later Opus models, some with tools) suggests harness plus model generation matter more than fine-tuning for general parts, but these rows are not controlled comparisons.
- Feedback should combine deterministic kernel queries (volumes, bounding boxes, face counts, interference, mass properties) with renders; renders alone are weak for dimensions and for assemblies.
- Vendor ranking flips by benchmark and by capability; a team should stay model-agnostic and keep its own eval set.

### Gaps
- No controlled study found that takes one 2026 frontier model and measures bare vs render-loop vs kernel-tool-loop on the same benchmark; the with-tools leaderboard rows are suggestive only.
- No retrieved head-to-head of a fine-tuned specialist vs frontier models on MUSE/RealCADBench/CADEngBench.
- Per-model P3D-Bench numbers and the full BenchCAD table (Appendix G / Table 10) were not readable.
- No fine-tuning-on-BenchCAD results found.

## 4. Commercial landscape

### Takeaway
Shipping products fall into four groups: code-CAD agents (Zoo/Zookeeper, Adam, open-source Claude Code plugins), learned B-rep generators (Spectral Labs SGS-1, Autodesk neural CAD, Backflip scan-to-CAD), incumbent assistants that are mostly Q&A or command automation (Autodesk Assistant, Onshape AI Advisor, SOLIDWORKS AURA/LEO), and adjacent engineering copilots (Leo AI). Verified funding in this pass is modest (Backflip $30M, Adam $4.1M, Leo AI $9.7M total, Mach9 $34M); many named companies could not be verified.

### Cited Findings

Startups
- Zoo (formerly KittyCAD): Zookeeper is a conversational CAD agent built into Zoo Design Studio, shipped January 2026 with Design Studio v1.1; the same CAD tools are exposed via a Zoo MCP server so other agents can drive them; Zoo's CAD language is KCL (KCL 3.0 announced) — [Zoo docs: Zookeeper](https://docs.zoo.dev/research/zookeeper); [Digital Engineering 24/7](https://www.digitalengineering247.com/article/zoo-introduces-zookeeper-agent-for-cad-design/products); [Zoo blog](https://zoo.dev/blog)
- Zoo pricing: Text-to-CAD API bills per second at $0.50/min ($0.0083/s extra usage); failed calls are not charged; free allowance was 40 min/month, now 20 min ($10 balance). An October 2026 third-party check lists Free $0 / 20 min, Plus $20/month ~400 min, Pro $99/month 2,500 min; modeling in Design Studio is unlimited while Zookeeper reasoning time and API usage are metered — [Zoo billing post](https://zoo.dev/blog/turning-on-billing-for-text-to-cad); [Zoo ML API](https://zoo.dev/machine-learning-api); [llms.blog roundup](https://www.llms.blog/posts/best-ai-cad-tools)
- Adam (adam.new, YC W25): $4.1M seed led by TQ Ventures with 468 Capital, Pioneer and Script Capital; moving from consumer text-to-3D to an AI copilot for professional CAD; open-source CADAM repo ~3,500 GitHub stars by late May 2026; paid tiers about $5.99 and $17.99/month per one review — [Apollo Technical roundup](https://www.apollotechnical.com/ai-cad-tools/); [AdamCAD review](https://pasqualepillitteri.it/en/news/3372/adamcad-text-to-cad-ai-review-2026)
- Backflip AI: founded by Markforged founders; $30M Series A co-led by NEA and a16z (Dec 2024); launched a CAD copilot turning 3D scans into editable models; one source claims digitizing a part drops from ~$1,500 to $10 — [TechCrunch](https://techcrunch.com/2024/12/19/backed-by-a16z-and-nea-backflip-raises-30m-series-a-to-turn-text-into-ai-generated-designs/); [VoxelMatters](https://www.voxelmatters.com/backflip-ai-launches-cad-copilot-that-turns-3d-scans-into-editable-models/)
- Spectral Labs SGS-1 (announced Sept 2025): pitched as a foundation model for structured CAD; takes an image or 3D mesh and outputs B-rep parts in STEP; demoed inside Fusion 360 with a plug-in; cannot create full assemblies in one shot — [Spectral Labs: Introducing SGS-1](https://www.spectrallabs.ai/research/SGS-1); [Spectral Labs on X](https://x.com/spectral_hq/status/1967642998646411418); [WorldCAD Access](https://upfrontezine.substack.com/p/whats-new-in-cad-bcc)
- Leo AI: engineering assistant for mechanical engineers that reads CAD, PDM and standards; $5M seed led by Flint Capital, $9.7M total — [Apollo Technical roundup](https://www.apollotechnical.com/ai-cad-tools/)
- Vendor-blog characterization (Leo AI, commercially interested): Zoo generates geometry for concept exploration, Adam produces parametric code for script workflows, SGS-1 pushes native B-rep but "is still early" — [Leo AI comparison](https://www.getleo.ai/blog/text-to-cad-tools-comparison-guide)
- Mach9: dropped "Robotics" and pivoted to AI CAD software; $34M Series A co-led by First Round and Bessemer (TechCrunch, 2026-10-21) — [TechCrunch](https://techcrunch.com/2026/10/21/mach9-raises-34m-after-pivoting-to-ai-cad-software/)
- Adjacent: CADDi (manufacturing drawing/data AI) valued at $1.2B after a $114M Series D (Sept 2026); Vizcom (industrial-design rendering) $27M Series B — [Fortune](https://fortune.com/2026/09/15/caddi-manufacturing-startup-valuation-funding-round-series-d-exclusive/); [Apollo Technical roundup](https://www.apollotechnical.com/ai-cad-tools/)
- Independent hands-on test of seven text-to-CAD tools exists (Wevolver) — [Wevolver](https://www.wevolver.com/article/we-tested-7-text-to-cad-tools-are-they-actually-useful-for-engineers) (content not readable this session)

Incumbents
- Autodesk neural CAD: introduced at AU 2025 as a foundation model that reasons about geometry and generates editable B-rep from text, sketches and images for refinement in Fusion; Autodesk says it cannot yet guarantee precision and pairs it with deterministic parametric engines; AutoConstrain is the named early Fusion feature; customer fine-tuning on own data floated — [DEVELOP3D](https://develop3d.com/cad/autodesks-ai-blueprint-for-cad/); [Digital Engineering 24/7](https://www.digitalengineering247.com/article/autodesk-to-release-3d-generative-ai-foundation-models-for-autodesk-fusion-forma/cad); [Autodesk neural technology](https://www.autodesk.com/solutions/autodesk-ai/neural-technology)
- Autodesk Assistant: reported generally available to all Fusion users at AU 2026 and live in Inventor, Moldflow and Vault; the expanded "next-generation" assistant is not GA, with rollout, terms and regions to be announced in 2027; Fusion's assistant has prompt-to-API capability reaching most Fusion functionality; from 2026-10-13 Fusion subscriptions include a monthly Flex Token quota (beta) for agentic tasks per a third-party roundup — [Fusion blog](https://www.autodesk.com/products/fusion-360/blog/changes-to-autodesk-assistant-in-autodesk-fusion-beginning-october-6th/); [DailyCADCAM](https://dailycadcam.com/autodesk-previews-next-gen-ai-assistant-in-its-fusion-forma-flow-industry-clouds-at-au2026/); [All3DP](https://all3dp.com/6/autodesk-announces-the-ai-future-of-fusion-emphasis-on-future/); [llms.blog](https://www.llms.blog/posts/best-ai-cad-tools)
- PTC Onshape AI Advisor: in-product design guidance and troubleshooting (Creo AI Assistant in beta at the time); a 2026 comparison table says it is built in since 2025 and does not act on the open model, with no drawing or macro features — [ABI Research](https://www.abiresearch.com/market-research/insight/7787074-ai-is-reshaping-cad-but-suppliers-must-be-); [MecAgent comparison](https://mecagent.com/blog/ai-cad-tools-2026) (vendor blog)
- Dassault SOLIDWORKS: AURA assistant reported GA with SOLIDWORKS 2026 after beta; a comparison table describes the assistant (LEO) in SOLIDWORKS Design 2026 on 3DEXPERIENCE, with drawing creation and macro generation in Early Access and a cloud-services named-user licence required — [ABI Research](https://www.abiresearch.com/market-research/insight/7787074-ai-is-reshaping-cad-but-suppliers-must-be-); [MecAgent comparison](https://mecagent.com/blog/ai-cad-tools-2026)
- Analyst view: most CAD AI is assistive, copilots are table stakes across major vendors, and Autodesk's neural CAD is the distinct bet on generative geometry — [ABI Research](https://www.abiresearch.com/market-research/insight/7787074-ai-is-reshaping-cad-but-suppliers-must-be-)

### Inferences
- GA today: Zoo Text-to-CAD API and Zookeeper, Adam, Backflip scan-to-CAD, incumbent chat assistants. Demo or limited: Autodesk neural CAD generation in Fusion, Autodesk next-gen assistant (2027), SGS-1 (early, no one-shot assemblies).
- Zoo is the only verified vendor with public metered API pricing and an MCP server, making it the most buildable-on commercial stack; the open-source build123d/CadQuery plus coding-agent route is the zero-licence alternative.
- Incumbents hold the distribution and the kernel/feature tree; their assistants are opening tool/API access to agents (Fusion prompt-to-API, Flex Tokens), which may make "agent that drives the incumbent CAD" more viable than a new CAD system.
- Much of the comparative coverage is vendor-authored (Leo AI, MecAgent), so competitive characterizations are biased.

### Gaps
- No verified information retrieved for: Hanomi, Dirac, DraftAid, Foundation EGI, Hestus, Trace, Siemens NX/Design Copilot, nTop, PhysicsX, Autodesk Project Bernini, CADGPT-style plugins, Quilter-style mechanical analogues, Tripo/Meshy. Unverified recollection: Hestus makes a sketch-constraint helper add-in for Fusion; DraftAid automates 2D drawings from 3D models; Dirac makes assembly work instructions; Foundation EGI is an MIT spin-out on engineering general intelligence; nTop and PhysicsX are implicit-modeling and physics-surrogate companies rather than CAD generators; Project Bernini was Autodesk's 2024 research text/image-to-3D-shape model; Tripo and Meshy output meshes, not B-rep.
- Zoo's funding and Spectral Labs' funding were not confirmed (a LinkedIn snippet mentioning $40M across seed and Series A did not name the company).
- Adam's seed date and its Onshape integration were not confirmed from a primary source; pricing came from a single multi-language review site.
- Wevolver's hands-on verdicts could not be read.
- No independent accuracy benchmarks of commercial tools (Zoo, Adam, SGS-1, neural CAD) on public benchmarks were found.

## 5. Widely acknowledged open problems

### Takeaway
The consistent message of 2026 work is that executable, plausible-looking CAD is not the same as correct CAD: assemblies, design intent, functional and manufacturable correctness, and evaluation itself are open, while tolerances/GD&T are barely addressed in the literature at all.

### Cited Findings
- Assemblies: full assemblies are substantially harder than parts for MLLMs — [P3D-Bench](https://arxiv.org/html/2606.11152v2); executable code often produces invalid assemblies and annotated assembly data is scarce — [MUSE](https://arxiv.org/html/2605.28579v1); Claude Opus 4.8 and others score lower on RealCADBench's Assembly Track judge metric than GPT-5.5 (60.24 vs 76.33) — [RealCADBench](https://arxiv.org/html/2609.03773v1); SGS-1 cannot do one-shot assemblies — [Spectral Labs](https://www.spectrallabs.ai/research/SGS-1)
- Functional and manufacturable correctness: best closed models ~19-21% on MUSE's functionality/manufacturability/assemblability at paper time — [MUSE](https://arxiv.org/html/2605.28579v1)
- Design intent and parametric behavior: executable code can violate design intent, and generated parameter families diverge from reference structural response — [CADEngBench](https://arxiv.org/pdf/2608.09296)
- Operation coverage: near-zero recall on fillet, chamfer, revolve, shell and counterbore holes for GPT-5.3; sweeps and lofts collapsed to extrudes; even the best specialist has weak essential-op coverage — [BenchCAD](https://arxiv.org/html/2605.10865v1)
- Training data: DeepCAD/Fusion 360 are sketch-extrude only, ABC has no history, Text2CAD text is templated — [Text2CAD-Bench](https://arxiv.org/html/2605.18430v1)
- Evaluation: Chamfer distance is unreliable for assemblies and renders give limited assembly guidance — [AssemCAD](https://arxiv.org/html/2607.05123v1); VLM judges cannot assess internal structure, precise dimensions or inter-part relations — [Text2CAD-Bench](https://arxiv.org/html/2605.18430v1); reported numbers vary with normalization and mean-vs-median CD — [cadrille](https://arxiv.org/pdf/2505.22914); capabilities are weakly correlated so single scores mislead — [CADEngBench](https://arxiv.org/pdf/2608.09296)
- Precision: Autodesk states neural CAD cannot yet guarantee perfect precision and must be paired with deterministic parametric engines — [DEVELOP3D](https://develop3d.com/cad/autodesks-ai-blueprint-for-cad/)
- Uncovered domains: sheet metal, multi-part assemblies and constrained parametric families are out of scope for Text2CAD-Bench — [Text2CAD-Bench](https://arxiv.org/html/2605.18430v1)
- Tolerances/fits: practitioner report that tolerance fit, assembly verification and manufacturability remain manual with coding-agent CAD (anecdotal blog) — [aomway](https://www.aomway.com/post/2404.html)

### Inferences
- Topological references are a structural weakness of code-CAD: fillets, chamfers and shells need stable selection of edges and faces, which is exactly where recall is near zero and where Pointer-CAD-style work is aimed.
- Geometry-similarity metrics reward looking right. Useful internal evals need executable checks: mass properties, interference, mate/DOF checks, hole and thread standards, DFM rules, and FEA against load cases.
- The least crowded areas with clear demand are GD&T/tolerance stack-up, drawings, sketch constraints and editability of the resulting feature tree, and assembly mates; public research on them is thin.
- Code-CAD output (CadQuery/build123d/KCL) exports STEP but loses the native feature tree in SolidWorks/Fusion/Onshape; round-tripping to incumbent parametric history is unsolved in the retrieved sources.

### Gaps
- No research found on GD&T or tolerance-aware generation, nor on complex freeform (Class-A) surfacing; absence here is from limited search, though it matches the lack of mentions in the benchmark papers.
- No quantitative study found on editability or feature-tree quality of generated models as judged by practising engineers.
- No data on sketch-constraint inference quality (AutoConstrain, Hestus-type tools).
