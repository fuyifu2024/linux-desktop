import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
w=load('winapps','src/winapps.py')
h=load('help','src/help.py')
g=load('gate','scripts/check-release.py')

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        env=patch.dict(os.environ,{'XDG_DATA_HOME':str(self.base/'data')})
        env.start(); self.addCleanup(env.stop)
        self.installer=self.base/'installer $(touch NEVER).exe'
        self.installer.write_bytes(b'MZ-test')

    def test_prefix_and_command_are_isolated(self):
        a=w.create_app(self.installer); b=w.create_app(self.installer)
        self.assertNotEqual(a,b)
        with patch.object(w,'runtime',return_value='/usr/bin/wine'), patch.object(w.subprocess,'run') as run:
            run.return_value.returncode=0
            w.execute(a,self.installer,install=True)
            args,kwargs=run.call_args
            self.assertEqual(args[0],['/usr/bin/wine',str(self.installer)])
            self.assertEqual(kwargs['env']['WINEPREFIX'],str(w.app_dir(a)/'prefix'))
            self.assertNotIn('shell',kwargs)

    def test_msi(self):
        msi=self.base/'test.msi'; msi.write_bytes(b'test')
        a=w.create_app(msi)
        with patch.object(w,'runtime',return_value='/usr/bin/wine'),patch.object(w.subprocess,'run') as run:
            run.return_value.returncode=0
            w.execute(a,msi,install=True)
            self.assertEqual(run.call_args.args[0],['/usr/bin/wine','msiexec','/i',str(msi)])

    def test_reject_paths(self):
        for invalid in ['../prefix','/tmp','bad','00000000-0000-0000-0000-000000000000/../x']:
            with self.assertRaises(ValueError): w.app_dir(invalid)
        txt=self.base/'x.txt'; txt.write_text('x')
        with self.assertRaises(ValueError): w.create_app(txt)

    def test_external_shortcut_rejected(self):
        a=w.create_app(self.installer)
        with self.assertRaises(ValueError): w.register(a,self.installer)

    def test_launch_failure_records_state(self):
        a=w.create_app(self.installer)
        with patch.object(w,'runtime',return_value='/usr/bin/wine'),patch.object(w.subprocess,'run') as run:
            run.return_value.returncode=42
            with self.assertRaises(RuntimeError): w.execute(a,self.installer)
        self.assertEqual(json.loads((w.app_dir(a)/'app.json').read_text())['status'],'failed')

    def test_missing_runtime_does_not_report_success(self):
        a=w.create_app(self.installer)
        with patch.object(w,'runtime',side_effect=RuntimeError('missing')):
            with self.assertRaises(RuntimeError): w.execute(a,self.installer)
        self.assertEqual(json.loads((w.app_dir(a)/'app.json').read_text())['status'],'created')

    def test_locale(self):
        for value,expected in [('zh_CN.UTF-8','zh-Hans'),('zh_TW.UTF-8','zh-Hant'),('fr_FR.UTF-8','fr'),('ja_JP.UTF-8','ja'),('zz_ZZ','en')]:
            self.assertEqual(h.language(value),expected)

    def test_missing_evidence_blocks_release(self):
        self.assertEqual(len(g.validate(self.base)),4)

    def test_fake_success_without_evidence_blocks_release(self):
        report={k:'test' for k in ['hardware','image_sha256','source_commit','tester','tested_at']}
        report['results']={k:{'status':'passed'} for k in list(g.SCENARIOS)+list(g.APPS)}
        for target in g.TARGETS: (self.base/f'{target}.json').write_text(json.dumps(report))
        self.assertTrue(g.validate(self.base))

    def test_seven_tutorials(self):
        for lang in ['zh-Hans','zh-Hant','en','ja','ru','fr','es']:
            page=(ROOT/'tutorial'/f'{lang}.html').read_text()
            self.assertIn('apt update',page)
            self.assertIn(f'lang="{lang}"',page)
            for other in ['zh-Hans','zh-Hant','en','ja','ru','fr','es']:
                self.assertIn(other+'.html',page)

if __name__=='__main__': unittest.main()
