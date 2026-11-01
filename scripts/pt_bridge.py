import sys, asyncio
from pathlib import Path
from aiohttp import web
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Lab' / 'Packet Tracer' / 'cisco-pt-mcp'))
from mcp_server.bridge import PTBridge
bridge = PTBridge(tool_timeout=45)
async def status(req):
    return web.json_response({'connected': bridge.is_connected})
async def call(req):
    data = await req.json()
    try:
        result = await bridge.call_tool(data['name'], data.get('arguments', {}))
        return web.json_response(result)
    except Exception as exc:
        return web.json_response({'success':False,'error':str(exc)},status=500)
async def main():
    await bridge.start()
    app=web.Application(); app.router.add_get('/status',status); app.router.add_post('/call',call)
    runner=web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner,'127.0.0.1',7532).start()
    print('Local project bridge ready on 7531; project API on 7532',flush=True)
    await asyncio.Event().wait()
asyncio.run(main())
