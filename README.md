# Pi Swarm Extension 🐝

Welcome to the **Pi Swarm Extension**, an advanced orchestration bridge that connects the [Pi Coding Agent](https://github.com/mariozechner/pi-coding-agent) with **CrewAI**. 

This extension allows you to delegate complex, multi-agent tasks to isolated swarms of AI agents directly from your Pi terminal, using a declarative YAML-based configuration.

---

## 🎯 What does it do?
Instead of forcing the main Pi agent to do all the heavy lifting, the Swarm Extension acts as a manager. You define "Teams" of specialized agents (e.g., a "Code Review Team" with a Senior Developer and a Security Engineer), and Pi orchestrates their execution in the background using Google Gemini models.


## 📚 Architecture & Documentation

We use ADRs (Architecture Decision Records) to document the "why" behind our technical choices. You can read them in the `docs/` folder:
- [RFC-001: Original Proposal](docs/001-swarm-subagents-crewai.md)
- [ADR-001: Integrated CrewAI Architecture](docs/adrs/001-swarm-architecture.md)
- [ADR-002: Multi-Repo Smart Routing](docs/adrs/002-multi-repo-smart-routing.md)
- [ADR-003: Shared Consciousness & Tools](docs/adrs/003-crewai-context-and-tools.md)
- [ADR-004: RBAC Tooling Configuration](docs/adrs/004-rbac-tooling-configuration.md)

## 🚀 Quick Start

### 1. The Command
Launch a swarm from Pi using the `/swarm` command:

```bash
/swarm <team-name> "Your instructions or context here"
```

**Example:**
```bash
/swarm review-team "Please audit the code in @personal/marketpulse/api"
```

### 2. Multi-Repo Smart Routing (The `@` Syntax)
The extension supports "Meta-Workspace" routing. If you use `@domain/repository` in your prompt, the extension will automatically resolve the absolute path and provide the specific repository context to the Swarm.

---

## 🛠️ Configuration & Customization

Swarms are configured declaratively via YAML files. By default, the extension looks for teams in `~/.pi/agent-library/swarms/`. You can override this by setting the `PI_AGENT_LIBRARY` environment variable.

### Directory Structure of a Team
```
my-team/
├── team.yaml       # Defines the agents, models, and tools
└── blueprint.yaml  # Defines the sequential tasks they must execute
```

### `team.yaml` (Agents & Models)
This file defines the actors. It supports a **Model Cascade Hierarchy** and **Role-Based Access Control (RBAC)** for tools.

```yaml
name: "Code Review Team"
process_mode: "sequential"     # Can be 'sequential' or 'hierarchical'
model: "gemini/gemini-2.5-flash" # Default model for the whole team

agents:
  - role: "Security Researcher"
    backstory: "You find vulnerabilities on the internet."
    goal: "Find recent CVEs."
    tools_access_level: "read-web" # Has access to internet search
    model: "gemini/gemini-1.5-pro" # Overrides team model for complex reasoning

  - role: "Senior Developer"
    backstory: "You analyze local code."
    goal: "Review the code securely."
    tools_access_level: "read"     # Can read local files, no internet, no writing
```

#### Tool Access Levels (RBAC)
To prevent agents from making destructive actions, assign one of these levels:
* `none`: Only thinks. No access to tools. (Default)
* `read`: Can list directories (`ls`) and read files (`cat`).
* `read-web`: Can read local files AND search the internet via Brave Search.
* `write`: Can read files, search the web, and create/overwrite local files.

### `blueprint.yaml` (Tasks)
Defines what the agents actually do. You can use dynamic variables like `{{prompt}}` which are injected directly from your Pi terminal command.

```yaml
tasks:
  - name: "Initial Search"
    agent: "Security Researcher"
    description: "Search the web based on the user request: {{prompt}}"
    expected_output: "A summary of findings."

  - name: "Code Review"
    agent: "Senior Developer"
    description: "Based on the research, analyze the code."
    expected_output: "A Markdown report."
```

---

## ⚙️ Setup & Dependencies

### Prerequisites
1. **Python 3.12+**
2. **Virtual Environment**: A venv must be created at `~/.pi/agent/swarms/venv`.
3. **CrewAI & LiteLLM**: Installed inside the venv (`pip install crewai litellm google-genai requests`).
4. **API Keys**:
   * `GEMINI_API_KEY`: Required for the default LLM inference.
   * `PI_AGENT_LIBRARY`: (Optional) Absolute path to your custom agent-library folder.
   * `PI_META_WORKSPACE`: (Optional) Base path for resolving the `@` syntax (defaults to `~/repos/`).
   * *(Coming Soon)* `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`: For multi-provider model support.
   * `BRAVE_SEARCH_API_KEY`: Required if using the `read-web` tool level.

### Installation
Move the `.ts` files into your Pi extensions directory:
```bash
cp src/swarm-orchestrator.ts ~/.pi/agent/extensions/
cp src/brave-search.ts ~/.pi/agent/extensions/
```
Move the runner to the Pi agent folder:
```bash
mkdir -p ~/.pi/agent/swarms
cp src/crew_runner.py ~/.pi/agent/swarms/
```

Type `/reload` in Pi to load the new commands and tools!
