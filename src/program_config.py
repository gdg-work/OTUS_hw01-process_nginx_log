#!/usr/bin/env python3

import config_file_parser as cfp
import pyparsing as pp
import logging
from   typing import Optional, NamedTuple


class ConfigObj(NamedTuple):
        log_dir: str
        report_dir: str
        report_size: int
        verbose: bool = False
        log_glob: str = 'nginx_access.log-%Y%m%d'
        report_glob: str = 'report-%Y.%m.%d.html'
        allow_exts: list[str] = []
        journal: str = ''

def config_from_cli(cli_params, default_cfg) -> Optional[ConfigObj]:
    "Initialize from parsed CLI parameters"
    # first, use config file or a CLI config string
    cfg = {}
    try:
        cfg = cfp.parse_config(cfp.config, default_cfg, logging)
    except pp.ParseException:
        logging.error("Syntax error in default config!")
        return None

    logging.debug("Current config: " + str(cfg))

    if cli_params.config_file is not None:
        cfg_file_name = cli_params.config_file
        try:
            with open(cfg_file_name, 'r') as f_cfgfile:
                updates = cfp.parse_config(cfp.config, f_cfgfile.read(), logging)
                if updates is not None:
                    cfg.update(updates)
                else:
                    logging.debug('Null config, using default configuration')
        except OSError:
            logging.error(f'Configuration file: <{cfg_file_name}> cannot be read')
            return None
        except pp.ParseException:
            logging.error(f'Configuration file <{cfg_file_name}> is not parseable')
            return None

    # removed, too cumbersome to use
    #if cli_params.config is not None:
    #    try:
    #        parsed = cfp.parse_config(cfp.config, cli_params.config, logging)
    #        cfg.update(parsed)
    #    except pp.ParseException:
    #        logging.error('Invalid config in command line, will use default')

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
    if cli_params.journal != '':
        cfg['journal'] = cli_params.journal
    if cli_params.allow_exts is not None:
        cfg['allow_exts'] = list(cfp.ext_list.parse_string(cli_params.allow_exts))

    return ConfigObj(
            log_dir     = cfg['log_dir'],
            report_dir  = cfg['report_dir'],
            report_size = int(cfg['report_size']),
            verbose     = cfg['verbose'], 
            log_glob    = cfg['log_glob'],
            report_glob = cfg['report_glob'],
            allow_exts  = cfg['allow_exts'],
            journal     = cfg['journal'],
        )

if __name__ == "__main__":
    print("This is a library, not a program")
