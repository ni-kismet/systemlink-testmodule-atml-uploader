import xml.etree.ElementTree as et

class AtmlUUT(object):
    def __init__(self, test_run_result_node: et.Element, namespace_dict):
        uut_node = test_run_result_node.find("tr:UUT", namespace_dict)
        self.serial_number = uut_node.find("c:SerialNumber", namespace_dict).text
        try:
            part_number_node = uut_node.find("c:Definition/c:Identification/c:IdentificationNumbers/c:IdentificationNumber[@type='Part']", namespace_dict)
            self.part_number = part_number_node.attrib["number"]
        except:
            self.part_number = ""

    def to_json(self):
        return f'{{ "serialNumber": "{self.serial_number}", '\
            f'"partNumber": "{self.part_number}" }}'

    def __repr__(self):
        return self.to_json()
