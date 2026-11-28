import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from chimster.project import Project

@unittest.skipUnless(importlib.util.find_spec("mcp"),"Independent SDK not installed")
class SDKClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio(self):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory() as d:
            p=Project.create(Path(d)/"project","Demo","newvegas")
            params=StdioServerParameters(command=sys.executable,args=["-m","chimster","--mcp","--project",str(p.root)])
            async with stdio_client(params) as (reader,writer):
                async with ClientSession(reader,writer) as session:
                    result=await session.initialize()
                    self.assertEqual(result.serverInfo.name,"chimster")
                    names={tool.name for tool in (await session.list_tools()).tools}
                    self.assertIn("project_status",names)
                    self.assertNotIn("project_apply_create",names)
                    answer=await session.call_tool("project_status",{})
                    self.assertFalse(answer.isError)
                    self.assertEqual(json.loads(answer.content[0].text)["name"],"Demo")
                    resources=await session.list_resources()
                    self.assertIn("chimster://project/status",{str(r.uri) for r in resources.resources})

if __name__=="__main__":
    unittest.main()
