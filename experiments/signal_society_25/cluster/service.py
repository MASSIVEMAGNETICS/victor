from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from signal_society import SignalSociety25
from .release_train import manifest
from .sentinel import VictorOmniSentinel
from .phylogeny import phylogeny_metrics

class OmniService:
    def __init__(self, db_path: str | Path, seed: int = 25, seed_mode: str = "signal"):
        self.sim=SignalSociety25(db_path,seed,seed_mode)

    def close(self):
        self.sim.db.close()

    def payload(self, path: str, query: dict[str,list[str]]) -> tuple[int,dict]:
        if path=="/health":
            gate=VictorOmniSentinel(self.sim).deployment_gate()
            return (200 if gate["deployable"] else 503),{"service":"victor-omni-sentinel","gate":gate}
        if path=="/sentinel":
            return 200,VictorOmniSentinel(self.sim).scan()
        if path=="/metrics":
            return 200,{**self.sim.metrics(),"phylogeny":phylogeny_metrics(self.sim)}
        if path=="/releases":
            return 200,manifest()
        if path=="/copilot":
            aid=(query.get("agent_id") or ["A14"])[0]
            objective=(query.get("q") or ["What should I inspect next?"])[0]
            parent=(query.get("parent") or [None])[0]
            if aid not in self.sim.agents:
                return 404,{"error":"unknown agent","agent_id":aid}
            return 200,self.sim.learn.copilot(aid,objective,parent)
        return 404,{"error":"not found","routes":["/health","/sentinel","/metrics","/releases","/copilot"]}

def serve(db: str | Path, host: str="0.0.0.0", port: int=8787, seed: int=25, seed_mode: str="signal"):
    app=OmniService(db,seed,seed_mode)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed=urlparse(self.path)
            status,payload=app.payload(parsed.path,parse_qs(parsed.query))
            body=json.dumps(payload,sort_keys=True,indent=2).encode()
            self.send_response(status)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers(); self.wfile.write(body)
        def log_message(self, fmt, *args):
            return
    server=ThreadingHTTPServer((host,int(port)),Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close(); app.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="signal_society_25.db")
    p.add_argument("--host",default="0.0.0.0")
    p.add_argument("--port",type=int,default=8787)
    p.add_argument("--seed",type=int,default=25)
    p.add_argument("--seed-mode",choices=["signal","neutral","none"],default="signal")
    a=p.parse_args()
    serve(a.db,a.host,a.port,a.seed,a.seed_mode)

if __name__=="__main__":
    main()
