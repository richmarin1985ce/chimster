import unittest,struct
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.fnv_quest import export
from chimster.quest_compile import checked,attach
from chimster.fnv_records import scan,HEADER,subs
from chimster.fnv_patch import sub
class CompileTests(unittest.TestCase):
    def test_attach(self):
        spec={"schema":1,"id":"Quest","title":"Quest","stages":[{"index":0,"log":"Start","actions":[{"op":"stage","index":10}]},{"index":10,"log":"Done","complete":True}]}
        with TemporaryDirectory() as d:
            p=Path(d)/"Quest.esp";a=Path(d)/"donor";b=Path(d)/"out";a.mkdir();b.mkdir()
            with self.assertRaises(ValueError):export(spec,p)
            self.assertEqual(export(spec,p,script_draft=True)["uncompiled_scripts"],1)
            raw=p.read_bytes();r=scan(p)["records"][0];i=r["offset"];_,n,*_=HEADER.unpack_from(raw,i);parts=list(subs(raw[i+24:i+24+n]))
            # Synthetic opaque bytes test transport only, not valid GECK bytecode.
            code=b"fixture";source=b"SetStage Quest 10\n"
            h=struct.pack("<4xIIIHH",0,len(code),0,0,1)
            pos=next(k for k,(tag,v) in enumerate(parts) if tag==b"SCHR")
            parts[pos:pos+3]=[(b"SCHR",h),(b"SCDA",code),(b"SCTX",source)]
            body=b"".join(sub(k,v) for k,v in parts);header=raw[i:i+24];delta=len(body)-n
            g=i-24;group=raw[g:g+24]
            donor=raw[:g]+group[:4]+struct.pack("<I",struct.unpack_from("<I",group,4)[0]+delta)+group[8:]+header[:4]+struct.pack("<I",len(body))+header[8:]+body+raw[i+24+n:]
            q=a/p.name;q.write_bytes(donor)
            self.assertEqual(attach(p,q,b/p.name)["attached_scripts"],1)
            self.assertEqual(p.read_bytes(),raw)
            with self.assertRaises(ValueError):checked([(b"SCHR",h),(b"SCDA",code),(b"SCTX",b"wrong")],source)
