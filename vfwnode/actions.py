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

    def configure(self, serviceObj):
        roles = j.application.config.getList('grid.node.roles')
        if 'fw' not in roles:
            roles.append('fw')
            j.application.config.set('grid.node.roles', roles)
            j.atyourservice.get(name='jsagent', instance='main').restart()

        # configure vfwnode
        basepath = '/var/lib/libvirt/images/routeros/'
        if not j.system.fs.exists(basepath):
            j.system.fs.createDir(basepath)
        if not j.system.fs.exists(j.system.fs.joinPaths(basepath, 'template')):
            j.system.btrfs.subvolumeCreate(basepath, 'template')
        j.system.fs.copyFile('/opt/code/git/binary/routeros/root/routeros-small-NETWORK-ID.qcow2',
                             j.system.fs.joinPaths(basepath, 'template', 'routeros.qcow2'))
