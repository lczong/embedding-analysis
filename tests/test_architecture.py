"""Import isolation: one experiment must work when every sibling is unavailable."""
import subprocess
import sys
import unittest


class ExperimentIsolation(unittest.TestCase):
    def test_each_experiment_imports_with_siblings_blocked(self):
        for owner in ['ood','multilabel','unseen','overview','structure']:
            with self.subTest(experiment=owner):
                script='''
import importlib
import importlib.abc
import sys
owner=sys.argv[1]
prefix='embedding_analysis.experiments.'
class BlockSiblings(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.startswith(prefix) and fullname[len(prefix):].split('.')[0]!=owner:
            raise AssertionError('Cross-experiment dependency: '+fullname)
sys.meta_path.insert(0,BlockSiblings())
for module in ['workflow','compute','plotting']+([] if owner=='overview' else ['metrics','summary']):
    importlib.import_module(prefix+owner+'.'+module)
'''
                result=subprocess.run([sys.executable,'-c',script,owner],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
