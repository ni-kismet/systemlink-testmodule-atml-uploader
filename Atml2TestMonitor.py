import argparse
import glob
import json
import logging
import math
import os.path
import tempfile
from time import perf_counter
import uuid
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd

import re
from AtmlReader.AtmlFile import AtmlFile
from AtmlReader.AtmlTestStep import AtmlTestStep

import constants
from test_monitor_web_api import TestMonitorWebApi
# from uploadATMLfiles import AtmlUploader
import requests
import copy
import sys
from pympler import asizeof
import os

from typing import List


debug = False
step_request_size_limit = 1000000

# create logger with 'spam_application'
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if debug else logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')  
fh = logging.FileHandler(str(Path(tempfile.gettempdir()).joinpath('uploadATMLresults.log')), mode='w')
fh.setLevel(logging.DEBUG if debug else logging.WARNING)
fh.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)

temp_atml_dir = str(Path(tempfile.gettempdir()).joinpath('ATML_Files'))

session = None

def set_global_session():
    global session
    if not session:
        session = requests.Session()

def convert_status_string(status:str):
    if re.match(r'(running|waiting|looping|custom)', status, re.RegexFlag.I):
        return status.capitalize()
    elif re.match(r'error', status, re.RegexFlag.I):
        return "Errored"
    elif re.match(r'(terminate|abort)', status, re.RegexFlag.I):
        return "Terminated"
    elif re.match(r'pass', status, re.RegexFlag.I):
        return "Passed"
    else:
        return status.capitalize()

class Atml2TestMonitor(object):
    def __init__(self, file_path: str, server: str, user_name:str, password:str, protocol:str='http', session = None):
        self.atml_file = AtmlFile(file_path)
        self.file_path = file_path
        self.server = server
        self.user_name = user_name
        self.password = password
        self.protocol = protocol
        self.test_monitor = TestMonitorWebApi(master_name=self.server, user_name=self.user_name, password=self.password, protocol=self.protocol, session=session)
        # self.file_uploader = AtmlUploader(self.server, self.user_name, self.password, self.protocol)
    
    def get_testmon_result(self, keywords:List[str]=['']):        
        atml_test_results = self.atml_file.test_results
        atml_result_set = atml_test_results.result_set
        started_at = atml_result_set.start_date_time
        stopped_at = atml_result_set.end_date_time
        status = convert_status_string(atml_result_set.outcome.value)

        properties = json.loads(atml_result_set.step_properties.to_json())

        result = {
            "startedAt": started_at.isoformat(),
            "totalTimeInSeconds": (stopped_at - started_at).total_seconds(),
            "programName": "Program Name",
            "operator": atml_test_results.operator.name,
            "systemId": atml_test_results.station.name,
            "hostName": atml_test_results.station.name,
            "status": {"statusType": status, "statusName": status},
            "partNumber": atml_test_results.uut.part_number,
            "serialNumber": atml_test_results.uut.serial_number,
            "keywords": keywords,
            "properties": properties,
            "fileIds": []
        }
        return result

    def get_testmon_step_from_TestStep(self, test_step: AtmlTestStep, result_id: str, parent_step_id: str = "root"):
        started_at = test_step.start_date_time
        stopped_at = test_step.end_date_time
        elapsed_time = (stopped_at - started_at).total_seconds()
        if elapsed_time == 0:
            elapsed_time = 1
        status = convert_status_string(test_step.outcome.value)
       
        # report_text = group_object.properties["HWT_ReportText"] if "HWT_ReportText" in group_object.properties.keys() else ""
        inputs = [{"name":input_param.name, "value":input_param.value} for input_param in test_step.inputs]
        outputs = [{"name":output_result.name, "value":output_result.value} for output_result in test_step.outputs]
        measurements = [{ 
            "comparisonType": meas.comparator,
            "highLimit": float(meas.upper_limit),
            "lowLimit": float(meas.lower_limit),
            "measurement": float(meas.value),
            "nominalValue": "",
            "name": meas.name,
            "status": meas.outcome.value if meas.outcome != None else "",
            "units": meas.unit}
            for meas in test_step.measurements]
        step_id = str(uuid.uuid4())
        step = {
            "stepId": step_id,
            "parentId": parent_step_id,
            "resultId": result_id,
            "data": {
                "text": "", 
                "parameters": measurements
            },
            "dataModel": "TestStand",
            "name": test_step.name,
            "inputs": inputs,
            "outputs": outputs,
            "startedAt" : started_at.isoformat(),
            "totalTimeInSeconds": elapsed_time,
            "status": {"statusType": status, "statusName": status}
        }
        return step

    def get_testmon_steps(self, result_id:str):
        t1 = perf_counter()
        logger.debug(f"Start step calculation for result {result_id}")
        steps = []

        for test_step in self.atml_file.test_results.result_set.result_steps:
            try:                
                step = self.get_testmon_step_from_TestStep(test_step, result_id)   
                steps.append(step)             
            except Exception as e:
                logger.error(step)
                logger.error(e)
        logger.debug(f"End step calculation for result {result_id} elapsed time {perf_counter() - t1}")
        return steps

    def existing_result(self, result)->str:
        result_obj = None
        t2 = perf_counter()
        logger.debug(f"Start querying for result {result['partNumber']} {result['programName']}")  
        response_json = self.test_monitor.query_results_json({
            "programNames": [result["programName"]],
            "products": [result["partNumber"]],
            "serialNumbers": [result["serialNumber"]],
            "hostNames": [result["hostName"]],
            "startedAtQuery": [{
                "operation": "EQUAL",
                "comparisonValue": result["startedAt"]
                }],
            "statuses": [result["status"]],
            "operators": [result["operator"]]
            },
            skip=0,
            take=1).json()
        logger.debug(f"End querying for result {result['partNumber']} {result['programName']} elapsed time {perf_counter() - t2}")
        if len(response_json["results"]) > 0:
            result_obj = response_json["results"][0]
        return result_obj

    def delete_result(self, result, remove_files=False):
        t2 = perf_counter()
        logger.debug(f"Start deleting result {result['partNumber']} {result['programName']}")
        response = self.test_monitor.delete_results([result])
        logger.debug(f"End deleting result {result['partNumber']} {result['programName']} elapsed time {perf_counter() - t2}")
        if response.status_code is not 204 and response.status_code is not 500:
            logger.warning(f'Result Delete Response({response.status_code}): {response.text} \n')
        elif remove_files:                
            for file_id in result['fileIds']:
                try:
                    self.file_uploader.delete_file(file_id)
                except:
                    pass

    def publish_result(self, result, duplicate_mode:str='skip', upload_files:bool=True)->str:
        t1 = perf_counter()
        logger.debug(f"Start publishing result {result['partNumber']} {result['programName']}")
        response = None
        result_id = None
        result_status = "created"

        try:
            if duplicate_mode != 'new':
                # delete existing result record and all steps. This will likely result in a timeout.
                existing_result = self.existing_result(result)
                if existing_result != None:
                    if duplicate_mode == 'replace':
                        result["id"] = existing_result['id']
                        self.delete_result(result, remove_files=True)
                        result.pop('id', None)
                        result_status = "replaced"
                    elif duplicate_mode == 'skip':
                        logger.debug(f"End publishing skipped result {result['partNumber']} {result['programName']} elapsed time {perf_counter() - t1}")
                        return (None, "skipped")
            # create result record
            # if upload_files:
            #     file_id = self.file_uploader.upload_file(self.file_path)
            #     self.file_uploader.update_file_metadata(file_id, self.atml_file.object().properties)        
            #     # file_ids = [file["id"] for file in upload_atml_files([self.file_path], server=self.server, user_name=self.user_name, password=self.password, protocol=self.protocol, num_processes=1, duplicate_mode=duplicate_mode)]
            #     result["fileIds"] = [file_id]

            t2 = perf_counter()
            logger.debug(f"Start creating result {result['partNumber']} {result['programName']}")   
            response = self.test_monitor.create_results([result])
            logger.debug(f"End creating result {result['partNumber']} {result['programName']} elapsed time {perf_counter() - t2}")
            if response.status_code is not 201:
                logger.warning(f'Result Create Response({response.status_code}): {response.text}')
            response_json = response.json()
            result_id = response_json["results"][0]["id"]
        except Exception as e:            
            if response != None:
                logger.error(f'Result Create Response({response.status_code}): {response.text}')
            else:
                logger.error("Result Create Response was None")
            logger.error(e)
            result_status = "tried"
            # raise(e)
        finally:
            logger.debug(f"End publishing result {result['partNumber']} {result['programName']} elapsed time {perf_counter() - t1}")
        return (result_id, result_status)
    

    def publish_single_step_with_children(self, step): 
        t1 = perf_counter()
        logger.debug(f"Start publishing step {step['name']}")      
        # children = step["children"].copy()
        steps = [step]
        total_size = asizeof.asizeof(steps)
        num_batches = (total_size // step_request_size_limit) + 1 if step_request_size_limit > 0 else 1
        flatten_children = num_batches > 1

        if flatten_children and "children" in step and len(step["children"]) > 0:
            steps.extend(step.pop("children"))
            step["children"] = []

        response = None
        try:
            step_batch_size = (len(steps) // num_batches) + 1 if num_batches > 1 else len(steps)
            for batch_idx in range(num_batches):                
                offset = batch_idx*step_batch_size
                if offset < len(steps):    
                    response = None
                    accepted_return = 201
                    batch_steps = steps[offset : offset + step_batch_size]
                    response = self.test_monitor.create_steps(batch_steps)
                    # response = self.test_monitor.create_steps(steps)
                    # else:
                    #     response = self.test_monitor.update_steps(steps[offset : offset + step_batch_size])
                    #     accepted_return = 200

                    if response.status_code is not accepted_return:
                        exception = None 
                        response_text = response.text
                        if len(response_text) > 1000:
                            response_text = f'{response_text[:1000]}...'
                        if response.status_code < accepted_return:
                            exception = Exception(f'Step Create Response({response.status_code}): {response_text}')
                        elif response.status_code == 504:
                            exception = Exception(f'Step Create Response({response.status_code}): Timeout\nSize of steps: {asizeof.asizeof(batch_steps)} bytes')
                        else:
                            # logger.error(f'Step Create Response({response.status_code}): {response.text}\nSize of step: {asizeof.asizeof(step)} bytes\nNumber of children: {len(step["children"])}\nRequest: {steps[offset : offset + step_batch_size]}')
                            steps_string = str(batch_steps)
                            if len(steps_string) > 1000:
                                steps_string = f'{steps_string[:1000]}...'
                            exception = Exception(f'Step Create Response({response.status_code}): {response_text}\nSize of steps: {asizeof.asizeof(batch_steps)} bytes\nRequest: {batch_steps}')
                        raise(exception)
                    _response_json = response.json()
            
        except Exception as e:
            if "Step" not in str(e):   
                if response != None:
                    response_text = response.text
                    if len(response_text) > 1000:
                        response_text = f'{response_text[:1000]}...'
                    logger.error(f'Step Create Response({response.status_code}): {response_text}')
                else:
                    logger.error("Step Create Response was None")
            logger.error(e)
            raise(e)            
        finally:
            logger.debug(f"End publishing step {step['name']} elapsed time {perf_counter() - t1}")

    def publish_steps(self, steps):
        for _index, step in enumerate(steps, 1):
            self.publish_single_step_with_children(step)
            # percentage = 100 * (index / len(steps))
            
        return []

def _process_file(file_path: str, server: str, user_name:str, password:str, protocol:str, logger_ref=None, duplicate_mode:str='skip', upload_files:bool=True, keywords:List[str]=['']):
    try:
        global logger
        if logger_ref and logger_ref != logger:
            logger = logger_ref

        atml_test_mon = Atml2TestMonitor(file_path, server, user_name, password, protocol=protocol)
        #pylint: disable=undefined-variable        
        # file_ids = []
        result = atml_test_mon.get_testmon_result(keywords=keywords)
        # hwt_result = result["properties"]["toolkitVersion"] != ""
        result['id'], status = atml_test_mon.publish_result(result, duplicate_mode=duplicate_mode, upload_files=upload_files)
        if result['id'] != None:
            try:
                steps = atml_test_mon.get_testmon_steps(result['id'])
                _step_ids = atml_test_mon.publish_steps(steps)
            except Exception as e:
                if result['id'] != None:
                    atml_test_mon.delete_result(result)
                logger.error('Result deleted due to Step Creation error.')
                raise(e)    
    except Exception as e:
        logger.error(f'Error processing file {file_path}\n{e}')
        status = "tried"
    return status

class FileProcessFunctor(object):
    """
    `pool.imap` requires a single argument function, and doesn't
    allow lambdas because of a Pickle limitation. Instead, we use a
    functor pattern to work around this limitation.
    """
    def __init__(self, server:str, user_name:str, password:str, protocol:str, logger_ref:object, duplicate_mode:str='skip', upload_files:bool=True, keywords:List[str]=['']):
        self.server = server
        self.user_name = user_name
        self.password = password
        self.protocol = protocol
        self.logger = logger_ref
        self.duplicate_mode = duplicate_mode
        self.upload_files = upload_files
        self.keywords = keywords

    def __call__(self, file_path):
        logger2 = logging.getLogger(__name__+str(os.getpid()))
        if not len(logger2.handlers):
            loglevel = self.logger.level if self.logger != None else logging.WARNING
            logger2.setLevel(logging.DEBUG if debug else loglevel)
            formatter2 = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')  
            fh2 = logging.FileHandler(str(Path(tempfile.gettempdir()).joinpath(f'uploadATMLresults_{str(os.getpid())}.log')))
            fh2.setLevel(logging.DEBUG if debug else loglevel)
            fh2.setFormatter(formatter2)
            # add the handlers to the logger
            logger2.addHandler(fh2)
        return _process_file(file_path, self.server, self.user_name, self.password, self.protocol, logger2, duplicate_mode=self.duplicate_mode, upload_files=self.upload_files, keywords=self.keywords)

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
            time_difference_in_seconds = (self.compare_time - file_time).total_seconds()
            include_file = 0 <= time_difference_in_seconds <= self.num_days*86400
            self.keep_processing = not self.presorted_files or ((include_file or time_difference_in_seconds < 0) and self.presorted_files)
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

def upload_atml_results(source_folder:str, server:str=None, user_name:str=None, password:str=None, protocol:str='http', num_days:int=-1, last_day:str='now', max_files:int=-1, num_processes:int=1, log_file:str='uploadATMLresults.log', log_level:str='WARNING', show_console:bool=False, file_filters:List[str]=[''], duplicate_mode:str='skip', upload_files:bool=True, keywords:List[str]=['']):
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
    
    if source_folder == '':
        source_folder = temp_atml_dir
    if server is None:
        server = constants.MASTER_NAME
    if user_name is None:
        user_name = constants.MASTER_AUTH[0]
    if password is None:
        password = constants.MASTER_AUTH[1]
    extensions = ['xml']
    start_at = r''

    file_paths = filter_folder(source_folder, extensions, file_filters=file_filters, num_days=num_days, last_day=last_day, max_files=max_files, start_at=start_at, show_console=show_console)
    status_counter = Counter()
    t1 = perf_counter()

    if num_processes > 1 and not debug:
        with Pool(processes=(num_processes), initializer=set_global_session) as pool:
            for index, status in enumerate(pool.imap(FileProcessFunctor(server, user_name, password, protocol, logger, duplicate_mode=duplicate_mode, upload_files=upload_files, keywords=keywords), file_paths)):
                status_counter.update({status: 1})
                if show_console:   
                    percentage = 100 * ((index+1) / len(file_paths)) 
                    print('{0} {1} result ({2}/{3}) {4:.2f}% "{5}"'.format(datetime.now().time().strftime('%H:%M:%S'), status.capitalize(), (index+1), len(file_paths), percentage, file_paths[index])) 
    else:
        set_global_session()
        for index, file_path in enumerate(file_paths):
            status = _process_file(file_path, server, user_name, password, protocol, logger_ref=logger, duplicate_mode=duplicate_mode, upload_files=upload_files, keywords=keywords)
            status_counter.update({status: 1})
            if show_console:
                percentage = 100 * ((index+1) / len(file_paths)) 
                print('{0} {1} result ({2}/{3}) {4:.2f}% "{5}"'.format(datetime.now().time().isoformat(), status.capitalize(), (index+1), len(file_paths), percentage, file_paths[index])) 
    if show_console:
        print(f'Upload status summary: {dict(status_counter)}')    
        print(f"Upload elapsed time: {perf_counter() - t1}")

    return status_counter

if __name__ == "__main__":     
    parser = argparse.ArgumentParser(description="upload a folder of atml files to test monitor.")
    parser.add_argument('source', nargs='?', default=temp_atml_dir, help='source folder path')
    parser.add_argument('-d', '--days', default=-1, type=int, help='number of days to process starting from the most recent file. defaults to all days found in the source folder (-1).')
    parser.add_argument('--lastday', default='now', type=str, help='the day to start reverse-processing files. defaults to "now".', choices=["now", "last", 'YYYY-MM-DD'])
    parser.add_argument('--filecount', default=-1, type=int, help='number of files to process. defaults to no limit (-1).')
    parser.add_argument('-l', '--logfile', default=str(Path(tempfile.gettempdir()).joinpath('uploadATMLresults.log')), help='log file to be created or overwritten.')
    parser.add_argument('--loglevel', default='WARNING', help='level to log from most verbose to least.', choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument('--consolelevel', default='INFO', help='level to output to stdout from most verbose to least. defaults to "WARNING".', choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument('-q', '--quiet', action="store_true", help="no console output including progress, overrides consolelevel.")
    parser.add_argument('--numprocesses', default=cpu_count(), type=int, help='number processes to use. defaults to as many as available.')
    parser.add_argument('-s', '--server', default=None, help='hostname/ip and port for the server connection.')
    parser.add_argument('-u', '--username', default=None, help="username for the server connection.")
    parser.add_argument('-p', '--password', default=None, help="password for the server connection.")
    parser.add_argument('--protocol', default='http', help="protocol for the server connection.", choices=['http','https'])
    parser.add_argument('-f', '--filefilters', default='', type=str, help="comma separated filters for file names. wildcard character is '*'.")
    parser.add_argument('--duplicatemode', default='skip', type=str, help='what to do with duplicate files. defaults to "skip". "new" means to create a duplicate record, "replace" means to override existing files, "skip" means to ignore existing files.', choices=["new", "replace", 'skip'])
    parser.add_argument('--nofiles', action="store_true", help="whether up upload and attach the atml file to results.")
    parser.add_argument('-k', '--keywords', default='', type=str, help="comma separated keywords to add to results.")
 
    args = parser.parse_args()

    # if debugging bypass the command line
    if debug:
        args.quiet = False
        args.source = r"C:\repos\battery-tester\Cycle Test"
        args.server = "ni-mfg:9090"
        args.username = "admin"
        args.password = "labview==="
        args.loglevel = "DEBUG"
        args.consolelevel = "WARNING"
        # args.days = 1
        # args.protocol = "https"
        # args.filecount= 1000
        # args.lastday = 'last'
        # args.filefilters = 'TS112'
        args.duplicatemode = 'new'

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

    upload_atml_results(args.source, server=args.server, user_name=args.username, password=args.password, protocol=args.protocol, num_days=args.days, last_day=args.lastday.lower(), max_files=args.filecount, num_processes=args.numprocesses, log_file=args.logfile, log_level=args.loglevel, show_console=show_console, file_filters=args.filefilters.split(','), duplicate_mode=args.duplicatemode.lower(), upload_files=not args.nofiles, keywords=args.keywords.split(','))  
