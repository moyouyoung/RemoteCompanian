import asyncio
import websockets
import subprocess

async def handler(websocket):
    async for message in websocket:
        print(f"Received command: {message}")
        try:
            # Execute the received command (BE CAREFUL WITH SECURITY!)
            process = subprocess.Popen(message, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await asyncio.get_event_loop().run_in_executor(None, process.communicate)

            if stdout:
                response = f"Command Output:\n{stdout.decode()}"
                await websocket.send(response)
            elif stderr:
                error_response = f"Command Error:\n{stderr.decode()}"
                await websocket.send(error_response)
            else:
                await websocket.send("Command executed successfully (no output).")

        except Exception as e:
            error_message = f"Error executing command: {e}"
            print(error_message)
            await websocket.send(error_message)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("WebSocket server started on ws://0.0.0.0:8765")
        await asyncio.Future()  # Keep the server running

if __name__ == "__main__":
    asyncio.run(main())