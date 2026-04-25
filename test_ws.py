import asyncio
import websockets

async def test():
    try:
        ws = await websockets.connect('ws://192.168.31.121:8175', ping_interval=None)
        print("Connected!")
        await ws.close()
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

asyncio.run(test())
