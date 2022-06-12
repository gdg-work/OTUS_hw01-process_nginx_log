#!/usr/bin/env python3


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import argparse as ap
import nginx_log_parser as nlp
import config_file_parser as cfp
import pyparsing as pp
import logging
import sys
import os
import pathlib as pl

# You can modify the default configuration here
CONFIG = """
    REPORT_SIZE: 1000
    REPORT_DIR: ./reports
    LOG_DIR: ./log
    VERBOSE: True
    LOG_GLOB = nginx_access_ui.log-*
    REPORT_GLOB = report-*.html
    ALLOW_EXTENSIONS = gz, Z
"""

class ConfigObj:
    "Program configuration as an object"
    def __init__(self, log_dir: str, report_dir: str, report_size: int,
                 verbose: bool, log_glob: str, report_glob: str,
                 allow_exts: list[str]):
        self.log_dir     = log_dir
        self.report_dir  = report_dir
        self.report_size = int(report_size)
        self.verbose     = verbose
        self.log_glob    = log_glob
        self.report_glob = report_glob
        self.allow_exts  = set(allow_exts)

    @classmethod
    def from_cli(cls, cli_params, default_cfg):
        "Initialize from parsed CLI parameters"
        # first, use config file or a CLI config string
        try:
            defaults = cfp.parse_config(cfp.config, default_cfg, logging)
        except pp.ParseException:
            logging.error("Syntax error in default config!")
            raise
        cfg = {
            'log_dir':     defaults['log_dir'],
            'report_dir':  defaults['report_dir'],
            'report_size': defaults['report_size'],
            'verbose':     defaults['verbose'],
            'log_glob':    defaults['log_glob'],
            'report_glob': defaults['report_glob'],
            'allow_exts':  defaults['allow_exts'],
        }

        if cli_params.config is not None:
            try:
                parsed = cfp.config.parse_string(cli_params.config)
            except pp.ParseException:
                logging.error('Invalid config in command line')
                raise
            cfg['log_dir']     = parsed.log_dir
            cfg['report_dir']  = parsed.report_dir
            cfg['report_size'] = parsed.report_size
            cfg['verbose']     = parsed.verbose
            cfg['log_glob']    = parsed.log_glob
            cfg['report_glob'] = parsed.report_glob
            cfg['allow_exts']  = parsed.allow_exts

        else:
            if cli_params.config_file is not None:
                cfg_file_name = cli_params.config_file
                try:
                    with open(cfg_file_name, 'r') as f_cfg:
                        cfg = cfp.config.parse_file(f_cfg)
                except OSError:
                    logging.error(f'Configuration file: <{cfg_file_name}> cannot be read')
                    raise
                except pp.ParseException:
                    logging.error(f'Configuration file <{cfg_file_name}> is not parseable')
                    raise

        # overwrite params from CLI
        if cli_params.report_size is not None:
            cfg['report_size'] = cli_params.report_size
        if cli_params.report_dir is not None:
            cfg['report_dir'] = cli_params.report_dir
        if cli_params.log_dir is not None:
            cfg['log_dir'] = cli_params.log_dir
        if cli_params.verbose is True:
            cfg['verbose'] = True
        if cli_params.report_glob is not None:
            cfg['report_glob'] = cli_params.report_glob
        if cli_params.log_glob is not None:
            cfg['log_glob'] = cli_params.log_glob
        if cli_params.allow_exts is not None:
            cfg['allow_exts'] = cli_params.ignore_exts
        return ConfigObj(cfg['log_dir'], cfg['report_dir'], int(cfg['report_size']),
                         cfg['verbose'], cfg['log_glob'], cfg['report_glob'],
                         cfg['allow_exts'])

    def __repr__(self):
        return("Program configuration: " + ", ".join([
            "Report dir: {}".format(self.report_dir),
            "Log dir: {}".format(self.log_dir),
            "Verbose: {}".format(self.verbose),
            "Report size: {}".format(self.report_size),
            "Log template: {}".format(self.log_glob),
            "Report template: {}".format(self.report_glob),
            "Allowed extensions: {}".format(",".join(list(self.allow_exts)))
            ]))


def CheckConfig(config) -> bool:
    "Is the given config a valid one?"
    src_dir = pl.Path(config.log_dir)
    if src_dir.exists():
        return True
    return False

def filter_input_extensions(paths: list[pl.Path], allowedExtensions: list[str]) -> list[pl.Path]:
    '''Only files without compression extensions and with allowed extensions
    will stay in the paths list'''
    return []

def selectInputFiles(config, log) -> pl.Path:
    src_dir = pl.Path(config.log_dir)
    dest_dir = pl.Path(config.report_dir)
    # Date format of YYYYMMDD allows us to sort files lexicographically searching for the last file
    last_src_file = max(src_dir.glob(config.log_glob + '*'))
    # check destination directory for report of that date
    
    return last_src_file

def parse_cli(args) -> ap.Namespace:
    p = ap.ArgumentParser(
            description = "Process NGinx log, compute statistics of response time by URL.  Internal cautious use only!", 
            epilog = f'Built-in config is: "{CONFIG}"')
    configs = p.add_mutually_exclusive_group()
    configs.add_argument('-F', '--config-file', type=str, required=False,
            dest='config_file', help="Configuration file path (optional)")
    configs.add_argument('-c', '--config', required=False,
            help=("Optional configuration data as a string: " +
            "(LOG_DIR:... REPORT_DIR:... VERBOSE:... REPORT_SIZE:...) " +
            "You can use ':' or '=', all fields are optional, fields separator is whitespace"))
    p.add_argument('-v', '--verbose', required=False, action='store_true',
            help="Verbosity flag, prints debug messages")
    p.add_argument('-L', '--log-dir', required=False, dest='log_dir',
            help='Directory with log files, optional')
    p.add_argument('-R', '--report-dir', required=False, dest='report_dir',
            help='Directory for HTML reports, optional')
    p.add_argument('-S', '--report-size', required=False, dest='report_size',
            help='Desired report size in lines, optional')
    p.add_argument('--report-glob', required=False, dest='report_glob',
            help='filename template for report, use strptime metacharacters')
    p.add_argument('--log-glob', required=False, dest='log_glob',
            help='filename template for log files, use strptime metacharacters')
    return p.parse_args(args)


def main():
    try:
        config = ConfigObj.from_cli(parse_cli(sys.argv[1:]), CONFIG)
        if config.verbose:
            logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
            logging.debug("Final configuration: \n" + str(config))
    except Exception:
        pass
    pass

if __name__ == "__main__":
    main()
