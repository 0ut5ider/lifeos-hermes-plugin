# ABOUTME: Exercises Algorithm file and versioned doctrine edits through actual authenticated native HTTP.
# ABOUTME: Requires current owner publication, native syntax and version semantics, and unchanged later bytes.
import json
from pathlib import Path
import unittest
import subprocess
import importlib
import os
import sys
import signal
import time
from lifeos_hook_bridge.memory_access import NativeMemory
import httpx
import test_memory_algorithm_jobs as fixture

RULES = 'LIFEOS/USER/CONFIG/OPERATIONAL_RULES.md'


class MemoryAlgorithmEditTests(unittest.TestCase):
    native_module = 'algorithm-tab.ts'
    create_fixture = fixture.MemoryAlgorithmJobRelayTests.create_fixture
    native_module_name = fixture.MemoryAlgorithmJobRelayTests.native_module_name
    stop_dashboard = fixture.MemoryAlgorithmJobRelayTests.stop_dashboard
    stop_pulse = fixture.MemoryAlgorithmJobRelayTests.stop_pulse
    login = fixture.MemoryAlgorithmJobRelayTests.login
    setUp = fixture.MemoryAlgorithmJobRelayTests.setUp

    def seed(self):
        path = self.root / RULES
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('---\nversion: 1.2.3\nlast_updated: 2000-01-01T00:00:00Z\nlast_updated_by: synthetic\n---\n# Synthetic operating rules\n\nKeep a complete observed result before publication.\n')
        path.chmod(0o600)
        return path

    def test_anonymous_edits_refuse_before_source_or_version_change(self):
        path = self.seed()
        before = path.read_bytes()
        for target, body in [('/file', {'id':'operational-rules','content':'Synthetic changed rule. '*5}),
                ('/doctrine', {'content':'Synthetic doctrine. '*40,'bump':'patch','note':'Synthetic update note.'})]:
            response=httpx.post(self.native+'/api/algorithm-tab'+target,json=body)
            self.assertEqual(response.status_code,401,response.text)
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual((self.root/'LIFEOS/ALGORITHM/LATEST').read_text(),'3.2.1\n')

    def test_owner_file_save_keeps_native_frontmatter_and_stale_write_refusal(self):
        path = self.seed()
        content = path.read_text().replace('Keep a complete observed result before publication.', 'Keep all current observed results before each owner publication.')
        with httpx.Client(timeout=45) as client:
            self.login(client)
            view=client.get(self.native+'/api/algorithm-tab/file?id=operational-rules')
            self.assertEqual(view.status_code,200,view.text)
            body={'id':'operational-rules','content':content,'expectedMtime':view.json()['mtime']}
            result=client.post(self.native+'/api/algorithm-tab/file',json=body)
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(set(result.json()),{'ok','mtime','commit'})
            self.assertTrue(result.json()['ok'])
            self.assertEqual(set(result.json()['commit']),{'committed','detail'})
            saved=path.read_text()
            self.assertIn('version: 1.2.4',saved)
            self.assertIn('last_updated_by: pulse-algorithm-tab',saved)
            self.assertIn('Keep all current observed results before each owner publication.',saved)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            stale=client.post(self.native+'/api/algorithm-tab/file',json=body)
            self.assertEqual(stale.status_code,409,stale.text)
            self.assertEqual(path.read_text(),saved)

    def test_invalid_hook_syntax_refuses_without_source_change(self):
        path=self.root/'hooks/LoadMemory.hook.ts'
        before=path.read_bytes()
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/file',json={'id':'load-memory-hook','content':'function broken( { '+('synthetic '*10)})
            self.assertEqual(result.status_code,422,result.text)
        self.assertEqual(path.read_bytes(),before)

    def test_owner_doctrine_save_versions_fixed_files_and_preserves_existing_next_tag(self):
        content='# The Algorithm 3.2.1\n\n'+('Synthetic testable doctrine claim. '*25)
        directory=self.root/'LIFEOS/ALGORITHM'
        before=(directory/'v3.2.1.md').read_bytes()
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/doctrine',json={'content':content,'bump':'patch','note':'Synthetic doctrine update.'})
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(set(result.json()),{'ok','version','previous','commit'})
            self.assertEqual(result.json()['version'],'3.2.2')
            self.assertEqual(result.json()['previous'],'3.2.1')
            self.assertEqual((directory/'LATEST').read_text(),'3.2.2\n')
            self.assertTrue((directory/'v3.2.2.md').read_text().startswith('# The Algorithm 3.2.2\n'))
            self.assertIn('Synthetic doctrine update.',(directory/'changelog.md').read_text())
            for name in ('LATEST','v3.2.2.md','changelog.md'):
                self.assertEqual((directory/name).stat().st_mode & 0o777,0o600)
            immutable=directory/'v3.2.3.md'
            immutable.write_text('Synthetic immutable next tag.\n')
            blocked=client.post(self.native+'/api/algorithm-tab/doctrine',json={'content':content,'bump':'patch','note':'Another synthetic doctrine update.'})
            self.assertEqual(blocked.status_code,409,blocked.text)
            self.assertEqual(immutable.read_text(),'Synthetic immutable next tag.\n')
            self.assertEqual((directory/'LATEST').read_text(),'3.2.2\n')
        self.assertEqual((directory/'v3.2.1.md').read_bytes(),before)

    def test_owner_commit_preserves_unrelated_staged_files(self):
        path=self.seed()
        repo=(self.root/'LIFEOS/USER').resolve()
        def git(*args):
            result=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            return result.stdout
        git('init','-q','-b','feature/synthetic-algorithm')
        git('config','user.name','Synthetic Algorithm Test')
        git('config','user.email','test@example.invalid')
        other=repo/'unrelated.txt'
        other.write_text('Synthetic original staged file.\n')
        git('add','--','CONFIG/OPERATIONAL_RULES.md','unrelated.txt')
        git('commit','-q','-m','test(algorithm): seed files')
        other.write_text('Synthetic separate staged change.\n')
        git('add','--','unrelated.txt')
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/file',json={'id':'operational-rules',
                'content':path.read_text().replace('Keep a complete observed result before publication.', 'Keep each current observed result before publication.')})
            self.assertEqual(result.status_code,200,result.text)
            self.assertTrue(result.json()['commit']['committed'],result.text)
        self.assertEqual(git('show','--name-only','--format=','HEAD').strip(),'CONFIG/OPERATIONAL_RULES.md')
        self.assertEqual(git('diff','--cached','--name-only').strip(),'unrelated.txt')
        self.assertEqual(other.read_text(),'Synthetic separate staged change.\n')

    def instrument_render(self, callback):
        self.fixture.login()
        self.fixture.client.get('/api/plugins/lifeos-hook-bridge/memory/pulse/state')
        module=importlib.import_module('lifeos_memory_settings.memory_algorithm_edit')
        original=module._render
        seen=[]
        def render(*args,**kwargs):
            result=original(*args,**kwargs)
            seen.append(result[0]['status'])
            callback()
            return result
        module._render=render
        self.addCleanup(setattr,module,'_render',original)
        return seen

    def test_actual_render_source_change_preserves_the_later_owner_file(self):
        path=self.seed()
        changed='Synthetic later owner rule. '*4
        seen=self.instrument_render(lambda:path.write_text(changed))
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/file',json={'id':'operational-rules','content':'Synthetic requested rule. '*4})
            self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(seen,[200])
        self.assertEqual(path.read_text(),changed)

    def test_actual_render_owner_revocation_refuses_publication(self):
        path=self.seed()
        before=path.read_bytes()
        seen=self.instrument_render(lambda:self.fixture.configuration.update(lambda value:value['accounts'].pop('dashboard:basic:synthetic-owner')))
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/file',json={'id':'operational-rules','content':'Synthetic requested rule. '*4})
            self.assertEqual(result.status_code,403,result.text)
        self.assertEqual(seen,[200])
        self.assertEqual(path.read_bytes(),before)

    def test_actual_doctrine_render_preserves_a_later_immutable_tag(self):
        directory=self.root/'LIFEOS/ALGORITHM'
        tag=directory/'v3.2.2.md'
        seen=self.instrument_render(lambda:tag.write_text('Synthetic later immutable version.\n'))
        before={name:(directory/name).read_bytes() for name in ('LATEST','changelog.md','v3.2.1.md')}
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/doctrine',json={'content':'Synthetic doctrine claim. '*30,'bump':'patch','note':'Synthetic version note.'})
            self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(seen,[200])
        self.assertEqual(tag.read_text(),'Synthetic later immutable version.\n')
        self.assertEqual({name:(directory/name).read_bytes() for name in before},before)

    def test_bounded_fixed_private_and_linked_file_requests_refuse(self):
        path=self.seed()
        before=path.read_bytes()
        with httpx.Client(timeout=45) as client:
            self.login(client)
            for body,expected in [({'id':'../outside','content':'Synthetic requested rule. '*4},404),
                    ({'id':'operational-rules','content':'Synthetic requested rule. '*4,'path':'outside'},400),
                    ({'id':'operational-rules','content':'x'*300000},400),
                    ({'id':'operational-rules','content':'<private>Synthetic excluded rule.</private>'*3},503)]:
                with self.subTest(body_keys=sorted(body),expected=expected):
                    result=client.post(self.native+'/api/algorithm-tab/file',json=body)
                    self.assertEqual(result.status_code,expected,result.text)
                    self.assertEqual(result.headers.get('cache-control'),'no-store')
                    self.assertEqual(path.read_bytes(),before)
            outside=self.fixture.home/'outside-synthetic-rule.md'
            outside.write_bytes(before)
            path.unlink()
            path.symlink_to(outside)
            result=client.post(self.native+'/api/algorithm-tab/file',json={'id':'operational-rules','content':'Synthetic requested rule. '*4})
            self.assertEqual(result.status_code,503,result.text)
            self.assertEqual(outside.read_bytes(),before)

    def test_doctrine_commit_tracks_the_new_version_and_preserves_other_staged_files(self):
        repo=self.root
        def git(*args):
            result=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            return result.stdout
        git('init','-q','-b','feature/synthetic-doctrine')
        git('config','user.name','Synthetic Algorithm Test')
        git('config','user.email','test@example.invalid')
        other=repo/'unrelated.txt'
        other.write_text('Synthetic original file.\n')
        git('add','--','LIFEOS/ALGORITHM/LATEST','LIFEOS/ALGORITHM/v3.2.1.md','LIFEOS/ALGORITHM/changelog.md','unrelated.txt')
        git('commit','-q','-m','test(algorithm): seed doctrine')
        other.write_text('Synthetic separate staged change.\n')
        git('add','--','unrelated.txt')
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/doctrine',json={'content':'Synthetic doctrine claim. '*30,
                'bump':'patch','note':'Synthetic doctrine version update.'})
            self.assertEqual(result.status_code,200,result.text)
            self.assertTrue(result.json()['commit']['committed'],result.text)
        self.assertEqual(set(git('show','--name-only','--format=','HEAD').split()),
            {'LIFEOS/ALGORITHM/LATEST','LIFEOS/ALGORITHM/changelog.md','LIFEOS/ALGORITHM/v3.2.2.md'})
        self.assertEqual(git('diff','--cached','--name-only').strip(),'unrelated.txt')

    def test_actual_partial_doctrine_publication_restores_all_original_files(self):
        directory=self.root/'LIFEOS/ALGORITHM'
        original={name:(directory/name).read_bytes() for name in ('LATEST','changelog.md','v3.2.1.md')}
        for count in (1,2,3):
            with self.subTest(publication=count):
                result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_algorithm_edit_process.py')),
                    str(self.fixture.configuration.path),str(self.root),str(count)],capture_output=True,text=True,timeout=40,
                    env=dict(os.environ,HOME=str(self.fixture.home),HERMES_HOME=str(self.fixture.profile)))
                self.assertEqual((result.returncode,result.stdout,result.stderr),(73,'',''))
                memory=NativeMemory(self.root)
                with memory._transaction(): pass
                self.assertEqual({name:(directory/name).read_bytes() for name in original},original)
                self.assertFalse((directory/'v3.2.2.md').exists())

    def test_later_owner_edit_after_publication_withholds_the_prior_response(self):
        path=self.seed()
        self.fixture.login()
        self.fixture.client.get('/api/plugins/lifeos-hook-bridge/memory/pulse/state')
        module=importlib.import_module('lifeos_memory_settings.memory_access')
        original=module.NativeMemory._operation
        seen=[]
        later='Synthetic owner edit after completed publication. '*3
        def publish(memory,*args,**kwargs):
            result=original(memory,*args,**kwargs)
            if len(args)>2 and args[2].get('operation')=='algorithm_edit' and result['status']=='committed':
                seen.append(result['status'])
                path.write_text(later)
            return result
        module.NativeMemory._operation=publish
        self.addCleanup(setattr,module.NativeMemory,'_operation',original)
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/file',json={'id':'operational-rules','content':'Synthetic requested rule. '*4})
            self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(seen,['committed'])
        self.assertEqual(path.read_text(),later)

    def test_git_environment_cannot_redirect_snapshot_or_owner_commits(self):
        path=self.seed()
        repo=(self.root/'LIFEOS/USER').resolve()
        redirect=self.fixture.home/'synthetic-redirected-git'
        redirect.mkdir()
        def git(directory,*args):
            result=subprocess.run(['git','-C',str(directory),*args],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            return result.stdout
        for directory in (repo,redirect):
            git(directory,'init','-q','-b','feature/synthetic-boundary')
            git(directory,'config','user.name','Synthetic Algorithm Test')
            git(directory,'config','user.email','test@example.invalid')
        git(repo,'add','--','CONFIG/OPERATIONAL_RULES.md')
        git(repo,'commit','-q','-m','test(algorithm): seed owner file')
        external=redirect/'external.txt'
        external.write_text('Synthetic external repository data.\n')
        git(redirect,'add','--','external.txt')
        git(redirect,'commit','-q','-m','test(algorithm): seed external file')
        initial_owner=git(repo,'rev-parse','HEAD')
        initial_external=git(redirect,'rev-parse','HEAD')
        selectors={'GIT_DIR':str(redirect/'.git'),'GIT_WORK_TREE':'/',
            'GIT_INDEX_FILE':str(redirect/'.git/redirected-index')}
        previous={key:os.environ.get(key) for key in selectors}
        try:
            os.environ.update(selectors)
            with httpx.Client(timeout=45) as client:
                self.login(client)
                result=client.post(self.native+'/api/algorithm-tab/file',json={'id':'operational-rules',
                    'content':path.read_text().replace('complete observed','current observed')})
                self.assertEqual(result.status_code,200,result.text)
        finally:
            for key,value in previous.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value
        current_external=git(redirect,'rev-parse','HEAD')
        current_owner=git(repo,'rev-parse','HEAD')
        observation={'response':result.json(),'external_changed':current_external!=initial_external,
            'owner_changed':current_owner!=initial_owner}
        self.assertEqual(current_external,initial_external,json.dumps(observation))
        self.assertTrue(result.json()['commit']['committed'],json.dumps(observation))
        self.assertNotEqual(current_owner,initial_owner,json.dumps(observation))
        self.assertEqual(external.read_text(),'Synthetic external repository data.\n')

    def test_interrupted_publication_keeps_later_owner_bytes_for_review(self):
        directory=self.root/'LIFEOS/ALGORITHM'
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_algorithm_edit_process.py')),
            str(self.fixture.configuration.path),str(self.root),'3'],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,HOME=str(self.fixture.home),HERMES_HOME=str(self.fixture.profile)))
        self.assertEqual((result.returncode,result.stdout,result.stderr),(73,'',''))
        tag=directory/'v3.2.2.md'
        later='Synthetic later immutable doctrine owner edit.\n'
        tag.write_text(later)
        from lifeos_hook_bridge.memory_access import MemoryUnavailable
        with self.assertRaisesRegex(MemoryUnavailable,'preserves a later artifact edit'):
            with NativeMemory(self.root)._transaction():pass
        self.assertEqual(tag.read_text(),later)
        self.assertEqual((directory/'LATEST').read_text(),'3.2.2\n')

    def test_actual_git_hook_refusal_preserves_the_saved_file(self):
        path=self.seed()
        repo=(self.root/'LIFEOS/USER').resolve()
        def git(*args):
            result=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            return result.stdout
        git('init','-q','-b','feature/synthetic-hook')
        git('config','user.name','Synthetic Algorithm Test')
        git('config','user.email','test@example.invalid')
        git('add','--','CONFIG/OPERATIONAL_RULES.md')
        git('commit','-q','-m','test(algorithm): seed owner file')
        before=git('rev-parse','HEAD')
        hook=repo/'.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nprintf \"Synthetic hook executes.\\n\" > .git/owner-hook-observed\nexit 1\n')
        hook.chmod(0o700)
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/file',json={'id':'operational-rules',
                'content':'Synthetic requested rule after hook refusal. '*4})
            self.assertEqual(result.status_code,200,result.text)
            self.assertFalse(result.json()['commit']['committed'],result.text)
        self.assertEqual(git('rev-parse','HEAD'),before)
        self.assertEqual((repo/'.git/owner-hook-observed').read_text(),'Synthetic hook executes.\n')
        self.assertIn('Synthetic requested rule after hook refusal.',path.read_text())

    def test_inherited_native_home_cannot_redirect_private_edit_rendering(self):
        path=self.seed()
        external_root=self.fixture.home/'synthetic-external-native-home'
        external=external_root/RULES
        external.parent.mkdir(parents=True)
        external.write_text('Synthetic external native source. '*4)
        before=external.read_bytes()
        repo=(self.root/'LIFEOS/USER').resolve()
        def git(directory,*args):
            result=subprocess.run(['git','-C',str(directory),*args],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            return result.stdout
        for directory,selected in ((repo,'CONFIG/OPERATIONAL_RULES.md'),(external_root,RULES)):
            git(directory,'init','-q','-b','feature/synthetic-native-home')
            git(directory,'config','user.name','Synthetic Algorithm Test')
            git(directory,'config','user.email','test@example.invalid')
            git(directory,'add','--',selected)
            git(directory,'commit','-q','-m','test(algorithm): seed source')
        initial_owner=git(repo,'rev-parse','HEAD')
        initial_external=git(external_root,'rev-parse','HEAD')
        previous=os.environ.get('CLAUDE_CONFIG_DIR')
        try:
            os.environ['CLAUDE_CONFIG_DIR']=str(external_root)
            with httpx.Client(timeout=45) as client:
                self.login(client)
                result=client.post(self.native+'/api/algorithm-tab/file',json={'id':'operational-rules',
                    'content':'Synthetic requested isolated owner edit. '*4})
        finally:
            if previous is None:os.environ.pop('CLAUDE_CONFIG_DIR',None)
            else:os.environ['CLAUDE_CONFIG_DIR']=previous
        observation={'status':result.status_code,'response':result.text,'external_changed':external.read_bytes()!=before}
        self.assertEqual(external.read_bytes(),before,json.dumps(observation))
        self.assertEqual(result.status_code,200,json.dumps(observation))
        self.assertIn('Synthetic requested isolated owner edit.',path.read_text())
        self.assertTrue(result.json()['commit']['committed'],result.text)
        self.assertNotEqual(git(repo,'rev-parse','HEAD'),initial_owner)
        self.assertEqual(git(external_root,'rev-parse','HEAD'),initial_external)

    def test_timed_out_actual_git_hook_has_no_running_child(self):
        path=self.seed()
        repo=(self.root/'LIFEOS/USER').resolve()
        def git(*args):
            result=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            return result.stdout
        git('init','-q','-b','feature/synthetic-hook-timeout')
        git('config','user.name','Synthetic Algorithm Test')
        git('config','user.email','test@example.invalid')
        git('add','--','CONFIG/OPERATIONAL_RULES.md')
        git('commit','-q','-m','test(algorithm): seed owner file')
        hook=repo/'.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nprintf \"%s %s\\n\" \"$$\" \"$PPID\" > .git/owner-hook-pids\nexec sleep 90\n')
        hook.chmod(0o700)
        pid_file=repo/'.git/owner-hook-pids'
        def alive(pid):
            try:return Path('/proc/'+str(pid)+'/stat').read_text().split(') ',1)[1].split()[0] not in {'Z','X'}
            except FileNotFoundError:return False
        def cleanup():
            if not pid_file.exists():return
            for pid in map(int,pid_file.read_text().split()):
                try:os.kill(pid,signal.SIGKILL)
                except ProcessLookupError:pass
        self.addCleanup(cleanup)
        with httpx.Client(timeout=50) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/file',json={'id':'operational-rules',
                'content':'Synthetic requested rule with a timed hook. '*4})
            self.assertEqual(result.status_code,503,result.text)
        self.assertTrue(pid_file.exists(),'The actual hook does not start')
        pids=list(map(int,pid_file.read_text().split()))
        deadline=time.monotonic()+2
        while any(alive(pid) for pid in pids) and time.monotonic()<deadline:time.sleep(0.05)
        self.assertEqual([pid for pid in pids if alive(pid)],[],{'running_children':pids})
        with httpx.Client(timeout=30) as client:
            self.login(client)
            recovered=client.get(self.native+'/api/algorithm-tab/file?id=operational-rules')
            self.assertEqual(recovered.status_code,200,recovered.text)
        self.assertIn('Keep a complete observed result before publication.',path.read_text())
        self.assertNotIn('Synthetic requested rule with a timed hook.',path.read_text())

    def test_later_immutable_tag_at_publication_is_not_overwritten(self):
        directory=self.root/'LIFEOS/ALGORITHM'
        tag=directory/'v3.2.2.md'
        before={name:(directory/name).read_bytes() for name in ('LATEST','changelog.md')}
        later='Synthetic concurrent immutable doctrine owner version.\n'
        self.fixture.login()
        self.fixture.client.get('/api/plugins/lifeos-hook-bridge/memory/pulse/state')
        module=importlib.import_module('lifeos_memory_settings.memory_algorithm_edit')
        original=module.publish
        def concurrent(path,data):
            if Path(path)==tag:tag.write_text(later)
            return original(path,data)
        module.publish=concurrent
        self.addCleanup(setattr,module,'publish',original)
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/doctrine',json={'content':'Synthetic requested doctrine claim. '*25,
                'bump':'patch','note':'Synthetic requested next version.'})
            self.assertEqual(result.status_code,503,result.text)
        self.assertEqual(tag.read_text(),later)
        self.assertEqual({name:(directory/name).read_bytes() for name in before},before)

    def test_saved_modification_time_matches_native_view_at_a_millisecond_boundary(self):
        path=self.seed()
        self.fixture.login()
        self.fixture.client.get('/api/plugins/lifeos-hook-bridge/memory/pulse/state')
        module=importlib.import_module('lifeos_memory_settings.memory_algorithm_edit')
        original=module.publish
        stamp=1700000000999999600
        def publish(target,data):
            original(target,data)
            if Path(target)==path:os.utime(path,ns=(stamp,stamp))
        module.publish=publish
        self.addCleanup(setattr,module,'publish',original)
        with httpx.Client(timeout=45) as client:
            self.login(client)
            result=client.post(self.native+'/api/algorithm-tab/file',json={'id':'operational-rules',
                'content':'Synthetic current rule with an exact modification time. '*4})
            self.assertEqual(result.status_code,200,result.text)
            current=client.get(self.native+'/api/algorithm-tab/file?id=operational-rules')
            self.assertEqual(current.status_code,200,current.text)
            self.assertEqual(result.json()['mtime'],current.json()['mtime'])
            self.assertEqual(current.json()['mtime'],'2023-11-14T22:13:20.999Z')
            repeated=client.post(self.native+'/api/algorithm-tab/file',json={'id':'operational-rules',
                'content':'Synthetic next owner edit using the returned modification time. '*4,
                'expectedMtime':result.json()['mtime']})
            self.assertEqual(repeated.status_code,200,repeated.text)
