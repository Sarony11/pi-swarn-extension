# ADR 002: Multi-Repo Smart Routing for Swarms

## Status
Accepted

## Context
When opening the Pi terminal at the meta-workspace level (`~/repos/`), the agent's current working directory (`cwd`) is static and lacks specific project context. Furthermore, platform engineering tasks frequently span multiple repositories (e.g., touching `mms/code` for features, `mms/terraform` for infrastructure, and `mms/gitops` for deployment). 

Relying solely on the `cwd` or forcing the user to manually pass absolute paths is friction-heavy and doesn't scale for complex multi-repo operations.

## Decision
We will implement a **Hybrid Smart Routing System** in the Pi Swarm Orchestrator Extension, combining explicit syntax parsing with LLM-based heuristic fallback.

### 1. Explicit Fast-Track (The `@` Syntax)
Users can explicitly target repositories using the `@domain/repository` syntax within their prompt.
- **Example**: `/swarm "Add auth module to @personal/marketpulse and update @personal/infra"`
- **Mechanism**: The Node.js extension parses the prompt using Regex (`/@([\w-]+\/[\w-]+)/g`), resolves the absolute paths, and reads the `catalog-info.yaml` from each targeted repository.
- **Benefit**: Zero-latency, 100% deterministic, prevents agents from wandering into unrelated repositories.

### 2. LLM Router Fallback (Agentic Intent Parsing)
If no `@` tags are detected, the system will fall back to an LLM-based router.
- **Example**: `/swarm "Deploy the MMS checkout service to dev"`
- **Mechanism**: Before launching the main CrewAI swarm, the extension invokes a lightweight, high-speed model (Gemini 2.5 Flash). This "Router Agent" is provided with an index of the `resource-catalog` and the user's prompt. It returns a strict JSON payload containing the inferred `repos_involucrados` and `equipo_recomendado`.
- **Benefit**: Enables natural language intent, dynamically mapping semantic requests to physical repositories based on the Backstage catalog definitions.

## Consequences
- **Positive**: Seamless multi-repo context handling. Power users can use `@` for speed, while complex/ambiguous tasks still succeed via the Router Agent.
- **Negative**: The fallback mechanism introduces slight latency (1-2 seconds) and token usage to parse the intent before the actual Swarm execution begins.
- **Architecture Impact**: The Python CrewAI runner will need to accept a list of workspaces/contexts rather than a single `cwd`.
