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
        osiscl = j.clients.osis.getByInstance('main')
        osis_size = j.clients.osis.getCategory(osiscl, 'cloudbroker', 'size')

        sizecbs = [(512, 1), (1024, 1), (2048, 2), (4096, 2),
                   (8192, 4), (16384, 8)]
        disksizes = [10, 20, 50, 100, 250, 500, 1000, 2000]
        for memory, cpu in sizecbs:
            sizes = osis_size.search({'memory': memory, 'vcpus': cpu})[1:]
            if sizes:
                size = sizes[0]
                if set(size['disks']) == set(disksizes):
                    continue
                else:
                    size['disks'] = list(set(size['disks'] + disksizes))
                    osis_size.set(size)
                    continue
            size = dict()
            size['disks'] = disksizes
            size['memory'] = memory
            size['vcpus'] = cpu
            size['gids'] = [j.application.whoAmI.gid]
            osis_size.set(size)
