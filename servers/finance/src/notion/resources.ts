import {
    ListResourcesRequestSchema,
    ReadResourceRequestSchema
  } from "@modelcontextprotocol/sdk/types.js";
  import { notion } from "./notionClient.js";
  import { DB_ACCOUNTS_ID, DB_TRANSACTIONS_ID } from "../env.js";
  import { Server } from "@modelcontextprotocol/sdk/server/index.js";
  
  export default function registerResources(server: Server) {


    server.setRequestHandler(ListResourcesRequestSchema, async () => {
      const accounts = await notion.databases.query({ database_id: DB_ACCOUNTS_ID });
  
      return {
        resources: [
          ...accounts.results.map((page: any) => ({
            uri: `notion://account/${page.id}`,
            name: page.properties?.Nombre?.title?.[0]?.plain_text || "Cuenta sin nombre",
            mimeType: "application/json",
          })),
          {
            uri: "notion://transactions",
            name: "Últimos movimientos financieros",
            mimeType: "application/json"
          }
        ]
      };
    });
  
    // Leer contenido de recursos
    server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const uri = request.params.uri;
  
      if (uri.startsWith("notion://account/")) {
        const id = uri.split("/").pop()!;
        const page = await notion.pages.retrieve({ page_id: id });
  
        return {
          contents: [
            {
              uri,
              mimeType: "application/json",
              text: JSON.stringify(page, null, 2)
            }
          ]
        };
      }
  
      if (uri === "notion://transactions") {
        const response = await notion.databases.query({
          database_id: DB_TRANSACTIONS_ID,
          page_size: 100
        });
  
        const data = response.results.map((page: any) => ({
          id: page.id,
          description: page.properties?.Decription?.title?.[0]?.plain_text || "",
          date: page.properties?.["Transaction Date"]?.date?.start || null,
          amount: page.properties?.["Transaction Amount"]?.number,
          type: page.properties?.["Type Transacction"]?.select?.name || "",
          spendType: page.properties?.["Type Spend"]?.select?.name || "",
          origin: page.properties?.Origen?.relation?.[0]?.id || null,
          destination: page.properties?.Destino?.relation?.[0]?.id || null,
        }));
  
        return {
          contents: [
            {
              uri,
              mimeType: "application/json",
              text: JSON.stringify(data, null, 2)
            }
          ]
        };
      }
  
      throw new Error("Resource not found");
    });
  }
  