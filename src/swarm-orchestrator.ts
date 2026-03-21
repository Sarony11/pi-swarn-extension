import { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

export default function (pi: ExtensionAPI) {
  pi.registerCommand("swarm", {
    description: "Launch a CrewAI swarm. Usage: /swarm [team-name] [\"prompt\"]",
    handler: async (args: string, context: any) => {
      const cwd = context.cwd;
      
      let explicitTeamName = "";
      let userPrompt = "";

      // Parse arguments gracefully
      const parts = args.trim().split(" ");
      if (parts.length > 0 && parts[0] && !parts[0].startsWith('"')) {
         explicitTeamName = parts[0];
         userPrompt = parts.slice(1).join(" ");
      } else {
         userPrompt = parts.join(" ");
      }
      
      // Clean up surrounding quotes from prompt
      if (userPrompt.startsWith('"') && userPrompt.endsWith('"')) {
          userPrompt = userPrompt.substring(1, userPrompt.length - 1);
      }

      // Catalog context
      const catalogPath = path.join(cwd, "catalog-info.yaml");
      let system = "unknown-system";
      let domain = "unknown-domain";
      let componentName = path.basename(cwd);

      if (fs.existsSync(catalogPath)) {
        const catalogContent = fs.readFileSync(catalogPath, "utf-8");
        const systemMatch = catalogContent.match(/system:\s*([^\s]+)/);
        const domainMatch = catalogContent.match(/domain:\s*([^\s]+)/);
        const nameMatch = catalogContent.match(/name:\s*([^\s]+)/);

        if (systemMatch) system = systemMatch[1].replace(/['"]/g, '');
        if (domainMatch) domain = domainMatch[1].replace(/['"]/g, '');
        if (nameMatch) componentName = nameMatch[1].replace(/['"]/g, '');
      } else {
        system = "demo-system";
        domain = "experimental";
      }

      let teamName = explicitTeamName || "demo-team"; 

      const teamDir = path.join(os.homedir(), "repos", "agent-library", "swarms", teamName);
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
        topic: componentName,
        system: system,
        domain: domain,
        workspace: cwd,
        prompt: userPrompt || "Please analyze the current project state."
      };
      
      const jsonContext = JSON.stringify(contextVars);
      const safeJson = jsonContext.replace(/'/g, "'\\''");
      const cmd = `~/.pi/agent/swarms/venv/bin/python ${runnerPath} --team-dir ${teamDir} --context '${safeJson}' < /dev/null`;

      // UI Feedback - Show progress in the chat window
      context.ui.notify(`🚀 Swarm [${teamName}] is waking up and thinking... this might take a minute depending on the LLM.`, "info");
      
      // Execute asynchronously to not block Pi's event loop entirely, although execSync blocks node 
      // it's better to use promises with exec to allow UI to render.
      const { exec } = require("child_process");
      
      return new Promise<void>((resolve) => {
          exec(cmd, { encoding: "utf8" }, (error: any, stdout: string, stderr: string) => {
              if (error) {
                  const errorMsg = `[Swarm Error]\n\n${error.message}\n\n${stderr}`;
                  context.ui.notify("Swarm encountered an error.", "error");
                  console.log(errorMsg); // This will appear in the chat history
              } else {
                  context.ui.notify("✅ Swarm completed successfully!", "info");
                  console.log(`[Swarm Result: ${teamName}]\n\n` + stdout); // Print output to chat
              }
              resolve();
          });
      });
    }
  });

  console.log("[Swarm Extension] Loaded. Teams available: demo-team, reviewer-team.");
}
