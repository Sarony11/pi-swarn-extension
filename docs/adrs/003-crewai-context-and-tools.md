# ADR 003: Shared Consciousness and Tooling for Swarm Agents

## Status
Accepted

## Context
In the current implementation (ADR-001), CrewAI subagents act as isolated text processors. When a user requests a swarm to "review the @agent-library/rules/", the agents only receive the literal string as a prompt. They lack two fundamental capabilities that the main Pi agent possesses:
1. **Shared Consciousness (Global Rules):** They do not know the global environment rules defined in `AGENTS.md` (e.g., the strict separation between `mms` and `personal` domains, or Saul's specific technical preferences).
2. **Autonomy (Tools):** They do not have the ability to read files, execute bash commands, or browse the `resource-catalog` to gather context dynamically.

To make the swarm truly useful, subagents must be "first-class citizens" in the workspace, possessing the same baseline context and exploration capabilities as the orchestrator.

## Decision
We will enhance the CrewAI runner and swarm architecture with two new mechanisms:

### 1. Global Context Injection (`AGENTS.md`)
Before instantiating any CrewAI `Agent`, the `crew_runner.py` script (or the TS extension) will dynamically locate and read the relevant `AGENTS.md` files (the global one in `~/.pi/agent/AGENTS.md` or `~/repos/AGENTS.md`, and any domain-specific ones). 
This content will be automatically concatenated to the `backstory` of every agent. This ensures that every agent "knows who Saul is", understands the workspace layout, and respects domain boundaries without needing to repeat this in every `team.yaml`.

### 2. Native CrewAI Tooling ("Hands and Eyes")
Instead of passing entire codebases within the initial prompt (which is inefficient and breaks context windows), we will equip the subagents with Python-based CrewAI Tools (`crewai.tools.BaseTool`).
Specifically, we will provide:
- `ListDirectoryTool`: To explore workspace structures.
- `ReadFileTool`: To read source code, catalog YAMLs, and markdown rules on demand.
- *(Future)* `PiSkillProxyTool`: To allow CrewAI agents to trigger Pi skills via the JSON-RPC bridge.

## Consequences
- **Positive:** Subagents become highly autonomous. They can verify paths, read documentation, and understand context before acting, drastically reducing hallucinations. They will automatically adhere to the global engineering standards set in `AGENTS.md`.
- **Negative:** Injecting the `AGENTS.md` into every agent's backstory will increase the baseline token usage for every prompt. However, Gemini 2.5 Flash handles large contexts efficiently and cheaply.
- **Architecture Impact:** Modifies `crew_runner.py` to handle file I/O for `AGENTS.md` and requires the development of custom tool classes inside the swarm runner.
