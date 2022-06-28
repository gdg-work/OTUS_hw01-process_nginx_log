#!/usr/bin/env python3

import log_analyzer as la
import program_config as pconf

import unittest as ut
import pathlib as pl
import itertools as it
import datetime
import logging
import json
from array import array

TEMPDIR = '/tmp'

# Just a string, it will be parsed by config_parser module.
# Format: key: value, you can use : or = as a separator
CONFIG = """
    REPORT_SIZE: 100
    REPORT_DIR: /tmp/test/report/
    LOG_DIR: /tmp/test/log/
    VERBOSE: off
    LOG_GLOB: nginx-access-ui.log-%Y%m%d
    REPORT_GLOB: report-%Y.%m.%d.html
    ALLOW_EXTENSIONS: gz
    REPORT_TEMPLATE: report.html
    # Next line is for optional journal file.
    # JOURNAL:
"""

log = logging.getLogger('test-log-analyzer')

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
        for fake_date in range(20210310,20210329):
            fake_filename = "nginx-test-acc_{}.log".format(fake_date)
            if fake_date % 3 == 0:
                (cls.in_dir / pl.Path(fake_filename + '.gz')).touch(mode=0o644)
            else:
                if fake_date % 5 == 0:
                    (cls.in_dir / pl.Path(fake_filename + '.bz2')).touch(mode=0o644)
                else:
                    (cls.in_dir / pl.Path(fake_filename)).touch(mode=0o644)
        # create another set of files, with different date templates

        fn_prefix = "nginx-test-acc_"
        for fake_year in range(2007, 2010):
            for fake_month in range(7,8):
                for fake_day in range(15,19):
                    date = datetime.date(fake_year, fake_month, fake_day)

                    match date.toordinal():
                        case int(n) if n % 3 == 0:
                            fn_suffix = '.log.gz'
                        case int(n) if n %5 == 0:
                            fn_suffix = '.log.bz2'
                        case int(n) if n %7 == 0:
                            fn_suffix = '.log.xz'
                        case _:
                            fn_suffix = '.log'

                    fn_day_first = date.strftime(f"{fn_prefix}%d.%m.%Y{fn_suffix}")
                    fn_mon_first = date.strftime(f"{fn_prefix}%m-%d-%Y{fn_suffix}")
                    fn_yr_first  = date.strftime(f"{fn_prefix}%F{fn_suffix}")
                    (cls.in_dir / pl.Path(fn_day_first)).touch(mode=0o644)
                    (cls.in_dir / pl.Path(fn_mon_first)).touch(mode=0o644)
                    (cls.in_dir / pl.Path(fn_yr_first)).touch(mode=0o644)

        cfg = pconf.ConfigObj(log_dir=str(TestFilesSelection.in_dir),
                           report_dir=str(TestFilesSelection.out_dir),
                           report_size=10, verbose=True,
                           log_glob='nginx-test-acc_%Y%m%d.log',
                           report_glob='report_%F.html',
                           allow_exts=['.gz'],
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
            pass  # for possibility to comment/uncomment the previous line
        for dir in (cls.in_dir, cls.out_dir, cls.empty_dir, cls._dir):
            dir.rmdir()
            pass

    @ut.skip('for testing of tests')
    def test_list_logs(self):
        print("\n", "\n".join([str(f) for f in TestFilesSelection.in_dir.glob('*')]))
        return

    def test_find_last_log(self):
        select_input_file = TestFilesSelection.funcs_table['select_input_file']
        fn = select_input_file()
        self.assertEqual(fn, pl.Path('/tmp/TestDir/log/nginx-test-acc_20210328.log.gz'))

    def test_find_no_log(self):
        norep_cfg = pconf.ConfigObj(log_dir=str(TestFilesSelection.empty_dir),
                           report_dir=str(TestFilesSelection.out_dir),
                           report_size=10, verbose=True,
                           log_glob='nginx-test-acc_%Y%m%d.log',
                           report_glob='rep_%Y-%m-%d.html',
                           template_html='report.html',
                           debug=False,
                           journal='',
                           allow_exts=['.gz'])

        fn = la.setup_functions(norep_cfg, TestFilesSelection.logger)['select_input_file']()
        self.assertEqual(fn, None)

    def test_find_log_time_format_dayfirst(self):
        rep_cfg = pconf.ConfigObj(log_dir=str(TestFilesSelection.in_dir),
                           report_dir=str(TestFilesSelection.out_dir),
                           report_size=10, verbose=True,
                           log_glob='nginx-test-acc_%d.%m.%Y.log',
                           report_glob='rep_%Y-%m-%d.html',
                           template_html='report.html',
                           debug=False,
                           journal='',
                           allow_exts=['.gz'])
        fn = la.setup_functions(rep_cfg, TestFilesSelection.logger)['select_input_file']()
        self.assertEqual(fn, pl.Path('/tmp/TestDir/log/nginx-test-acc_18.07.2009.log'))

    def test_find_log_time_format_monthfirst(self):
        rep_cfg = pconf.ConfigObj(log_dir=str(TestFilesSelection.in_dir),
                           report_dir=str(TestFilesSelection.out_dir),
                           report_size=10, verbose=True,
                           log_glob='nginx-test-acc_%m-%d-%Y.log',
                           report_glob='rep_%Y-%m-%d.html',
                           template_html='report.html',
                           debug=False,
                           journal='',
                           allow_exts=['.gz'])
        fn = la.setup_functions(rep_cfg, TestFilesSelection.logger)['select_input_file']()
        self.assertEqual(fn, pl.Path('/tmp/TestDir/log/nginx-test-acc_07-18-2009.log'))

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
        config = pconf.configure(argv, log, CONFIG)
        self.assertNotEqual(config, None)
        # we didn't have to check 'config' for value 'None' here, because of assertion
        self.assertTrue(config.verbose)
        self.assertTrue(config.debug)

    def test_cfg_template(self):
        argv = "".split()

class TestOutputData(ut.TestCase):
    """Testing of statistics computing and serialization"""

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
            la.OutputUrlStats('/1', 2, 0.0, 0.2,  0.3, 0.0, 60, 33.33),
            la.OutputUrlStats('/2', 1, 0.0, 0.1,  0.2, 0.0, 20, 33.34),
            la.OutputUrlStats('/3', 1, 0.0, 0.15, 0.2, 0.0, 20, 33.33),
            ]
        # select only a first element, but wrap in a list
        js = json.dumps(recs, cls=la.OutputJSONEncoder, separators=(',', ':'))
        self.assertEqual(js, '[' + ','.join([
            '{"url":"/1","count":2,"time_avg":0.0,"time_max":0.2,"time_sum":0.3,"time_med":0.0,"time_perc":60,"count_perc":33.33}',
            '{"url":"/2","count":1,"time_avg":0.0,"time_max":0.1,"time_sum":0.2,"time_med":0.0,"time_perc":20,"count_perc":33.34}',
            '{"url":"/3","count":1,"time_avg":0.0,"time_max":0.15,"time_sum":0.2,"time_med":0.0,"time_perc":20,"count_perc":33.33}',
            ]) + ']')

class TestMedian(ut.TestCase):
    "testing of median computing function"

    def test_median_empty_array(self):
        ui = la.UrlInfo(array('l',[]), occurencies=0, max_latency=0, sum_latency=0)
        m = la.compute_median(ui)
        self.assertEqual(m, 0)

    def test_median_one_value(self):
        ui = la.UrlInfo(array('l',[13]), occurencies=1, max_latency=13, sum_latency=13)
        m = la.compute_median(ui)
        self.assertEqual(m, 13)

    def test_median_two_values(self):
        ui = la.UrlInfo(array('l',[13, 17]), occurencies=2, max_latency=17, sum_latency=30)
        m = la.compute_median(ui)
        self.assertEqual(m, 15)

    def test_median_three_values(self):
        ui = la.UrlInfo(array('l',[13, 15, 17]), occurencies=3, max_latency=17, sum_latency=45)
        m = la.compute_median(ui)
        self.assertEqual(m, 15)

    def test_median_constant_value(self):
        ui = la.UrlInfo(array('l',[13] * 5), occurencies=5, max_latency=13, sum_latency=13*5)
        m = la.compute_median(ui)
        self.assertEqual(m, 13)

    def test_median_reverse_sorted(self):
        vals = list(range(10,20))
        ui = la.UrlInfo(array('l',reversed(vals)), occurencies=10,
                        max_latency=19, sum_latency=sum(range(10,20)))
        m = la.compute_median(ui)
        self.assertEqual(m, 14)

if __name__ == "__main__":
    ut.main()
