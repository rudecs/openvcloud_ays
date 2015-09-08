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
        ovcClientHRD = j.atyourservice.get(name='ovc_client', instance='$(instance.ovc_client)').hrd
        self.ovc = j.tools.ms1.get(apiURL=ovcClientHRD.getStr('instance.param.apiurl'))
        self.spacesecret = self.ovc.getCloudspaceSecret(ovcClientHRD.getStr('instance.param.login'),
                                              ovcClientHRD.getStr('instance.param.passwd'),
                                              ovcClientHRD.getStr('instance.param.cloudspace'),
                                              location=ovcClientHRD.getStr('instance.param.location'))
        j.system.platform.ubuntu.generateLocalSSHKeyPair()
        # create service required to connect to ovc reflector with ays
        self.key = j.system.fs.fileGetContents('/root/.ssh/id_rsa')
        data = {'instance.key.priv': self.key}
        keyService = j.atyourservice.new(name='sshkey', instance='vnas', args=data)
        keyService.install()


        j.actions.start(description='create vnas master', action=self.createMaster, category='vnas', name='vnas_master', serviceObj=serviceObj)
        j.actions.start(description='create vnas Active directory', action=self.createAD, category='vnas', name='vnas_ad', serviceObj=serviceObj)
        for i in range(1, 6):
            id = i
            stackID = 2+i
            j.actions.start(description='create vnas stor %s' % i, action=self.createBackend, actionArgs={'id': id, 'stackID': stackID}, category='vnas', name='vnas_stor %s' % i, serviceObj=serviceObj)
        for i in range(1, 6):
            j.actions.start(description='create vnas frontend %s' % i, action=self.createFrontend, actionArgs={'id': id, 'stackID': stackID}, category='vnas', name='vnas_stor %s' % i, serviceObj=serviceObj)
            self.createFrontend(id, stackID=3+i)

    def createMaster(self):
        id, ip, port = self.ovc.createMachine(self.spacesecret, 'vnas_master', memsize=2, ssdsize=10, imagename='Ubuntu 14.04 x64', delete=True, stackId=1,  sshkey=self.key)


        data = {
            'instance.ip': ip,
            'instance.ssh.port': port,
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': 'vnas',
            'instance.jumpscale': True,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        nodeMaster = j.atyourservice.new(name='node.ssh', instance='vnas_master', args=data)
        nodeMaster.install(reinstall=True)

        data = {'instance.param.rootpasswd': 'rooter'}
        vnasMaster = j.atyourservice.new(name='vnas_master', instance='main', args=data, parent=vnasMaster)
        vnasMaster.consume('node', nodeMaster.instance)
        vnasMaster.install(reinstall=True)

    def createAD(self):
        id, ip, port = self.ovc.createMachine(self.spacesecret, 'vnas_ad', memsize=2, ssdsize=10, imagename='Ubuntu 14.04 x64', stackId=1, delete=True, sshkey=self.key)
        self.ADIP = ip

        data = {
            'instance.ip': ip,
            'instance.ssh.port': port,
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': 'vnas',
            'instance.jumpscale': True,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        nodeAD = j.atyourservice.new(name='node.ssh', instance='vnas_ad', args=data)
        nodeAD.install(reinstall=True)

        vnasAD = j.atyourservice.new(name='vnas_ad', instance='main', args=data, parent=nodeAD)
        vnasAD.consume('node', nodeAD)
        vnasAD.install(reinstall=True)

    def createBackend(self, id, stackID):
        vmName = 'vnas_backend%s' % id
        id, ip, port = self.ovc.createMachine(self.spacesecret, vmName, memsize=4, ssdsize=10, imagename='Ubuntu 14.04 x64', delete=True, stackId=stackID, sshkey=self.key)
        self.ovc.stopMachine(self.spacesecret, vmName)
        for x in xrange(1, 11):
            diskName = 'data%s' % x
            ovc.addDisk(self.spaceSecret, vmName, diskName, size=2000, description=None, type='D')
        self.ovc.startMachine(self.spacesecret, vmName)

        data = {
            'instance.ip': ip,
            'instance.ssh.port': port,
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': 'vnas',
            'instance.jumpscale': True,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        node = j.atyourservice.new(name='node.ssh', instance=vmName, args=data)
        node.install(reinstall=True)

        data = {
            'instance.stor.id': id,
            'instance.stor.export.dir': '/mnt/disks',
            'instance.disk.number': 10,
            'instance.disk.size': 2000,
        }
        vnasStor = j.atyourservice.new(name='vnas_stor', instance='main', args=data, parent=node)
        vnasStor.consume('node', node)
        vnasStor.install(reinstall=True)

    def createFrontend(self, id, stackID):
        vmName = 'vnas%s' % id
        id, ip, port = self.ovc.createMachine(self.spacesecret, vmName, memsize=2, ssdsize=10, imagename='Ubuntu 14.04 x64', delete=True, stackId=stackID, sshkey=self.key)

        data = {
            'instance.ip': ip,
            'instance.ssh.port': port,
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': 'vnas',
            'instance.jumpscale': True,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        node = j.atyourservice.new(name='node.ssh', instance=vmName, args=data)
        node.install(reinstall=True)

        data = {
            'instance.member.ad.address': self.ADIP,
            'instance.member.address': ip,
        }
        vnasStor = j.atyourservice.new(name='vnas_node', instance='main', args=data, parent=node)
        vnasStor.consume('node', node)
        vnasStor.install(reinstall=True)

