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

    def prepare(self, serviceObj):
        """
        this gets executed before the files are downloaded & installed on appropriate spots
        """
        j.system.fs.writeFile(filename="/etc/apt/sources.list.d/openvstorage.list", contents="deb http://apt-ovs.cloudfounders.com unstable/", append=False)
        j.do.execute('apt-get update')
        j.do.execute('apt-get install -y --force-yes openvstorage-hc')

    def configure(self, serviceObj):
        import json
        dictLayout = {
            '/mnt/bfs': {
                'device': 'DIR_ONLY',
                'percentage': 100
            },
            '/mnt/cache1': {
                'device': 'DIR_ONLY',
                'percentage': 100,
                'label': 'cache1',
                'type': 'writecache'
            },
            '/mnt/cache2': {
                'device': 'DIR_ONLY',
                'percentage': 100
            },
            '/var/tmp': {
                'device': 'DIR_ONLY',
                'percentage': 100
            }
        }

        layout = json.dumps(dictLayout)
        serviceObj.hrd.set('instance.disklayout', layout)

        j.system.fs.copyFile("/opt/code/git/binary/openvstorage/openvstorage/openvstorage_preconfig.cfg", "/tmp/openvstorage_preconfig.cfg")
        serviceObj.hrd.applyOnFile("/tmp/openvstorage_preconfig.cfg")
        j.do.execute('ovs setup')
        return True