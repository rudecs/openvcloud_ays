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
        ovcClientHRD = j.atyourservice.get(name='ovc_client', instance='$(instance.ovc_client)').hrd
        self.ovc = j.tools.ms1.get(apiURL=ovcClientHRD.getStr('instance.param.apiurl'))
        self.spacesecret = self.ovc.getCloudspaceSecret(ovcClientHRD.getStr('instance.param.login'),
                                              ovcClientHRD.getStr('instance.param.passwd'),
                                              ovcClientHRD.getStr('instance.param.cloudspace'),
                                              location=ovcClientHRD.getStr('instance.param.location'))

        if not j.system.fs.exists(path='/root/.ssh/id_rsa'):
            j.system.platform.ubuntu.generateLocalSSHKeyPair()
        self.key = j.system.fs.fileGetContents('/root/.ssh/id_rsa')
        self.keypub = j.system.fs.fileGetContents('/root/.ssh/id_rsa.pub')
        data = {'instance.key.priv': self.key}
        keyService = j.atyourservice.new(name='sshkey', instance='vnas', args=data)
        keyService.install()

        j.actions.start(description='create vnas master', action=self.createMaster, actionArgs={'serviceObj': serviceObj}, category='vnas', name='vnas_master', serviceObj=serviceObj)

        j.actions.start(description='create vnas Active directory', action=self.createAD, actionArgs={'serviceObj': serviceObj}, category='vnas', name='vnas_ad', serviceObj=serviceObj)

        nbrBackend = serviceObj.hrd.getInt('instance.nbr.stor')
        nbrDisk = serviceObj.hrd.getInt('instance.nbr.disk')
        for i in range(1, nbrBackend+1):
            id = i
            stackID = 2+i
            j.actions.start(description='create vnas stor %s' % i, action=self.createBackend, actionArgs={'id': id, 'stackID': stackID, 'nbrDisk': nbrDisk}, category='vnas', name='vnas_stor %s' % i, serviceObj=serviceObj)

        nbrFrontend = serviceObj.hrd.getInt('instance.nbr.front')
        for i in range(1, nbrFrontend+1):
            j.actions.start(description='create vnas frontend %s' % i, action=self.createFrontend, actionArgs={'id': id, 'stackID': stackID, 'serviceObj': serviceObj}, category='vnas', name='vnas_node %s' % i, serviceObj=serviceObj)

    def createMaster(self , serviceObj):
        _, ip = j.system.net.getDefaultIPConfig()
        serviceObj.hrd.set('instance.master.ip', ip)
        data = {'instance.param.rootpasswd': 'rooter'}
        vnasMaster = j.atyourservice.new(name='vnas_master', instance='main', args=data)
        vnasMaster.install(reinstall=True, deps=True)

    def createAD(self, serviceObj):
        id, _, _ = self.ovc.createMachine(self.spacesecret, 'vnas_ad', memsize=2, ssdsize=10, imagename='Ubuntu 14.04 x64', delete=True, sshkey=self.keypub)
        obj = self.ovc.getMachineObject(self.spacesecret, 'vnas_ad')
        ip = obj['interfaces'][0]['ipAddress']
        serviceObj.hrd.set('instance.ad.ip', ip)

        data = {
            'instance.ip': ip,
            'instance.ssh.port': 22,
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': 'vnas',
            'instance.jumpscale': True,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        j.atyourservice.remove(name='node.ssh', instance='vnas_ad')
        nodeAD = j.atyourservice.new(name='node.ssh', instance='vnas_ad', args=data)
        nodeAD.install(reinstall=True)

        # allow SSH SAL to connect seamlessly
        cl = nodeAD.actions.getSSHClient(nodeAD)
        cl.ssh_keygen('root', keytype='rsa')
        cl.run('cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys')
        self.setGitCredentials(cl)

        vnasAD = j.atyourservice.new(name='vnas_ad', instance='main', args=data, parent=nodeAD)
        vnasAD.consume('node', nodeAD.instance)
        vnasAD.install(reinstall=True, deps=True)

    def createBackend(self, id, stackID, nbrDisk):
        vmName = 'vnas_backend%s' % id
        id, _, _ = self.ovc.createMachine(self.spacesecret, vmName, memsize=4, ssdsize=10, imagename='Ubuntu 14.04 x64', delete=True, sshkey=self.keypub)
        obj = self.ovc.getMachineObject(self.spacesecret, vmName)
        ip = obj['interfaces'][0]['ipAddress']

        self.stopVM(vmName)
        for x in xrange(1, nbrDisk+1):
            diskName = 'data%s' % x
            self.ovc.addDisk(self.spacesecret, vmName, diskName, size=2000, description=None, type='D')
        self.startVM(vmName)

        if not j.system.net.waitConnectionTest(ip, 22, 120):
            j.events.opserror_critical(msg="VM didn't restart after we add disks to it", category="vnas_deploy")

        data = {
            'instance.ip': ip,
            'instance.ssh.port': 22,
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': 'vnas',
            'instance.jumpscale': True,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        j.atyourservice.remove(name='node.ssh', instance=vmName)
        node = j.atyourservice.new(name='node.ssh', instance=vmName, args=data)
        node.install(reinstall=True)

        # allow SSH SAL to connect seamlessly
        cl = node.actions.getSSHClient(node)
        cl.ssh_keygen('root', keytype='rsa')
        cl.run('cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys')
        self.setGitCredentials(cl)

        data = {
            'instance.stor.id': id,
            'instance.stor.export.dir': '/mnt/disks',
            'instance.disk.number': nbrDisk,
            'instance.disk.size': 2000,
        }
        vnasStor = j.atyourservice.new(name='vnas_stor', instance='main', args=data, parent=node)
        vnasStor.consume('node', node.instance)
        vnasStor.install(reinstall=True, deps=True)

        for i in range(nbrDisk):
            data = {
                'instance.disk.id': i,
                'instance.nfs.host': '192.168.103.0/24',
                'instance.nfs.options': 'no_root_squash, no_subtree_check',
            }
            stor_disk = j.atyourservice.new(name='vnas_stor_disk', instance="disk%s" % i, args=data, parent=vnasStor)
            stor_disk.consume('node', node.instance)
            stor_disk.install(deps=True)

    def createFrontend(self, id, stackID, serviceObj):
        vmName = 'vnas%s' % id
        id, _, _ = self.ovc.createMachine(self.spacesecret, vmName, memsize=2, ssdsize=10, imagename='Ubuntu 14.04 x64', delete=True, sshkey=self.keypub)
        obj = self.ovc.getMachineObject(self.spacesecret, vmName)
        ip = obj['interfaces'][0]['ipAddress']

        data = {
            'instance.ip': ip,
            'instance.ssh.port': 22,
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': 'vnas',
            'instance.jumpscale': True,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        j.atyourservice.remove(name='node.ssh', instance=vmName)
        node = j.atyourservice.new(name='node.ssh', instance=vmName, args=data)
        node.install(reinstall=True)

        cl = node.actions.getSSHClient(node)
        cl.ssh_keygen('root', keytype='rsa')
        cl.run('cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys')
        self.setGitCredentials(cl)

        data = {
            'instance.member.ad.address': serviceObj.hrd.get('instance.ad.ip'),
            'instance.member.address': ip,
            'instance.agentcontroller.address': serviceObj.hrd.get('instance.master.ip'),
            'instance.agent.nid': id,
        }
        vnasNode = j.atyourservice.new(name='vnas_node', instance='main', args=data, parent=node)
        vnasNode.consume('node', node.instance)
        vnasNode.install(reinstall=True, deps=True)

    def stopVM(self, vmName):
        for i in xrange(5):
            self.ovc.stopMachine(self.spacesecret, vmName)
            obj = self.ovc.getMachineObject(self.spacesecret, vmName)
            if obj['status'] == 'HALTED':
                return
            else:
                time.sleep(1.5)
        j.events.opserror_critical(msg="can't halt vm", category="vnas deploy")

    def startVM(self, vmName):
        for i in xrange(5):
            self.ovc.startMachine(self.spacesecret, vmName)
            obj = self.ovc.getMachineObject(self.spacesecret, vmName)
            if obj['status'] == 'RUNNING':
                return
            else:
                time.sleep(1.5)
        j.events.opserror_critical(msg="can't start vm", category="vnas deploy")

    def setGitCredentials(self, cl):
        cl.run('jsconfig hrdset -n whoami.git.login -v "%s"' % j.application.config.getStr('whoami.git.login'))
        cl.run('jsconfig hrdset -n whoami.git.passwd -v "%s"' % urllib.quote_plus(j.application.config.getStr('whoami.git.passwd')))
