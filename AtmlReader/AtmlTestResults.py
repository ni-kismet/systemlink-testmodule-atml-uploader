import xml.etree.ElementTree as et
import datetime

try:
    from AtmlReader.AtmlSystemOperator import AtmlSystemOperator
    from AtmlReader.AtmlStation import AtmlStation
    from AtmlReader.AtmlUUT import AtmlUUT
    from AtmlReader.AtmlOutcome import AtmlOutcome
    from AtmlReader.AtmlStepProperties import AtmlStepProperties
    from AtmlReader.AtmlResultSet import AtmlResultSet
except:    
    from AtmlSystemOperator import AtmlSystemOperator
    from AtmlStation import AtmlStation
    from AtmlUUT import AtmlUUT
    from AtmlOutcome import AtmlOutcome
    from AtmlStepProperties import AtmlStepProperties
    from AtmlResultSet import AtmlResultSet

class AtmlTestResults(object):
    def __init__(self, root_node: et.Element, namespace_dict):
        test_results_node = root_node.find("trc:TestResults", namespace_dict)
        self.operator = AtmlSystemOperator(test_results_node, namespace_dict)
        self.uut = AtmlUUT(test_results_node, namespace_dict)
        self.station = AtmlStation(test_results_node, namespace_dict)
        # self.outcome = AtmlOutcome(test_results_node, namespace_dict)
        self.result_set = AtmlResultSet(test_results_node, namespace_dict)

        
    def to_json(self):
        return  f'{{ "uut": {self.uut.to_json()}, '\
            f'"station": {self.station.to_json()}, '\
            f'"operator": {self.operator.to_json()}, '\
            f'"resultSet": {self.result_set.to_json()}}}'
            
    def __repr__(self):
        return self.to_json()
    