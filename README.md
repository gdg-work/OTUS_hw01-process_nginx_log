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
usage: log_analyzer.py [-h] [-F CONFIG_FILE | -c CONFIG] [-v] [-L LOG_DIR] \
		       [-R REPORT_DIR] [-S REPORT_SIZE] \
                       [--report-glob REPORT_GLOB] [--log-glob LOG_GLOB] \
		       [--allow-extension ALLOW_EXTS]

Process NGinx log, compute statistics of response time by URL.
Internal cautious use only!

options:
  -h, --help            show this help message and exit
  -F CONFIG_FILE, --config-file CONFIG_FILE
                        Configuration file path (optional)
  -c CONFIG, --config CONFIG
                        Optional configuration data as a string:
			(LOG_DIR:... REPORT_DIR:... VERBOSE:... REPORT_SIZE:...)
			You can use ':' or '=', all fields are optional,
			fields separator is whitespace
  -v, --verbose         Verbosity flag, prints debug messages
  -L LOG_DIR, --log-dir LOG_DIR
                        Directory with log files, optional
  -R REPORT_DIR, --report-dir REPORT_DIR
                        Directory for HTML reports, optional
  -S REPORT_SIZE, --report-size REPORT_SIZE
                        Desired report size in lines, optional
  --report-glob REPORT_GLOB
                        filename template for report, use strftime metacharacters
  --log-glob LOG_GLOB   filename template for log files, use strptime metacharacters
  --allow-extension ALLOW_EXTS
                        Possible compressed log file extension like gz or bz2

Built-in config is:
	REPORT_SIZE: 1000
	REPORT_DIR: ./reports
	LOG_DIR: ./log
	VERBOSE: off
	LOG_GLOB = nginx-access-ui.log-*.gz
	REPORT_GLOB = report-*.html
	ALLOW_EXTENSIONS = gz
```

When all your log files are compressed, please don't include compression extension to `log_glob`,
it will cause time/date parsing errors.  Use `allow_extensions` parameter.

## Open questions

Открытые вопросы, на которые я пока не знаю ответа.

1.  Часть URL представляет собой запросы к API, у которых есть параметры.
    Есть ли смысл отбрасывать параметры, учитывая, что они могут меняться?  

    На мой взгляд, да: получим более объективную картину, иначе сто запросов к 
    одному URL с разными параметрами дадут нам сто строк в итоговой таблице.
