#!/usr/bin/env python3
"""VFB MCP 서버를 curl 없이 직접 호출하는 최소 클라이언트 (표준 라이브러리만).
  vfb_mcp.py tools                      # 도구 목록
  vfb_mcp.py call <tool> '<json args>'  # 도구 호출
"""
import sys, json, urllib.request
URL = "https://vfb3-mcp.virtualflybrain.org"
H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
sid = None
def rpc(method, params=None, _id=1, notify=False):
    global sid
    body = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if not notify: body["id"] = _id
    h = dict(H); 
    if sid: h["Mcp-Session-Id"] = sid
    req = urllib.request.Request(URL, json.dumps(body).encode(), h, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        sid = r.headers.get("Mcp-Session-Id", sid)
        raw = r.read().decode(); ctype = r.headers.get("Content-Type", "")
    if notify or not raw.strip(): return None
    if "text/event-stream" in ctype:  # SSE 형식이면 data: 줄만 모아 JSON으로
        raw = "".join(l[5:] for l in raw.splitlines() if l.startswith("data:"))
    return json.loads(raw)
rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "fly-brain-lab", "version": "0"}})
rpc("notifications/initialized", notify=True)
if sys.argv[1] == "tools":
    for t in rpc("tools/list", _id=2)["result"]["tools"]:
        print(f"- {t['name']}: {t.get('description','').strip().splitlines()[0][:140]}")
else:
    res = rpc("tools/call", {"name": sys.argv[2], "arguments": json.loads(sys.argv[3] if len(sys.argv) > 3 else "{}")}, _id=3)
    for c in res["result"]["content"]:
        print(c.get("text", json.dumps(c)[:2000]))
