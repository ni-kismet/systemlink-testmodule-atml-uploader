import xml.etree.ElementTree as et
from datetime import datetime
import json
try:
    from AtmlReader.AtmlOutcome import AtmlOutcome
    from AtmlReader.AtmlStepProperties import AtmlStepProperties
    from AtmlReader.AtmlTestStepParameter import AtmlTestStepParameter
    from AtmlReader.AtmlTestStepResult import AtmlTestStepResult
except:
    from AtmlOutcome import AtmlOutcome
    from AtmlStepProperties import AtmlStepProperties
    from AtmlTestStepParameter import AtmlTestStepParameter
    from AtmlTestStepResult import AtmlTestStepResult

class AtmlTestStep(object):
    def __init__(self, test_step_node: et.Element, namespace_dict):
        self.name = test_step_node.attrib["name"]
        self.id = test_step_node.attrib["ID"]
        self.start_date_time = datetime.fromisoformat(test_step_node.attrib["startDateTime"])
        self.end_date_time = datetime.fromisoformat(test_step_node.attrib["endDateTime"])
        try:
            self.test_reference_id = test_step_node.attrib["testReferenceID"]
        except:
            self.test_reference_id = ""
        self.step_properties = AtmlStepProperties(test_step_node, namespace_dict)
        self.outcome = AtmlOutcome(test_step_node, namespace_dict)
        self.inputs = []
        self.outputs = []
        self.measurements = []
        if test_step_node.find("tr:Parameters", namespace_dict):
            for _index, parameter_node in enumerate(test_step_node.findall("tr:Parameters/tr:Parameter", namespace_dict)):
                self.inputs.append(AtmlTestStepParameter(parameter_node, namespace_dict))
        if test_step_node.find("tr:TestResult", namespace_dict):
            for _index, test_step_result_node in enumerate(test_step_node.findall("tr:TestResult", namespace_dict)):
                step_result = AtmlTestStepResult(test_step_result_node, namespace_dict)
                if step_result.upper_limit != None or step_result.lower_limit != None:
                    self.measurements.append(step_result)
                else:
                    self.outputs.append(step_result)
    def to_json(self):
        name_json = json.dumps(self.name)
        return f'{{ "name": {name_json}, '\
            f'"id": {json.dumps(self.id)}, '\
            f'"startDateTime": {json.dumps(self.start_date_time.isoformat())}, '\
            f'"endDateTime": {json.dumps(self.end_date_time.isoformat())}, '\
            f'"testReferenceID": {json.dumps(self.test_reference_id)}, '\
            f'"properties": {self.step_properties.to_json()}, '\
            f'"outcome": {self.outcome.to_json()}, '\
            f'"inputs": [{",".join([step_input.to_json() for step_input in self.inputs])}], '\
            f'"outputs": [{",".join([step_output.to_json() for step_output in self.outputs])}], '\
            f'"measurements": [{",".join([measurement.to_json() for measurement in self.measurements])}] }}'

    def __repr__(self):
        return self.to_json()
