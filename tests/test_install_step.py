# ABOUTME: Verifies native installation step results and cancellation through real child processes.
# ABOUTME: Checks that timed-out descendants cannot publish files after their parent stops.
from pathlib import Path
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest


class InstallStepTests(unittest.TestCase):
    def run_step(self,command,root,timeout=5):
        from lifeos_hook_bridge.install_source import _install_step
        return _install_step(command,cwd=root,environment=os.environ.copy(),timeout=timeout)

    def test_result_retains_exit_code_and_both_captured_streams(self):
        with tempfile.TemporaryDirectory(prefix='install-step-') as directory:
            for code in (0,23):
                with self.subTest(code=code):
                    program='import sys;print("synthetic stdout");print("synthetic stderr",file=sys.stderr);sys.exit('+str(code)+')'
                    result=self.run_step([sys.executable,'-c',program],Path(directory))
                    self.assertEqual(result.returncode,code)
                    self.assertEqual(result.stdout,'synthetic stdout\n')
                    self.assertEqual(result.stderr,'synthetic stderr\n')

    def test_timed_out_parent_and_descendant_cannot_publish_later(self):
        with tempfile.TemporaryDirectory(prefix='install-step-') as directory:
            root=Path(directory);marker=root/'later-publication.txt'
            child='from pathlib import Path;import time;time.sleep(0.6);Path('+repr(str(marker))+').write_text("unexpected publication")'
            parent='import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",'+repr(child)+']);time.sleep(5)'
            started=time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):
                self.run_step([sys.executable,'-c',parent],root,timeout=0.2)
            self.assertLess(time.monotonic()-started,2)
            time.sleep(0.8)
            self.assertFalse(marker.exists())

    def test_interrupted_controller_cancels_native_parent_and_descendant(self):
        with tempfile.TemporaryDirectory(prefix='install-step-') as directory:
            root=Path(directory);marker=root/'later-publication.txt';ready=root/'ready.txt'
            child='from pathlib import Path;import time;time.sleep(0.6);Path('+repr(str(marker))+').write_text("unexpected publication")'
            parent=('import subprocess,sys,time;from pathlib import Path;'
                'subprocess.Popen([sys.executable,"-c",'+repr(child)+']);'
                'Path('+repr(str(ready))+').write_text("ready");time.sleep(5)')
            controller=('import os,sys;from pathlib import Path;'
                'from lifeos_hook_bridge.install_source import _install_step\n'
                'try:\n _install_step('+repr([sys.executable,'-c',parent])+',cwd=Path('+repr(str(root))+'),environment=os.environ.copy())\n'
                'except KeyboardInterrupt:\n sys.exit(130)\n')
            process=subprocess.Popen([sys.executable,'-c',controller],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                deadline=time.monotonic()+5
                while not ready.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(0.01)
                self.assertTrue(ready.exists())
                process.send_signal(signal.SIGINT)
                output,errors=process.communicate(timeout=5)
                self.assertEqual(process.returncode,130,output+errors)
                self.assertEqual(output+errors,'')
                time.sleep(0.8)
                self.assertFalse(marker.exists())
            finally:
                if process.poll() is None:process.kill();process.communicate()


if __name__=='__main__':
    unittest.main()
