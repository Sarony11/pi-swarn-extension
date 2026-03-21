import { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";

const BRAVE_PARAMS = Type.Object({
  query: Type.String({ description: "The search query (e.g., 'latest kubernetes CVEs 2026')" }),
  count: Type.Optional(Type.Number({ description: "Number of results to return (default: 5, max: 10)" }))
});

export default function braveSearchExtension(pi: ExtensionAPI) {
  pi.on("session_start", (_event, ctx) => {
    pi.registerTool({
      name: "brave_search",
      label: "Brave Search API",
      description: "Search the web using Brave Search API. Use this to find current events, documentation, bug fixes, or general knowledge.",
      promptSnippet: "Use brave_search to find information on the internet.",
      promptGuidelines: ["Always use this tool when asked about recent events, documentation, or something you don't know."],
      parameters: BRAVE_PARAMS,
      async execute(_toolCallId, params) {
        const apiKey = process.env.BRAVE_SEARCH_API_KEY;
        if (!apiKey) {
          return { content: [{ type: "text", text: "Error: BRAVE_SEARCH_API_KEY environment variable is not set." }] };
        }

        const query = encodeURIComponent(params.query);
        const count = params.count || 5;
        
        try {
          const response = await fetch(`https://api.search.brave.com/res/v1/web/search?q=${query}&count=${count}`, {
            headers: {
              "Accept": "application/json",
              "Accept-Encoding": "gzip",
              "X-Subscription-Token": apiKey
            }
          });

          if (!response.ok) {
            return { content: [{ type: "text", text: `Brave Search API Error: ${response.status} ${response.statusText}` }] };
          }

          const data = await response.json();
          const results = data.web?.results || [];

          if (results.length === 0) {
            return { content: [{ type: "text", text: "No results found." }] };
          }

          let output = `Search results for "${params.query}":\n\n`;
          results.forEach((item: any, index: number) => {
            output += `${index + 1}. Title: ${item.title}\n`;
            output += `   URL: ${item.url}\n`;
            output += `   Snippet: ${item.description}\n\n`;
          });

          return { content: [{ type: "text", text: output }] };
        } catch (error: any) {
          return { content: [{ type: "text", text: `Error executing search: ${error.message}` }] };
        }
      }
    });
    console.log("[Brave Search Extension] Tool registered.");
  });
}
