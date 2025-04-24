import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import  registerResources  from './notion/resources.js';
import registerTools from './notion/tools.js';
import {
  ListPromptsRequestSchema,
  GetPromptRequestSchema
} from "@modelcontextprotocol/sdk/types.js";
import { notion } from "./notion/notionClient.js";
import { DB_ACCOUNTS_ID } from "./env.js";

const serverMCP = new McpServer({
  name: "Demo",
  version: "1.0.0",
});


const server = serverMCP.server;
server.registerCapabilities( {
  resources: {},
  tools: {},
  prompts: {},
})

registerResources(server);
registerTools(serverMCP);

const transport = new StdioServerTransport();
await serverMCP.connect(transport);

console.info(
  '{"jsonrpc": "2.0", "method": "log", "params": { "message": "Finanzas MCP server running..." }}'
);
