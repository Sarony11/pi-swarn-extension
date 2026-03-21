import { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

export default function (pi: ExtensionAPI) {
  pi.registerCommand("swarm", {
    description: "Launch a CrewAI swarm. Usage: /swarm <team-name> [--focus] \"prompt\"",
    handler: async (args: string, context: any) => {
      const cwd = context.cwd;
      const metaWorkspace = process.env.PI_META_WORKSPACE || path.join(os.homedir(), "repos");
      
      let explicitTeamName = "";
      let userPrompt = "";
      let isStrictFocus = false;

      // Parse arguments gracefully
      const parts = args.trim().split(" ");
      let promptParts = [];
      
      for (let i = 0; i < parts.length; i++) {
        if (parts[i] === "--focus") {
          isStrictFocus = true;
        } else if (!explicitTeamName && !parts[i].startsWith('"') && i === 0) {
          explicitTeamName = parts[i];
        } else {
          promptParts.push(parts[i]);
        }
      }
      
      userPrompt = promptParts.join(" ");
      
      // Clean up surrounding quotes from prompt
      if (userPrompt.startsWith('"') && userPrompt.endsWith('"')) {
          userPrompt = userPrompt.substring(1, userPrompt.length - 1);
      }

      // 1. Extract Explicit @paths
      let focusedPaths: string[] = [];
      const atPathRegex = /@([\w-]+\/[\w-]+(?:\/[\w-]+)*)/g;
      let match;
      while ((match = atPathRegex.exec(userPrompt)) !== null) {
        const resolvedPath = path.join(metaWorkspace, match[1]);
        focusedPaths.push(resolvedPath);
      }

      // 2. Catalog Discovery (if not strict)
      if (!isStrictFocus) {
        const catalogDir = path.join(metaWorkspace, "resource-catalog", "components");
        if (fs.existsSync(catalogDir)) {
          const files = fs.readdirSync(catalogDir);
          for (const file of files) {
            if (file.endsWith(".yaml") || file.endsWith(".yml")) {
              const content = fs.readFileSync(path.join(catalogDir, file), "utf-8");
              
              // Poor man's YAML parsing for performance and zero-dependencies
              const nameMatch = content.match(/name:\s*"?([\w-]+)"?/);
              const systemMatch = content.match(/system:\s*"?([\w-]+)"?/);
              const domainMatch = content.match(/domain:\s*"?([\w-]+)"?/);
              const localPathMatch = content.match(/agentic\.pi\/workspace-path:\s*"?([^"\n]+)"?/);

              const compName = nameMatch ? nameMatch[1] : "";
              const compSystem = systemMatch ? systemMatch[1] : "";
              const compDomain = domainMatch ? domainMatch[1] : "unknown";

              // Check if prompt mentions the component or system
              const promptLower = userPrompt.toLowerCase();
              if ((compName && promptLower.includes(compName.toLowerCase())) || 
                  (compSystem && promptLower.includes(compSystem.toLowerCase()))) {
                
                let targetPath = "";
                if (localPathMatch) {
                  targetPath = path.join(metaWorkspace, localPathMatch[1].trim());
                } else {
                  targetPath = path.join(metaWorkspace, compDomain, compName);
                }
                focusedPaths.push(targetPath);
              }
            }
          }
        }
      }

      // Deduplicate paths
      focusedPaths = [...new Set(focusedPaths)];

      // Team Resolution
      let teamName = explicitTeamName || "demo-team"; 
      let agentLibraryPath = process.env.PI_AGENT_LIBRARY || path.join(os.homedir(), ".pi", "agent-library");
      if (!fs.existsSync(agentLibraryPath) && fs.existsSync(path.join(metaWorkspace, "agent-library"))) {
         agentLibraryPath = path.join(metaWorkspace, "agent-library");
      }
      
      const teamDir = path.join(agentLibraryPath, "swarms", teamName);
      if (!fs.existsSync(teamDir)) {
        context.ui.notify(`[Swarm Error] Team directory not found at ${teamDir}`);
        return;
      }

      const runnerPath = path.join(os.homedir(), ".pi", "agent", "swarms", "crew_runner.py");
      if (!fs.existsSync(runnerPath)) {
        context.ui.notify(`[Swarm Error] Python bridge not found at ${runnerPath}`);
        return;
      }

      const contextVars = { 
        workspace: cwd,
        prompt: userPrompt || "Please analyze the current project state."
      };
      
      const jsonContext = JSON.stringify(contextVars).replace(/'/g, "'\\''");
      const jsonPaths = JSON.stringify(focusedPaths).replace(/'/g, "'\\''");
      
      const cmd = `~/.pi/agent/swarms/venv/bin/python ${runnerPath} --team-dir ${teamDir} --context '${jsonContext}' --focused-paths '${jsonPaths}' < /dev/null`;

      context.ui.notify(`🚀 Swarm [${teamName}] is waking up and thinking... this might take a minute depending on the LLM.`, "info");
      
      const { exec } = require("child_process");
      return new Promise<void>((resolve) => {
          exec(cmd, { encoding: "utf8" }, (error: any, stdout: string, stderr: string) => {
              if (error) {
                  const errorMsg = `[Swarm Error]\n\n${error.message}\n\n${stderr}`;
                  context.ui.notify("Swarm encountered an error.", "error");
                  console.log(errorMsg);
              } else {
                  context.ui.notify("✅ Swarm completed successfully!", "info");
                  console.log(`[Swarm Result: ${teamName}]\n\n` + stdout);
              }
              resolve();
          });
      });
    }
  });

  console.log("[Swarm Extension] Loaded. Multi-Repo Smart Routing enabled.");
}
