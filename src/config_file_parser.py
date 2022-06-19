#!/usr/bin/env python3
import pyparsing as pp
from typing import Optional
# ------- Config file parsing ----------:
# # optional comment to end of line 
# REPORT_SIZE   : 1000,
# REPORT_DIR    : ./reports,
# LOG_DIR       : ./log,
# VERBOSE       : True,
# REPORT_GLOB   : report-%Y-%m-%d.html
# LOG_GLOB      : nginx_log-%Y%m%d
# ALLOW_EXTS    : gz, bz2
# JOURNAL       : /tmp/nginx_parser.log
# TEMPLATE_HTML : report.html

var_name_separator = pp.Suppress(pp.Char(':='))
comment_line = pp.Optional(pp.LineStart() + '#' + pp.SkipTo(pp.LineEnd()))
# path is too simplistic, needs to be replaced by OS.path, may be
path         = pp.Word(pp.identbodychars + '.~/')
true_val     = pp.one_of('true on 1', caseless=True).set_parse_action(pp.replace_with(True))
false_val    = pp.one_of('false  off 0', caseless=True).set_parse_action(pp.replace_with(False))
bool_val     = pp.Or([true_val, false_val])

# -- time strings in filenames
supported_time_metas = pp.Char('YmdbF')
time_metachar = pp.Combine('%' + supported_time_metas)
time_other = pp.Optional(pp.Word(pp.alphanums + '-;_!@#$^&*([{}]),.<>/?`'))
time_pattern = pp.Combine(time_metachar +
                          pp.ZeroOrMore(time_other + 
                                        time_metachar)).set_results_name('time_fmt')

path_element = pp.Word(pp.alphanums + '-_+.@#^=[]{}(),')  # Note the absense of '%'

# -- filenames with strptime metacharacters to be replaced with date/time components
fileglob_time_middle = pp.Combine(path_element + time_pattern + path_element)
fileglob_time_end = pp.Combine(path_element + time_pattern)
fileglob_time_beginning = pp.Combine( time_pattern + path_element)
fileglob_tmpl  = pp.Or([fileglob_time_middle,
                        fileglob_time_end,
                        fileglob_time_beginning]).set_results_name('fname_template')
# -- log file
my_journal = pp.Optional(pp.Suppress(pp.CaselessKeyword('journal')) + var_name_separator +
              path.set_results_name('journal'))

# -- files extensions list
ext_component = pp.Word(pp.alphanums, min=1, max=4)  # .zest
ext_keyword   = pp.CaselessKeyword('allow_extensions')
ext_sep       = pp.Char(',. ')
ext_list      = (pp.delimited_list(ext_component, ext_sep, allow_trailing_delim=True))
allow_exts    = (pp.Optional(pp.Suppress(ext_keyword) + var_name_separator +
                 pp.Optional(ext_list).set_results_name('allowed_exts')))
# -- config variables
report_size  = pp.Optional(pp.Suppress(pp.CaselessKeyword('report_size')) +
               var_name_separator + pp.Word(pp.nums).set_results_name('report_size'))
report_dir   = pp.Optional(pp.Suppress(pp.CaselessKeyword('report_dir')) +  
               var_name_separator + path.set_results_name('report_dir'))
log_dir      = pp.Optional(pp.Suppress(pp.CaselessKeyword('log_dir')) +
               var_name_separator + path.set_results_name('log_dir'))
verbose_flag = pp.Optional(pp.Suppress(pp.CaselessKeyword('verbose')) +
               var_name_separator + bool_val.set_results_name('verbose'))
log_glob     = pp.Optional(pp.Suppress(pp.CaselessKeyword('log_glob')) +
               var_name_separator + fileglob_tmpl.set_results_name('log_glob'))
report_glob  = pp.Optional(pp.Suppress(pp.CaselessKeyword('report_glob')) +
               var_name_separator + fileglob_tmpl.set_results_name('report_glob'))
log_date_format = pp.Optional(pp.Suppress(pp.CaselessKeyword('log_date_format')) + 
               var_name_separator + time_pattern)
report_date_format = pp.Optional(pp.Suppress(pp.CaselessKeyword('report_date_format')) + 
               var_name_separator + time_pattern)
report_template = pp.Optional(pp.Suppress(pp.CaselessKeyword('template_html')) +
               var_name_separator + path.set_results_name('template_html'))
# -- config as a whole
config       = pp.Each([comment_line, report_size, report_dir, log_dir,
                        verbose_flag, log_glob, report_glob, allow_exts,
                        log_date_format, report_date_format, my_journal,
                        report_template])
# ---- End of config file parsing ----

def template_to_glob(tmpl :str) -> str:
    """converts filename template with strptime metacharacters to
       shell globbing pattern.  Not all metacharacters are supported yet, only %[YmdbF]
       Years are limited by pattern 20xx, where x is [0-9]
    """
    metachar_table = {
        '%F': '20[0-9][0-9]-[01][0-9]-[0-3][0-9]',
        '%Y': '20[0-9][0-9]',
        '%m': '[01][0-9]',
        '%d': '[0-3][0-9]',
        '%b': '[A-Z][a-z][a-z]',
        }
    curstr = tmpl
    for mc in metachar_table.keys():
        curstr = curstr.replace(mc, metachar_table[mc])
    return curstr

def parse_config(parser_obj, config_string, log) -> Optional[dict]:
    try:
        parsed = parser_obj.parse_string(config_string)
        if parsed:
            # Can't make a good parser here. parserObject in ParseObject returns
            if parsed.allowed_exts:
                extensions_list = list(parsed.allowed_exts)
            else:
                extensions_list = []
            return {
                'report_size': parsed.report_size,
                'report_dir' : parsed.report_dir,
                'log_dir'    : parsed.log_dir,
                'verbose'    : parsed.verbose,
                'debug'      : False,
                'report_glob': parsed.report_glob,
                'log_glob'   : parsed.log_glob,
                'allow_exts' : extensions_list,
                'template_html' : parsed.template_html,
            }
        else:
            log.error(f"Trying to parse empty string <{config_string}> as a program configuration")
            return None
    except pp.ParseException:
        log.error(f"Cannot parse configuration: <{config_string}>")
        return None


if __name__ == "__main__":
    print("This is a library, not a program")
