"""Pipeline configuration: paths, thresholds, and the model tier registry.

Every threshold here was set from a measurement over the corpus, not intuition.
The measurement that produced each one is named in its comment so a future
reader can re-derive it rather than trusting it.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from . import policy as _policy

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

def _workspace_setting(name: str) -> str | None:
    """Read one value from workspace.toml beside this package."""
    path = Path(__file__).resolve().parent.parent / "workspace.toml"
    if not path.is_file():
        return None
    try:
        with path.open("rb") as fh:
            return (tomllib.load(fh).get("workspace") or {}).get(name)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def dump_root() -> Path:
    """The trace dump this workspace works on.

    Resolution order is env var, then workspace.toml, then a clear failure --
    never a silent default. A module constant pointing at one directory is fine
    while there is one dump and wrong the moment there are two: a pipeline
    quietly indexing last month's corpus produces results that look entirely
    normal.
    """
    configured = os.environ.get("ARENA_DUMP") or _workspace_setting("dump")
    if not configured:
        raise SystemExit(
            "No trace dump configured.\n"
            "  Point this workspace at one:  ./arena dump --set /path/to/dump\n"
            "  or for a single command:      ARENA_DUMP=/path/to/dump ./arena ...")
    root = Path(configured).expanduser()
    if not (root / "sessions").is_dir():
        raise SystemExit(
            f"{root} does not look like a trace dump: no sessions/ directory.")
    return root


def sessions_root() -> Path:
    return dump_root() / "sessions"


def __getattr__(name: str) -> Path:
    """Resolve DUMP_ROOT and SESSIONS on first use (PEP 562).

    Importing this package must not require a configured dump: `arena keys`,
    `arena dump` and `arena status` have to work in a fresh workspace, and a
    module-level constant would fail the import for every command.
    """
    if name == "DUMP_ROOT":
        return dump_root()
    if name == "SESSIONS":
        return sessions_root()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
ARTIFACTS = Path(os.environ.get(
    "ARENA_PIPELINE_ARTIFACTS",
    Path(__file__).resolve().parent.parent / "pipeline-artifacts"))

# --------------------------------------------------------------------------
# Signals
# --------------------------------------------------------------------------

#: Signals excluded everywhere. `tool_hallucination`: measured 1 failure in
#: 72,398 annotations across this dump (a `pash` typo), and 0 in 12,886 in the
#: previous one. It discriminates nothing.
DEAD_SIGNALS = ("tool_hallucination",)

# --------------------------------------------------------------------------
# Model tiers
# --------------------------------------------------------------------------

#: This dump pools 72 models. A correction on a weak model is weak evidence
#: that a *task* is hard -- the model may simply be incapable of anything. Tier
#: is therefore a confidence weight on trace-derived difficulty evidence, never
#: proof of difficulty: only calibration proves that.
FRONTIER_PREFIXES = (
    "claude-opus-5", "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6",
    "claude-sonnet-5", "claude-fable-5",
    "gpt-5.6", "gpt-5.5",
    "gemini-3.5", "gemini-3.1-pro",
    "grok-4.3", "grok-4.5", "grok-4.6",
)


def tier(model_name: str | None) -> str:
    m = model_name or ""
    return "frontier" if any(m.startswith(p) for p in FRONTIER_PREFIXES) else "other"


# --------------------------------------------------------------------------
# Scope: non-coding professional knowledge work
# --------------------------------------------------------------------------

#: This programme builds NON-CODING professional knowledge-work environments:
#: finance, business, consulting, publishing, editorial, legal, medical. The
#: deliverable is a document, a register, a schedule or an analysis -- something
#: a careful reader with the same sources can check without executing anything.
#:
#: This is not a stylistic preference, it decides the whole funnel. A pipeline
#: tuned for code selects code: keyed on manifests, test files and source
#: extensions, the non-coding share of this dump's candidates collapsed to 8
#: seeds out of 102, and only one survived. The bias was in the thresholds, not
#: the corpus -- measured with a document lens the same corpus yields 20
#: doc-dominant seeds across 15 sessions.
SCOPE = "knowledge_work"

#: Extensions a professional deliverable is actually made of.
DELIVERABLE_EXT = frozenset({
    ".md", ".txt", ".csv", ".tsv", ".json", ".yaml", ".yml", ".toml", ".xml",
    ".html", ".rst", ".tex", ".jsonl", ".ini", ".cfg",
})

#: File-type inventory, not a scope verdict. Stage D must read the actual request
#: and evidence: a non-coding research workspace may also contain scripts.
CODE_EXT = frozenset({
    ".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".cs", ".java", ".dart", ".lua",
    ".luau", ".go", ".c", ".h", ".hpp", ".cpp", ".vue", ".svelte", ".rb", ".php",
    ".kt", ".swift", ".sh", ".sql", ".ipynb", ".gradle",
})

#: Legacy index screening threshold; new evidence-complete indices defer scope
#: to content classification instead of excluding by file extension/byte share.
MIN_DELIVERABLE_SHARE = 0.5

#: Session categories that signal professional knowledge work. Categories are
#: session-level in this dump, so they widen the net; the per-seed judgment is
#: the classifier's `deliverable_kind`.
KNOWLEDGE_WORK_CATEGORIES = frozenset({
    "document_creation", "data_analysis", "writing_professional",
    "research_lookup", "planning_brainstorm", "education_tutoring",
    "media_analysis", "translation", "workflow_automation",
})

#: Truth sources available without executing the agent's output. `held_out_tests`
#: and `build_or_compile` are coding truth sources and are out of scope here.
KNOWLEDGE_WORK_TRUTH = ("structural_assertion", "numeric_tolerance",
                        "register_reconciliation", "exact_contract")

# --------------------------------------------------------------------------
# File classification
# --------------------------------------------------------------------------

TEXT_EXT = frozenset({
    ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt", ".json", ".html",
    ".css", ".scss", ".rs", ".cs", ".java", ".dart", ".lua", ".luau", ".yml",
    ".yaml", ".toml", ".csv", ".sql", ".sh", ".go", ".c", ".h", ".hpp", ".cpp",
    ".xml", ".vue", ".svelte", ".rb", ".php", ".kt", ".swift", ".r", ".m",
    ".ipynb", ".tf", ".gradle", ".properties", ".ini", ".cfg", ".env",
})

BINARY_EXT = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".pptx", ".docx",
    ".xlsx", ".zip", ".mp3", ".mp4", ".wav", ".jar", ".bin", ".parquet",
    ".so", ".dll", ".exe", ".ttf", ".otf", ".ico", ".woff", ".woff2",
})

MANIFEST_NAMES = frozenset({
    "package.json", "requirements.txt", "Cargo.toml", "pyproject.toml",
    "pom.xml", "build.gradle", "go.mod", "Gemfile", "composer.json",
    "pubspec.yaml", "setup.py", "Makefile", "CMakeLists.txt", "tsconfig.json",
    "Dockerfile", "vite.config.ts", "vite.config.js", "webpack.config.js",
})

#: Tool names whose payloads carry recoverable file bodies.
#: `read_file` and `edit_file` return the WHOLE file in `output.content`;
#: `write_file` carries it in the input. Workspace manifests also carry inline
#: text and references into files/; dump.recover combines all three channels.
BODY_TOOLS_OUTPUT = ("read_file", "edit_file")
BODY_TOOLS_INPUT = ("write_file",)

# --------------------------------------------------------------------------
# Model and reasoning effort
# --------------------------------------------------------------------------

#: The AUTHORING model: the designer and the other non-measurement stages that
#: read it, so an authored result is attributable to a named model rather than
#: to whichever default a module happened to carry. It is NOT the calibration
#: model -- `claude-opus-5` is retired from calibration. Calibration models come
#: from `policy.resolve_calibration_models()`.
# v2 (2026-10-02): the newest Opus authors and classifies. It is neither
# calibration model, so the designer never builds traps against itself, and
# the semantic reviewer (gpt-6-astra) stays a different family.
ARENA_MODEL = "claude-opus-5-5"

#: Authoring reasoning effort, sent as `output_config.effort`. The API default
#: is `high`; `xhigh` sits between `high` and `max`.
#:
#: Note what this is NOT: `budget_tokens` is rejected with a 400 on this model,
#: and thinking is adaptive and ON by default -- effort is the only dial, and
#: leaving it unset is a choice of `high`, not a choice of "no thinking".
#:
#: It does NOT apply to calibration. Calibration effort is
#: `policy.SPEC_CALIBRATION_EFFORT` (`high`), reported with every rate; figures
#: taken at a different effort are not comparable.
ARENA_EFFORT = "xhigh"


# --------------------------------------------------------------------------
# Selection thresholds
# --------------------------------------------------------------------------

# HARD FLOORS -- properties we cannot author around. These kill.
#
# Everything else that used to kill is now a TIER BOUNDARY in select/priority.py.
# The distinction matters: drawing one hard line at "2+ corrections and 3+
# documents" left a surviving pool of 6 sessions -- enough for one batch and
# nothing after it -- while ranking a trace with 12 corrections and 27 retained
# files beside one with exactly 2 and 0. Floors decide admissibility; tiers
# decide order.
MIN_TURNS = 2                 # a single-turn seed cannot be multi-step
MIN_CORRECTIONS = 1           # zero pushback is no failure evidence at all
MIN_RECOVERED_PATHS = 1       # nothing to lift means no fixture
MIN_RECOVERED_BYTES = 4_000   # below this the "document" is a fragment

#: Categories that cannot carry a deterministic grader on their own. A session
#: is dropped only when its categories are a SUBSET of these -- a session that
#: also writes code is kept, and the aesthetic turns are dropped at seed level.
UNGRADABLE_ONLY = frozenset({"image_video_generation", "chitchat_meta"})

#: Replay-readiness cut. Below 0.50 the fixture stops being liftable and becomes
#: authored, which is the fidelity complaint we are trying to answer.
REPLAY_READY = 0.55

#: Component weights for the replay-readiness index. They sum to 1.0.
#:
#: Reweighted for knowledge work. The coding version scored `scaffolding` at
#: 0.12 for a package.json or a test file -- meaningless for a deliverable a
#: reader checks rather than runs, and actively harmful, because it ranked
#: repositories above document sets. In its place `structured_data` rewards the
#: registers, tables and forms a professional task is graded against: a CSV of
#: records or a JSON form is what makes a deterministic grader possible at all.
RR_WEIGHTS = {
    "breadth": 0.24,         # how many deliverable paths we can recover in full
    "volume": 0.20,          # how many bytes of them
    "versions": 0.18,        # before/after pairs -> free ground truth
    "coverage": 0.12,        # recovered paths vs what the hash-trail says changed
    "deliverable_share": 0.12,  # doc bytes vs code bytes in the same seed
    "untruncated": 0.08,     # corpus truncation is 1.27%; penalise the outliers
    "structured_data": 0.06, # registers/tables in the SOURCE; see note below
}

#: Note on `structured_data`: it was weighted 0.14 on the assumption that a
#: gradable task needs gradable source material. Measured, 19 of the 21
#: knowledge-work candidates score zero -- the traces carry prose, not registers.
#: The assumption was wrong. The output contract is something we IMPOSE (kw-006
#: turned a document-structuring session into audit.json + pagination.csv); what
#: the trace must supply is the situation, the documents and the corrections.
#: Kept at a low weight because a source register still makes grounding easier.

# --------------------------------------------------------------------------
# Calibration bands (PLAYBOOK §3)
# --------------------------------------------------------------------------

FLOOR_BAND = (0.90, 1.01)     # ~100% pass; at most 2; never gates
CORE_BAND = (0.30, 0.70)      # the only band a gate may rest on
STRETCH_BAND = (0.0, 0.30)    # <30%; at most 2; never gates
MIN_CORE_CHECKS = 4
MAX_FLOOR_CHECKS = 2
MAX_STRETCH_CHECKS = 2

# --------------------------------------------------------------------------
# Trap budget
# --------------------------------------------------------------------------

#: Hard floor. A task carrying four or fewer traps is not a hard task; it is a
#: long instruction with a couple of hazards in it. Below this the bundle is
#: refused outright.
MIN_TRAPS = 5

#: Above the floor the expectation SCALES with the trace, because a rich trace
#: can carry more without inventing anything: more documents means more surfaces
#: to hide a conflict on, more usable corrections means more real failure modes,
#: and more scored objectives means more places a trap can bite.
#:
#: Deliberately not a constant. A 3-document seed with 5 corrections and a
#: 20-document seed with 12 are not the same task, and holding both to the same
#: trap count either starves the second or forces the first to invent.
TRAP_SCALE = {"surfaces": 0.5, "corrections": 0.5, "objectives": 0.25}


def expected_traps(surfaces: int, usable_corrections: int, objectives: int) -> int:
    """Traps a bundle of this size should carry. Never below MIN_TRAPS."""
    scaled = (TRAP_SCALE["surfaces"] * surfaces
              + TRAP_SCALE["corrections"] * usable_corrections
              + TRAP_SCALE["objectives"] * objectives)
    return max(MIN_TRAPS, round(scaled))


# --------------------------------------------------------------------------
# Concurrency and rate limits: at the maximum by default
# --------------------------------------------------------------------------
# Operator decision, 2026-09-24: run at maximum. The binding capacity is the
# one Coder calibration workspace -- 20 concurrent campaigns (the QC
# template's rated 20-concurrency; operator decision 2026-09-25: one workspace,
# never a pool of several). Everything upstream is sized to keep it full; the
# provider accounts' own RPM/TPM limits remain the real ceiling, and 429s are
# retried by the transport rather than counted as results.

#: Concurrent native campaigns the workspace can hold (`coder.Settings`).
POOL_CAMPAIGNS = 20
#: Tasks screened or qualifying at once. Each runs its two model campaigns in
#: parallel.
MAX_QUALIFY_WORKERS = POOL_CAMPAIGNS // 2
#: Tasks authoring at once, sized to keep qualification fed.
MAX_TASK_WORKERS = MAX_QUALIFY_WORKERS
#: Batch-wide rollout slots for authoring-time model calls, one per pool campaign.
MAX_ROLLOUT_BUDGET = POOL_CAMPAIGNS
#: In-flight provider requests for authoring, review and classification.
MAX_PROVIDER_CONCURRENCY = POOL_CAMPAIGNS
#: Semantic reviews running at once. Each is a long-context agent rollout on
#: the reviewer model, and a resumed 40-task batch sent 13 at once and lost
#: every one to the provider's rate limit (build 2026-09-26). Reviews queue;
#: authoring, on the other provider, is not affected.
MAX_REVIEW_CONCURRENCY = 6
#: Hard stop on provider requests per process: a runaway-spend guard, not a
#: throttle. Exhausting it stops the run loudly (`ProviderBudgetExhausted`).
MAX_API_REQUESTS = 20_000


#: Batch discipline: author, validate, calibrate, review, re-fit -- then the
#: next batch. Small enough that a systemic defect costs one batch, not ten.
BATCH_SIZE = 3
ROLLOUTS_PER_STEP = 10


#: Bundle directory names. `a-001-<task-name>` is the working-tree scheme;
#: `kw-a001-` was its predecessor and still names everything built before the
#: change; `a_f2_<task-name>` is the delivered name inside `F2-scenario/` etc.
#: All are matched -- a tool that silently skipped one tree would report a clean
#: sweep over half the corpus.
BUNDLE_GLOBS = ("a-[0-9]*", "kw-a[0-9]*", "a_f[0-3]_*")


#: Bundles are grouped by category on disk, so a reader can see what kind of
#: task they are looking at without opening a ledger. The directory name is the
#: category's own word, not its letter -- `rich/` reads; `A/` does not.
#: The names are `policy.TARGET_LEVEL_DIRS`; this is an alias, never a copy.
#: Trees built before 2026-09-26 use `policy.LEGACY_CATEGORY_DIRS`
#: (rich/strong/fixture-led/thin); `orchestrate._bundle_for` still finds them.
CATEGORY_DIRS = _policy.TARGET_LEVEL_DIRS


def bundle_paths(root):
    """Every bundle under `root`, at the top level or inside a category folder.

    Both, because the two layouts coexist: everything built before the grouping
    sits flat, and a sweep that found only one of them would report a clean
    result over half the corpus.
    """
    from pathlib import Path
    root = Path(root)
    found = set()
    for pattern in BUNDLE_GLOBS:
        found.update(p for p in root.glob(pattern) if p.is_dir())
        found.update(p for p in root.glob(f"*/{pattern}") if p.is_dir())
    return sorted(found)
