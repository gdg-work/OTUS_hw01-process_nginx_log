#!/usr/bin/env python3

import unittest as ut
import log_analyzer as la
import pathlib as pl
import itertools as it
import logging

TEMPDIR = '/tmp'

class TestFilesSelection(ut.TestCase):
    "Testing selection if input/output files"
    
    @classmethod
    def setUpClass(cls):
        cls._dir = pl.Path(TEMPDIR, 'TestDir')
        cls.in_dir = cls._dir / pl.Path('log')
        cls.out_dir = cls._dir / pl.Path('report')
        for p in (cls._dir, cls.in_dir, cls.out_dir):
            p.mkdir()
        for fake_date in range(20210320,20210330):
            fake_filename = "nginx-test-acc_{}.log".format(fake_date)
            if fake_date % 3 == 0:
                (cls.in_dir / pl.Path(fake_filename)).touch(mode=0o644)
            else:
                (cls.in_dir / pl.Path(fake_filename + '.gz')).touch(mode=0o644)
        cls.cfg = la.ConfigObj(log_dir=str(TestFilesSelection.in_dir),
                           report_dir=str(TestFilesSelection.out_dir),
                           report_size=10, verbose=True,
                           log_glob='nginx-test-acc_*log',
                           report_glob='rep*.html')
        return

    @classmethod
    def tearDownClass(cls):
        for fn in it.chain(cls.in_dir.glob('*'), cls.out_dir.glob('*'),
                           (f for f in cls._dir.glob('*') if not f.is_dir())):
            fn.unlink()
        for dir in (cls.in_dir, cls.out_dir, cls._dir):
            dir.rmdir()

    @ut.skip('for testing of tests')
    def test_list_logs(self):
        print("\n".join([str(f) for f in TestFilesSelection.in_dir.glob('*')]))
        self.assertTrue(True)

    def test_find_last_log(self):
        fn = la.selectInputFiles(TestFilesSelection.cfg, logging)
        self.assertEqual(fn, pl.Path('/tmp/TestDir/log/nginx-test-acc_20210329.log.gz'))

    def test_find_last_report(self):
        pass

if __name__ == "__main__":
    ut.main()
