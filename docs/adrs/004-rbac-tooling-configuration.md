# ADR 004: Role-Based Access Control (RBAC) for Swarm Tools

## Status
Accepted

## Context
As we expand the toolset available to CrewAI subagents (giving them the ability to not just read files, but potentially execute bash commands, edit code, and write new files), the risk of unintended destructive actions increases. 

Not all agents need all tools. A "Security Auditor" agent might only need `read` access to examine code and configurations. A "Technical Writer" might need `read` and `write` access to generate documentation. A "DevOps Automation" agent might need `bash` access to run terraform plans or tests. 

Providing global access to all tools to every agent is a violation of the Principle of Least Privilege and poses a security risk, especially when the swarm operates autonomously.

## Decision
We will implement a **Role-Based Access Control (RBAC)** mechanism at the agent configuration level within the `team.yaml` files. 

We introduce a new optional parameter for each agent: `tools_access_level`.

### Access Levels:
1.  **`none` (Default if omitted):** The agent operates as a pure LLM text processor. No tools are provided.
2.  **`read`:** The agent is granted non-destructive exploration tools.
    -   `ListDirectoryTool`
    -   `ReadFileTool`
    -   *(Future)* Safe Bash Tool (e.g., restricted to `grep`, `find`, `cat`)
3.  **`write`:** The agent is granted destructive/modifying tools in addition to read tools.
    -   All `read` tools.
    -   `WriteFileTool`
    -   `EditFileTool`
    -   *(Future)* Unrestricted Bash Tool (execute tests, git commands)

### Example Configuration (`team.yaml`):
```yaml
agents:
  - role: "Senior Developer"
    goal: "Analyze code..."
    tools_access_level: "read"  # Only reads and inspects
    
  - role: "Documentation Writer"
    goal: "Generate READMEs..."
    tools_access_level: "write" # Allowed to create files on disk
```

## Consequences
- **Positive:** Enforces the Principle of Least Privilege. Significantly reduces the risk of an LLM hallucination destroying code or infrastructure. Allows the orchestrator to safely deploy specialized "Action Swarms" alongside safe "Analysis Swarms".
- **Negative:** Requires careful configuration of `team.yaml` files. If a user forgets to assign `tools_access_level: "read"`, the agent might fail to complete a task that requires file inspection, returning a generic "I don't have access" message.
- **Architecture Impact:** The `crew_runner.py` script must dynamically construct the `tools` array for each `Agent` instantiation based on the parsed `tools_access_level` string, rather than passing a static list to everyone.
