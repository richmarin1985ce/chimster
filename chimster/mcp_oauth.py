"""Operator-configured OAuth protected resource. No hosted identity service."""
import base64
import hashlib
import ipaddress
import json
import os
import ssl
import stat
import time
from pathlib import Path
from urllib.parse import urlsplit,urlencode
from urllib.request import Request,build_opener,HTTPRedirectHandler,HTTPSHandler

SCOPE="chimster:read"

def https_url(value,resource=False):
    if not isinstance(value,str):raise ValueError("URL required")
    u=urlsplit(value)
    if u.scheme!="https" or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError("explicit HTTPS URL required")
    if resource and u.path!="/mcp":raise ValueError("resource URL must end in /mcp")
    return u

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

class OAuthConfig:
    def __init__(self,path):
        p=Path(path).expanduser()
        st=p.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_size>16384:
            raise ValueError("invalid OAuth config")
        if os.name=="posix" and (st.st_uid!=os.getuid() or st.st_mode&0o077):
            raise ValueError("OAuth config must be private")
        data=json.loads(p.read_text(encoding="utf-8"))
        required={"resource","issuer","introspection_endpoint","client_id","client_secret","certfile","keyfile"}
        if set(data)-required-{"bind","port"} or not required<=set(data):
            raise ValueError("invalid OAuth configuration")
        self.resource=data["resource"]
        url=https_url(self.resource,True)
        self.host=url.netloc.lower()
        self.issuer=data["issuer"]
        https_url(self.issuer)
        self.endpoint=data["introspection_endpoint"]
        https_url(self.endpoint)
        self.client_id=data["client_id"]
        self.client_secret=data["client_secret"]
        if not all(isinstance(v,str) and 1<=len(v)<=2048 for v in (self.client_id,self.client_secret)):
            raise ValueError("invalid introspection credentials")
        self.bind=str(ipaddress.IPv4Address(data.get("bind","127.0.0.1")))
        self.port=data.get("port",url.port or 443)
        if type(self.port) is not int or not 1<=self.port<=65535:raise ValueError("invalid port")
        self.tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.tls.minimum_version=ssl.TLSVersion.TLSv1_2
        self.tls.load_cert_chain(data["certfile"],data["keyfile"])
        self.opener=build_opener(NoRedirect(),HTTPSHandler(context=ssl.create_default_context()))

    def metadata(self):
        return {"resource":self.resource,"authorization_servers":[self.issuer],
                "scopes_supported":[SCOPE],"bearer_methods_supported":["header"]}

    def authenticate(self,token):
        # RFC 7662 introspection. No local JWT acceptance or unsigned claims.
        if not isinstance(token,str) or not 1<=len(token)<=4096 or not token.isascii() or any(c.isspace() for c in token):
            return None
        from urllib.parse import quote_plus
        credentials=quote_plus(self.client_id)+":"+quote_plus(self.client_secret)
        basic=base64.b64encode(credentials.encode("ascii")).decode("ascii")
        req=Request(self.endpoint,data=urlencode({"token":token,"token_type_hint":"access_token"}).encode("ascii"),
                    headers={"Authorization":"Basic "+basic,"Content-Type":"application/x-www-form-urlencoded","Accept":"application/json"},
                    method="POST")
        try:
            with self.opener.open(req,timeout=5) as r:
                raw=r.read(32769)
            if len(raw)>32768:return None
            data=json.loads(raw)
            if not isinstance(data,dict):return None
            aud=data.get("aud")
            valid_aud=aud==self.resource or isinstance(aud,list) and self.resource in aud
            exp=data.get("exp")
            if data.get("active") is not True or data.get("iss")!=self.issuer or not valid_aud or type(exp) not in (int,float) or not time.time()<exp:
                return None
            if not isinstance(data.get("scope"),str) or SCOPE not in data["scope"].split():return None
            if not isinstance(data.get("sub"),str) or not data["sub"]:return None
            # Bind HTTP session to the exact access token without retaining it.
            return hashlib.sha256(token.encode("ascii")).hexdigest()
        except (OSError,ValueError,TypeError,UnicodeError):
            return None
