#!/usr/bin/env python3

import log_analyzer as la
import program_config as pconf

import unittest as ut
import pathlib as pl
import itertools as it
import datetime
import logging
import json
from typing import NamedTuple

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
                           allow_exts=['gz'],
                           template_html='report.html',
                           debug=False,
                           journal='')
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
                           template_html='report.html',
                           debug=False,
                           journal='',
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

class TestConfigure(ut.TestCase):
    "test parsing of CLI and making the config object"

    def test_verbose_debug_1(self):
        argv = '-vvv -L /tmp -R /tmp -S 300'.split()
        config = pconf.configure(argv)
        self.assertNotEqual(config, None)
        self.assertTrue(config.verbose)
        self.assertTrue(config.debug)

    def test_cfg_template(self):
        argv = "".split()

class TestOutputData(ut.TestCase):
    """Testing of statistics computing and serialization"""

#            la.OutputUrlStats('/1', 2, 0.0, 0.2,  0.3, 0.0, 20, 33.33),
#            la.OutputUrlStats('/2', 1, 0.0, 0.1,  0.2, 0.0, 20, 33.33),
#            la.OutputUrlStats('/3', 1, 0.0, 0.15, 0.2, 0.0, 20, 33.33),

    def test_is_instance(self):
        orec = la.OutputUrlStats('/1', 2, 0.0, 0.2,  0.3, 0.0, 20, 33.33)
        self.assertTrue(isinstance(orec, la.OutputUrlStats))

    def test_nt_serialize(self):
        "test serialization of named tuple"
        nt = la.GeneralStats(2, 423)
        js = json.dumps(nt, default = lambda x: x.__dict__, separators=(',', ':'))
        self.assertEqual(js, '{"total_records":2,"sum_latency":423}')
        

    def test_serialize_output_stats(self):
        recs = [
            la.OutputUrlStats('/1', 2, 0.0, 0.2,  0.3, 0.0, 20, 33.33),
            la.OutputUrlStats('/2', 1, 0.0, 0.1,  0.2, 0.0, 20, 33.33),
            la.OutputUrlStats('/3', 1, 0.0, 0.15, 0.2, 0.0, 20, 33.33),
            ]
        # select only a first element, but wrap in a list
        js = json.dumps([recs[0]], cls=la.OutputJSONEncoder, separators=(',', ':'))
        self.assertEqual(js, '[{"url":"/1","count":2,"time_avg":0.0,"time_max":0.2,"time_sum":0.3,"time_med":0.0,"time_perc":20,"count_perc":33.33}]')

if __name__ == "__main__":
    ut.main()
