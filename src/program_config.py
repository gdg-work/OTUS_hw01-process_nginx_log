#!/usr/bin/env python3

import config_file_parser as cfp
import pyparsing as pp
import logging

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

if __name__ == "__main__":
    print("This is a library, not a program")
