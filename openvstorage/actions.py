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

    # in next version of the service, we have to sandbox openvstorage and don't rely on apt
    packages = ['kvm', 'libvirt0', 'python-libvirt', 'virtinst', 'openvstorage-hc']

    def installOVSRemote(self, cl):
        cl.file_write(location="/etc/apt/sources.list.d/openvstorage.list", content="deb http://apt-ovs.cloudfounders.com alpha/", sudo=True)
        cl.sudo('apt-get update')
        cl.sudo('apt-get install -y --force-yes %s' % ' '.join(self.packages))

    def installOVSLocal(self):
        j.system.fs.writeFile(filename="/etc/apt/sources.list.d/openvstorage.list", contents="deb http://apt-ovs.cloudfounders.com alpha/", append=False)
        j.system.platform.ubuntu.updatePackageMetadata()
        for package in packages:
            j.system.platform.ubuntu.install(self.package)

    def configure(self, serviceObj):

        # choose if master node or extra node install
        if not serviceObj.hrd.getBool('instance.joincluster', True) or \
           serviceObj.hrd.get('instance.masterip') == '':
            # master install
            serviceObj.hrd.set('instance.joinCluster', False)
            serviceObj.hrd.set('instance.masterip', serviceObj.hrd.getStr('instance.targetip'))
            serviceObj.hrd.set('instance.masterpasswd', serviceObj.hrd.getStr('instance.targetpasswd'))
            self.installOVSLocal()
        else:
            # extra node install
            serviceObj.hrd.set('instance.joinCluster', True)
            cl = j.remote.cuisine.connect(serviceObj.hrd.get('instance.targetip'), 22, serviceObj.hrd.get('instance.targetpasswd'))
            cl.fabric.api.env['user'] = serviceObj.hrd.get('instance.targetuser', 'root')
            self.installOVSRemote(cl)

        serviceObj.hrd.save()

        j.system.fs.copyFile("/opt/code/git/binary/openvstorage/openvstorage/openvstorage_preconfig.cfg", "/tmp/openvstorage_preconfig.cfg")
        serviceObj.hrd.applyOnFile("/tmp/openvstorage_preconfig.cfg")
        j.do.execute('ovs setup')

        return True
