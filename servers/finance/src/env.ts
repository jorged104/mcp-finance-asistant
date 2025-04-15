import { config } from "dotenv";
config();

export const NOTION_TOKEN = process.env.NOTION_TOKEN!;
export const DB_ACCOUNTS_ID = process.env.NOTION_DB_ACCOUNTS!;
export const DB_TRANSACTIONS_ID = process.env.NOTION_DB_TRANSACTIONS!;
