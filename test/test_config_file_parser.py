#!/usr/bin/env python3
""" test configuration file parser """
import unittest as ut
import config_file_parser as cfp
import logging as log
import pyparsing as pp

class TestConfigFileParser(ut.TestCase):

    def test_comments(self):
        t1 = cfp.comment_line.run_tests(
            ['', '# adfldsakjf', '#;ldksjaf ldsakjf ldsa fj', '####################'],
            comment=None, print_results = False)
        self.assertTrue(t1[0], 'Good comment doesnt parse')
        t2 = cfp.comment_line.run_tests(
            [' .#', '..# adfldsakjf', 'adsfadsf#;ldksjaf ldsakjf ldsa fj', '-- ####################'],
            failure_tests=True, comment=None, print_results=False)
        self.assertTrue(t2[0], 'Bad comment parsed successfully')

    def test_booleans(self):
        t1 = cfp.bool_val.run_tests('''
            # boolean truth values
            TRUE
            true
            True
            On
            ON
            on
            1
            # boolean false values
            FALSE
            false
            False
            Off
            OFF
            off
            0
            ''', print_results=False)
        self.assertTrue(t1[0], 'Good boolean doesnt parse')
        t2 = cfp.bool_val.run_tests('''
            trae,
            TRUUE,
            3
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t2[0], 'Bad boolean value parsed successfully')

    def test_paths(self):
        t1 = cfp.log_dir.run_tests('''
            # set log directory (success)
            LOG_DIR: /the/log/dir
            LOG_DIR: /tmp/logdir
            LOG_DIR: .
            LOG_DIR: ../logs
            LOG_DIR = ./logs/
            ''', print_results=False)
        self.assertTrue(t1[0], 'Good log_dir doesnt parse')
        t2 = cfp.report_dir.run_tests('''
            # set report directory (success)
            REPORT_DIR: /the/log/report
            REPORT_DIR = /the/log/report
            REPORT_DIR:     /tmp/report_dir
            REPORT_DIR  :  .
            REPORT_DIR   :../reports
            report_dir: ../reports/
            ''', print_results=False)
        self.assertTrue(t2[0], 'Good report_dir doesnt parse')

    @ut.skip("Doens't work yet")
    def test_quoted_paths(self):
        t = cfp.report_dir.run_tests('''
            # set report directory (border cases)
            REPORT_DIR: A long directory name with some spaces
            REPORT_DIR:     /tmp/Yet another long directory name
            REPORT_DIR  :  "Quoted string with / a separator".
            REPORT_DIR   :"../reports"
            report_dir: '../reports/'
            ''', print_results=True)
        self.assertTrue(t[0], 'Good report_dir doesnt parse')

    def test_verbose(self):
        t1 = cfp.verbose_flag.run_tests('''
            # set/unset verbosity flat
            VERBOSE: True
            Verbose = False
            verbosE: 0
            verBose: off
            verbose = 0
            ''', print_results=False)
        self.assertTrue(t1[0], 'Good verbose flag doesnt parse')
        t2 = cfp.verbose_flag.run_tests('''
            # set/unset verbosity, failure tests
            virbose: false
            verbose:: false
            verbose: folse
            verbose: 2
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t2[0], 'Bad verbosity flag parsed successfully')

    def test_timepattern(self):
        t = cfp.time_pattern.run_tests("""
                %F
                %Y%m%d
                %d.%m.%Y
                %d-%b-%Y
                %b;%d;%Y
                %b_%d_%Y
                """, print_results=False)
        self.assertTrue(t[0], 'Good date patterns doesnt parse')

    def test_log_pattern(self):
        lp = cfp.fileglob_tmpl.run_tests('''
                nginx_log-%F
                nginx-%F_log.log
                nginx-access_%Y%m%d.log
                nginx-test-acc_%Y-%m-%d.log.gz
                nginx-test-acc_%m-%d-%Y.log.gz
                nginx-test-acc_%m-%d-%y.log.gz
                nginx-test-acc_%d.%m.%Y.log.gz
                ''', print_results=False)
        self.assertTrue(lp[0], 'Good log pattern doesnt pass')

    @ut.skip('excluded due to changed file name conception')
    def test_filename_parser(self):
        t1 = cfp.fileglob_star_middle.run_tests('''
            somefile*continue
            somefile*ext.gz
            ''', failure_tests=False, print_results=False)
        self.assertTrue(t1[0], '1st variant of file name fails')
        t2 = cfp.fileglob_star_end.run_tests('''
            somefile*
            another12-%long-(file)+name@somewhere-*
            somefile*.gz
            ''', failure_tests=False, print_results=False)
        self.assertTrue(t2[0], '2st variant of file name fails')
        t3 = cfp.fileglob_star_beginning.run_tests('''
            *_some_file_name.txt
            *_l0ngfIlEN@m[e).log.gz
            ''', failure_tests=False, print_results=False)
        self.assertTrue(t3[0], '3rd variant of file name fails')
        t4 = cfp.fileglob_tmpl.run_tests('''
            somefile*continue
            somefile*ext.gz
            somefile*
            another12-%long-(file)+name@somewhere-*
            somefile*.gz
            *_some_file_name.txt
            *_l0ngfIlEN@m[e).log.gz
            ''', print_results=False)
        self.assertTrue(t4[0], 'Auto-select variant of file name fails')
        t5 = cfp.fileglob_tmpl.run_tests('''
            *
            ldsjkfsdfddf
            ' '
            1
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t5[0], 'These filename tests had to fail')

    def test_ignored_exts_list(self):
        t1 = cfp.allow_exts.run_tests('''
            allow_extensions: xz
            allow_extensions: xz,bz2
            allow_extensions = bz2,xz,zst,Z
            allow_extensions: bz2, xz, zst, Z
            ''', print_results=False)
        self.assertTrue(t1[0], 'Failed good list of permitted extensions')
        t2 = cfp.allow_exts.run_tests('''
            allow_extensions: xz:
            allow_extensions: xz;bz2
            allow_extensions = bz2,xz,zasst,Z
            allow_extensions: bz2,_xz, zst, Z
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t2[0], 'Passed bad list of permitted extensions')
        parsed_exts = cfp.allow_exts.parse_string('allow_extensions: bz2, xz, zst, zip')
        self.assertEqual(list(parsed_exts), ['bz2', 'xz', 'zst', 'zip'], 'Incorrect parsing of extensions list')

    def test_config_report_template(self):
        confstring_nl = "\n".join([
            'report_size: 250', 'report_dir: /tmp', 'log_dir: /var/log', 'verbose: false', 'report_glob=report_%F.html',
            'log_glob=nginx_access_%F.log', 'template_html=./resource/report.html',])
        confstring_spaces = " ".join([
            'report_size: 250', 'report_dir: /tmp', 'log_dir: /var/log', 'verbose: false', 'report_glob=report_%F.html',
            'log_glob=nginx_access_%F.log', 'template_html=./resource/report.html',])
        t = cfp.config.run_tests(confstring_nl, print_results=False)
        t = cfp.config.run_tests(confstring_spaces, print_results=False)
        self.assertTrue(t[0], 'Good config string doesnt parse')
        p = cfp.config.parse_string(confstring_nl)
        self.assertEqual(p.template_html, "./resource/report.html")

    def test_config_parser(self):
        t = cfp.config.run_tests(
            'report_size: 250 report_dir: /tmp log_dir: /var/log verbose: false report_glob=report_%F.html log_glob=nginx_access_%F.log',
            print_results=False)
        self.assertTrue(t[0], 'Good config doesnt parse')

    def test_config_parser_comment_only(self):
        t = cfp.config.run_tests(
            '# Just some comment here',
            comment=pp.Empty(),
            print_results=True)
        self.assertTrue(t[0], 'Comment-only config doesnt parse')

    def test_config_parser_multiline(self):
        t = cfp.config.run_tests(["""
            report_size: 300
            report_dir = /tmp/report
            log_dir: /tmp/log
            verbose: 1
            report_glob: report_%F.html
            template_html: report.html
            log_glob: nginx_access-%Y%m%d.log
            """], comment=None, print_results=False)
        self.assertTrue(t[0], 'Good multiline config doesnt parse')

    @ut.skip('was used for selecting different values from test data')
    def test_config_parser_printparsed(self):
        cfg_str = """
            report_size: 300
            report_dir = /tmp/report
            log_dir: /tmp/log
            verbose: 1
            report_glob = report_%F.html
            log_glob = nginx_access-%F.log
        """
        t = cfp.config.run_tests([cfg_str], comment=None, print_results=False)
        self.assertTrue(t[0], 'Good multiline config doesnt parse')

    def test_config_parser_results(self):
        p = cfp.config.parse_string('''
                report_size: 300
                report_dir = /tmp/report
                log_dir: /tmp/log
                verbose: 1
                report_glob = report_%Y%m%d.html
                log_glob = nginx_access-%F.log
                allow_extensions = bz2,zst,xz
            ''')
        self.assertEqual(p.verbose, True, 'Incorrect verbosity parsed')
        self.assertEqual(p.report_size, '300', 'Incorrect report size parsed')
        self.assertEqual(p.report_dir, "/tmp/report", 'Incorrect report dir')
        self.assertEqual(p.log_dir, "/tmp/log", 'Incorrect log dir')
        self.assertEqual(p.log_glob, "nginx_access-%F.log", 'Incorrect log glob pattern')
        self.assertEqual(p.report_glob, "report_%Y%m%d.html", 'Incorrect report glob pattern')
        self.assertEqual(list(p.allowed_exts), ['bz2', 'zst', 'xz'], 'Incorrect parsing of allowed extensions list')

    def test_subsets_config(self):
        "Test parsing of config's subsets"
        p = cfp.config.run_tests([
                "",
                "verbose=on",
                "report_dir = /tmp/reports",
            ], print_results=False)
        self.assertEqual(p[0], True)
        p = cfp.config.parse_string('''
                report_size: 300
                report_dir = /tmp/report
            ''')
        self.assertEqual(dict(p), { 'report_size': '300',
                                    'report_dir' : "/tmp/report"})

    def test_make_glob_fun(self):
        "test converting strptime pattern to shell globbing pattern"
        self.assertEqual(cfp.template_to_glob('report_%F.html'), "report_20[0-9][0-9]-[01][0-9]-[0-3][0-9].html")
        self.assertEqual(cfp.template_to_glob('nginx_access_%Y%m%d.log'), "nginx_access_20[0-9][0-9][01][0-9][0-3][0-9].log")
        self.assertEqual(cfp.template_to_glob('nginx_access_%m-%d.log'), "nginx_access_[01][0-9]-[0-3][0-9].log")
        self.assertEqual(cfp.template_to_glob('nginx_access_%b-%d.log'), "nginx_access_[A-Z][a-z][a-z]-[0-3][0-9].log")

    def test_parse_config_fun(self):
        "Test parsing of config file with function from config_file_parser module"
        s = """
            report_size: 300
            report_dir = /tmp/report
            log_dir: /tmp/log
            verbose: 1
            report_glob = report_%F.html
            log_glob = nginx_access-%Y%m%d.log
            allow_extensions = gz,zst,xz
        """
        cfg_p = cfp.parse_config(cfp.config, s, log)
        self.assertEqual(cfg_p['verbose'], True, 'Incorrect verbosity parsed')
        self.assertEqual(cfg_p['report_size'], '300', 'Incorrect report size parsed')
        self.assertEqual(cfg_p['report_dir'], "/tmp/report", 'Incorrect report dir')
        self.assertEqual(cfg_p['log_dir'], "/tmp/log", 'Incorrect log dir')
        self.assertEqual(cfg_p['log_glob'], "nginx_access-%Y%m%d.log", 'Incorrect log glob pattern')
        self.assertEqual(cfg_p['report_glob'], "report_%F.html", 'Incorrect report glob pattern')
        self.assertEqual(cfg_p['allow_exts'], ['gz', 'zst', 'xz'], 'Incorrect report glob pattern')

if __name__ == "__main__":
    ut.main()
