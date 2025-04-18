# client.py (Run this on your Windows PC)

import asyncio
import websockets

async def send_command(uri, command):
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(command)
            print(f"Sent command: {command}")
            response = await websocket.recv()
            print(f"Received response: {response}")
    except ConnectionRefusedError:
        print(f"Error: Could not connect to the server at {uri}. Make sure the server is running.")
    except Exception as e:
        print(f"An error occurred: {e}")

async def main():
    uri = "ws://192.168.1.38:8765"  # Replace with your Raspberry Pi's IP address
    while True:
        command = input("Enter command to send (or 'exit' to quit): ")
        if command.lower() == "exit":
            break
        await send_command(uri, command)

if __name__ == "__main__":
    asyncio.run(main())