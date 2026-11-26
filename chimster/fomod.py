"""Minimal FOMOD metadata for staged packages; no complex conditional installer."""
from pathlib import Path,PurePosixPath
import xml.etree.ElementTree as ET

def write_fomod(root,name,author,version,files):
    root=Path(root).resolve(strict=True)
    if not root.is_dir() or not all(isinstance(x,str) and x.strip() for x in (name,author,version)):raise ValueError("invalid metadata")
    validated=[];seen=set()
    for value in files:
        p=PurePosixPath(value)
        if not p.parts or p.is_absolute() or ".." in p.parts or "\\" in value or ":" in value or p.parts[0].casefold()=="fomod":raise ValueError("unsafe installer path")
        key=p.as_posix().casefold()
        if key in seen:raise ValueError("duplicate destination")
        seen.add(key)
        real=root.joinpath(*p.parts).resolve(strict=True)
        if not real.is_relative_to(root) or not real.is_file():raise ValueError("missing file")
        validated.append(p.as_posix())
    if not validated:raise ValueError("empty installer")
    folder=root/"fomod";folder.mkdir(exist_ok=False)
    info=ET.Element("fomod")
    for tag,val in [("Name",name),("Author",author),("Version",version)]:ET.SubElement(info,tag).text=val
    config=ET.Element("config",{"xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance","xsi:noNamespaceSchemaLocation":"http://qconsulting.ca/fo3/ModConfig5.0.xsd"})
    ET.SubElement(config,"moduleName").text=name
    required=ET.SubElement(config,"requiredInstallFiles")
    for path in sorted(validated):ET.SubElement(required,"file",{"source":path,"destination":path})
    ET.ElementTree(info).write(folder/"info.xml",encoding="utf-8",xml_declaration=True)
    ET.ElementTree(config).write(folder/"ModuleConfig.xml",encoding="utf-8",xml_declaration=True)
    return folder
