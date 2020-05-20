import xml.etree.ElementTree as et
import json
import subprocess
import pathlib
import os

try:
    from AtmlReader.AtmlTestResults import AtmlTestResults
except:
    from AtmlTestResults import AtmlTestResults

           
class AtmlFile(object):
    def __init__(self, file_path):
        file_handle = None
        root = None
        namespace_dict = {"trc":"urn:IEEE-1636.1:2011:01:TestResultsCollection",
                "tr":"urn:IEEE-1636.1:2011:01:TestResults",
                "c":"urn:IEEE-1671:2010:Common",
                "xsi":"http://www.w3.org/2001/XMLSchema-instance",
                "ts":"www.ni.com/TestStand/ATMLTestResults/2.0"}
        file_handle = open(file_path, encoding="utf8")
        root = et.fromstring(file_handle.read())        
        self.test_results = AtmlTestResults(root, namespace_dict)
        if file_handle != None:
            file_handle.close()
    
    def to_json(self):
        return f'{{ "testResults": {self.test_results.to_json()} }}'

    def __repr__(self):
        return self.to_json()
    
if __name__ == "__main__":
    atml_file_path = r'C:\repos\battery-tester\Cycle Test\Battery Cycle Test_Report[3 22 37 PM][2 5 2020].xml'

    atml_file = AtmlFile(atml_file_path)
    atml_file_string = atml_file.to_json()
    with open(r'C:\Users\rfriedma\AppData\Local\Temp\atml_file.json', 'w') as f:
        f.write(atml_file_string)
    atml_json = json.loads(atml_file_string)
