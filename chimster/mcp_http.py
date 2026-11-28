"""Read-only MCP HTTP with optional operator-configured TLS/OAuth; no SSE."""
import json
import os
import secrets
import stat
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SESSION_TTL=900
MAX_SESSIONS=8
MAX_BODY=1024*1024

def create_token(path):
    p=Path(path).expanduser()
    token=secrets.token_urlsafe(32)
    fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"w",encoding="ascii") as f:
        f.write(token+"\n")
    return token

def read_token(path):
    p=Path(path).expanduser()
    s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_size>128:
        raise ValueError("invalid token file")
    if os.name=="posix" and (s.st_uid!=os.getuid() or s.st_mode&0o077):
        raise ValueError("token file must be private")
    token=p.read_text(encoding="ascii").strip()
    if len(token)<32 or not token.isascii() or not all(c.isalnum() or c in "-_" for c in token):
        raise ValueError("invalid token")
    return token

class Server(HTTPServer):
    def __init__(self,project,token=None,port=0,oauth=None):
        from .mcp_bridge import Bridge
        self.project=project
        self.token=token
        self.oauth=oauth
        if oauth is None and not token:raise ValueError("token required")
        self.sessions={}
        self.bridge_factory=lambda:Bridge(project)
        super().__init__((oauth.bind,oauth.port) if oauth else ("127.0.0.1",port),Handler)
        if oauth:
            try:self.socket=oauth.tls.wrap_socket(self.socket,server_side=True,do_handshake_on_connect=False)
            except Exception:
                self.server_close();raise
    def get_request(self):
        sock,address=super().get_request()
        sock.settimeout(10)
        return sock,address
    def expire(self):
        now=time.monotonic()
        for key,(bridge,version,last,principal) in list(self.sessions.items()):
            if now-last>SESSION_TTL:
                self.drop(key)
    def drop(self,key):
        bridge,_,_,_=self.sessions.pop(key)
        if bridge.jobs:bridge.jobs.close()
        if bridge.production_jobs:bridge.production_jobs.close()
    def server_close(self):
        for key in list(self.sessions):self.drop(key)
        super().server_close()

class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.0"
    def setup(self):
        super().setup()
        self.connection.settimeout(10)
    def log_message(self,*args):
        pass
    def reply(self,status,data=None,session=None):
        body=b"" if data is None else json.dumps(data,ensure_ascii=True,allow_nan=False).encode("ascii")
        self.send_response(status)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        if body:self.send_header("Content-Type","application/json")
        if status==401:
            challenge="Bearer"
            if self.server.oauth:challenge+=' resource_metadata="'+self.server.oauth.resource.removesuffix("/mcp")+'/.well-known/oauth-protected-resource/mcp", scope="chimster:read"'
            self.send_header("WWW-Authenticate",challenge)
        if session:self.send_header("Mcp-Session-Id",session)
        self.end_headers()
        if body:self.wfile.write(body)
    def validate_host(self):
        port=self.server.server_port
        allowed=([self.server.oauth.host],) if self.server.oauth else ([f"127.0.0.1:{port}"],[f"localhost:{port}"])
        hosts=self.headers.get_all("Host",[])
        if [v.lower() for v in hosts] not in allowed or self.headers.get("Origin") is not None:
            self.reply(403);return False
        return True
    def authorized(self):
        if self.path!="/mcp":
            self.reply(404);return False
        if not self.validate_host():return False
        auth=self.headers.get_all("Authorization",[])
        if len(auth)!=1 or not auth[0].isascii() or not auth[0].startswith("Bearer "):
            self.reply(401);return False
        if self.server.oauth:
            self.principal=self.server.oauth.authenticate(auth[0][7:])
        else:
            self.principal="local" if secrets.compare_digest(auth[0],"Bearer "+self.server.token) else None
        if self.principal is None:
            self.reply(401);return False
        self.server.expire()
        return True
    def do_GET(self):
        if self.server.oauth and self.path in ("/.well-known/oauth-protected-resource/mcp","/.well-known/oauth-protected-resource"):
            if self.validate_host():self.reply(200,self.server.oauth.metadata())
            return
        if self.authorized():self.reply(405)
    def do_DELETE(self):
        if not self.authorized():return
        key=self.headers.get("Mcp-Session-Id")
        if key not in self.server.sessions or self.server.sessions[key][3]!=self.principal:self.reply(404);return
        self.server.drop(key)
        self.reply(204)
    def do_POST(self):
        if not self.authorized():return
        if self.headers.get("Transfer-Encoding") or self.headers.get_content_type()!="application/json":
            self.reply(415);return
        try:
            lengths=self.headers.get_all("Content-Length",[])
            if len(lengths)!=1:raise ValueError()
            n=int(lengths[0])
            if not 0<n<=MAX_BODY:raise ValueError()
            msg=json.loads(self.rfile.read(n))
            if not isinstance(msg,dict):raise ValueError()
        except (ValueError,UnicodeError,RecursionError,OSError):
            self.reply(400);return
        from .mcp_modern import VERSION,modern_request,dispatch,error
        if self.headers.get("MCP-Protocol-Version")==VERSION or modern_request(msg):
            params=msg.get("params",{})
            params=params if isinstance(params,dict) else {}
            method=msg.get("method")
            expected=params.get("name") if method in ("tools/call","prompts/get") else params.get("uri") if method=="resources/read" else None
            if (self.headers.get_all("MCP-Protocol-Version",[])!=[VERSION] or
                self.headers.get_all("Mcp-Method",[])!=[method] or
                (expected is not None and self.headers.get_all("Mcp-Name",[])!=[expected]) or
                self.headers.get("Mcp-Session-Id") is not None):
                self.reply(400,error(msg,-32020,"Header mismatch"));return
            bridge=self.server.bridge_factory()
            bridge.transport="oauth-https" if self.server.oauth else "loopback-http"
            try:
                result=dispatch(bridge,msg)
                code=result.get("error",{}).get("code")
                self.reply(404 if code==-32601 else 400 if code else 200,result)
            finally:
                if bridge.jobs:bridge.jobs.close()
                if bridge.production_jobs:bridge.production_jobs.close()
            return
        key=self.headers.get("Mcp-Session-Id")
        if msg.get("method")=="initialize" and key is None:
            if len(self.server.sessions)>=MAX_SESSIONS:
                self.reply(503);return
            bridge=self.server.bridge_factory()
            bridge.transport="oauth-https" if self.server.oauth else "loopback-http"
            result=bridge.dispatch(msg)
            if result is None or "result" not in result:
                if bridge.jobs:bridge.jobs.close()
                if bridge.production_jobs:bridge.production_jobs.close()
                self.reply(400,result);return
            # HTTP JSON-only transport does not support push subscriptions.
            result["result"]["capabilities"]["resources"]={}
            version=result["result"]["protocolVersion"]
            if version=="2024-11-05":
                if bridge.jobs:bridge.jobs.close()
                if bridge.production_jobs:bridge.production_jobs.close()
                self.reply(400);return
            key=secrets.token_urlsafe(24)
            self.server.sessions[key]=(bridge,version,time.monotonic(),self.principal)
            self.reply(200,result,key);return
        if key not in self.server.sessions or self.server.sessions[key][3]!=self.principal:
            self.reply(404 if key else 400);return
        bridge,version,_,_=self.server.sessions[key]
        supplied=self.headers.get("MCP-Protocol-Version")
        if supplied!=version and not (supplied is None and version=="2025-03-26"):
            self.reply(400);return
        self.server.sessions[key]=(bridge,version,time.monotonic(),self.principal)
        if msg.get("method") in ("resources/subscribe","resources/unsubscribe"):
            result={"jsonrpc":"2.0","id":msg.get("id"),"error":{"code":-32601,"message":"Subscriptions require stdio"}}
        else:
            result=bridge.dispatch(msg)
        self.reply(202 if result is None else 200,result)

def run(project,token_file,port):
    token=read_token(token_file)
    with Server(project,token,port) as server:
        print(json.dumps({"url":f"http://127.0.0.1:{server.server_port}/mcp","access":"read-only","authentication":"Bearer token from selected file"}),flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass


def run_remote(project,config_file):
    from .mcp_oauth import OAuthConfig
    config=OAuthConfig(config_file)
    with Server(project,oauth=config) as server:
        print(json.dumps({"url":config.resource,"access":"read-only","authentication":"OAuth introspection over TLS"}),flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
