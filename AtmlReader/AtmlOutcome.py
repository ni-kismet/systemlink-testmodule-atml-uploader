import xml.etree.ElementTree as et

class AtmlOutcome(object):
    def __init__(self, parent_with_outcome: et.Element, namespace_dict):

        outcome_node = parent_with_outcome.find("tr:Outcome", namespace_dict)
        if outcome_node == None:
            outcome_node = parent_with_outcome.find("tr:ActionOutcome", namespace_dict)

        try:
            self.qualifier = outcome_node.attrib["qualifier"]
        except:
            self.qualifier = ""
        self.value = outcome_node.attrib["value"]
        
    def to_json(self):
        return f'{{ "value": "{self.value}", '\
            f'"qualifier": "{self.qualifier}" }}'

    def __repr__(self):
        return self.to_json()
