"""Bundle canonical documentation in wheel builds without maintaining duplicate pages."""
from pathlib import Path
from shutil import copytree
from setuptools import setup
from setuptools.command.build_py import build_py

class BuildWithManual(build_py):
    def run(self):
        super().run()
        root=Path(__file__).resolve().parent/"docs"
        dest=Path(self.build_lib)/"chimster"/"manual"
        copytree(root,dest,dirs_exist_ok=True,ignore=lambda d,n:[x for x in n if x.startswith(".") or (Path(d)/x).is_file() and Path(x).suffix.lower() not in {".md",".txt",".rst"}])

setup(cmdclass={"build_py":BuildWithManual})
