from JumpScale import j
import time

ActionsBase=j.atyourservice.getActionsBaseClass()

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
        contents = "\n  /mnt/vmstor/** rw,\n  /mnt/vmstor/**/** rw,"
        j.system.fs.writeFile('/etc/apparmor.d/abstractions/libvirt-qemu', contents, True)
        txt = j.codetools.getTextFileEditor('/etc/apparmor.d/abstractions/libvirt-qemu')
        txt.appendReplaceLine('/sys/devices/system/cpu', '  /sys/devices/system/cpu/** r,')
        txt.save()
        if j.system.platform.ubuntu.serviceExists('apparmor'):
            j.system.platfor.ubuntu.reloadService('apparmor')

        ccl = j.clients.osis.getNamespace('cloudbroker')

        oob_interface = 'backplane1'
        ipaddress = j.system.net.getIpAddress(oob_interface)[0][0]

        # create a new stack:
        # reload whoAmI and wait till nid is set agent might stil lbe starting itself
        start = time.time()
        timeout = 60
        while j.application.whoAmI.nid == 0 or time.time() < start + timeout:
            time.sleep(3)
            j.application.loadConfig()
            j.application.initWhoAmI(True) 
        if not ccl.stack.search({'referenceId': str(j.application.whoAmI.nid), 'gid': j.application.whoAmI.gid})[0]:
            stack = dict()
            stack['id'] = None
            stack['apiUrl'] = 'qemu+ssh://%s/system' % ipaddress
            stack['descr'] = 'libvirt node'
            stack['type'] = 'LIBVIRT'
            stack['status'] = 'ENABLED'
            stack['name'] = j.system.net.getHostname()
            stack['gid'] = j.application.whoAmI.gid
            stack['referenceId'] = str(j.application.whoAmI.nid)
            ccl.stack.set(stack)

        return True
