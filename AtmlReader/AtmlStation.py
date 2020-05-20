import xml.etree.ElementTree as et
import datetime

class AtmlStation(object):
    def __init__(self, test_run_result_node: et.Element, namespace_dict):        
        test_station_node = test_run_result_node.find("tr:TestStation", namespace_dict)
        self.name = test_station_node.find("c:SerialNumber", namespace_dict).text
        # self.computer_name = test_station_node.find("Item[@Name='Computer_Name']").attrib["Value"]

    def to_json(self):
        return f'{{ "name": "{self.name}" }}'
            # ,
            # f'"computerName": "{self.computer_name}" }}'

    def __repr__(self):
        return self.to_json()
