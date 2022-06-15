#!/usr/bin/env python3


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import argparse as ap
import nginx_log_parser as nlp
import config_file_parser as cfp
import program_config as prgconf
import pyparsing as pp
import itertools as it
import logging
import sys
import os
import pathlib as pl
import datetime as dt
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
    LOG_DATE_FORMAT: %Y%m%d
    REPORT_DATE_FORMAT: %Y.%m.%d
"""

def setup_functions(config, log):
    """
    Defines some functions with pre-defined parameters of 'configuration object'
    and 'logger object'.
    Returns a dictionary with function name as key and defined function as value
    """

    def check_config() -> bool:
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


    def select_input_file() -> Optional[pl.Path]:
        log.debug(f'select_input_file called, config.log_dir is <{config.log_dir}>, config.log_glob is <{config.log_glob}>')
        src_dir = pl.Path(config.log_dir)
        # Date format of YYYYMMDD allows us to sort files lexicographically searching
        # for the last file. Here we chain iterators of log_glob per se and with all
        # allowed extensions
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
            log.debug(f'No input files matching pattern <{config.log_glob}> found')
            return None

    def parse_input_date(input_file_name) -> Optional[dt.date]:
        log.debug(f'parse_input_date called with filename: {input_file_name}')
        prefix, suffix = config.log_glob.split('*')
        input_short_name = pl.Path(input_file_name).name
        date_w_suffix = input_short_name[len(prefix):]
        log.debug(f'parse_input_date::date with suffix: {date_w_suffix}')
        date_only = date_w_suffix[0:date_w_suffix.index(suffix)]
        log.debug(f'parse_input_date::date as string: {date_only}')
        try:
            return dt.datetime.strptime(date_only, config.log_time_fmt).date()
        except: 
            log.error(f'parse_input_date::Unparseable date (format {config.log_time_fmt}, given string {date_only})')
            return None

    def make_report_filename(input_file) -> pl.Path:
        log.debug(f'make_report_filename called with input file: {input_file}')
        # Using the new 3.10 features here, could be done with if/else
        match parse_input_date(input_file):
            case None:
                log.info('Invalid date in input file, trying to cope.  Will use current date instead')
                report_date = dt.date.today().strftime(config.report_time_fmt)
            case infile_date:
                log.debug(f'search_for_report: input file date is: {infile_date}')
                report_date = infile_date.strftime(config.report_time_fmt)
        # construct report's name
        prefix, suffix = config.report_glob.split('*')
        report_file_name = pl.Path(prefix + report_date + suffix)
        full_report_fn = pl.Path(config.report_dir / report_file_name)
        log.debug(f'make_report_filename::constructed filename is: {full_report_fn}')
        return full_report_fn

    def search_for_report(input_file) -> Optional[pl.Path]:
        log.debug(f'search_for_report called with input file: {input_file}')
        dest_dir = pl.Path(config.report_dir)
        # Does the output directory exists?
        if dest_dir.is_dir():
            log.debug('search_for_report::destination directory does exist')
            full_report_fn = make_report_filename(input_file)
            if full_report_fn.exists() and full_report_fn.is_file() and full_report_fn.stat().st_size > 0:
                log.debug(f'search_for_report::Found existing report file: {full_report_fn}')
                return full_report_fn
            else:
                # the file will be created/recreated
                return None
        else:
            log.debug("search_for_report: destination directory doesn't exist")
            return None

    def process_files():
        log.debug('process_files called with config and log')
        input_fn = select_input_file()
        if input_fn is None:
            # no input files, that's normal
            return
        match search_for_report(input_fn):
            case None:
                pass
            case pl.Path(file_name):
                log.debug(f"Existing report file {file_name} found, no work to do")
                pass
        pass

    return {
            'check_config': check_config,
            'select_input_file': select_input_file,
            'parse_input_date': parse_input_date,
            'make_report_filename': make_report_filename,
            'process_files': process_files,
        }

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
        config = prgconf.ConfigObj.from_cli(parse_cli(sys.argv[1:]), CONFIG)
        if config.verbose:
            logger.debug("Final configuration: \n" + str(config))
            logger.setLevel(logging.DEBUG)
        funs = setup_functions(config, logger)
        if funs['check_config']():
            funs['process_files']()
        else:
            logger.critical('Invalid configuration')
            sys.exit(1)
    except pp.ParseException:
        logger.critical('Cannot parse config, this is fatal error')

if __name__ == "__main__":
    main()
