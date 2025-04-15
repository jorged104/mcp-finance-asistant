import asyncio
from typing import Optional
from contextlib import AsyncExitStack
from config import load_config  
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self, api_key: str):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.client = OpenAI(api_key=api_key)
    # methods will go here

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env={"NOTION_TOKEN": "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",
                 "NOTION_DB_ACCOUNTS":"1cf764d59d8c80c0807ad9fb1510dcc7" ,
                 "NOTION_DB_TRANSACTIONS":"1cf764d59d8c8061b615c588e7380709"}
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
    
    async def process_query(self, query: str) -> str:

        """Process a query using OpenAI and available tools (functions)"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        # Obtener herramientas disponibles
        response = await self.session.list_tools()
        functions = [{
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        } for tool in response.tools]

        # Primera llamada al modelo OpenAI con funciones
        response = self.client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=messages,
            functions=functions,
            function_call="auto"
        )
        print("Response:", str(response))
        final_text = []
        message = response.choices[0].message

        while True:
            if response.choices[0].message.content:
                final_text.append(response.choices[0].message.content)
                break

            if message.function_call:
                name = message.function_call.name
                arguments =message.function_call.arguments

                # Ejecutar función
                result = await self.session.call_tool(name, eval(arguments))  # asegúrate que `arguments` sea dict

                # Añadir a la conversación
                messages.append(message)
                messages.append({
                    "role": "function",
                    "name": name,
                    "content": result.content
                })

                # Nueva llamada
                response = self.client.chat.completions.create(
                    model="gpt-4-1106-preview",
                    messages=messages,
                    functions=functions,
                    function_call="auto"
                )
                message = response.choices[0].message.content

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    config = load_config()
    client = MCPClient(config["llm"]["api_key"])
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys

    asyncio.run(main())    