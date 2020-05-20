import requests
import json
from datetime import datetime

server="manticore:9090"
auth = ("admin","labview===")

result = {
    "serialNumber": "delete",
    "partNumber": "delete",
    "startedAt": datetime.utcnow().isoformat(),
    "programName": "update_test",
    "hostName": "delete",
    "stationId": "delete",
    "operator": "delete",
    "status": {"statusName":"Delete", "statusType": "Failed"},
    "keywords":["delete"]
}
response = requests.post(f"http://{server}/nitestmonitor/v2/results", json={"results":[result]}, auth=auth, verify=False)
response_json = response.json()
result_created = response_json["results"][0]
result_created["properties"]["test"] = "update"
response = requests.post(f"http://{server}/nitestmonitor/v2/update-results", json={"results":[result_created]}, auth=auth, verify=False)
