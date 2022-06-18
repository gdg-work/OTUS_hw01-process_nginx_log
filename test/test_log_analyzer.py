#!/usr/bin/env python3

import log_analyzer as la
import program_config as pconf

import unittest as ut
import pathlib as pl
import itertools as it
import datetime
import logging

TEMPDIR = '/tmp'

class TestFilesSelection(ut.TestCase):
    "Testing selection if input/output files"
    
    @classmethod
    def setUpClass(cls):
        cls._dir = pl.Path(TEMPDIR, 'TestDir')
        cls.in_dir = cls._dir / pl.Path('log')
        cls.out_dir = cls._dir / pl.Path('report')
        cls.empty_dir = cls._dir / pl.Path('empty')
        # set up logging 
        cls.logger = logging.getLogger('test_log_analyzer')
        # make test directories
        for p in (cls._dir, cls.in_dir, cls.out_dir, cls.empty_dir):
            p.mkdir()
        # create some files in the test directory
        for fake_date in range(20210310,20210331):
            fake_filename = "nginx-test-acc_{}.log".format(fake_date)
            if fake_date % 3 == 0:
                (cls.in_dir / pl.Path(fake_filename + '.gz')).touch(mode=0o644)
            else:
                if fake_date % 5 == 0:
                    (cls.in_dir / pl.Path(fake_filename + '.bz2')).touch(mode=0o644)
                else:
                    (cls.in_dir / pl.Path(fake_filename)).touch(mode=0o644)

        cfg = pconf.ConfigObj(log_dir=str(TestFilesSelection.in_dir),
                           report_dir=str(TestFilesSelection.out_dir),
                           report_size=10, verbose=True,
                           log_glob='nginx-test-acc_%Y%m%d.log',
                           report_glob='report_%F.html',
                           allow_exts=['gz'],)
        cls.funcs_table = la.setup_functions(cfg, cls.logger)
        return

    @classmethod
    def tearDownClass(cls):
        for fn in it.chain(cls.in_dir.glob('*'), cls.out_dir.glob('*'),
                           (f for f in cls._dir.glob('*') if not f.is_dir())):
            fn.unlink()
        for dir in (cls.in_dir, cls.out_dir, cls.empty_dir, cls._dir):
            dir.rmdir()

    @ut.skip('for testing of tests')
    def test_list_logs(self):
        print("\n", "\n".join([str(f) for f in TestFilesSelection.in_dir.glob('*')]))
        self.assertTrue(True)

    def test_find_last_log(self):
        select_input_file = TestFilesSelection.funcs_table['select_input_file']
        fn = select_input_file()
        self.assertEqual(fn, pl.Path('/tmp/TestDir/log/nginx-test-acc_20210329.log'))

    def test_find_no_log(self):
        norep_cfg = pconf.ConfigObj(log_dir=str(TestFilesSelection.empty_dir),
                           report_dir=str(TestFilesSelection.out_dir),
                           report_size=10, verbose=True,
                           log_glob='nginx-test-acc_%Y%m%d.log',
                           report_glob='rep_%Y-%m-%d.html',
                           allow_exts=['gz'])

        fn = la.setup_functions(norep_cfg, TestFilesSelection.logger)['select_input_file']()
        self.assertEqual(fn, None)

    def test_parse_input_date(self):
        in_fn = "/tmp/TestDir/log/nginx-test-acc_20210329.log"
        parse_input_date = TestFilesSelection.funcs_table['parse_input_date']
        date = parse_input_date(in_fn)
        self.assertEqual(date, datetime.date(2021,3,29))

    def test_make_report_name(self):
        mkname = TestFilesSelection.funcs_table['make_report_filename']
        name = mkname('nginx-test-acc_20220102.log')
        self.assertEqual(name, pl.Path('/tmp/TestDir/report/report_2022-01-02.html'))


if __name__ == "__main__":
    ut.main()
