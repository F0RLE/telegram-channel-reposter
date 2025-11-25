connected_websockets = set()

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_websockets.add(ws)
    logger.info("Debug client connected")

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'ping':
                    await ws.send_str('pong')
    finally:
        connected_websockets.remove(ws)
        logger.info("Debug client disconnected")

    return ws

async def index_handler(request):
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bot Debug Console</title>
    <style>
        body {
            background-color: #1e1e1e;
            color: #d4d4d4;
            font-family: 'Consolas', 'Monaco', monospace;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            height: 100vh;
            box-sizing: border-box;
        }
        h1 { margin-top: 0; color: #61afef; }
        #log-container {
            flex-grow: 1;
            overflow-y: auto;
            background-color: #252526;
            border: 1px solid #3e3e42;
            padding: 10px;
            border-radius: 4px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .log-entry { margin-bottom: 2px; border-bottom: 1px solid #333; padding: 2px 0; }
        .log-time { color: #569cd6; margin-right: 10px; }
        .log-level { font-weight: bold; margin-right: 10px; }
        .level-INFO { color: #9cdcfe; }
        .level-WARNING { color: #dcdcaa; }
        .level-ERROR { color: #f44747; }
        .level-CRITICAL { color: #d16969; background-color: #330000; }
        .level-DEBUG { color: #808080; }
        #status { margin-bottom: 10px; font-size: 0.9em; color: #808080; }
        .connected { color: #6a9955; }
        .disconnected { color: #f44747; }
    </style>
</head>
<body>
    <h1>🤖 Bot Debug Console</h1>
    <div id="status">Status: <span id="connection-status" class="disconnected">Disconnected</span></div>
    <div id="log-container"></div>

    <script>
        const logContainer = document.getElementById('log-container');
        const statusSpan = document.getElementById('connection-status');
        let ws;

        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = () => {
                statusSpan.textContent = 'Connected';
                statusSpan.className = 'connected';
                addLog('SYSTEM', 'INFO', 'Connected to debug server');
            };

            ws.onclose = () => {
                statusSpan.textContent = 'Disconnected (Retrying...)';
                statusSpan.className = 'disconnected';
                setTimeout(connect, 3000);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    addLog(data.name, data.level, data.message, data.time);
                } catch (e) {
                    console.error('Error parsing log:', e);
                }
            };
        }

        function addLog(name, level, message, time) {
            const div = document.createElement('div');
            div.className = 'log-entry';
            
            const timeSpan = document.createElement('span');
            timeSpan.className = 'log-time';
            timeSpan.textContent = time || new Date().toLocaleTimeString();
            
            const levelSpan = document.createElement('span');
            levelSpan.className = `log-level level-${level}`;
            levelSpan.textContent = `[${level}]`;
            
            const msgSpan = document.createElement('span');
            msgSpan.textContent = `${name}: ${message}`;
            
            div.appendChild(timeSpan);
            div.appendChild(levelSpan);
            div.appendChild(msgSpan);
            
            logContainer.appendChild(div);
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        connect();
    </script>
</body>
</html>
    """
    return web.Response(text=html_content, content_type='text/html')

class WebSocketLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = {
            "time": self.formatter.formatTime(record) if self.formatter else "",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage()
        }
        data = json.dumps(log_entry)
        
        # Broadcast to all connected clients
        # Create a copy of the set to avoid runtime errors if set changes during iteration
        for ws in list(connected_websockets):
            asyncio.create_task(ws.send_str(data))


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

async def start_debug_server(host='127.0.0.1', port=8080):
    # Find available port
    start_port = port
    while is_port_in_use(port):
        port += 1
        if port > start_port + 10: # Try 10 ports
            logger.error(f"Could not find available port between {start_port} and {port}")
            return None

    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    url = f"http://{host}:{port}"
    logger.info(f"Debug server started at {url}")
    
    # Save port to file for launcher to read
    try:
        with open(os.path.join(os.path.dirname(__file__), 'debug_port.txt'), 'w') as f:
            f.write(str(port))
    except Exception as e:
        logger.error(f"Failed to save debug port: {e}")
    
    # Auto-open browser
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.error(f"Failed to open browser: {e}")
        
    return runner


