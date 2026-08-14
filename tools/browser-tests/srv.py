import asyncio
from pythonosc import osc_bundle, osc_message
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer

def handler(address, *args):
    print("HANDLER", address, args)

async def main():
    d = Dispatcher()
    d.map("/nova/*", handler)
    server = AsyncIOOSCUDPServer(("127.0.0.1", 9002), d, asyncio.get_event_loop())
    t, _ = await server.create_serve_endpoint()
    print("listening 9002")
    await asyncio.sleep(8)

asyncio.run(main())
EOF
echo done