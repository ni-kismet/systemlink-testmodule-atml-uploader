import requests
import constants
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TestMonitorWebApi(object):

    def __init__(self, master_name: str = None, user_name:str=None, password:str=None, protocol:str='http', session=None):
        self.master_name = \
            master_name if master_name is not None \
            else constants.MASTER_NAME
        self.master_auth = \
            (user_name, password) if user_name is not None and password is not None \
            else constants.MASTER_AUTH
        self.protocol = protocol
        self.session = session if session != None else requests.Session()

    def get_all_results(self) -> requests.Response:
        url = constants.TEST_MONITOR_SVC_URLS['base_sans_protocol'].format(self.protocol, self.master_name) + \
              constants.TEST_MONITOR_SVC_URLS['query_results']
        query_json = {}
        return self.session.post(url,
                             json=query_json,
                             verify=False,
                             auth=self.master_auth)

    def create_results(self, results) -> requests.Response:
        url = constants.TEST_MONITOR_SVC_URLS['base_sans_protocol'].format(self.protocol, self.master_name) + \
              constants.TEST_MONITOR_SVC_URLS['create_results']
        results_json = {
            'results': results
        }
        return self.session.post(url,
                             json=results_json,
                             verify=False,
                             auth=self.master_auth)

    def update_results(self, results) -> requests.Response:
        url = constants.TEST_MONITOR_SVC_URLS['base_sans_protocol'].format(self.protocol, self.master_name) + \
              constants.TEST_MONITOR_SVC_URLS['update_results']
        updates_json = {
            'results': results,
            'replace': False#,
            #'determineStatusFromSteps': True
        }
        return self.session.put(url,
                            json=updates_json,
                            verify=False,
                            auth=self.master_auth)

    def delete_results(self, results, delete_steps:bool = True) -> requests.Response:
        url = constants.TEST_MONITOR_SVC_URLS['base_sans_protocol'].format(self.protocol, self.master_name) + \
              constants.TEST_MONITOR_SVC_URLS['delete_results']
        delete_json = {
            'ids': [result["id"] for result in results],
            'deleteSteps': delete_steps
        }
        return self.session.post(url,
                            json=delete_json,
                            verify=False,
                            auth=self.master_auth)

    def query_results(self,
                      id=None,
                      system_id=None) -> requests.Response:
        url = constants.TEST_MONITOR_SVC_URLS['base_sans_protocol'].format(self.protocol, self.master_name) + \
              constants.TEST_MONITOR_SVC_URLS['query_results']
        query_json = {
            'id': id,
            'systemId': system_id
        }
        return self.session.post(url,
                             json=query_json,
                             verify=False,
                             auth=self.master_auth)

    def query_results_json(self, query_json, skip=0, take=1000) -> requests.Response:
        url = constants.TEST_MONITOR_SVC_URLS['base_sans_protocol'].format(self.protocol, self.master_name) + \
              constants.TEST_MONITOR_SVC_URLS['query_results_skip_take'].format(skip, take)
        return self.session.post(url,
                             json=query_json,
                             verify=False,
                             auth=self.master_auth)

    def create_steps(self, steps) -> requests.Response:
        url = constants.TEST_MONITOR_SVC_URLS['base_sans_protocol'].format(self.protocol, self.master_name) + \
              constants.TEST_MONITOR_SVC_URLS['create_steps']
        steps_json = {
            'steps': steps
        }
        return self.session.post(url,
                             json=steps_json,
                             verify=False,
                             auth=self.master_auth)

    def update_steps(self, steps) -> requests.Response:
        url = constants.TEST_MONITOR_SVC_URLS['base_sans_protocol'].format(self.protocol, self.master_name) + \
              constants.TEST_MONITOR_SVC_URLS['create_steps']
        updates_json = {
            'steps': steps
            #'determineStatusFromSteps': True
        }
        return self.session.put(url,
                            json=updates_json,
                            verify=False,
                            auth=self.master_auth)

    def query_steps_json(self, query_json, skip=0, take=50000) -> requests.Response:
        url = constants.TEST_MONITOR_SVC_URLS['base_sans_protocol'].format(self.protocol, self.master_name) + \
              constants.TEST_MONITOR_SVC_URLS['query_steps_skip_take'].format(skip, take)
        return self.session.post(url,
                             json=query_json,
                             verify=False,
                             auth=self.master_auth)
