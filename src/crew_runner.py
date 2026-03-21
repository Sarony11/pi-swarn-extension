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

def load_yaml(filepath):
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


@tool("List Directory Tool")
def list_directory_tool(path: str) -> str:
    """Lists the contents of a directory. Use this to explore the workspace. If path starts with @, it maps to ~/repos/."""
    try:
        if path.startswith('@'): 
            path = path.replace('@', '~/repos/', 1)
        expanded_path = os.path.expanduser(path)
        if not os.path.exists(expanded_path): 
            return f"Error: '{path}' does not exist."
        if not os.path.isdir(expanded_path): 
            return f"Error: '{path}' is not a directory."
        items = os.listdir(expanded_path)
        return f"Contents of {path}:\n" + "\n".join(items)
    except Exception as e:
        return f"Error: {str(e)}"

@tool("Read File Tool")
def read_file_tool(path: str) -> str:
    """Reads the content of a file. Use this to examine code, markdown, or config files. Output truncated to 1000 lines. If path starts with @, it maps to ~/repos/."""
    try:
        if path.startswith('@'): 
            path = path.replace('@', '~/repos/', 1)
        expanded_path = os.path.expanduser(path)
        if not os.path.exists(expanded_path): 
            return f"Error: '{path}' does not exist."
        if not os.path.isfile(expanded_path): 
            return f"Error: '{path}' is not a file."
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
        if path.startswith('@'): 
            path = path.replace('@', '~/repos/', 1)
        expanded_path = os.path.expanduser(path)
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

def run_real_swarm(team_dir: str, context: Dict[str, Any]):
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
            
        enhanced_backstory = agent_config['backstory'] + rbac_prompt + global_rules

        agent = Agent(
            role=agent_config['role'],
            goal=agent_config['goal'],
            backstory=enhanced_backstory,
            verbose=True,
            allow_delegation=False,
            llm=agent_llm,
            tools=agent_tools
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
            agent=agents[task_config['agent']]
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


    print(f"Starting real CrewAI Swarm execution with Gemini...")
    result = crew.kickoff()
    print("\n--- Final Output ---\n")
    print(result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--team-dir", required=True)
    parser.add_argument("--context", required=False, default="{}")
    args = parser.parse_args()
    
    context_data = json.loads(args.context)
    run_real_swarm(args.team_dir, context_data)
