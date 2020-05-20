import xml.etree.ElementTree as et
import datetime
import json
try:
    from AtmlReader.AtmlTestStep import AtmlTestStep
except:
    from AtmlTestStep import AtmlTestStep

class AtmlResultSet(AtmlTestStep):
    def __init__(self, test_results_node: et.Element, namespace_dict):
        result_set_node = test_results_node.find("tr:ResultSet", namespace_dict)
        super().__init__(result_set_node, namespace_dict)
        self.result_steps = []
        try:
            steps = []
            for _idx, step_node in enumerate(result_set_node.getchildren()):
                try:
                    if step_node.tag in [f"{{{namespace_dict['tr']}}}SessionAction",f"{{{namespace_dict['tr']}}}Test"]:
                        steps.append(AtmlTestStep(step_node, namespace_dict))
                except Exception as _e:
                    # param_name = param_node.find('Formal_Parameter').attrib["Name"]
                    # print(f'Test: {self.name}\nParam: {param_name}\nException: {e}')
                    pass
            self.result_steps = steps
        except Exception as _e:
            # print(f'Test: {self.name}\nException: {e}')
            pass

        
    def to_json(self):
        parent_json = super().to_json()
        parent_dict = json.loads(parent_json)
        parent_dict["steps"] = [json.loads(step.to_json()) for step in self.result_steps]
        return json.dumps(parent_dict)

    def __repr__(self):
        return self.to_json()