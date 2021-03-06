#!/usr/bin/env python3

import config_file_parser as cfp
import pyparsing as pp
import argparse as ap
import logging
from   typing import Optional, NamedTuple

class ConfigObj(NamedTuple):
    log_dir: str
    report_dir: str
    report_size: int
    verbose: bool
    debug: bool
    log_glob: str
    report_glob: str
    allow_exts: list[str]
    journal: str
    template_html: str

def parse_cli(args, default_config) -> ap.Namespace:
    p = ap.ArgumentParser(
            description = ("Process NGinx log, compute statistics of response time by URL." +
            "Internal cautious use only!"),
            epilog = f'Built-in config is: "{default_config}"')
    p.add_argument('-F', '--config-file', type=str, required=False,
            default='/usr/local/etc/parse_nginx_log.conf',
            dest='config_file', help="Configuration file path (optional)")
    verbosity_lvl_group = p.add_mutually_exclusive_group()
    verbosity_lvl_group.add_argument('-v', action='count', dest='verbose', default=0,
            help="Verbosity flag, prints information messages ('-vv' also prints debug)",
            )
    verbosity_lvl_group.add_argument('--verbose', action='store', type=int, dest='verbose', default=0,
            help="Verbosity level as a digit (0-2, 0 for ERROR only output, 1 for INFO, 2 for DEBUG)",
            )
    p.add_argument('-L', '--log-dir', required=False, dest='log_dir',
            help='Directory with source log files, optional')
    p.add_argument('-R', '--report-dir', required=False, dest='report_dir',
            help='Directory for HTML reports, optional')
    p.add_argument('-S', '--report-size', required=False, dest='report_size',
            help='Desired report size in lines, optional')
    p.add_argument('-j', '--journal-to', required=False, dest='journal',
            help="This program's log file, default to STDERR")
    p.add_argument('--report-glob', required=False, dest='report_glob',
            help='filename template for report, use strptime metacharacters')
    p.add_argument('--log-glob', required=False, dest='log_glob',
            help='filename template for log files, use strptime metacharacters')
    p.add_argument('--allow-extension', required=False, dest='allow_exts',
            help='Possible compressed log file extension like gz or bz2')
    p.add_argument('--template', required=False, default='', help='HTML template for the report')
    return p.parse_args(args)

def config_from_cli(cli_params: ap.Namespace, default_cfg: str, log: logging.Logger) -> Optional[ConfigObj]:
    "Initialize from parsed CLI parameters"
    # first, use config file or a CLI config string
    cfg = cfp.parse_config(cfp.config, default_cfg, log)
    if cfg is None:
        log.error('Cannot parse default (internal) config, exiting')
        return None

    log.debug("Current config: " + str(cfg))

    if cli_params.config_file is not None:
        cfg_file_name = cli_params.config_file
        try:
            with open(cfg_file_name, 'r', encoding='utf-8') as f_cfgfile:
                updates = cfp.parse_config(cfp.config, f_cfgfile.read(), log)
                if updates is not None:
                    cfg.update(updates)
                else:
                    log.debug('Null config, using default configuration')
        except OSError:
            log.error(f'Configuration file: <{cfg_file_name}> cannot be read')
            return None
        except pp.ParseException:
            log.error(f'Configuration file <{cfg_file_name}> is not parseable')
            return None

    # overwrite params from CLI
    if cli_params.report_size is not None:
        cfg['report_size'] = cli_params.report_size
    if cli_params.report_dir is not None:
        cfg['report_dir'] = cli_params.report_dir
    if cli_params.log_dir is not None:
        cfg['log_dir'] = cli_params.log_dir
    if cli_params.verbose > 0:
        cfg['verbose'] = True
        if cli_params.verbose > 1:
            cfg['debug'] = True
    if cli_params.report_glob is not None:
        cfg['report_glob'] = cli_params.report_glob
    if cli_params.log_glob is not None:
        cfg['log_glob'] = cli_params.log_glob
    if cli_params.journal != '':
        cfg['journal'] = cli_params.journal
    if cli_params.template != '':
        cfg['template_html'] = cli_params.template
    if cli_params.allow_exts is not None:
        cfg['allow_exts'] = list(cfp.ext_list.parse_string(cli_params.allow_exts))

    # fix 'allow_exts' list: add dots to filename extensions
    extslist = ['.' + e.strip('.') for e in cfg['allow_exts']]
    cfg['allow_exts'] = extslist

    return ConfigObj(
            log_dir     = cfg['log_dir'],
            report_dir  = cfg['report_dir'],
            report_size = int(cfg['report_size']),
            verbose     = cfg['verbose'], 
            debug       = cfg['debug'],
            log_glob    = cfg['log_glob'],
            report_glob = cfg['report_glob'],
            allow_exts  = cfg['allow_exts'],
            journal     = cfg['journal'],
            template_html = cfg['template_html']
        )
        
def configure(argv: list[str], log: logging.Logger, default_config :str):
    try:
        result = config_from_cli(parse_cli(argv, default_config), default_config, log)
        return result
    except pp.ParseException:
        log.critical('Cannot parse config, this is fatal error')
        return None

if __name__ == "__main__":
    print("This is a library, not a program")
