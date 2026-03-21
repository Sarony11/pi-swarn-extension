# ADR 005: Catalog-Driven Smart Routing and Discovery

## Status
Accepted

## Context
When a user launches a swarm from the root workspace (`~/repos/`), the agents need to know which specific directories to focus on to complete the task. Relying on an LLM to blindly explore the disk (`ls -R`) is slow, expensive, and non-deterministic. Relying purely on explicit paths (`@domain/repo`) adds friction. We need a deterministic way to translate user intent into specific physical directories using the Backstage `resource-catalog`.

## Decision
We will implement a **Node.js Pre-processing Routing Layer** in the `swarm-orchestrator.ts` extension, adhering to the "Graceful Degradation" Triad (Root Workspace > Agent Library > Resource Catalog).

### 1. The Pre-processing Architecture
Instead of using a "Context Discovery Agent" inside CrewAI, the Pi TS extension will parse the prompt and the `resource-catalog` (if it exists) *before* spawning the Python process. It will extract a list of `focused_paths` and pass them to Python. This keeps the CrewAI swarm purely focused on cognitive engineering tasks.

### 2. Relative Path Mapping (The `workspace-path` Annotation)
While standard Backstage relies solely on remote Git URLs, Agentic Platform Engineering requires strict deterministic mapping between a catalog component and its local physical location. 

To bridge this gap without breaking Backstage standards, we will use custom annotations. Components can optionally define their relative path from the Root Workspace using the `agentic.pi/workspace-path` annotation.

Example:
```yaml
annotations:
  agentic.pi/workspace-path: "personal/marketpulse"
```

**The Node.js Resolution Flow:**
1. **Explicit Annotation:** The extension checks for `agentic.pi/workspace-path`. If found, it concatenates it with `PI_META_WORKSPACE` (e.g., `~/repos/personal/marketpulse`). This provides 100% determinism.
2. **Heuristic Fallback:** If the annotation is missing, the extension falls back to an intelligent guess based on domain/system structure (e.g., `PI_META_WORKSPACE` / `domain` / `name`).

This design also unlocks future Platform Engineering use cases, such as "One-Click Workstation Bootstrap", where a new employee could clone an entire System and the script would know exactly what folder structure to create based on these annotations.

### 3. Discovery Mode vs. `--focus`
- **Discovery Mode (Default):** If the user asks to "review the mms-engineering-platform", the TS extension will query the catalog, find the system, retrieve ALL components belonging to that system, and inject all their physical paths into the swarm's focus area.
- **Strict Mode (`--focus`):** If the user passes the `--focus` flag (e.g., `/swarm team --focus "Fix @mms/terraform"`), the extension bypasses the catalog's relation discovery. It strictly confines the swarm's attention ONLY to the explicitly mentioned `@paths`, preventing context drift.

## Consequences
- **Positive:** High determinism. Zero extra LLM tokens or latency for path discovery. Respects Backstage conventions and allows the extension to be used by any community member (graceful degradation).
- **Negative:** Requires the user's local folder structure to loosely match the catalog's naming conventions for the heuristic translation to work.
- **Architecture Impact:** The python runner (`crew_runner.py`) will accept a new argument `--focused-paths` and inject a strict boundary instruction into the agents' `backstory`.
