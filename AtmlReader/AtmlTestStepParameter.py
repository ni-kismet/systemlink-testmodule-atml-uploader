import xml.etree.ElementTree as et
import datetime
import json

class AtmlTestStepParameter(object):
    def __init__(self, parameter_node: et.Element, namespace_dict):        
        self.name = parameter_node.attrib["name"]
        self.id = parameter_node.attrib["ID"]
        self.values = []
        self.value = None
        try:
            for _index, datum in enumerate(parameter_node.findall("tr:Data/c:Datum", namespace_dict)):
                self.values.append(datum.attrib["value"])
                self.flags = datum.attrib["flags"]
                self.type = datum.attrib[f"{{{namespace_dict['xsi']}}}type"]
            if len(self.values) > 0:
                self.value = self.values[0]
        except:
            pass
        
    def to_json(self):
        return f'{{ "name": {json.dumps(self.name)},'\
            f'"id": {json.dumps(self.id)}, '\
            f'"value": {json.dumps(self.value)} }}'
            # ,
            # f'"computerName": "{self.computer_name}" }}'

    def __repr__(self):
        return self.to_json()