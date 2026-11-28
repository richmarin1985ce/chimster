"""Preview a bounded subset of book markup without rewriting native text."""
from html.parser import HTMLParser
from html import escape
class Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.runs=[];self.stack=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ("br","p"):self.runs.append(("\n",tuple(self.stack)))
        if tag in ("font","div","p","b","i","u","center"):
            self.stack.append((tag,a.get("face","") if tag=="font" else a.get("align","")))
        if tag=="img":self.runs.append(("[Image: "+str(a.get("src",""))+"]",tuple(self.stack)))
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                del self.stack[i:];break
        if tag=="p":self.runs.append(("\n",tuple(self.stack)))
    def handle_data(self,data):
        self.runs.append((data,tuple(self.stack)))
def runs(source):
    if len(source)>256000:raise ValueError("Book markup too large")
    p=Reader();p.feed(source);p.close();return p.runs
def preview_html(source):
    out=[]
    for value,styles in runs(source):
        body=escape(value).replace("\n","<br>")
        for tag,arg in reversed(styles):
            if tag in ("b","i","u"):body=f"<{tag}>{body}</{tag}>"
            elif tag=="font":body='<span data-native-font="'+escape(arg,quote=True)+'">'+body+'</span>'
            elif tag=="center" or arg in ("left","center","right","justify"):
                align="center" if tag=="center" else arg
                body='<span style="display:block;text-align:'+align+'">'+body+'</span>'
        out.append(body)
    return "".join(out)
