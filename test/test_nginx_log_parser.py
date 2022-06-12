#!/usr/bin/env python3

import unittest as ut
import nginx_log_parser as nlp

class TestLogParser(ut.TestCase):
    """Testing of different elements of log parsing"""

    def test_real_numbers_success(self):
        t = nlp.realNum.run_tests('''
            # These tests of real numbers must succeed and return values
            # a standard example of floating point number (+)
            1.234
            # yet another (+)
            12.34
            12.3456797687786578687698798797685
            1234.
            .1234
            ''', print_results = False)
        self.assertTrue(t[0], "realNum: bad conversion of str to real number")
        # Samples of more thorough testing, the tests could be improved
        self.assertEqual(t[1][0][1]['value'], "1.234")
        self.assertEqual(t[1][1][1]['value'], "12.34")
        self.assertAlmostEqual(float(t[1][2][1]['value']), 12.345679768)

    def test_real_numbers_fail(self):
        t = nlp.realNum.run_tests('''
            # These tests of real numbers must fail
            # invalid FP separator
            1,234
            # two separators adjacent
            12..34
            # two separators separated
            1.23.4
            # two seps on edges
            .1234.
            # the lone separator
            .
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t[0], 'These tests must fail but does not!')

    def test_valid_IP_addrs(self):
        t = nlp.ipAddrV4.run_tests("""
            # Good IPv4 addresses
            123.123.123.123
            0.0.0.0
            255.255.255.255
            """, print_results=False)
        self.assertTrue(t[0], 'IPv4 address parsing is broken!')

    def test_invalid_IP_addrs(self):
        t = nlp.ipAddrV4.run_tests("""
            # badly formatted data in place of IPv4 address
            123
            123.124.123
            123.23.45.
            3.4.5.6.7
            1.2..3
            255.255.255.256
            """, failure_tests=True, print_results=False)
        self.assertTrue(t[0], 'The invalid IPv4 address passed parsing!')

    def test_date_parse_success(self):
        t = nlp.timeStamp.run_tests('''
            # These tests must succeed on parse step and can fail on strptime checking
            30/Jun/2017:03:28:22 +0300
            30/Jun/2017:03:28:22 +2300
            30/Jun/2017:03:28:22 +0300
            03/Jun/2017:03:28:22 +0300
            31/Jul/2017:03:28:22 +0300
            ''', failure_tests=False, print_results=False)
        self.assertTrue(t[0], 'The formally valid date doesnt parse!')

    def test_date_parse_failure(self):
        "Some of these tests will fail on parsing step. Other with strptime step"
        t = nlp.timeStamp.run_tests('''
            30/Juk/2017:03:28:22 +0300
            30/jun/2017:03:28:22 +0300
            30/Jun/2017:03:28:22 +03
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t[0], 'Invalid date parsed successfully!')

    def test_invalid_date_parse_fail(self):
        t = nlp.timeStamp.run_tests('''
            # These tests must succeed on parse step and can fail on strptime checking
            32/Jun/2017:03:28:22 +0300
            00/Jun/2017:03:28:22 +0300
            30/Jun/2017:33:28:22 +0300
            30/Feb/2017:03:28:22 +0300
            30/Jun/2017:03:78:02 +3000
            30/Jun/2017:03:28:22 +0370
            30/Jun/2017:03:28:22 +2361
            31/Jun/2017:03:28:22 +0300
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t[0], 'The string that is formally valid, but invalid as date parsed successfully!')

    def test_url_parse(self):
        t1 = nlp.urlProto.run_tests('''
            # good protocol selectors
            http:/
            https:/
            ftp:/
            ''', print_results=False)
        self.assertTrue(t1[0], 'Good protocol doesnt parse')
        t2 = nlp.urlProto.run_tests('''
            # bad protocol selectors
            file:/
            unknown:/
            http::/
            https/
            sftp:/
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t2[0], 'Bad protocol marker parsed successfully')
        t3 = nlp.urlString.run_tests('''
            # good URLs for parsing
            http://www.ya.ru
            https://www.ya.ru
            ftp://ftp.ya.ru
            http://www.ya.ru/test/of/long/line
            https://api.some.site/api/v1/test?param1=value1&param2=value2
            ''', print_results=False)
        self.assertTrue(t3[0], 'Error of parsing good URL')
        t4 = nlp.urlString.run_tests('''
            # bad samples of  URLs for parsing
            httpa://www.ya.ru
            https:/www.ya.ru
            ftp//ftp.ya.ru
            http:www.ya.ru/test/of/long/line
            https://api.some.site/api/v1/test!?param1=value1&param2=value2
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t4[0], 'Bad URL parses successfully')

    def test_request_parse_success(self):
        t = nlp.httpRequestData.run_tests('''
            # these strings must be parsed successfully. Double quotes are part of test string"
            "GET /api/v2/group/2970039/banners HTTP/1.1"
            "HEAD https://docs.python.org/3/library/re.html#regular-expression-objects HTTP/1.0"
            "GET /api/1/campaigns/?id=7804552 HTTP/1.1"
            "GET /api/v2/group/7786679/statistic/sites/?date_type=day&date_from=2017-06-28&date_to=2017-06-28 HTTP/1.1"
            ''', print_results=False)
        self.assertTrue(t[0], 'Good request data doesnt parse')

    def test_request_parse_failure(self):
        t = nlp.httpRequestData.run_tests('''
            # these strings must fail. Double quotes are part of test string
            "GTE /api/v2/group/2970039/banners HTTP/1.1"
            "HEAD https://docs.python.org/3/library/re.html!regular-expression-objects HTTP/1.0"
            "GET /api/1/campaigns/?id=7804552 HTTP/1.2"
            "GET HTTP/1.1"
            "/api/v2/group/7786679/statistic/sites/?date_type=day&date_from=2017-06-28&date_to=2017-06-28 HTTP/1.1"
            "HEAD https://docs.python.org/3/library/re.html!regular-expression-objects"
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t[0], 'Bad request info parses successfully')

    def test_referrer_parse(self):
        t1 = nlp.refererUrl.run_tests("""
            "-"
            "http://127.0.0.1/test/api/localhost"
            "https://docs.python.org/3/library/re.html/regular-expression-objects"
            "/api/3214123/1234/qd32"
            """, print_results=False)
        self.assertTrue(t1[0], 'Good referer URL doesnt parse')
        t2 = nlp.refererUrl.run_tests('''
            ""
            "sctp://"
            "/123:235/23
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t2[0], 'Bad referer URL info parses successfully')

    def test_log_line_parse(self):
        t1 = nlp.logLine.run_tests('''
            1.196.116.32 -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/banner/25013431 HTTP/1.1" 200 948 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752758" "dc7161be3" 0.917
            1.168.65.96 -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/internal/banner/24288647/info HTTP/1.1" 200 351 "-" "-" "-" "1498697423-2539198130-4708-9752780" "89f7f1be37d" 0.072
            1.169.137.128 -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/banner/21456892 HTTP/1.1" 200 70795 "-" "Slotovod" "-" "1498697423-2118016444-4708-9752779" "712e90144abee9" 0.158
            1.168.65.96 -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/internal/banner/24197629/info HTTP/1.1" 200 293 "-" "-" "-" "1498697423-2539198130-4708-9752783" "89f7f1be37d" 0.058
            1.194.135.240 -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/group/7786683/statistic/sites/?date_type=day&date_from=2017-06-28&date_to=2017-06-28 HTTP/1.1" 200 22 "-" "python-requests/2.13.0" "-" "1498697423-3979856266-4708-9752782" "8a7741a54297568b" 0.061
            1.169.137.128 -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/banner/16803530 HTTP/1.1" 200 6766 "-" "Slotovod" "-" "1498697423-2118016444-4708-9752781" "712e90144abee9" 0.156
            1.196.116.32 -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/banner/24913311 HTTP/1.1" 200 897 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752748" "dc7161be3" 1.243
            1.196.116.32 -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/banner/25019908 HTTP/1.1" 200 989 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752760" "dc7161be3" 1.321
            1.196.116.32 -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/banner/24998073 HTTP/1.1" 200 983 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752755" "dc7161be3" 1.403
            ''', print_results=False)
        self.assertTrue(t1[0], 'Error of parsing good log lines')
        t2 = nlp.logLine.run_tests('''
            1.196.116.32 -  - [29/Jun/2017:03:50:23 +0300] "-" 200 983 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752755" "dc7161be3" 1.403
            1.138.198.128 -  - [29/Jun/2017:18:00:19 +0300] "GET //;@169.254.169.254/latest/meta-data/iam/security-credentials/Ec2LeastPrivileged HTTP/1.1" 302 5 "-" "Mozilla/4.0 (compatible; Win32; WinHttp.WinHttpRequest.5)" "-" "1498748419-3305784397-4709-10417084" "-" 0.008
            - -  - [29/Jun/2017:03:50:23 +0300] "GET /api/v2/banner/24913311 HTTP/1.1" 200 897 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752748" "dc7161be3" 1.243
            ''', failure_tests=True, print_results=False)
        self.assertTrue(t2[0], 'Invalid log line passed parsing')

if __name__ == "__main__":
    ut.main()
