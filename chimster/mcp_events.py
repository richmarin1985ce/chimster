"""MCP resource subscriptions for committed project metadata."""
import hashlib
import json
import threading

class Subscriptions:
    def __init__(self, read_resource):
        self.read_resource=read_resource
        self.entries={}
        self.lock=threading.Lock()

    def fingerprint(self,uri):
        try:
            contents=self.read_resource(uri)
            return hashlib.sha256(json.dumps(contents,sort_keys=True,ensure_ascii=True).encode()).hexdigest()
        except (OSError,ValueError,KeyError,TypeError):
            return None

    def subscribe(self,uri):
        with self.lock:
            if len(self.entries)>=32 and uri not in self.entries:
                raise ValueError("subscription limit")
            value=self.fingerprint(uri)
            if value is None:
                raise ValueError("resource unavailable")
            self.entries[uri]=value

    def unsubscribe(self,uri):
        with self.lock:
            self.entries.pop(uri,None)

    def poll(self):
        events=[]
        with self.lock:
            for uri,old in list(self.entries.items()):
                current=self.fingerprint(uri)
                if current!=old:
                    self.entries[uri]=current
                    events.append({"jsonrpc":"2.0","method":"notifications/resources/updated","params":{"uri":uri}})
        return events
