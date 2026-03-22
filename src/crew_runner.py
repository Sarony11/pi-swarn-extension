import sys
import yaml
import json
import requests
import os
import argparse
from typing import Dict, Any

try:
    from crewai import Agent, Task, Crew, Process, LLM
    from crewai.tools import tool
except ImportError as e:
    print(f"CrewAI imports failed: {e}")
    sys.exit(1)
    
# --- Custom JSON Observability Logger ---
class JsonObservabilityLogger:
    def __init__(self):
        self.total_tokens = 0
        
    def log_event(self, event_type: str, data: dict):
        payload = {
            "event": event_type,
            **data
        }
        # Print to stdout as JSON Lines so the Node orchestrator can parse it
        print(json.dumps(payload), flush=True)

logger = JsonObservabilityLogger()

def step_callback(step_output):
    """Hook called after each step of an agent."""
    # Not all CrewAI versions expose tokens here perfectly, but we try
    # to capture what the agent just did.
    tool_name = getattr(step_output, 'tool', 'unknown_tool')
    action = getattr(step_output, 'action', '')
    thought = getattr(step_output, 'thought', '')
    
    logger.log_event("agent_step", {
        "tool": tool_name,
        "action": action,
        "thought": thought[:100] + "..." if len(thought) > 100 else thought
    })

import datetime
SESSION_DIR = os.path.expanduser("~/.pi/agent/sessions")
os.makedirs(SESSION_DIR, exist_ok=True)
session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
checkpoint_file = os.path.join(SESSION_DIR, f"swarm_checkpoint_{session_id}.json")

def task_callback(task_output):
    """Hook called when a task finishes."""
    agent_role = getattr(task_output.agent, 'role', 'Unknown Agent') if hasattr(task_output, 'agent') else 'Unknown'
    summary = task_output.summary if hasattr(task_output, 'summary') else ''
    raw_output = getattr(task_output, 'raw', '')
    
    # Checkpoint State Backup
    try:
        checkpoint_data = {}
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
        
        tasks_done = checkpoint_data.get("tasks", [])
        tasks_done.append({
            "agent": agent_role,
            "summary": summary,
            "output_preview": raw_output[:500] + "..." if len(raw_output) > 500 else raw_output
        })
        checkpoint_data["tasks"] = tasks_done
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
    except Exception:
        pass # Failsafe
        
    # Capture token usage if available in the output
    token_usage = getattr(task_output, 'token_usage', {})
    logger.log_event("task_completed", {
        "agent": agent_role,
        "summary": summary,
        "tokens": token_usage,
        "checkpoint": checkpoint_file
    })

def load_yaml(filepath):
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)



def secure_resolve_path(requested_path: str) -> str:
    # Virtual Chroot: Ensure agents cannot access arbitrary host files
    base_dir = os.environ.get('PI_META_WORKSPACE', os.path.expanduser('~/repos/'))
    if requested_path.startswith('@'):
        requested_path = requested_path.replace('@', base_dir, 1)
    
    expanded = os.path.abspath(os.path.expanduser(requested_path))
    allowed_dirs = [os.path.abspath(base_dir), os.path.abspath(os.getcwd())]
    
    is_allowed = any(expanded.startswith(d) for d in allowed_dirs)
    if not is_allowed:
        raise PermissionError(f"Security Alert: Path Traversal Blocked. '{expanded}' is outside the allowed workspace.")
    
    return expanded

@tool("List Directory Tool")
def list_directory_tool(path: str) -> str:
    """Lists the contents of a directory. Use this to explore the workspace. If path starts with @, it maps to ~/repos/."""
    try:
        expanded_path = secure_resolve_path(path)
        if not os.path.exists(expanded_path): 
            return f"Error: '{expanded_path}' does not exist."
        if not os.path.isdir(expanded_path): 
            return f"Error: '{expanded_path}' is not a directory."
        items = os.listdir(expanded_path)
        return f"Contents of {path}:\n" + "\n".join(items)
    except Exception as e:
        return f"Error: {str(e)}"

@tool("Read File Tool")
def read_file_tool(path: str) -> str:
    """Reads the content of a file. Use this to examine code, markdown, or config files. Output truncated to 1000 lines. If path starts with @, it maps to ~/repos/."""
    try:
        expanded_path = secure_resolve_path(path)
        if not os.path.exists(expanded_path): 
            return f"Error: '{expanded_path}' does not exist."
        if not os.path.isfile(expanded_path): 
            return f"Error: '{expanded_path}' is not a file."
        with open(expanded_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) > 1000:
                return "".join(lines[:1000]) + f"\n... [Truncated. Total lines: {len(lines)}]"
            return "".join(lines)
    except Exception as e:
        return f"Error: {str(e)}"


@tool("Write File Tool")
def write_file_tool(path: str, content: str) -> str:
    """Writes content to a file. Overwrites if it exists, creates if it doesn't. If path starts with @, it maps to ~/repos/."""
    try:
        expanded_path = secure_resolve_path(path)
        # Ensure directory exists
        os.makedirs(os.path.dirname(expanded_path), exist_ok=True)
        with open(expanded_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool("Brave Search Tool")
def brave_search_tool(query: str) -> str:
    """Searches the web using Brave Search API. Use this to find current documentation, news, or technical solutions."""
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return "Error: BRAVE_SEARCH_API_KEY environment variable is not set."
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key
    }
    params = {"q": query, "count": 5}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("web", {}).get("results", [])
        if not results:
            return "No results found."
            
        output = f"Search results for '{query}':\n\n"
        for i, item in enumerate(results, 1):
            output += f"{i}. Title: {item.get('title')}\n"
            output += f"   URL: {item.get('url')}\n"
            output += f"   Snippet: {item.get('description')}\n\n"
        return output
    except Exception as e:
        return f"Search failed: {str(e)}"


def load_global_context(workspace_dir: str) -> str:
    """Attempts to find and read AGENTS.md to inject global rules into agents."""
    possible_paths = [
        os.path.join(workspace_dir, "AGENTS.md"),
        os.path.expanduser("~/.pi/agent/AGENTS.md"),
        os.path.expanduser("~/repos/AGENTS.md")
    ]
    
    context_content = ""
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    context_content += f"\n\n--- Global Rules from {os.path.basename(path)} ---\n"
                    context_content += f.read()
            except Exception as e:
                print(f"Warning: Failed to read {path}: {e}")
                
    return context_content

def run_real_swarm(team_dir: str, context: Dict[str, Any], focused_paths: list):
    team_data = load_yaml(os.path.join(team_dir, "team.yaml"))
    blueprint_data = load_yaml(os.path.join(team_dir, "blueprint.yaml"))
    
    workspace = context.get('workspace', os.getcwd())
    global_rules = load_global_context(workspace)
    
    if "GEMINI_API_KEY" not in os.environ:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    agents = {}
    
    # In recent CrewAI versions, you don't need Langchain wrappers anymore.
    # You pass litellm native provider strings to LLM wrapper.
    global_default_model = "gemini/gemini-2.5-flash"
    team_model = team_data.get('model', global_default_model)

    for agent_config in team_data.get('agents', []):
        agent_model = agent_config.get('model', team_model)
        access_level = agent_config.get('tools_access_level', 'none').lower()
        
        # Determine backstory: From separate markdown file or inline
        backstory = agent_config.get('backstory', '')
        prompt_file = agent_config.get('prompt_file')
        
        if prompt_file:
            prompt_path = os.path.join(team_dir, prompt_file)
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    backstory = f.read()
            else:
                print(f"Warning: prompt_file '{prompt_file}' not found at {prompt_path}. Falling back to inline backstory.", file=sys.stderr)
        
        agent_llm = LLM(
            model=agent_model,
            api_key=os.environ["GEMINI_API_KEY"]
        )

        # RBAC Tooling assignment
        agent_tools = []
        rbac_prompt = "\n\n[SYSTEM CONSTRAINT] You have no tools available. You must rely solely on your knowledge and the provided context."
        
        if access_level == 'read':
            agent_tools = [list_directory_tool, read_file_tool]
            rbac_prompt = "\n\n[SYSTEM CONSTRAINT] You are operating in READ-ONLY mode. You can inspect local directories and read files, but you CANNOT modify them or search the web."
        elif access_level == 'read-web':
            agent_tools = [list_directory_tool, read_file_tool, brave_search_tool]
            rbac_prompt = "\n\n[SYSTEM CONSTRAINT] You are operating in READ-WEB mode. You can inspect local files and search the internet using Brave Search. You CANNOT modify files."
        elif access_level == 'write':
            agent_tools = [list_directory_tool, read_file_tool, write_file_tool, brave_search_tool]
            rbac_prompt = "\n\n[SYSTEM CONSTRAINT] You are operating in READ-WRITE mode. You have full access to local files, internet search, and can create/overwrite files."
            
        focus_prompt = ""
        if focused_paths:
            paths_str = "\n- ".join(focused_paths)
            focus_prompt = f"\n\n[WORKSPACE FOCUS] Your Root Workspace is {workspace}. However, for this specific task, you MUST focus your attention strictly on the following paths:\n- {paths_str}"
            
        enhanced_backstory = backstory + rbac_prompt + global_rules + focus_prompt

        agent = Agent(
            role=agent_config['role'],
            goal=agent_config['goal'],
            backstory=enhanced_backstory,
            verbose=True,
            allow_delegation=False,
            llm=agent_llm,
            tools=agent_tools,
            max_iter=agent_config.get('max_iterations', 5),
            max_execution_time=agent_config.get('max_execution_time', None),
            max_retry_limit=agent_config.get('max_retry_limit', 2),
            step_callback=step_callback
        )
        agents[agent_config['role']] = agent

    tasks = []
    for task_config in blueprint_data.get('tasks', []):
        desc = task_config.get('description', '')
        for k, v in context.items():
            desc = desc.replace(f"{{{{{k}}}}}", str(v))
            
        task = Task(
            description=desc,
            expected_output=task_config.get('expected_output', 'A valid output'),
            agent=agents[task_config['agent']],
            callback=task_callback
        )
        tasks.append(task)
    # Determine process mode from team.yaml (default to sequential)
    mode_str = team_data.get('process_mode', 'sequential').lower()
    if mode_str == 'hierarchical':
        # Hierarchical requires a manager LLM
        process_mode = Process.hierarchical
        manager_llm = LLM(model=team_model, api_key=os.environ["GEMINI_API_KEY"]) 
    else:
        process_mode = Process.sequential
        manager_llm = None

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        verbose=True,
        process=process_mode,
        manager_llm=manager_llm
    )

    logger.log_event("swarm_started", {"team": os.path.basename(team_dir), "mode": mode_str})
    result = crew.kickoff()
    
    # Final token usage is usually attached to the crew object
    final_usage = getattr(crew, 'usage_metrics', {})
    logger.log_event("swarm_completed", {"final_tokens": final_usage})
    
    # We still print the final output for the user to read easily
    print(f"\n--- Final Output ---\n{result}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--team-dir", required=True)
    parser.add_argument("--payload", required=True)
    args = parser.parse_args()
    
    with open(args.payload, 'r') as f:
        payload = json.load(f)
        
    context_data = payload.get("context", {})
    focused_paths = payload.get("focused_paths", [])
    
    run_real_swarm(args.team_dir, context_data, focused_paths)
