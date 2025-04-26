import { z } from "zod";
import { notion } from "./notionClient.js";
import { DB_TRANSACTIONS_ID } from "../env.js";
import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";

export default function registerTools(server: McpServer) {
  server.tool(
    "insert-movement",
    {
      date: z.string().describe("Fecha del movimiento (YYYY-MM-DD)"),
      amount: z.number().describe("Monto de la transacción"),
      description: z.string().describe("Descripción del movimiento"),
      type: z.string().optional().describe("Tipo de transacción (Gasto, Ingreso...)"),
      spendType: z.string().optional().describe("Categoría del gasto"),
      origin: z.string().optional().describe("ID de la cuenta origen"),
    },
    async (input) => {
      try {
        const page = await notion.pages.create({
          parent: { database_id: DB_TRANSACTIONS_ID },
          properties: {
            "Transaction Date": {
              date: { start: input.date },
            },
            "Transaction Amount": {
              number: input.amount,
            },
            "Decription": {
              title: [{ text: { content: input.description } }],
            },
            ...(input.type && {
              "Type Transacction": { select: { name: input.type } },
            }),
            ...(input.spendType && {
              "Type Spend": { select: { name: input.spendType } },
            }),
            "Origen": input.origin
              ? { relation: [{ id: input.origin }] }
              : { relation: [] },
          },
        });

        return {
          content: [
            {
              type: "text",
              text: `Movimiento insertado con éxito (ID: ${page.id})`,
            },
          ],
        };
      } catch (err: unknown) {
        const error = err as Error;
        return {
          content: [
            {
              type: "text",
              text: `❌ Error al insertar movimiento: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    }
  );
 
}
