 # A program for parsing NGinx logs.

 The task is to parse NGinx log file with additional 'response time' field at the lines end and compute
 some statistics.

## Directory structure:

```
.
├── data             ::  test data
├── homework.pdf     ::  task description (rus)
├── misc             ::  misc files
├── Optional         ::  optional tasks
├── OUT              ::  Samples of output format
├── README.md        ::  this file
├── src              ::  Source code
│   └── __pycache__  ::  Python cached (compiled) files
├── test             ::  Unit tests
│   └── SConstruct   ::  File for 'scons' build tool to run tests on changed files
└── TODO.md          ::  ToDo list
```

## Program configuration:

Priority, lowest to highest:

- Internal defaults
- Configuration file given with '-F' option
- Configuration string in command line
- Single options like --log-dir and --report-glob
- Some options aren't configurable via CLI options (yet)

Reports are sorted lexicographically and the program uses the last one,
so you have to use date format that places year before month before day.

## Invoking

Adopted from `--help` call, formatted:

```
dgolub[…/src] %» ./log_analyzer.py -h                                                                                                                                                  00:51:08  out_json  6✎
usage: log_analyzer.py [-h] [-F CONFIG_FILE] [-v | --verbose VERBOSE] [-L LOG_DIR] [-R REPORT_DIR] \
                       [-S REPORT_SIZE] [-j JOURNAL] [--report-glob REPORT_GLOB] [--log-glob LOG_GLOB] \
                       [--allow-extension ALLOW_EXTS] [--template TEMPLATE]

Process NGinx log, compute statistics of response time by URL. Internal cautious use only!

options:
  -h, --help            show this help message and exit
  -F CONFIG_FILE, --config-file CONFIG_FILE
                        Configuration file path (optional)
  -v                    Verbosity flag, prints information messages ('-vv' also prints debug)
  --verbose VERBOSE     Verbosity level as a digit (0-2, 0 for ERROR only output, 1 for INFO, 2 for DEBUG)
  -L LOG_DIR, --log-dir LOG_DIR
                        Directory with source log files, optional
  -R REPORT_DIR, --report-dir REPORT_DIR
                        Directory for HTML reports, optional
  -S REPORT_SIZE, --report-size REPORT_SIZE
                        Desired report size in lines, optional
  -j JOURNAL, --journal-to JOURNAL
                        This program's log file, default to STDERR
  --report-glob REPORT_GLOB
                        filename template for report, use strptime metacharacters
  --log-glob LOG_GLOB   filename template for log files, use strptime metacharacters
  --allow-extension ALLOW_EXTS
                        Possible compressed log file extension like gz or bz2
  --template TEMPLATE   HTML template for the report

Built-in config is: " REPORT_SIZE: 100
    REPORT_DIR: /tmp/test/report/
    LOG_DIR: /tmp/test/log/
    VERBOSE: off
    LOG_GLOB: nginx-access-ui.log-%Y%m%d
    REPORT_GLOB: report-%Y.%m.%d.html
    ALLOW_EXTENSIONS: gz
    REPORT_TEMPLATE: report.html
    # Next line is for optional journal file.
    # JOURNAL: "
```

When all your log files are compressed, please don't include compression extension to `log_glob`,
it will cause time/date parsing errors.  Use `allow_extensions` parameter.

## Open questions

Открытые вопросы, на которые я пока не знаю ответа.

1.  Часть URL представляет собой запросы к API, у которых есть параметры.
    Есть ли смысл отбрасывать параметры, учитывая, что они могут меняться?  

    На мой взгляд, да: получим более объективную картину, иначе сто запросов к 
    одному URL с разными параметрами дадут нам сто строк в итоговой таблице.

2.  Есть ли смысл считать медианы, это требует большого расхода памяти и не даёт никакой интересной информации.
    Если хочется всерьёз покопаться в этих данных — Pandas в помощь, он любую статистику посчитает и построит картинки.
