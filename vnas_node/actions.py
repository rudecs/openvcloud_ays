from JumpScale import j

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
    def configure(self, service_obj):

        def showmount(addr):
            cmd = 'showmount -e --no-headers %s' % addr
            _, output = j.system.process.execute(cmd)
            lines = output.splitlines()
            return [l.split(' ')[0] for l in lines]

        def mount(remoteHost, remoteDir, localDir):
            cmd = 'mount %s:%s %s' % (remoteHost, remoteDir, localDir)
            j.system.process.execute(cmd)

        stores = service_obj.hrd.getDictFromPrefix('instance.stores')
        for id, addr in stores.iteritems():
            availableDisks = showmount(addr)

            for disk in availableDisks:
                diskID = disk.split('/')[-1]
                mountID = int(id) * 100 + int(diskID)
                localDir = '/mnt/vdisks/%s' % mountID

                if not j.system.fs.exists(path=localDir):
                    j.system.fs.createDir(localDir)

                mount(addr, disk, localDir)

        vnaslb = j.atyourservice.get(name='vnaslb')
        vnaslb.restart()