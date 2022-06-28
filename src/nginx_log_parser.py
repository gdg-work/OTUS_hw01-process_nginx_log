#!/usr/bin/env python3
# https://pyparsing-docs.readthedocs.io/en/latest/HowToUsePyparsing.html#classes-in-the-pyparsing-module
import pyparsing as pp
import time
import locale
from collections import namedtuple
import logging
from typing import Optional
from math import floor

locale.setlocale(locale.LC_TIME,"C")

# ----- Parser setup -------
def validate_byte(parse_result) -> bool:
    "Checks that a string represents a valid floating-point number"
    try_num = int(parse_result[0])
    if try_num >= 0 and try_num < 256:
        return True
    else:
        return False
        # raise pp.ParseException(f"Invalid value for a byte: {try_num}")

def validate_real_number(parse_result):
    "Checks that a string represents a valid floating-point number"
    trynum = parse_result[0]
    try:
        float(trynum)
    except ValueError:
        raise pp.ParseException(f"Invalid number: {trynum}")

def validate_date(parse_result):
    "Checks that a string is really a good date"
    candi_date = parse_result[0]
    try:
        time.strptime(candi_date, '%d/%b/%Y:%H:%M:%S %z')
    except ValueError:
        raise pp.ParseException(f"Invalid string for date/time: {candi_date}")

# Floating point number has a three optional parts: before point, point and some digits after point
# Exponentian notation isn't supported yet
digits = pp.Word(pp.nums)
realNum1 = digits
realNum2 = pp.Combine(digits + '.')
realNum3 = pp.Combine('.' + digits)
realNum4 = pp.Combine(digits + '.' + digits)
realNum = pp.Or([realNum4, realNum3, realNum2, realNum1]).set_results_name('value')
realNum.set_parse_action(validate_real_number)

# ip address (v4)
digits1_3 = pp.Word(pp.nums, min=1,max=3)
byte_of_IP = digits1_3
byte_of_IP.add_condition(validate_byte)
ipAddrV4 = pp.Combine(byte_of_IP + ('.' + byte_of_IP) * 3).set_results_name('ip')
# -- time stamp ( 30/Jun/2017:03:28:22 +0300 )
signChar  = pp.Char('+-')
digits2   = pp.Word(pp.nums, exact=2)
digits4   = pp.Word(pp.nums, exact=4)
digits1_2 = pp.Word(pp.nums, min=1, max=2)
skipQuote = pp.Suppress('"')
monShort  = pp.MatchFirst([pp.Literal(s) for s in
                          "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()])
dateStr   = digits1_2 + '/' + monShort + '/' + digits4
timeStr   = digits2 + ':' + digits2 + ':' + digits2
tzStr     = pp.Combine(signChar + digits4)             # only numerical timezones supported now
timeStamp = pp.Combine(dateStr + ':' + timeStr + ' ' + tzStr).set_results_name('ts')
timeStamp.set_parse_action(validate_date)

# -- request record ("GET url HTTP/1.x")
requestType   = pp.MatchFirst([pp.Literal(s) for s in
                       "GET POST CONNECT DELETE HEAD OPTIONS PATCH PUT TRACE".split()]).set_results_name('request')
httpVersion   = pp.MatchFirst([pp.Literal('HTTP/1.0'), pp.Literal('HTTP/1.1')])
urlSchemas = ['http', 'https', 'ftp', 'gopher', 'file']
urlSchemas = [pp.CaselessKeyword(s) for s in urlSchemas]
urlProto = pp.Or(urlSchemas) + pp.Suppress(':/') 
urlChars = pp.alphanums + "/.?&=?_-#%"                 # URL parsing is rather simplistic yet
urlString = pp.Combine(pp.Opt(urlProto) + '/' + pp.Opt(pp.Word(urlChars))).set_results_name('url')
httpRequestData = skipQuote + requestType + urlString + pp.Suppress(httpVersion) + \
                  skipQuote.set_results_name('request')
# remote user, remote IP
remoteUser = pp.Suppress(pp.MatchFirst([pp.Literal('-'), pp.Word(pp.alphanums)]))
realIP = pp.Suppress(pp.MatchFirst([pp.Literal('-'), ipAddrV4]))
statusCode   = pp.Word(pp.nums, exact=3)
bytesTransferred = pp.Word(pp.nums)
refererUrl   = pp.Combine(skipQuote + pp.MatchFirst([pp.Literal('-'), urlString]) + skipQuote)
userAgent    = skipQuote + ... + skipQuote
forwardedFor = skipQuote + ... + skipQuote
requestID    = skipQuote + ... + skipQuote
rbUser       = skipQuote + ... + skipQuote

# -- request time (last field, just a floating point number with a decimal dot)
requestDuration = realNum.set_results_name('duration')
logLine = ( pp.LineStart() + pp.Suppress(ipAddrV4) +  remoteUser + realIP + pp.Suppress('[') + timeStamp + pp.Suppress(']') + httpRequestData +  statusCode + bytesTransferred + refererUrl +  userAgent + forwardedFor + requestID + rbUser + requestDuration + pp.LineEnd() )
# ---------- end of log file parsing ---------

# dureation in milliseconds, ingeger
Request = namedtuple('Request', ['ts', 'url', 'duration'])

def parse_log_line(log_line: str, log: logging.Logger) -> Optional[Request]:
    try:
        pll = logLine.parse_string(log_line)
        # small optimization: multiply durations to 1000, drop fractional part. 
        # This express time in milliseconds.
        int_duration = floor(float(pll.duration) * 1000)
        return Request(pll.ts, pll.url, int_duration)
    except pp.ParseException:
        log.debug('Error parsing the line ' + log_line)
        return None


if __name__ == "__main__":
    print("This is a library, not a program")
