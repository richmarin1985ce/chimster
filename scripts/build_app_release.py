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
        subprocess.run([sys.executable,"-m","PyInstaller","--noconfirm","--onefile","--name","chimster","--distpath",str(stage),"--workpath",str(p/"work"),"--specpath",str(p),"--paths",str(root),"--collect-all","glcontext","--collect-all","panda3d","--copy-metadata","panda3d","--collect-data","chimster","--collect-all","tkinterdnd2","--collect-submodules","fontTools","--add-data",str(root/"docs")+":chimster/manual",str(entry)],check=True,cwd=root)
        archive=output/f"chimster-{version}-{target_platform()}.zip"
        report=build(stage,archive,version,name)
        install=Installation(p/"installed");install.install(archive,report["sha256"],True)
        active=install.activate(version);exe=active["entrypoint"]
        subprocess.run([exe,"--help"],check=True,timeout=120)
        subprocess.run([exe,"project","create",str(p/"sample"),"Sample","newvegas"],check=True,timeout=120)
        subprocess.run([exe,"project","verify",str(p/"sample")],check=True,timeout=120)
        (output/(archive.name+".sha256")).write_text(report["sha256"]+"  "+archive.name+"\n",encoding="ascii")
        print(json.dumps({"archive":str(archive),"sha256":report["sha256"],"installed_smoke_test":True},indent=2))
if __name__=="__main__":main()
