# ABOUTME: Characterizes original Algorithm file and doctrine saves before changing their callers.
# ABOUTME: Runs actual native writes and Git failures in isolated synthetic roots with inference absent.
import json
import os
from pathlib import Path
import subprocess
import unittest
import test_memory_algorithm_edits as fixture


class NativeAlgorithmEditTests(unittest.TestCase):
    native_module = 'algorithm-tab.ts'
    create_fixture = fixture.MemoryAlgorithmEditTests.create_fixture
    native_module_name = fixture.MemoryAlgorithmEditTests.native_module_name
    stop_dashboard = fixture.MemoryAlgorithmEditTests.stop_dashboard
    stop_pulse = fixture.MemoryAlgorithmEditTests.stop_pulse
    login = fixture.MemoryAlgorithmEditTests.login
    seed = fixture.MemoryAlgorithmEditTests.seed

    def setUp(self):
        fixture.MemoryAlgorithmEditTests.setUp(self)
        tools=self.root/'LIFEOS/TOOLS'
        source=tools.resolve()
        tools.unlink()
        tools.mkdir()
        for entry in source.iterdir():
            if entry.name != 'Inference.ts': (tools/entry.name).symlink_to(entry,target_is_directory=entry.is_dir())
        self.assertFalse((tools/'Inference.ts').exists())

    def control(self, operation, body):
        source=Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])/'LIFEOS/PULSE/modules/algorithm-tab.ts'
        program=self.fixture.home/'algorithm-edit-control.ts'
        program.write_text(source.read_text()+'''\nconst input=JSON.parse(process.argv[2]);\nconst response=await (input.operation===\"file\"?saveFile(input.body):saveDoctrine(input.body));\nconsole.log(JSON.stringify({control:true,status:response.status,body:await response.json()}));\n''')
        result=subprocess.run(['bun','--no-install',str(program),json.dumps({'operation':operation,'body':body})],
            capture_output=True,text=True,timeout=30,env=dict(os.environ,HOME=str(self.fixture.home)))
        self.assertEqual((result.returncode,result.stderr),(0,''),result.stdout+result.stderr)
        rows=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{"control":true,')]
        self.assertEqual(len(rows),1,result.stdout)
        return rows[0]

    def test_original_file_save_frontmatter_stale_gate_and_syntax_characterization(self):
        path=self.seed()
        before=path.read_text()
        saved=self.control('file',{'id':'operational-rules','content':before.replace('complete observed','current observed')})
        self.assertEqual(saved['status'],200)
        self.assertEqual(set(saved['body']),{'ok','mtime','commit'})
        self.assertFalse(saved['body']['commit']['committed'])
        self.assertIn('git add failed:',saved['body']['commit']['detail'])
        self.assertIn('version: 1.2.4',path.read_text())
        self.assertIn('last_updated_by: pulse-algorithm-tab',path.read_text())
        current=path.read_bytes()
        refused=self.control('file',{'id':'operational-rules','content':before,'expectedMtime':'2000-01-01T00:00:00.000Z'})
        self.assertEqual(refused['status'],409)
        self.assertEqual(path.read_bytes(),current)
        hook=self.root/'hooks/LoadMemory.hook.ts'
        original=hook.read_bytes()
        syntax=self.control('file',{'id':'load-memory-hook','content':'function broken( { '+('synthetic '*10)})
        self.assertEqual(syntax['status'],422)
        self.assertEqual(hook.read_bytes(),original)

    def test_original_doctrine_save_header_changelog_and_tag_refusal_characterization(self):
        directory=self.root/'LIFEOS/ALGORITHM'
        old=(directory/'v3.2.1.md').read_bytes()
        body={'content':'# The Algorithm 3.2.1\n\n'+('Synthetic doctrine claim. '*30),'bump':'patch','note':'Synthetic native version note.'}
        saved=self.control('doctrine',body)
        self.assertEqual(saved['status'],200)
        self.assertEqual(saved['body']['version'],'3.2.2')
        self.assertEqual(saved['body']['previous'],'3.2.1')
        self.assertFalse(saved['body']['commit']['committed'])
        self.assertEqual((directory/'LATEST').read_text(),'3.2.2\n')
        self.assertTrue((directory/'v3.2.2.md').read_text().startswith('# The Algorithm 3.2.2\n'))
        self.assertIn('Synthetic native version note.',(directory/'changelog.md').read_text())
        (directory/'v3.2.3.md').write_text('Synthetic immutable tag.\n')
        refused=self.control('doctrine',body)
        self.assertEqual(refused['status'],409)
        self.assertEqual((directory/'v3.2.3.md').read_text(),'Synthetic immutable tag.\n')
        self.assertEqual((directory/'v3.2.1.md').read_bytes(),old)

    def test_original_git_commit_includes_unrelated_staged_files_known_bug(self):
        path=self.seed()
        repo=(self.root/'LIFEOS/USER').resolve()
        def git(*args):
            result=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            return result.stdout
        git('init','-q','-b','feature/synthetic-native-algorithm')
        git('config','user.name','Synthetic Algorithm Test')
        git('config','user.email','test@example.invalid')
        other=repo/'unrelated.txt'
        other.write_text('Synthetic original file.\n')
        git('add','--','CONFIG/OPERATIONAL_RULES.md','unrelated.txt')
        git('commit','-q','-m','test(algorithm): seed native files')
        other.write_text('Synthetic unrelated staged change.\n')
        git('add','--','unrelated.txt')
        saved=self.control('file',{'id':'operational-rules', 'content':path.read_text().replace('complete observed','current observed')})
        self.assertEqual(saved['status'],200)
        self.assertTrue(saved['body']['commit']['committed'])
        self.assertEqual(set(git('show','--name-only','--format=','HEAD').split()),{'CONFIG/OPERATIONAL_RULES.md','unrelated.txt'})
        self.assertEqual(git('diff','--cached','--name-only'),'')
