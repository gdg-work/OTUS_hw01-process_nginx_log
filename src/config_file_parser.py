#!/usr/bin/env python3
import pyparsing as pp
import typing as t

# ------- Config file parsing ----------
#     # optional comment to end of line
#     REPORT_SIZE: 1000,
#     REPORT_DIR: ./reports,
#     LOG_DIR: ./log,
#     VERBOSE: True,

var_name_separator = pp.Suppress(pp.Char(':='))
comment_line = pp.Optional(pp.LineStart() + '#' + pp.SkipTo(pp.LineEnd()))
# path is too simplistic, needs to be replaced by OS.path, may be
path         = pp.Word(pp.identbodychars + '.~/')
true_val     = pp.one_of('true on 1', caseless=True).set_parse_action(pp.replace_with(True))
false_val    = pp.one_of('false  off 0', caseless=True).set_parse_action(pp.replace_with(False))
bool_val     = pp.Or([true_val, false_val])
# -- filenames
time_metachars = pp.one_of('%Y %m %d %H %M %S %B %b %z')
time_format  = pp.OneOrMore(time_metachars)
year         = pp.Word(pp.nums, exact=4)  # very primitive now, can be extended
month        = pp.Word(pp.nums, exact=2)
day          = pp.Word(pp.nums, exact=2)
star         = pp.Char('*')
date_wo_seps = pp.Combine(year + month + day).set_results_name('date')
date_w_seps  = pp.Combine(year + pp.Suppress('.') + month + pp.Suppress('.') + day).set_results_name('date')
report_fn_tmpl =  pp.Keyword('report') + '-' + star + '.' + pp.Keyword('html')
compress_ext = pp.Optional(pp.Literal('.gz'))
path_element = pp.Word(pp.alphanums + '-_+.@#%^=[]{}(),')
# -- file glob is a combination of optional path element, star, optional path element and optional compress suffix
fileglob_star_middle = pp.Combine(path_element + star + path_element + compress_ext)
fileglob_star_end = pp.Combine(path_element + star + compress_ext)
fileglob_star_beginning = pp.Combine( star + path_element + compress_ext)
fileglob_tmpl  = pp.Or([fileglob_star_middle, fileglob_star_end, fileglob_star_beginning])
# -- files extensions list
ext_component = pp.Word(pp.alphanums, min=1, max=4)  # .zest
ext_keyword   = pp.CaselessKeyword('allow_extensions')
ext_sep       = pp.Char(',. ')
ext_list      = (pp.delimited_list(ext_component, ext_sep, allow_trailing_delim=True)).set_results_name('allowed_exts')
allow_exts    = (pp.Optional(pp.Suppress(ext_keyword) + var_name_separator + pp.Optional(ext_list))
                        )
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
# -- config as a whole
config       = pp.Each([comment_line, report_size, report_dir, log_dir,
                        verbose_flag, log_glob, report_glob, allow_exts])
# ---- End of config file parsing ----

def parse_config(parser_obj, config_string, log) -> dict:
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
                'report_glob': parsed.report_glob,
                'log_glob'   : parsed.log_glob,
                'allow_exts' : extensions_list
            }
    except pp.ParseException:
        log.critical(f"Cannot parse configuration: <{config_string}>, exiting")
        raise pp.ParseException('Unparseable config')
    return {}


if __name__ == "__main__":
    print("This is a library, not a program")
