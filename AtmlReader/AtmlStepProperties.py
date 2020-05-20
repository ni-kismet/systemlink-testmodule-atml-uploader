import xml.etree.ElementTree as et
import json

class AtmlStepProperties(object):
    def __init__(self, parent_with_properties: et.Element, namespace_dict):
        step_properties_node = parent_with_properties.find("tr:Extension/ts:TSStepProperties", namespace_dict)
        self.step_type = step_properties_node.find("ts:StepType", namespace_dict).text
        self.step_group = step_properties_node.find("ts:StepGroup", namespace_dict).text
        self.block_level = step_properties_node.find("ts:BlockLevel", namespace_dict).attrib["value"]
        self.index = step_properties_node.find("ts:Index", namespace_dict).attrib["value"]
        self.total_time = step_properties_node.find("ts:TotalTime", namespace_dict).attrib["value"]
        self.module_time = step_properties_node.find("ts:ModuleTime", namespace_dict).attrib["value"]

    def to_json(self):
        return f'{{ "stepType": {json.dumps(self.step_type)}, '\
            f'"stepGroup": {json.dumps(self.step_group)}, '\
            f'"blockLevel": {json.dumps(self.block_level)}, '\
            f'"index": {json.dumps(self.index)}, '\
            f'"totalTime": {json.dumps(self.total_time)}, '\
            f'"moduleTime": {json.dumps(self.module_time)} }}'

    def __repr__(self):
        return self.to_json()		
