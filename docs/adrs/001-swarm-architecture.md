# ADR-001: Integrated CrewAI Swarm Architecture

**Status**: Accepted
**Context**: Saul wants to enable multi-agent swarms (CrewAI) within Pi, with high autonomy, environment isolation, and access to Pi's existing skills.

## 1. Environment & Session Isolation
### Decision
Every `/swarm` invocation will trigger the creation of a dedicated Python Virtual Environment (`venv`) and a tracking session.
- **Venv Management**: The Pi extension will manage a cache of venvs in `~/.pi/agent/swarms/venvs/`. To optimize, we will use a "Base Venv" with CrewAI installed, and clones/symlinks for specific executions if needed.
- **Cleanup**: Sessions will follow the Pi lifecycle. If a session is deleted via `/session`, its associated Python artifacts (unless shared) will be marked for cleanup.

## 2. Multi-Terminal Bash Execution
### Decision
To prevent terminal clutter and race conditions:
- **Architecture**: Sub-agents will NOT share the main Pi terminal for bash commands.
- **Implementation**: We will use a "Virtual Terminal Manager" within the extension. Each agent in the swarm gets a virtual `pty` (pseudo-terminal). 
- **Visibility**: In `--verbose` mode, Pi will multiplex these outputs (prefixing logs with `[Agent-Name]`). In silent mode, only the final results and exit codes are reported.

## 3. Skill Integration (The Bridge)
### Decision
Sub-agents will access Pi Skills via a **JSON-RPC Bridge**.
- **Agent Tool**: Each sub-agent will be injected with a generic tool called `use_pi_skill(skill_name, arguments)`.
- **Execution**: This tool sends a request back to the Pi Extension (Node.js), which executes the Markdown/TS skill and returns the text output to the Python agent.
- **Focus**: Agents only "see" skills explicitly listed in their `team.yaml` to keep the context window clean.

## 4. Team & Task Definition (`agent-library/`)
### Decision
We will use a dual-YAML approach in `~/repos/agent-library/swarms/<team-name>/`:
- **`team.yaml`**: Defines agents (roles, backstories, models, and allowed skills).
- **`blueprint.yaml`**: Defines a sequence of task templates. 
- **Dynamic Tasking**: Pi will use the LLM to fill the "placeholders" in the `blueprint.yaml` based on the user's specific request before passing it to CrewAI.

## 5. Catalog-Driven Selection
### Decision
The extension will look for a `pi-swarm.yaml` or tags in `catalog-info.yaml`.
- Mapping logic: `System Type: service` -> Auto-selects `backend-dev-team`.
- Overridable via `/swarm <team-name>`.

## 6. Consequences
- **Positive**: High reliability, clear separation of concerns, reuse of existing investment in Skills.
- **Negative**: Increased disk usage (venvs), slight latency due to Node-Python bridge.
- **Risk**: Python dependency conflicts. Mitigated by using strict version pinning in the extension's internal installer.
