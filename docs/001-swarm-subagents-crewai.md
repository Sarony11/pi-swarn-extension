# RFC-001: CrewAI Swarms & Sub-agents for Pi Agent

**Status**: Draft
**Date**: 2026-03-20
**Author**: Pi Assistant & Saul Fernandez
**Project**: Agentic Personal Platform

## 1. Abstract
This RFC proposes an extension for the Pi Coding Agent to orchestrate multi-agent workflows using CrewAI. The goal is to allow Pi to delegate complex, multi-step tasks to specialized teams of sub-agents defined in the user's `agent-library/`, leveraging the `resource-catalog/` for context and team selection.

## 2. Motivation
Currently, Pi is a single-agent system. While powerful for direct coding, it lacks the ability to perform parallel research, cross-system audits, or complex planning that requires multiple "personas" (e.g., Security Researcher + Platform Engineer + QA).

## 3. Proposed Solution

### 3.1. Command Architecture
A new command `/swarm [team] [--verbose]` will be registered via a Pi Extension.
- **`[team]`**: Optional. Explicitly names a team to invoke (e.g., `audit-team`).
- **Default behavior**: If no team is specified, Pi reads the current directory's `catalog-info.yaml`, identifies the `system`/`domain`, and maps it to a team defined in `agent-library/swarms/`.

### 3.2. Configuration Structure (`agent-library/swarms/`)
Teams are defined in YAML to keep them declarative and portable.
```yaml
# Example: ~/repos/agent-library/swarms/cloud-ops/team.yaml
name: "Cloud Ops Team"
description: "Optimizes GCP resources and Terraform modules"
agents:
  - role: "Cloud Architect"
    backstory: "Expert in GCP and Terraform best practices..."
    goal: "Design scalable and cost-effective infrastructure"
    model: "anthropic/claude-3-5-sonnet"
  - role: "Security Auditor"
    backstory: "Focused on least privilege and IAM security..."
    goal: "Ensure all infrastructure meets security standards"
    model: "openai/gpt-4o"
mapping:
  systems: ["gcp-infra", "landing-zone"]
  domains: ["platform-engineering"]
```

### 3.3. Execution Flow
1. **Pi Extension (Node.js)**: Captures `/swarm` command and arguments.
2. **Context Resolution**: Reads `catalog-info.yaml` and `agent-library/swarms/`.
3. **Bridge**: Spawns a Python process running a generic `crew_runner.py`.
4. **CrewAI (Python)**: Executes the swarm using the YAML configuration.
5. **Feedback Loop**:
   - `Verbose`: Stream logs to Pi terminal.
   - `Silent`: Show only status updates (e.g., "Agent X is researching...").
6. **Result**: The final output of the Crew is returned to Pi as a message and/or file.

## 4. Integration with Resource Catalog
The `resource-catalog` serves as the **Dynamic Context Provider**. The swarm should have read access to the catalog to understand dependencies between systems.

## 5. Security & Isolation
- Each swarm execution runs in a isolated Python environment (`venv`).
- Tools granted to sub-agents must be explicitly defined in the YAML configuration.

## 6. Unresolved Questions (for the next phase)
- How to handle shared memory/state between Pi and the Swarm?
- Should we allow the Swarm to call Pi's built-in tools (`edit`, `bash`) directly?
- Best way to handle Python dependency management automatically.
