import { z } from "zod";
import { notion } from "./notionClient.js";
import { DB_TRANSACTIONS_ID } from "../env.js";
import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";

function getNotionPropertyValue(property: any, type: string): any {
  if (!property || property.type !== type) return null;
  return property[type];
}

export default function registerTools(server: McpServer) {
  server.tool(
    "insert-movement",
    {
      date: z.string().describe("Fecha del movimiento (YYYY-MM-DD)"),
      amount: z.number().describe("Monto de la transacción"),
      description: z.string().describe("Descripción del movimiento"),
      type: z.string().optional().describe("Tipo de transacción (Gasto, Ingreso...)"),
      spendType: z.string().optional().describe("Categoría del gasto"),
      origin: z.string().describe("ID de la cuenta origen"),
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
  
  server.tool(
    "get-latest-movements",
    {
      limit: z.number().default(5).describe("Cantidad de movimientos recientes a devolver"),
    },
    async (input) => { // Cambiado de ({ limit }, extra) a (input)
      try {
        const pages = await notion.databases.query({
          database_id: DB_TRANSACTIONS_ID,
          sorts: [{ property: "Transaction Date", direction: "descending" }],
          page_size: input.limit, // Cambiado de limit a input.limit
        });
        
  const movimientos = pages.results
          .filter((page): page is Extract<typeof page, { properties: any }> => 
            "properties" in page && page.object === "page"
          )
          .map(page => {
            const props = page.properties;
            
            // Usando la función helper para extraer valores de forma segura
            const dateValue = getNotionPropertyValue(props["Transaction Date"], "date");
            const amountValue = getNotionPropertyValue(props["Transaction Amount"], "number");
            const descriptionValue = getNotionPropertyValue(props["Decription"], "title");
            const typeValue = getNotionPropertyValue(props["Type Transacction"], "select");
            const spendTypeValue = getNotionPropertyValue(props["Type Spend"], "select");
            
            return {
              date: dateValue?.start || "",
              amount: amountValue || 0,
              description: descriptionValue?.[0]?.text?.content || "",
              type: typeValue?.name || "",
              spendType: spendTypeValue?.name || "",
            };
          });
        // Convert the movimientos array to a formatted string for text response
        const movimientosText = movimientos.map((mov, idx) =>
          `#${idx + 1} - Fecha: ${mov.date}, Monto: ${mov.amount}, Descripción: ${mov.description}, Tipo: ${mov.type}, Categoría: ${mov.spendType}`
        ).join('\n');

        return {
          content: [{ type: "text", text: movimientosText || "No se encontraron movimientos." }],
        };
      } catch (err: unknown) {
        const error = err as Error;
        return {
          content: [
            {
              type: "text",
              text: `❌ Error al obtener movimientos: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
  "get-movements-by-keyword",
  {
    keyword: z.string().describe("Palabra clave para buscar en la descripción"),
    limit: z.number().default(5).describe("Cantidad máxima de movimientos a devolver"),
  },
  async ({ keyword, limit }) => {
    const pages = await notion.databases.query({
      database_id: DB_TRANSACTIONS_ID,
      filter: {
        property: "Decription",
        rich_text: { contains: keyword },
      },
      page_size: limit,
    });

    const items  = pages.results
          .filter((page): page is Extract<typeof page, { properties: any }> => 
            "properties" in page && page.object === "page"
          )
          .map(page => {
            const props = page.properties;
      return {
        date: getNotionPropertyValue(props["Transaction Date"], "date")?.start || "",
        description: getNotionPropertyValue(props["Decription"], "title")?.[0]?.text?.content || "",
        amount: getNotionPropertyValue(props["Transaction Amount"], "number") || 0,
        category: getNotionPropertyValue(props["Type Spend"], "select")?.name || "",
      };
    });

   const itemsText = items.map((item, i) => 
  `#${i + 1} - ${item.date}: ${item.description} (Q${item.amount}) [${item.category}]`
).join("\n");

return {
  content: [{ type: "text", text: itemsText || "No se encontraron movimientos con esa palabra." }],
};
  }
);

server.tool(
  "get-total-by-category",
  {
    category: z.string().describe("Nombre exacto de la categoría (Type Spend)"),
    startDate: z.string().describe("Fecha inicio (YYYY-MM-DD)"),
    endDate: z.string().describe("Fecha fin (YYYY-MM-DD)"),
  },
  async ({ category, startDate, endDate }) => {
    const results = await notion.databases.query({
      database_id: DB_TRANSACTIONS_ID,
      filter: {
        and: [
          { property: "Type Spend", select: { equals: category } },
          { property: "Transaction Date", date: { on_or_after: startDate } },
          { property: "Transaction Date", date: { on_or_before: endDate } },
        ],
      },
    });

    const total = results.results.reduce((sum, page : any) => {
      const amount = getNotionPropertyValue(page.properties["Transaction Amount"], "number") || 0;
      return sum + amount;
    }, 0);

    return {
      content: [{ type: "text", text: `Total gastado en ${category}: Q${total.toFixed(2)}` }],
    };
  }
);

server.tool(
  "get-movements-by-date-range",
  {
    startDate: z.string().describe("Fecha inicio (YYYY-MM-DD)"),
    endDate: z.string().describe("Fecha fin (YYYY-MM-DD)"),
  },
  async ({ startDate, endDate }) => {
    try {
      const results  = await notion.databases.query({
        database_id: DB_TRANSACTIONS_ID,
        filter: {
          and: [
            { property: "Transaction Date", date: { on_or_after: startDate } },
            { property: "Transaction Date", date: { on_or_before: endDate } },
          ],
        },
        sorts: [{ property: "Transaction Date", direction: "ascending" }],
        page_size: 100, 
      });

      const movimientos  = results.results
.filter((page): page is Extract<typeof page, { properties: any }> => 
            "properties" in page && page.object === "page"
          )
        .map((page) => {
          const props = page.properties;
          return {
            date: getNotionPropertyValue(props["Transaction Date"], "date")?.start || "",
            description: getNotionPropertyValue(props["Decription"], "title")?.[0]?.text?.content || "",
            amount: getNotionPropertyValue(props["Transaction Amount"], "number") || 0,
            category: getNotionPropertyValue(props["Type Spend"], "select")?.name || "",
            type: getNotionPropertyValue(props["Type Transacction"], "select")?.name || "",
          };
        });

      const text = movimientos.map((m, i) =>
        `#${i + 1} - ${m.date}: ${m.description} (Q${m.amount}) [${m.type} / ${m.category}]`
      ).join("\n");

      return {
        content: [{ type: "text", text: text || "No se encontraron movimientos en ese rango." }],
      };
    } catch (err: unknown) {
      const error = err as Error;
      return {
        content: [{ type: "text", text: `❌ Error al consultar movimientos: ${error.message}` }],
        isError: true,
      };
    }
  }
);



}
