from JumpScale import j
from ConfigParser import SafeConfigParser
import cStringIO as StringIO
from urlparse import urlparse
import json

ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):
    """
    process for install
    -------------------
    step1: prepare actions
    step2: check_requirements action
    step3: download files & copy on right location (hrd info is used)
    step4: configure action
    step5: check_uptime_local to see if process stops  (uses timeout $process.stop.timeout)
    step5b: if check uptime was true will do stop action and retry the check_uptime_local check
    step5c: if check uptime was true even after stop will do halt action and retry the check_uptime_local check
    step6: use the info in the hrd to start the application
    step7: do check_uptime_local to see if process starts
    step7b: do monitor_local to see if package healthy installed & running
    step7c: do monitor_remote to see if package healthy installed & running, but this time test is done from central location
    """

    def configure(self, serviceObj):
        # import OVS graphs
        datasourceip = serviceObj.hrd.get('instance.datasource.ip')
        datasourceport = serviceObj.hrd.get('instance.datasource.port')
        datasourcename = serviceObj.hrd.get('instance.datasource.name')
        gcl = j.clients.grafana.getByInstance('main')
        dashboards_dir = '/opt/grafana/dashboards'
        for path in j.system.fs.listFilesInDir(path=dashboards_dir, filter='*.json'):
            print("add %s dashboard to grafana" % j.system.fs.getBaseName(path))
            dashboard = j.system.fs.fileGetContents(path)
            db = json.loads(dashboard)
            db['id'] = None
            print(gcl.updateDashboard(db))
