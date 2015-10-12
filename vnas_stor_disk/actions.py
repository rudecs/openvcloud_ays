from JumpScale import j
import contoml

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
        services = j.atyourservice.findServices(name='vnas_stor')
        if len(services) < 1:
            j.events.opserror_critical(msg="can't find vnas_stor. install vnas_stor first", category="vnas_stor_disk")

        storHRD = services[0].hrd
        disksDir = storHRD.get('instance.stor.export.dir')
        diskID = serviceObj.hrd.getInt('instance.disk.id')
        path = j.system.fs.joinPaths(disksDir, str(diskID))
        nfsHost = serviceObj.hrd.getStr('instance.nfs.host')
        nfsOptions = serviceObj.hrd.getStr('instance.nfs.options')

        # format disks
        alpha = 'bcdefghijklmnopqrstuvwxyz'
        devName = '/dev/vd%s' % alpha[diskID]
        cmd = 'mkfs.%s %s' % ("btrfs", devName)
        j.system.process.execute(cmd, dieOnNonZeroExitCode=False, outputToStdout=True)

        if not j.system.fs.exists(path=path):
            j.system.fs.createDir(path)

        cmd = 'mount %s %s' %(devName, path)
        j.system.process.execute(cmd, dieOnNonZeroExitCode=True, outputToStdout=True)

        if not j.system.fs.exists(path="/etc/exports"):
            j.system.fs.createEmptyFile('/etc/exports')
        exports = '%s %s(%s)' % (path, nfsHost, nfsOptions)
        j.system.fs.writeFile(filename="/etc/exports", contents=exports, append=True)
        # nfs = j.ssh.nfs.get(j.ssh.connect())
        # share = nfs.add(path)
        # share.addClient(nfsHost, nfsOptions)
        # nfs.commit()

        output = j.system.fs.joinPaths(path, '.vnasdisk.toml')
        j.system.fs.createEmptyFile(output)

        disk = {'id': diskID, 'pool': ''}
        contoml.dump(disk, output, prettify=True)