#!/usr/bin/env python3


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import argparse as ap
import nginx_log_parser as nlp
import config_file_parser as cfp
import pyparsing as pp
import itertools as it
import logging
import sys
import os
import pathlib as pl
import datetime
from typing import Optional

# You can modify the default configuration here
CONFIG = """
    REPORT_SIZE: 1000
    REPORT_DIR: ./reports
    LOG_DIR: ./log
    VERBOSE: off
    LOG_GLOB = nginx-access-ui.log-*.gz
    REPORT_GLOB = report-*.html
    ALLOW_EXTENSIONS = gz
    LOG_DATE_FORMAT: '%Y%m%d'
    REPORT_DATE_FORMAT: '%Y.%m.%d'
"""

class ConfigObj:
    "Program configuration as an object"
    def __init__(self, log_dir: str, report_dir: str, report_size: int,
                 verbose: bool = False,
                 log_glob: str = 'nginx_access-*.log', 
                 report_glob: str = 'report-*.html',
                 allow_exts: list[str] = [],
                 log_date_format: str = "%Y%m%d",
                 report_date_format: str = "%Y-%m-%d"):
        self.log_dir     = log_dir
        self.report_dir  = report_dir
        self.report_size = int(report_size)
        self.verbose     = verbose
        self.log_glob    = log_glob
        self.report_glob = report_glob
        self.allow_exts  = set(allow_exts)
        self.log_time_fmt = log_date_format
        self.report_time_fmt = report_date_format

    @classmethod
    def from_cli(cls, cli_params, default_cfg):
        "Initialize from parsed CLI parameters"
        # first, use config file or a CLI config string
        try:
            defaults = cfp.parse_config(cfp.config, default_cfg, logging)
            cfg = defaults
        except pp.ParseException:
            logging.error("Syntax error in default config!")
            raise

        if cli_params.config is not None:
            try:
                parsed = cfp.parse_config(cfp.config, cli_params.config, logging)
            except pp.ParseException:
                logging.error('Invalid config in command line')
                raise
            for key, value in parsed:
                cfg[key] = value

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
            cfg['allow_exts'] = list(cfp.ext_list.parse_string(cli_params.allow_exts))
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
            "Allowed extensions: {}".format(", ".join(list(self.allow_exts))),
            "Log time format {}".format(self.log_time_fmt),
            "Report time format: {}".format(self.report_time_fmt),
            ]))


def check_config(config, log) -> bool:
    log.debug('check_config called')
    "Is the given config a valid one?"
    src_dir = pl.Path(config.log_dir)
    dest_dir = pl.Path(config.report_dir)
    if not src_dir.exists():
        log.error(f"Source directory <{src_dir}> doesn't exist")
        return False
    if dest_dir.exists() and not dest_dir.is_dir():
        log.error("Destination path <{dest_dir}> exists and isn't a directory")
        return False
    # Shall we create non-existing output directory here? XXX
    return True

def are_log_files_here(config, log) -> bool:
    "Check if the input file(s) exists"
    log.debug('are log files here')
    src_dir = pl.Path(config.log_dir)
    try:
        next(it.chain(
                src_dir.glob(config.log_glob),
                it.chain.from_iterable([
                    src_dir.glob(config.log_glob + ext)
                    for ext in config.allow_exts
            ])))
    except StopIteration:
        log.debug('are_log_files_here: no input files found')
    return True

def are_reports_here(config, log) -> bool:


def select_input_file(config, log) -> Optional[pl.Path]:
    log.debug('select_input_file called')
    src_dir = pl.Path(config.log_dir)
    # are there any source files?
    if not are_log_files_here:
        log.info('No input files found, exiting')
        return None
    # Date format of YYYYMMDD allows us to sort files lexicographically searching for the last file
    try:
        last_src_file = max(it.chain(
                            src_dir.glob(config.log_glob),
                            it.chain.from_iterable([
                                src_dir.glob(config.log_glob + ext)
                                for ext in config.allow_exts
                        ])))
        # check destination directory for report of that date
        log.debug(f'select_input_file: Input file {last_src_file} found, processing')
        return last_src_file
    except ValueError:
        # max() on empty sequence -- no input files found
        log.debug('No input files matching glob found')
        return None

def parse_input_date(input_file_name, config, log) -> datetime.date:
    log.debug('parse_input_date called with filename: {input_file_name}')
    prefix, suffix = config.log_glob.split('*')
    input_short_name = pl.Path(input_file_name).name
    date_w_suffix = input_short_name[len(prefix):]
    log.debug(f'parse_input_date::date with suffix: {date_w_suffix}')
    date_only = date_w_suffix[1:date_w_suffix.index(suffix)+1]
    log.debug(f'parse_input_date::date as string: {date_only}')
    return datetime.date(2021,1,1)

def search_for_report(input_file, config, log) -> Optional[pl.Path]:
    log.debug('search_for_report called with input file: {input_file}')
    dest_dir = pl.Path(config.report_dir)
    # Does the output directory exists?
    if dest_dir.is_dir():
        log.debug('destination directory does exist')
        if are_reports_here(config, log)
            # Date format of YYYY.MM.DD allows us to use max() in the search of most recent file
            last_report = max(dest_dir.glob(config.report_glob))
            # select timestamp part from input file name and from last report name
            infile_date = parse_input_date(input_file, config, log)
        else:
            # output directory doesnt contain report files
            log.debug('No report files in the output directory')
            return None
    else:
        log.debug("search_for_report: destination directory doesn't exist")
        return None

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
    p.add_argument('--allow-extension', required=False, dest='allow_exts',
            help='Possible compressed log file extension like gz or bz2')
    return p.parse_args(args)

def process_files(config, log):
    log.debug('process_files called with config and log')
    input_fn = select_input_file(config, log)
    search_for_report(input_fn, config, log)
    pass

def setup_logger() -> logging.Logger:
    # create formatter
    formatter = logging.Formatter('%(asctime)s: %(levelname)s -- %(message)s')
    # create console handler and set level to info
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    # create logger
    logger = logging.getLogger('Console')
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)
    return logger

def main():
    # set up logging
    logger = setup_logger()
    try:
        config = ConfigObj.from_cli(parse_cli(sys.argv[1:]), CONFIG)
        if config.verbose:
            logger.debug("Final configuration: \n" + str(config))
            logger.setLevel(logging.DEBUG)
        if check_config(config, logger):
            process_files(config, logger)
        else:
            logger.critical('Invalid configuration')
            sys.exit(1)
    except pp.ParseException:
        logger.critical('Cannot parse config, this is fatal error')

if __name__ == "__main__":
    main()
