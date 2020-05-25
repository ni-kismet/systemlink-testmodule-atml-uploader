import argparse
import datetime
import glob
import json
import logging
import os
import pprint
import sys
import tempfile
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count
from pathlib import Path
from time import perf_counter

import requests

import constants
from typing import List

pp = pprint.PrettyPrinter(indent=2)

header = { "content-type": 'application/json' }
protocol = 'http'
debug = False

temp_tdms_dir = str(Path(tempfile.gettempdir()).joinpath('ATML_Files'))

# create logger with 'spam_application'
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if debug else logging.WARNING)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')  

session = None

def set_global_session():
    global session
    if not session:
        session = requests.Session()

class DateTimeEncoder(json.JSONEncoder):
    #pylint: disable=method-hidden
    def default(self, o):
        if isinstance(o, datetime):
            try:
                microseconds = int(round(o.microsecond/1000000, 3)*1000000)
                if microseconds == 1000000:
                    o = o + timedelta(seconds=1)
                    return o.replace(tzinfo=None,microsecond=0).isoformat(timespec='microseconds')[:-3] + 'Z'
                else:
                    return o.replace(tzinfo=None,microsecond=microseconds).isoformat(timespec='microseconds')[:-3] + 'Z'
            except Exception as e:
                print(f'us:{microseconds}\nobj: {o}\n{e}')
        return json.JSONEncoder.default(self, o)

class AtmlUploader(object):

    def __init__(self, master_name: str = None, user_name:str=None, password:str=None, protocol:str='http'):
        self.master_name = \
            master_name if master_name is not None \
            else constants.MASTER_NAME
        self.master_auth = \
            (user_name, password) if user_name is not None and password is not None \
            else constants.MASTER_AUTH
        self.protocol = protocol

    def delete_file(self, file_id: str):
        response = None
        try:            
            set_global_session()
            response = session.delete(f'{self.protocol}://{self.master_name}/nifile/v1/service-groups/Default/files/{file_id}',
                verify=False,
                auth=self.master_auth)
        except Exception as e:        
            if response != None:
                logger.error(f'response: {response.text} \n')
            else:
                logger.error("response was None\n")
            logger.error(e)
            raise(e)

    def upload_file(self, file_path: str) -> str:    
        file_name = Path(file_path).name        
        uploaded_file = {'uri':''}
        response = None
        try:               
            set_global_session()
            with open(file_path, 'rb') as f: 
                response = session.post(f'{self.protocol}://{self.master_name}/nifile/v1/service-groups/Default/upload-files',
                    files={file_name: f},
                    verify=False,
                    auth=self.master_auth)
            uploaded_file = json.loads(response.text)
        except Exception as e:        
            if response != None:
                logger.error(f'response: {response.text} \n')
            else:
                logger.error("response was None\n")
            logger.error(e)
            raise(e)
        return Path(uploaded_file["uri"]).stem

    def query_file(self, file_path: str) -> str:
        file_name = Path(file_path).name
        body = { "propertiesQuery": [ { "key": "Name", "operation": "EQUAL", "value": file_name } ] }
        _st= f'{self.protocol}://{self.master_name}/nifile/v1/service-groups/Default/query-files'
        response = None
        try:               
            set_global_session()
            response = session.post(f'{self.protocol}://{self.master_name}/nifile/v1/service-groups/Default/query-files',
                data=json.dumps(body),
                headers=header,
                verify=False,
                auth=self.master_auth)
            
            files = json.loads(response.text)["availableFiles"]
            return files[0]["id"] if len(files) > 0 else ''
        except Exception as e:
            if response != None:
                logger.error(f'Response: {response.text} \n')
            else:
                logger.error("Response was None\n")
            logger.error(e)
            return ''  

    def update_file_metadata(self, file_id: str, properties: dict, replace: bool = True):               
        set_global_session()
        body = {"replaceExisting": replace, "properties":properties}
        session.post(f'{self.protocol}://{self.master_name}/nifile/v1/service-groups/Default/files/{file_id}/update-metadata',
            data=json.dumps(body, cls=DateTimeEncoder),
            headers=header,
            auth=self.master_auth)

def _process_file(file_path:str, server:str, user_name:str, password:str, protocol:str, duplicate_mode:str='skips'):
    uploader = AtmlUploader(server, user_name, password, protocol)
    file_id = ''
    if duplicate_mode != 'new':
        file_id = uploader.query_file(file_path)
        if file_id != '' and duplicate_mode == 'skip':        
            return {"name": Path(file_path).name, "id": file_id}
    else:
        file_id = uploader.upload_file(file_path)

    try:
        atml_file = AtmlFile(file_path)
        root_object = tdms_file.object()
        uploader.update_file_metadata(file_id, root_object.properties)
    except Exception as e:
        logger.error(f'Error processing metadata for "{file_path}"\nException:{e}')
    return {"name": Path(file_path).name, "id": file_id}

class FileProcessFunctor(object):
    """
    `pool.imap` requires a single argument function, and doesn't
    allow lambdas because of a Pickle limitation. Instead, we use a
    functor pattern to work around this limitation.
    """
    def __init__(self, server:str, user_name:str, password:str, protocol:str='http', duplicate_mode:str='skip'):
        self.server = server
        self.user_name = user_name
        self.password = password
        self.protocol = protocol
        self.duplicate_mode = duplicate_mode

    def __call__(self, file_path):
        _process_file(file_path, self.server, self.user_name, self.password, self.protocol, duplicate_mode=self.duplicate_mode)

def upload_tdms_files(file_paths:[str], server: str=None, user_name:str=None, password:str=None, protocol:str='http', num_processes:int=1, log_file='uploadATMLfiles.log', log_level='WARNING', show_console:bool=False, duplicate_mode:str='skip'):
    if log_file != "":
        #  if debug else logging.WARNING)
        # create file handler which logs even debug messages
        fh = logging.FileHandler(log_file, mode='w')
        fh.setLevel(logging.DEBUG if debug else log_level)
        if fh.level < logger.level:
            logger.setLevel(fh.level)
        fh.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(fh)

    t1 = perf_counter()

    files=[]
    if num_processes > 1:
        with Pool(processes=(num_processes), initializer=set_global_session) as pool:
            imap_its = []
            for index, imap_it in enumerate(pool.imap(FileProcessFunctor(server, user_name, password, protocol=protocol, duplicate_mode=duplicate_mode), file_paths)):  
                imap_its.append(imap_it)
                if show_console:
                    percentage = 100 * ((index+1) / len(file_paths))
                    print('{0} Uploaded file ({1}/{2}) {3:.2f}% "{4}"'.format(datetime.now().time().strftime('%H:%M:%S'), (index+1), len(file_paths), percentage, file_paths[index]))
            for return_val in imap_its:
                files.append(return_val) 
    else:
        set_global_session()
        for index, file_path in enumerate(file_paths):
            files.append(_process_file(file_path, server, user_name, password, protocol, duplicate_mode=duplicate_mode))
            if show_console:
                percentage = 100 * ((index+1) / len(file_paths))
                print('{0} Uploaded file ({1}/{2}) {3:.2f}% "{4}"'.format(datetime.now().time().strftime('%H:%M:%S'), (index+1), len(file_paths), percentage, file_paths[index]))
    if show_console:
        print(f"Elapsed Time for File Uploads: {perf_counter() - t1}")
        
    return files

class FileWithinDaysFunctor(object):
    """
    `pool.imap` requires a single argument function, and doesn't
    allow lambdas because of a Pickle limitation. Instead, we use a
    functor pattern to work around this limitation.
    """
    def __init__(self, num_days, compare_time=datetime.now(), presorted_files=False, use_modify_time=True):
        self.num_days = num_days
        self.compare_time = compare_time
        self.presorted_files = presorted_files
        self.use_modify_time = use_modify_time
        self.keep_processing = True

    def __call__(self, file_path)->bool:
        if self.keep_processing:
            file_time = datetime.utcfromtimestamp(os.path.getmtime(file_path) if self.use_modify_time else os.path.getctime(file_path))
            include_file = (self.compare_time - file_time).total_seconds() <= self.num_days*86400
            self.keep_processing = not self.presorted_files or (include_file and self.presorted_files)
            return include_file
        else:
            return False

def filter_folder(folder:str, extensions:List[str], file_filters:List[str]=[''], num_days:int=-1, last_day:str='now', max_files:int=-1, start_at:str=r'', show_console:bool=False)->List[str]:
    file_paths=[]
    if show_console:
        print(f'Processing folder {folder}')
    t1 = perf_counter()
    for extension in extensions:
        for pattern in file_filters:
            file_filter_string = f'*{pattern}*' if pattern != '' in pattern else '*'
            file_paths.extend(glob.glob(f'{folder}/**/{file_filter_string}.{extension}', recursive=True))
    if show_console:
        print(f"Elapsed Time for File Enumeration: {perf_counter() - t1}")

    if num_days >= 0:
        t1 = perf_counter()
        latest_file_time = datetime.utcnow()
        presort = True
        latest_file=None
        if presort:
            file_paths.sort(key=os.path.getmtime, reverse=True)
            latest_file = file_paths[0]
        else:
            latest_file = max(file_paths, key=os.path.getmtime)

        if last_day == 'now':
            pass
        elif last_day == 'last':            
            latest_file_time = datetime.utcfromtimestamp(os.path.getmtime(latest_file))
        else:
            latest_file_time = datetime.fromisoformat(last_day)
        
        file_within_num_days = FileWithinDaysFunctor(num_days=num_days, compare_time=latest_file_time, presorted_files=presort, use_modify_time=True)
        file_paths = list(filter(file_within_num_days, file_paths))
        if show_console:
            print(f"Elapsed Time for File Day Filtering: {perf_counter() - t1}")
    else:
        file_paths.reverse()
    
    # the file to start processing at. 
    # meant for picking up a previous run at a problem file
    if start_at != '':
        start_at_index = file_paths.index(start_at)
        file_paths = file_paths[start_at_index:] if start_at_index >=0 else file_paths

    if max_files >= 0:
        file_paths = file_paths[:max_files]

    return file_paths

def upload_tdms_folder(source_folder:str, server: str=None, user_name:str=None, password:str=None, protocol:str='http', num_days:int=-1, last_day:str='now', max_files:int=-1, num_processes:int=8, log_file:str='uploadATMLfiles.log', log_level:str='WARNING', show_console:bool=False, file_filters:list=[''], duplicate_mode:str='skip'):
    t1 = perf_counter()
    extensions = ['tdms']
    if show_console:
        print(f"Elapsed Time for File Enumeration: {perf_counter() - t1}")
    
    file_paths = filter_folder(source_folder, extensions, file_filters=file_filters, num_days=num_days, last_day=last_day, max_files=max_files, start_at=r'', show_console=show_console)

    return upload_tdms_files(file_paths, server=server, user_name=user_name, password=password, protocol=protocol, show_console=show_console, duplicate_mode=duplicate_mode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="upload a folder of HTAP tdms files to test monitor.")
    parser.add_argument('source', nargs='?', default=temp_tdms_dir, help='source folder path')
    parser.add_argument('-d', '--days', default=-1, type=int, help='number of days to process starting from the most recent file')    
    parser.add_argument('--lastday', default='now', type=str, help='the day to start reverse-processing files. Options are "now", "last", or a day in YYYY-MM-DD format')
    parser.add_argument('--filecount', default=-1, type=int, help='number of files to process')
    parser.add_argument('-l', '--logfile', default=str(Path(tempfile.gettempdir()).joinpath('uploadATMLresults.log')), help='log file to be created or overwritten')
    parser.add_argument('--loglevel', default='WARNING', help='level to log from most verbose to least', choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument('--consolelevel', default='INFO', help='level to output to stdout from most verbose to least', choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument('-q', '--quiet', action="store_true", help="no console output including progress, overrides consolelevel")
    parser.add_argument('--numprocesses', default=cpu_count(), type=int, help='number processes to use. defaults to as many as available.')
    parser.add_argument('-s', '--server', default=None, help='hostname/ip and port for the server connection')
    parser.add_argument('-u', '--username', default=None, help="username for the server connection")
    parser.add_argument('-p', '--password', default=None, help="password for the server connection")
    parser.add_argument('--protocol', default='http', help="protocol for the server connection", choices=['http','https'])
    parser.add_argument('-f', '--filefilters', default='', type=str, help="comma separated filters for file names")
    parser.add_argument('--duplicatemode', default='skip', type=str, help="what to do with duplicated results. Options are 'new', 'replace', or 'skip'")
 
    args = parser.parse_args()

    if debug:
            args.quiet = False
            args.source = r"C:\TEMP\ATML_Files"
            args.server = "localhost:9090"
            args.username = "admin"
            args.password = "password"

    show_console = not args.quiet

    if show_console:
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(args.consolelevel)
        if ch.level < logger.level:
            logger.setLevel(ch.level)
        # create formatter and add it to the handlers
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    upload_tdms_folder(args.source, server=args.server, user_name=args.username, password=args.password, protocol=args.protocol, num_days=args.days, last_day=args.lastday.lower(), max_files=args.filecount, num_processes=args.numprocesses, log_file=args.logfile, log_level=args.loglevel, show_console=show_console, file_filters=args.filefilters.split(','), duplicate_mode=args.duplicatemode.lower())
