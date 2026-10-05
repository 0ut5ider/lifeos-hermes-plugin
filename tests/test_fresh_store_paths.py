# ABOUTME: Checks selected user-data paths through actual native scaffold and link tools.
# ABOUTME: Uses a small installation payload and records retained-store isolation without model calls.
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from lifeos_hook_bridge.install_source import install_lifeos, prepare_lifeos
import test_lifeos_install_source as install_fixture
from test_lifeos_install_source import git
from test_memory_native import SOURCE


TOOLS=SOURCE.parent/'Tools'


@unittest.skipUnless((TOOLS/'ScaffoldUser.ts').is_file() and shutil.which('bun'),
                     'Native installation tools and Bun are required')
class FreshStorePathTests(unittest.TestCase):
    def payload(self, root):
        upstream,_,patches=install_fixture.InstallSourceTests().fixture(root)
        tools=upstream/'LifeOS/Tools'
        for name in ('ScaffoldUser','LinkUser','InstallSettings','ActivateImports','InstallEngine'):
            shutil.copyfile(TOOLS/(name+'.ts'),tools/(name+'.ts'))
        (tools/'lib').mkdir()
        shutil.copyfile(TOOLS/'lib/atomic-write.ts',tools/'lib/atomic-write.ts')
        install=upstream/'LifeOS/install'
        (install/'settings.system.json').write_text(json.dumps({'env':{
            'LIFEOS_DIR':'$HOME/.claude/LIFEOS','LIFEOS_CONFIG_DIR':'$HOME/.config/LIFEOS'}}))
        target=install/'USER/CONFIG/LIFEOS_CONFIG.toml'
        target.parent.mkdir(parents=True)
        target.write_text('[principal]\nname="Adrian"\n[da]\nname="Cerebo"\n')
        (tools/'DeployCore.ts').write_text('''import {mkdirSync,writeFileSync} from 'node:fs';
const args=process.argv,root=args[args.indexOf('--config-root')+1];
mkdirSync(root+'/LIFEOS',{recursive:true});writeFileSync(root+'/LIFEOS/VERSION','7.40.5\\n');
''')
        (tools/'InstallHooks.ts').write_text('''import {readFileSync,writeFileSync} from 'node:fs';
const args=process.argv,path=args[args.indexOf('--config-root')+1]+'/settings.json';
const settings=JSON.parse(readFileSync(path,'utf8'));settings.hooks={Stop:[]};
writeFileSync(path,JSON.stringify(settings));
''')
        git('add','LifeOS',cwd=upstream)
        git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','native path fixture',cwd=upstream)
        revision=git('rev-parse','HEAD',cwd=upstream)
        candidate=root/'candidate'
        prepare_lifeos(str(upstream),candidate,revision,patches,('lifeos-test.patch',))
        return candidate,revision,patches

    def install(self, root, home, inherited):
        candidate,revision,patches=self.payload(root)
        with patch.dict(os.environ,inherited):
            result=install_lifeos(candidate,home/'.claude',root/'failed','bun',revision,patches,('lifeos-test.patch',))
        self.assertEqual(result['installed_version'],'7.40.5')
        self.assertEqual(result['steps'],['InstallSettings','DeployCore','ScaffoldUser','LinkUser','InstallHooks','ActivateImports'])
        self.assertTrue(result['restart_required'])
        return result

    def test_native_install_contract_and_selected_names(self):
        with tempfile.TemporaryDirectory(prefix='fresh-paths-') as directory:
            root=Path(directory);home=root/'selected-home'
            self.install(root,home,{'HOME':str(home),'LIFEOS_CONFIG_DIR':str(home/'.config/LIFEOS')})
            data=home/'.config/LIFEOS/USER'
            self.assertEqual((home/'.claude/LIFEOS/USER').resolve(),data)
            self.assertEqual((data/'CONFIG/LIFEOS_CONFIG.toml').read_text(),
                '[principal]\nname="Adrian"\n[da]\nname="Cerebo"\n')

    def test_fresh_install_excludes_inherited_user_store_and_path_settings(self):
        with tempfile.TemporaryDirectory(prefix='fresh-paths-') as directory:
            root=Path(directory);current=root/'current-home';selected=root/'selected-home'
            data=current/'.config/LIFEOS/USER';data.mkdir(parents=True)
            marker=data/'synthetic-retained.txt';marker.write_text('Synthetic retained original.\n')
            before={str(path.relative_to(data)):path.read_bytes() for path in data.rglob('*') if path.is_file()}
            self.install(root,selected,{'HOME':str(current),'LIFEOS_CONFIG_DIR':str(current/'.config/LIFEOS'),
                'LIFEOS_DIR':str(current/'.claude/LIFEOS'),'CLAUDE_CONFIG_DIR':str(current/'.claude')})
            fresh=selected/'.config/LIFEOS/USER'
            self.assertEqual((selected/'.claude/LIFEOS/USER').resolve(),fresh)
            self.assertFalse((fresh/'synthetic-retained.txt').exists())
            self.assertEqual({str(path.relative_to(data)):path.read_bytes() for path in data.rglob('*') if path.is_file()},before)
            settings=json.loads((selected/'.claude/settings.json').read_text())
            self.assertEqual(settings['env']['LIFEOS_CONFIG_DIR'],str(selected/'.config/LIFEOS'))
            self.assertEqual(settings['env']['LIFEOS_DIR'],str(selected/'.claude/LIFEOS'))


if __name__=='__main__':
    unittest.main()
