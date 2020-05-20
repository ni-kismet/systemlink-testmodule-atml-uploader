import xml.etree.ElementTree as et

class AtmlSystemOperator(object):
    def __init__(self, test_run_result_node: et.Element, namespace_dict):
        system_operator_node = test_run_result_node.find("tr:Personnel/tr:SystemOperator", namespace_dict)
        self.id = system_operator_node.attrib["ID"]
        self.name = system_operator_node.attrib["name"]

    def to_json(self):
        return f'{{ "id": "{self.id}", '\
            f'"name": "{self.name}" }}'

    def __repr__(self):
        return self.to_json()