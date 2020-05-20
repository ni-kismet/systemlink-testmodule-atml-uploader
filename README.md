# ATML Uploader <!-- omit in toc -->
This is home to scripts for uploading TestStand ATML report files into SystemLink Test Module.

- [Getting Started](#getting-started)
- [Overview](#overview)
- [Intended workflow:](#intended-workflow)
  - [Upload](#upload)
    - [Usage](#usage)
    - [Important script variables](#important-script-variables)
- [Debug workflow](#debug-workflow)

## Getting Started
2. Install [Python 3.x](https://www.python.org/ftp/python/3.7.1/python-3.7.1-amd64.exe)
3. Open a command prompt at the root repo directory
4. Run "python -m pip install -r [requirements.txt](requirements.txt)"
5. Use the [intended workflow](#intended-workflow) to work with ATML files

## Overview
Uploads TestStand ATML report files into SystemLink Test Module

## Intended workflow:
1. **Upload** ATML to Test Monitor

### Upload
[Atml2TestMonitor.py](Atml2TestMonitor.py) - upload TestStand ATML files to Test Monitor

#### Usage
Two options:
1. Run "python [Atml2TestMonitor.py](Atml2TestMonitor.py) -s [servername] -u [user] -p [password]" with other command line arguments as needed
2. Import [Atml2TestMonitor.py](Atml2TestMonitor.py) and call upload_atml_results with arguments as needed

#### Important script variables
| argument | use | default |
| - | - | - |
| source | positional argument to define the source folder for atml files to process. | %TEMP%\ATML_Files |
| -d --days | number of days to process starting from the lastday argument. | -1 |
| --lastday | the day to start reverse-processing files. "now" means use now as the timestamp, "last" means use the most recent file as the timestamp, "YYYY-MM-DD" means to use the supplied day as the timestamp. | now |
| --filecount | number of files to process. | -1 |
| -l --logfile | the log file to be created or overwritten. | %TEMP%\uploadTDMSresults.log |
| --loglevel | level to log from most verbose to least. choices are "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" | WARNING |
| --consolelevel | level to log to stdout from most verbose to least. choices are "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" | WARNING |
| -q --quiet | no console output including progress. | _not set_ |
| --numprocesses | number processes to use. | _all cpus_ |
| -s | hostname/ip and port for the server connection. | |
| -u | username for the server connection. | |
| -p | password for the server connection. | |
| --protocol | protocol for the server connection. choices are "http" and "https". | http |
| -f --filefilters | comma separated filters for file names. wildcard character is "*". | |
| --duplicatemode | what to do with duplicate files. "new" means to create a duplicate record, "replace" means to override existing files, "skip" means to ignore existing files. | skip |
| --nofiles | whether up upload and attach the atml file to results. | _not set_|
| -k --keywords | comma separated keywords to add to results. | |

## Debug workflow
This script runs with multiprocessing by default which can make it hard to debug with an IDE. Also depending on IDE it can get annoying to track command line arguments in a process/debug launching configuration. 

To this end the script has a special debug mode enabled by using the "debug" variable

