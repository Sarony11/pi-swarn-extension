# 🗺️ Pi Swarm Extension Roadmap

Welcome to the roadmap for the Pi Swarm Extension! This document outlines the current state of the project, what we are actively working on, and our long-term vision. 

If you are looking to contribute, this is the perfect place to find an interesting challenge.

## ✅ Done (Foundation)
- **Phase 1: Extension Skeleton**: Registration of the `/swarm` command in Pi.
- **Phase 2: Python Bridge**: Isolated `venv` execution and LiteLLM integration.
- **Phase 3: Base Tooling & RBAC**: Implementation of `tools_access_level` (none, read, read-web, write) and native tools (`ReadFile`, `ListDirectory`, `BraveSearch`).
- **Phase 4: Model Cascade**: Support for hierarchical model definition (Global -> Team -> Agent).

## 🚀 Now (Active Development)
We are currently focusing on making the agents context-aware and deeply integrated with the workspace environment.

- [x] **Phase 5.5: Global Context Injection (`AGENTS.md`)**
  - *Goal*: Agents are currently "blind" to workspace rules. We need the runner to dynamically read local or global `AGENTS.md` files and append them to the agent's `backstory`.
  - *Impact*: Subagents will automatically respect domain boundaries, coding guidelines, and user preferences without needing repetitive prompts.

- [ ] **Phase 5: Smart Routing (Catalog-Driven Discovery & `--focus`)**
  - *Goal*: Allow users to define target workspaces dynamically in the prompt (e.g., `/swarm team "Fix @mms/terraform"`). The TS extension should parse these paths and pass them to the python runner.
  - *Impact*: Enables multi-repository agentic workflows seamlessly.

## 🔜 Next (Short-term)
- [ ] **Phase 7: Multi-Provider LLM Support (Anthropic / OpenAI)**
  - *Goal*: Remove the hardcoded dependency on `GEMINI_API_KEY` and `gemini/*` models. Leverage LiteLLM to dynamically inject the correct API keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) based on the model specified in the `team.yaml`.
  - *Impact*: Makes the extension truly provider-agnostic, allowing community users to bring their preferred models (like Claude 3.5 Sonnet or GPT-4o) to their swarms.

- [ ] **Phase 8: Pi Skill Proxy (JSON-RPC Bridge)**
  - *Goal*: Allow CrewAI agents to invoke native Pi Skills via the Stdin/Stdout JSON-RPC bridge.
  - *Impact*: Subagents will be able to trigger complex IDE actions (like running tests, compiling, or triggering git commands) using Pi as a proxy.

## 🔮 Later (Long-term Vision)
- [ ] **Docker-based Execution Environment**
  - *Goal*: Move away from Python `venv` and execute the Swarms inside ephemeral Docker containers.
  - *Impact*: Maximum security isolation. Malicious or hallucinated agent actions (e.g., `rm -rf /`) will be contained within the sandbox.
- [ ] **TUI / Web Dashboard for Swarm Monitoring**
  - *Goal*: Implement a real-time UI within Pi to visualize the agent thought process, task delegation, and token usage instead of relying on terminal text output.

---

## Want to contribute?
Pick any unchecked item from the **Now** or **Next** sections! Please open an Issue first to discuss your approach before submitting a Pull Request.
