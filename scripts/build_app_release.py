"""Build one-file executable and offline installable ZIP; never publish automatically."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess,sys,os,json
from chimster import __version__
from chimster.app_releases import build,Installation,target_platform
def main():
    import panda3d.core
    root=Path(__file__).resolve().parents[1];output=root/"release-output";output.mkdir(exist_ok=True)
    version=__version__;name="chimster.exe" if os.name=="nt" else "chimster"
    with TemporaryDirectory(prefix="chimster-package-") as d:
        p=Path(d);entry=p/"launcher.py";entry.write_text("from chimster.cli import main\nmain()\n",encoding="utf-8")
        stage=p/"dist"
        subprocess.run([sys.executable,"-m","PyInstaller","--noconfirm","--onefile","--name","chimster","--distpath",str(stage),"--workpath",str(p/"work"),"--specpath",str(p),"--paths",str(root),"--collect-all","glcontext","--collect-all","panda3d","--copy-metadata","panda3d","--collect-data","chimster","--add-data",str(root/"docs")+":chimster/manual",str(entry)],check=True,cwd=root)
        archive=output/f"chimster-{version}-{target_platform()}.zip"
        report=build(stage,archive,version,name)
        install=Installation(p/"installed");install.install(archive,report["sha256"],True)
        active=install.activate(version);exe=active["entrypoint"]
        subprocess.run([exe,"--help"],check=True,timeout=120)
        subprocess.run([exe,"project","create",str(p/"sample"),"Sample","newvegas"],check=True,timeout=120)
        subprocess.run([exe,"project","verify",str(p/"sample")],check=True,timeout=120)
        # Exercise the actual installed MCP executable, not the source interpreter.
        config=json.loads(subprocess.check_output([exe,"--mcp","--project",str(p/"sample"),"--client-config"],text=True,timeout=120))
        server=config["mcpServers"]["chimster"]
        if Path(server["command"]).resolve()!=Path(exe).resolve():
            raise ValueError("MCP registration does not target installed executable")
        requests=[
            {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"installer-smoke","version":"1"}}},
            {"jsonrpc":"2.0","method":"notifications/initialized"},
            {"jsonrpc":"2.0","id":2,"method":"tools/list"},
            {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"project_status"}},
            {"jsonrpc":"2.0","id":4,"method":"resources/list"}]
        result=subprocess.run([server["command"],*server["args"]],input="".join(json.dumps(v)+"\n" for v in requests),text=True,capture_output=True,check=True,timeout=120)
        replies={row["id"]:row for row in map(json.loads,result.stdout.splitlines()) if "id" in row}
        if replies[1]["result"]["serverInfo"]["name"]!="chimster" or "project_status" not in {t["name"] for t in replies[2]["result"]["tools"]}:
            raise ValueError("MCP installer handshake failed")
        status=json.loads(replies[3]["result"]["content"][0]["text"])
        if status["name"]!="Sample" or status["revision"]!=0 or not replies[4]["result"]["resources"]:
            raise ValueError("MCP installer project inspection failed")
        (output/(archive.name+".sha256")).write_text(report["sha256"]+"  "+archive.name+"\n",encoding="ascii")
        print(json.dumps({"archive":str(archive),"sha256":report["sha256"],"installed_smoke_test":True},indent=2))
if __name__=="__main__":main()
