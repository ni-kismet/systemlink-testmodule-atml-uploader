import xml.etree.ElementTree as et
import datetime
import json

class AtmlTestStepResult(object):
    def __init__(self, test_result_node: et.Element, namespace_dict):        
        self.name = test_result_node.attrib["name"]
        self.id = test_result_node.attrib["ID"]
        self.values = []
        self.value = None
        self.unit = None
        self.comparator = ""
        self.upper_limit = None
        self.lower_limit = None
        self.outcome = None
        try:
            for _index, datum in enumerate(test_result_node.findall("tr:TestData/c:Datum", namespace_dict)):
                self.values.append(datum.attrib["value"])
                self.flags = datum.attrib["flags"]
                self.type = datum.attrib[f"{{{namespace_dict['xsi']}}}type"]
                self.unit = datum.attrib["nonStandardUnit"]
            if len(self.values) > 0:
                self.value = self.values[0]
        except:
            pass
        try:
            limit_nodes = test_result_node.findall(".//c:Limit", namespace_dict) + test_result_node.findall(".//c:SingleLimit", namespace_dict)
            for _index, limit_node in enumerate(limit_nodes):
                if limit_node:
                    limit_comparator = limit_node.attrib["comparator"]
                    self.comparator = self.comparator + limit_comparator
                    datum = limit_node.find("c:Datum", namespace_dict)
                    if "G" in limit_comparator.upper():
                        self.lower_limit = datum.attrib["value"]
                    elif "L" in limit_comparator.upper():
                        self.upper_limit = datum.attrib["value"]
        except Exception as _e:
            pass
        try:            
            self.outcome = AtmlOutcome(test_result_node, namespace_dict)
        except:
            pass
        
    def to_json(self):
        return f'{{ "name": {json.dumps(self.name)}, '\
            f'"id": {json.dumps(self.id)}, '\
            f'"value": {json.dumps(self.value)}, '\
            f'"upper": {json.dumps(self.upper_limit)}, '\
            f'"lower": {json.dumps(self.lower_limit)}, '\
            f'"comparator": {json.dumps(self.comparator)}, '\
            f'"unit": {json.dumps(self.unit)} }}'

            # ,
            # f'"computerName": "{self.computer_name}" }}'

    def __repr__(self):
        return self.to_json()

