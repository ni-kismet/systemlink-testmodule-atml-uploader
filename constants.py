# MASTER_NAME = 'alex-w-2018'
# MASTER_NAME = 'wadshtapvm'
# MASTER_NAME = '10.192.40.6'
MASTER_NAME = 'localhost:9090'
# MASTER_NAME = 'jprewitt5:9090'
# MASTER_NAME = '10.2.35.13:9090'
# ip-10-192-40-46.aws.natinst.com'
MASTER_AUTH = ('admin', 'admin')
# MASTER_AUTH = ('admin', 'labview===')

TEST_MONITOR_SVC_URLS = dict(
    base='http://{0}/nitestmonitor',
    base_sans_protocol='{0}://{1}/nitestmonitor',
    can_write='/v2/can-write',
    query_results='/v1/query-results',
    query_results_skip_take='/v1/query-results?skip={0}&take={1}',
    create_results='/v2/results',
    update_results='/v2/results',
    delete_result='/v2/results/{0}',
    query_steps='/v1/query-steps',
    query_steps_skip_take='/v1/query-steps?skip={0}&take={1}',
    create_steps='/v2/steps',
    delete_step='/v2/steps/{0}',
    delete_steps='/v2/delete-steps',
    delete_results='/v2/delete-results',
    list_report_files='/v2/reports',
    upload_report_for_result='/v2/results/{0}/upload',
    attach_report_to_result='/v2/results/{0}/attach',
    download_report='/v2/reports/{0}',
    delete_report='/v2/reports/{0}'
)
