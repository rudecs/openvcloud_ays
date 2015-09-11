from JumpScale import j
import time

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
        diskNbr = serviceObj.hrd.getInt('instance.disk.number')
        exportDir = serviceObj.hrd.getStr('instance.stor.export.dir')
        ovcClientHRD = j.atyourservice.get(name='ovc_client', instance='$(instance.ovc_client)').hrd
        ovc = j.tools.ms1.get(apiURL=ovcClientHRD.getStr('instance.param.apiurl'))

        ovc.stopMachine(self.spacesecret, vmName)
        time.sleep(2)
        for x in xrange(1, diskNbr+1):
            diskName = 'data%s' % x
            ovc.addDisk(self.spacesecret, vmName, diskName, size=2000, description=None, type='D')
            time.sleep(0.5)
        self.ovc.startMachine(self.spacesecret, vmName)
        time.sleep(2)

        for i in range(diskNbr):
            data = {
                'instance.disk.id': i,
                'instance.nfs.host': '192.168.0.103.0/24',
                'instance.nfs.options': 'no_root_squash, no_subtree_check',
            }
            stor_disk = j.atyourservice.new(name='vnas_stor_disk', instance="disk%s" % i, args=data, parent=serviceObj)
            stor_disk.install()
