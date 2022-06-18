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
import fileinput
import pathlib as pl
import datetime as dt
from typing import Optional, Union, NamedTuple, Callable
from collections.abc import MutableMapping
from enum import Enum
import json

# You can modify the default configuration here
CONFIG = """
    REPORT_SIZE: 100
    REPORT_DIR: /tmp/test/report/
    LOG_DIR: /tmp/test/log/
    VERBOSE: off
    LOG_GLOB: nginx-access-ui.log-%Y%m%d
    REPORT_GLOB: report-%Y.%m.%d.html
    ALLOW_EXTENSIONS: gz
    # Next line is for optional journal file.
    # JOURNAL:
"""

# Some pseudo constants for logger (see logging module documentation)
LOG_LINE_FORMAT = r'%(asctime)s: %(levelname).1s -- %(message)s'
LOG_DATE_FORMAT = r'%Y.%m.%d %H:%M:%S'

class ReportFileState(Enum):
    NOFILE = 1
    NODIR = 2

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
        try:
            if not src_dir.exists():
                log.error(f"Source directory <{src_dir}> doesn't exist")
                return False
            if dest_dir.exists() and not dest_dir.is_dir():
                log.error("Destination path <{dest_dir}> exists and isn't a directory")
                return False
        except PermissionError:
            log.critical(f"Permission denied checking source dir {src_dir} and destination dir {dest_dir}")
            return False
        return True

    def parse_input_date(input_file_name) -> Optional[dt.date]:
        """make a date from filename. We cannot simply call strptime because of
        compression extensions that are possible"""
        log.debug(f'parse_input_date called with filename: {input_file_name}')
        time_pattern = config.log_glob
        input_path = pl.Path(input_file_name)
        # get rid of compression extensions
        if ('.' + input_path.suffix) in config.allow_exts:
            input_short_name = input_path.stem
        else:  # no compression extension encounted
            input_short_name = input_path.name

        try:
            time = dt.datetime.strptime(input_short_name,time_pattern)
            return time.date()
        except ValueError:
            log.error(f'parse_input_date::Unparseable date (format {time_pattern}, filename {input_short_name})')
            return None
            
    def select_input_file() -> Optional[pl.Path]:
        log.debug(f'select_input_file called, config.log_dir is <{config.log_dir}>, config.log_glob is <{config.log_glob}>')
        src_dir = pl.Path(config.log_dir)
        # Date format of YYYYMMDD and alike allows us to sort files lexicographically searching
        # for the last file. Here we chain iterators of log_glob per se and with all
        # allowed extensions
        glob_pattern = cfp.template_to_glob(config.log_glob)
        try:
            last_src_file = max(it.chain(
                                src_dir.glob(glob_pattern),
                                it.chain.from_iterable([
                                    src_dir.glob(glob_pattern + ext)
                                    for ext in config.allow_exts
                            ])))
            # check destination directory for report of that date
            log.debug(f'select_input_file: Input file {last_src_file} found, processing')
            return last_src_file
        except ValueError:
            # max() on empty sequence -- no input files found
            log.debug(f'No input files matching pattern <{config.log_glob}> found')
            return None

    def make_report_filename(input_file) -> pl.Path:
        log.debug(f'make_report_filename called with input file: {input_file}')
        # Using the new 3.10 features here, could be done with if/else
        match parse_input_date(input_file):
            case None:
                log.info('Invalid date in input file, trying to cope.  Will use current date instead')
                report_file_name = dt.date.today().strftime(config.report_glob)
            case infile_date:
                log.debug(f'search_for_report: input file date is: {infile_date}')
                report_file_name = infile_date.strftime(config.report_glob)
        # construct report's name
        full_report_fn = pl.Path(config.report_dir) / pl.Path(report_file_name)
        log.debug(f'make_report_filename::constructed filename is: {full_report_fn}')
        return full_report_fn

    def search_for_report(input_file) -> Union[pl.Path, ReportFileState]:
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
                return ReportFileState.NOFILE
        else:
            log.debug("search_for_report: destination directory doesn't exist")
            return ReportFileState.NODIR

    class UrlInfo(NamedTuple):
        """all the URL information will be collected here. The URL itself will
           be a key in the dictionary where this tuple will be a value"""
        occurencies: int = 0
        max_latency: int = 0
        sum_latency: int = 0
        # durations: list[int] = []

    class GeneralStats(NamedTuple):
        """General statistics, i.e. requests count and total time used for requests processing"""
        total_records: int = 0
        sum_latency: int = 0

    UrlDict = MutableMapping[str, UrlInfo]
    StatsResult = tuple[UrlDict, GeneralStats]

    def add_to_stats(url, duration, url_stats: UrlDict, gen_stats: GeneralStats):
        # trying creation of docstrings from list of strings
        " ".join(["Add current record to statistics in url_stats and gen_stats variables.",
                  "Both url_stats and gen_stats will be modified by this function"])
        if url in url_stats:
            url_state = url_stats[url]
            url_stats[url] = UrlInfo(
                url_state.occurencies + 1,
                max(duration, url_state.max_latency),
                url_state.sum_latency + duration,
                # url_state.durations.append(durations),
            )
        else:
            # url_stats[url] = UrlInfo(1, duration, duration, [duration])
            url_stats[url] = UrlInfo(1, duration, duration)
        gen_stats = GeneralStats(total_records = gen_stats.total_records +1, sum_latency= gen_stats.sum_latency + duration)
        return url_stats, gen_stats


    def process_one_file(in_file_name: pl.Path) -> Optional[StatsResult]:
        log.debug(f'process_one_file::called with params {in_file_name}')
        # iterate over lines of (possibly compressed) file
        bad_lines_counter = 0
        read_lines_counter = 0
        general_stats = GeneralStats()
        url_stats = {}
        try:
            with fileinput.input(files=in_file_name, encoding='utf-8',
                    openhook=fileinput.hook_compressed) as fin:
                for in_line in fin:
                    read_lines_counter += 1
                    linedata = nlp.parse_log_line(in_line, log)
                    match linedata:
                        case None:
                            bad_lines_counter += 1
                        case nlp.Request(_, url, duration):
                            # small optimization: don't add zeroes
                            if duration > 0:
                                # ignore timestamp for now
                                url_stats, general_stats = add_to_stats(url, duration,  url_stats, general_stats)
                            pass
            log.info(f'% of bad lines in file {in_file_name}: ' +
                    "{:3.1f}".format(bad_lines_counter * 100 / read_lines_counter))
            return (url_stats, general_stats)
        except PermissionError:
            log.critical('Permission denied reading input file')
            return None
        except OSError:
            log.critical('Cannot read input file {in_file_name} (OSError)')
            return None

    class OutputUrlStats(NamedTuple):
        url: str
        count: int
        time_avg: float
        time_max: float
        time_sum: float
        time_med: float
        time_perc: float
        count_perc: float

    def compute_output_stats(UrlInfo, total_count, total_duration) -> OutputUrlStats:
        return None

    def process_stats(stats: StatsResult) -> list[OutputUrlStats]:
        """Computes some summary statistics about processing duration/latencies"""
        url_stats = stats[0]
        total_count = stats[1].total_records
        total_duration = stats[1].sum_latency
        # sort URL statistics by sum duration and take first N from them
        # url_stats.sort
        out = [compute_output_stats(rec, total_count, total_duration)
               for rec in url_stats
              ]
        return out

    def process_files():
        log.debug(f'process_files called')
        input_fn = select_input_file()
        if input_fn is None:
            # no input files, that's normal
            log.info(f'No input files matching {config.log_glob} found in {config.log_dir}, nothing to do')
            return
        report_search_result = search_for_report(input_fn)
        match report_search_result:
            case ReportFileState.NODIR:
                try:
                    pl.Path(config.report_dir).mkdir(parents=True)
                except PermissionError:
                    log.error(f'Permission denied creating report directory: {config.report_dir}')
                    return
            case pl.Path:
                log.info(f"Existing report file {report_search_result} found, no work to do")
            case ReportFileState.NOFILE:
                stats = process_one_file(input_fn)
                if stats is not None:
                    process_stats(stats)
                else:
                    log.debug('process_files: bad return from process_one_file')
        return

    return {
            'check_config': check_config,
            'select_input_file': select_input_file,
            'parse_input_date': parse_input_date,
            'make_report_filename': make_report_filename,
            'process_files': process_files,
        }


def parse_cli(args) -> ap.Namespace:
    p = ap.ArgumentParser(
            description = ("Process NGinx log, compute statistics of response time by URL." +
            "Internal cautious use only!"),
            epilog = f'Built-in config is: "{CONFIG}"')
    configs = p.add_mutually_exclusive_group()
    configs.add_argument('-F', '--config-file', type=str, required=False,
            default='/usr/local/etc/parse_nginx_log.conf',
            dest='config_file', help="Configuration file path (optional)")
    # removed, too cumbersome
    # configs.add_argument('-c', '--config', required=False,
    #        help=("Optional configuration data as a string: " +
    #        "(LOG_DIR:... REPORT_DIR:... VERBOSE:... REPORT_SIZE:...) " +
    #        "You can use ':' or '=', all fields are optional, fields separator is whitespace"))
    # 
    p.add_argument('-v', '--verbose', required=False, action='store_true',
            help="Verbosity flag, prints debug messages")
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
    return p.parse_args(args)


def parametrize_loggers(fmt, datefmt) -> tuple[logging.Logger,
                                               Callable[[int],None],  # logging.DEBUG etc.
                                               Callable[[str],None]]:
    formatter = logging.Formatter(fmt=fmt,
                                  datefmt=datefmt)
    logger = logging.getLogger('nginx log processing')
    logger.setLevel(logging.INFO)

    def add_console_logger():
        # create console handler and set level to info
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        return

    def setlevel(new_level):
        logger.setLevel(new_level)

    def add_file_logger(filename):
        fh = logging.FileHandler(filename)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        return

    add_console_logger()
    return (logger, setlevel, add_file_logger)

def main() :
    # set up logging
    log, set_lvl, add_logfile = parametrize_loggers(LOG_LINE_FORMAT, LOG_DATE_FORMAT)
    try:
        config = prgconf.config_from_cli(parse_cli(sys.argv[1:]), CONFIG)
        log.info(f"Config is: {config}")
        if config is None:
            log.critical('Unreadable config, exiting')
            sys.exit(2)
        if config.verbose:
            log.debug("Final configuration: \n" + str(config))
            set_lvl(logging.DEBUG)
        if config.journal is not None and config.journal != "":
            log.debug(f'main: config.journal is <{config.journal}>')
            add_logfile(config.journal)
        funs = setup_functions(config, log)
        if funs['check_config']():
            funs['process_files']()
        else:
            log.critical('Invalid configuration')
            sys.exit(1)
    except pp.ParseException:
        log.critical('Cannot parse config, this is fatal error')

if __name__ == "__main__":
    main()
