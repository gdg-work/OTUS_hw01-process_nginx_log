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
from dataclasses import dataclass
from typing import Optional, Union, NamedTuple, Callable, Any
from collections.abc import  MutableMapping
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
    REPORT_TEMPLATE: report.html
    # Next line is for optional journal file.
    # JOURNAL:
"""

# Some pseudo constants for logger (see logging module documentation)
LOG_LINE_FORMAT = r'%(asctime)s: %(levelname).1s -- %(message)s'
LOG_DATE_FORMAT = r'%Y.%m.%d %H:%M:%S'

class ReportFileState(Enum):
    NOFILE = 1
    NODIR = 2

class UrlInfo(NamedTuple):
    """all the URL information will be collected here. The URL itself will
       be a key in the dictionary where this tuple will be a value"""
    occurencies: int = 0
    max_latency: int = 0
    sum_latency: int = 0
    # durations: list[int] = []

@dataclass(frozen=True)
class GeneralStats:
    """General statistics, i.e. requests count and total time used for requests
    processing"""
    total_records: int
    sum_latency  : int

@dataclass(frozen=True)
class OutputUrlStats:
    "fields for JSON output"
    url       : str
    count     : int
    time_avg  : float
    time_max  : float
    time_sum  : float
    time_med  : float
    time_perc : float
    count_perc: float

UrlDict     = MutableMapping[str, UrlInfo]
StatsResult = tuple[UrlDict, GeneralStats]

# -- trying to re-implement Rust Status class
@dataclass(frozen=True)
class Err:
    msg: str = 'Some error occured'

@dataclass(frozen=True)
class Ok:
    data : Any = None

StatusWithData = Union[Err, Ok]

def compute_output_stats(url: str, url_info: UrlInfo, total_count: int,
                         total_duration: int) -> OutputUrlStats:
    return OutputUrlStats(
        url        = url,
        count      = url_info.occurencies,
        time_max   = float(url_info.max_latency) / 1000,
        time_sum   = float(url_info.sum_latency) / 1000,
        time_med   = 0.0,
        time_perc  = float(100*url_info.sum_latency)/float(total_duration),
        count_perc = float(100*url_info.occurencies)/float(total_count),
        time_avg   = url_info.sum_latency / (url_info.occurencies * 1000),
        )

def select_n_longest_delayd_urls(stats: UrlDict, n: int) -> list[str]:
    "Selects N URLs with the most sum_latency and returns them as a list"
    threshold = 1  # milliseconds, XXX better be parametrized
    url_tuples = [ (u, s.sum_latency) for u,s in stats.items() if s.sum_latency > threshold ]
    url_tuples.sort(key = lambda x: x[1], reverse=True)
    urls_selected = [u for u, _ in url_tuples][0:n]
    return urls_selected

def process_stats(stats: StatsResult, urls_count_to_select) -> list[OutputUrlStats]:
    """Computes some summary statistics about processing duration/latencies"""
    url_stats, totals = stats
    # sort URL statistics by sum duration and take first N from them
    urls_s = select_n_longest_delayd_urls(url_stats, urls_count_to_select)
    # url.stats.take_first(config.ort_size)
    return ([ compute_output_stats(url, url_stats[url], totals.total_records, totals.sum_latency)
               for url in urls_s ])

class OutputJSONEncoder(json.JSONEncoder):
    """Helper class for encoding OutputUrlStats to JSON"""

    def default(self, out_rec):
        if isinstance(out_rec, OutputUrlStats):
            return out_rec.__dict__
        else:
            return super().default(out_rec)

def output_to_json(stats_list: list[OutputUrlStats]) -> str:
    return json.dumps(stats_list, cls=OutputJSONEncoder, separators=(',', ':')) 

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
        report_tmpl = pl.Path(config.template_html)
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
        if report_tmpl.exists() and report_tmpl.is_file():
            try:
                with open(report_tmpl, "r") as f_in:
                    _ = f_in.read(1)  # read one byte to check the file
            except OSError:
                log.critical(f"Cannot read a template for report from file: <{report_tmpl}>")
                return False
        else:
            return False
        return True

    def parse_input_date(input_file_name) -> Optional[dt.date]:
        """make a date from filename. We cannot simply call strptime because of
        compression extensions that are possible"""
        log.debug(f'parse_input_date called with filename: {input_file_name}')
        time_pattern = config.log_glob
        input_path = pl.Path(input_file_name)
        # get rid of compression extensions
        if input_path.suffix in config.allow_exts:
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
                                    src_dir.glob(glob_pattern + ext)  # extensions in list are with dots (.gz etc)
                                    for ext in config.allow_exts ])))
            # check destination directory for report of that date
            log.debug(f'select_input_file: Input file {last_src_file} found, processing')
            return last_src_file
        except ValueError:
            # max() on empty sequence -- no input files found
            log.info(f'No input files matching pattern <{config.log_glob}> found')
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
                log.info(f'search_for_report::Found existing report file: {full_report_fn}')
                return full_report_fn
            else:
                # the file will be created/recreated
                return ReportFileState.NOFILE
        else:
            log.debug("search_for_report: destination directory doesn't exist")
            return ReportFileState.NODIR

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
        good_lines_counter = 0
        read_lines_counter = 0
        general_stats = GeneralStats(0, 0)
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
                            good_lines_counter += 1
            log.info(f'% of bad lines in file {in_file_name}: ' +
                    "{:3.1f}".format(bad_lines_counter * 100 / (good_lines_counter + bad_lines_counter)))
            return (url_stats, general_stats)
        except PermissionError:
            log.critical('Permission denied reading input file')
            return None
        except OSError:
            log.critical('Cannot read input file {in_file_name} (OSError)')
            return None

    def read_report_template() -> Optional[str]:
        """Tries to read report template from file in configuration object,
        returns contents of the file or None when read failed"""
        try:
            with open(config.template_html, 'r', encoding='utf8') as f_in:
                return f_in.read()
        except OSError:
            log.critical(f'Error reading report template from file <{config.template_html}>')
            return None

    def make_report(json_data: str) -> Optional[str]:
        "Mates json data and template to make formatted report"
        report_template = read_report_template()
        if report_template is not None:
            return report_template.replace(r'$table_json', json_data, 1)
        else:
            log.critical(f'Error reading HTML template file <{config.template_html}>')
            return None

    def write_json_to_output_file(json_data: str, input_fn: pl.Path) -> StatusWithData:
        if input_fn is None:
            # I know, at this point input_fn will definitely not be None, but...
            log.critical("No input file given, cannot construct output file")
            return Err(msg = "No input file name given, cannot create output")
        else:
            output_fn = make_report_filename(input_fn)
            report_html = make_report(json_data)
            if report_html is None:
                return Err('Null HTML output')
            else:
                try:
                    with open(output_fn, 'w', encoding='utf8') as out_f:
                        bytes_written = out_f.write(make_report(json_data))
                        return Ok(data = bytes_written)
                except OSError:
                    log.critical(f"Error writing to output file <{output_fn}>, disk full?")
                    return Err(msg = "Error writing to output file")

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
                    match write_json_to_output_file(
                                output_to_json(process_stats(stats, config.report_size)),
                                input_fn):
                        case Ok(data=bytes_written):
                            log.info(f'Finished, {bytes_written} bytes written to output file')
                        case Err(msg=message):
                            log.critical(message)
                else:
                    log.info('process_files: bad return from process_one_file')
        return

    return {
            'check_config': check_config,
            'select_input_file': select_input_file,
            'parse_input_date': parse_input_date,
            'make_report_filename': make_report_filename,
            'process_files': process_files,
        }

def parametrize_loggers(fmt, datefmt) -> tuple[logging.Logger,
                                               Callable[[int],None],  # set level logging.DEBUG etc.
                                               Callable[[str],None],  # set log filename
                                               ]:
    """Setting up loggers.  Parameters: 1) message format, 2) timestamp format
    Returns: 1) logger,
    2) function to set verbosity level, 
    3) function to add a log file to the logger.
    """
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    logger = logging.getLogger('Nginx log processing')

    def add_console_logger():
        # create console handler and set level to info. Uses 'logger' object from higher level
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        return

    def setlevel(new_level):
        logger.setLevel(new_level)

    def add_file_logger(filename):
        # adds a file to the logger
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
        config = prgconf.configure(sys.argv[1:], log, CONFIG)
        if config is None:
            log.critical('Unreadable config, exiting')
            sys.exit(2)
        if config.verbose:
            set_lvl(logging.INFO)
            if config.debug:
                log.debug("Final configuration: \n" + str(config))
                set_lvl(logging.DEBUG)
        else:
            set_lvl(logging.ERROR)
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
    # except Exception as e:
    #    log.critical("Unhandled exception caught: " + str(e))
    #    sys.exit(3)

if __name__ == "__main__":
    main()
