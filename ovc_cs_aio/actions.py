from JumpScale import j
import urllib

ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):

    def configure(self, serviceObj):
        ms1clHRD = j.application.getAppInstanceHRD(name='ms1_client', instance='$(instance.ms1_client.connection)')
        spacesecret = ms1clHRD.getStr('instance.param.secret')

        gitlabClientHRD = j.application.getAppInstanceHRD(name='gitlab_client', instance='$(instance.gitlab_client.connection)')
        self.gitlabLogin = gitlabClientHRD.getStr('instance.gitlab.client.login')
        self.gitlabPasswd = gitlabClientHRD.getStr('instance.gitlab.client.passwd')

        self.api = j.tools.ms1.get()
        delete = serviceObj.hrd.getBool('instance.param.override')

        def reflector():
            # install reflector
            self.initReflectorVM(spacesecret, '$(instance.reflector.root.passphrase)', '$(instance.param.repo.path)', delete=delete)
        j.actions.start(description='install reflector vm', action=reflector, category='openvlcoud', name='install_reflector', serviceObj=serviceObj)

        def proxy():
            # install proxy
            self.initProxyVM(spacesecret, '$(instance.proxy.host)', '$(instance.proxy.dcpm.servername)',
                        '$(instance.proxy.dcpm.internalhost)', '$(instance.proxy.ovs.servername)',
                        '$(instance.proxy.defense.servername)', '$(instance.proxy.novnc.servername)',
                         delete=delete)
        j.actions.start(description='install proxy vm', action=proxy, category='openvlcoud', name='install_proxy', serviceObj=serviceObj)

        def master():
            # install
            self.initMasterVM(spacesecret, '$(instance.master.rootpasswd)', '$(instance.master.publicip.start)',
                            '$(instance.master.publicip.end)', '$(instance.master.dcpm.url)',
                            '$(instance.ovs.url)', '$(instance.portal.url)', '$(instance.oauth.url)',
                            '$(instance.defense.url)', '$(instance.param.repo.path)', delete=delete)
        j.actions.start(description='install master vm', action=master, category='openvlcoud', name='install_master', serviceObj=serviceObj)

    def initReflectorVM(self, spacesecret, passphrase, repoPath, delete=False):
        """
        this methods need to be run from the ovc_git VM

        Master reflector VM is the machine that received the reverse tunnel from the nodes and create connection betwee master cloudspace and nodes

        will do following:
            - create vmachine
            - install JumpScale
            - install ovc_reflector service, this service do:
                - create keypair with passphrase for root
                - create user guest
                - create keypair for guest
            - copy keys from root and guest and copy the into the keys folder of the ovc_git repo
            - install bootrapp on ovc_git vm, this happens now, cause we need the ip of the relfector vm to install bootrapp
        """

        # create ovc_git vm
        try:
            _, pubIP, _ = self.api.createMachine(spacesecret, 'ovc_reflector', memsize='0.5', ssdsize='10', imagename='ubuntu.14.04.x64',sshkey='/root/.ssh/id_rsa.pub',delete=delete)
        except Exception as e:
            if e.message.find('Could not create machine it does already exist') == -1:
                raise e
        machine = self.api.getMachineObject(spacesecret, 'ovc_reflector')
        privIP = machine['interfaces'][0]['ipAddress']

        cl = j.ssh.connect(privIP, 22, keypath='/root/.ssh/id_rsa')

        # install Jumpscale
        print "install jumpscale"
        cl.run('curl https://raw.githubusercontent.com/Jumpscale/jumpscale_core7/master/install/install.sh > /tmp/js7.sh && bash /tmp/js7.sh')
        print "jumpscale installed"

        cl.run('jsconfig hrdset -n whoami.git.login -v "%s"' % self.gitlabLogin)
        cl.run('jsconfig hrdset -n whoami.git.passwd -v "%s"' % urllib.quote_plus(self.gitlabPasswd))

        # genretate keypair on the vm
        cl.ssh_keygen('root', keytype='rsa')
        cl.user_ensure('guest', home='/home/guest', shell='/bin/bash')
        cl.ssh_keygen('guest', keytype='rsa')
        # copy the key on the git vm
        keys = {
            '/root/.ssh/id_rsa': '%s/keys/reflector_root' % repoPath,
            '/root/.ssh/id_rsa.pub': '%s/keys/reflector_root.pub' % repoPath,
            '/home/guest/.ssh/id_rsa': '%s/keys/reflector_guest' % repoPath,
            '/home/guest/.ssh/id_rsa.pub': '%s/keys/reflector_guest.pub' % repoPath
        }
        for source, destination in keys.iteritems():
            content = cl.file_read(source)
            j.system.fs.writeFile(filename=destination, contents=content)


        # create service required to connect to ovc reflector with ays
        data = {
            'instance.key.priv': j.system.fs.fileGetContents('/root/.ssh/id_rsa')
        }
        keyService = j.atyourservice.new(name='sshkey', instance='ovc_reflector', args=data)
        keyService.install()

        data = {
            'instance.ip': privIP,
            'instance.ssh.port': 22,
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': keyService.instance,
            'instance.jumpscale': False,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        j.atyourservice.remove(name='node.ssh', instance='ovc_reflector')
        nodeService = j.atyourservice.new(name='node.ssh', instance='ovc_reflector', args=data)
        nodeService.install(reinstall=True)

        # install bootrapp on git vm
        data = {
            'instance.listen.port': 5000,
            'instance.ovc_git': repoPath,
            'instance.master.name': 'jumpscale__node.ssh__ovc_master',
            'instance.reflector.ip.priv': privIP,
            'instance.reflector.ip.pub': pubIP,
            'instance.reflector.name': 'jumpscale__node.ssh__ovc_reflector',
            'instance.reflector.user': 'guest'
        }
        bootrapp = j.atyourservice.remove(name='bootstrapp') # override service
        bootrapp = j.atyourservice.new(name='bootstrapp', args=data)
        bootrapp.install()
        # expose port of bootrapp
        self.api.createTcpPortForwardRule(spacesecret, 'ovc_git', 5000, pubipport=5000)

    def initProxyVM(self, spacesecret, host, dcpmServerName, dcpmInternalHost, ovsServerName, defenseServerName, novncServerName,
        delete=False):
        """
        this methods need to be run from the ovc_git VM

        Master reflector VM is the machine that received the reverse tunnel from the nodes and create connection betwee master cloudspace and nodes

        will do following:
            - create vmachine
            - create portforward on port 80 and 443
            - install JumpScale
            - install ssloffloader service
        """

        # create ovc_git vm
        try:
            self.api.createMachine(spacesecret, 'ovc_proxy', memsize='0.5', ssdsize='10', imagename='ubuntu.14.04.x64',sshkey='/root/.ssh/id_rsa.pub',delete=delete)
        except Exception as e:
            if e.message.find('Could not create machine it does already exist') == -1:
                raise e
        machine = self.api.getMachineObject(spacesecret, 'ovc_reflector')
        ip = machine['interfaces'][0]['ipAddress']

        # portforward 80 and 443 to 80 and 442 on ovc_proxy
        self.api.createTcpPortForwardRule(spacesecret, 'ovc_proxy', 80, pubipport=80)
        self.api.createTcpPortForwardRule(spacesecret, 'ovc_proxy', 443, pubipport=443)

        cl = j.ssh.connect(ip, 22, keypath='/root/.ssh/id_rsa')

        # install Jumpscale
        print "install jumpscale"
        cl.run('curl https://raw.githubusercontent.com/Jumpscale/jumpscale_core7/master/install/install.sh > /tmp/js7.sh && bash /tmp/js7.sh')
        print "jumpscale installed"

        cl.run('jsconfig hrdset -n whoami.git.login -v "%s"' % self.gitlabLogin)
        cl.run('jsconfig hrdset -n whoami.git.passwd -v "%s"' % urllib.quote_plus(self.gitlabPasswd))

        # create service required to connect to ovc reflector with ays
        data = {
            'instance.key.priv': j.system.fs.fileGetContents('/root/.ssh/id_rsa')
        }
        keyService = j.atyourservice.new(name='sshkey', instance='ovc_proxy', args=data)
        keyService.install()

        data = {
            'instance.ip': ip,
            'instance.ssh.port': 22,
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': keyService.instance,
            'instance.jumpscale': False,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        j.atyourservice.remove(name='node.ssh', instance='ovc_proxy')
        nodeService = j.atyourservice.new(name='node.ssh', instance='ovc_proxy', args=data)
        nodeService.install(reinstall=True)

        cloudspaceObj = self.api.getCloudspaceObj(spacesecret)
        data = {
            'instance.host': host,
            'instance.master.ipadress': cloudspaceObj['publicipaddress'],
            'instance.dcpm.servername': dcpmServerName,
            'instance.dcpm.internalhost': dcpmInternalHost,
            'instance.ovs.servername': ovsServerName,
            'instance.defense.servername': defenseServerName,
            'instance.novnc.servername': novncServerName
        }
        ssloffloader = j.atyourservice.new(name='ssloffloader', args=data, parent=nodeService)
        ssloffloader.consume('node', nodeService.instance)
        ssloffloader.install(deps=True)

    def initMasterVM(self, spacesecret, masterPasswd, publicipStart, publicipEnd, dcpmUrl, ovsUrl, portalUrl, oauthUrl, defenseUrl, repoPath, delete=False):
        """
        this methods need to be run from the ovc_git VM

        Master reflector VM is the machine that received the reverse tunnel from the nodes and create connection betwee master cloudspace and nodes

        will do following:
            - create vmachine
            - install JumpScale
            - create keypair for root
            - copy keypair in ovc_git keys directory
            - install cb_master_aio service
            - put reflector_guest.pub in /root/.ssh/authorized_keys
        """

        # create ovc_git vm
        try:
            self.api.createMachine(spacesecret, 'ovc_master', memsize='4', ssdsize='40', imagename='ubuntu.14.04.x64',sshkey='/root/.ssh/id_rsa.pub',delete=delete)
        except Exception as e:
            if e.message.find('Could not create machine it does already exist') == -1:
                raise e
        machine = self.api.getMachineObject(spacesecret, 'ovc_master')
        ip = machine['interfaces'][0]['ipAddress']

        # portforward 4444 to 4444 ovc_master
        self.api.createTcpPortForwardRule(spacesecret, 'ovc_proxy', 4444, pubipport=4444)

        cl = j.ssh.connect(ip, 22, keypath='/root/.ssh/id_rsa')


        # generate key pair on the vm
        print 'generate keypair on the vm'
        cl.ssh_keygen('root', keytype='rsa')
        keys = {
            '/root/.ssh/id_rsa': '%s/keys/master_root' % repoPath,
            '/root/.ssh/id_rsa.pub': '%s/keys/master_root.pub' % repoPath,
        }
        for source, destination in keys.iteritems():
            content = cl.file_read(source)
            j.system.fs.writeFile(filename=destination, contents=content)

        # install Jumpscale
        print "install jumpscale"
        cl.run('curl https://raw.githubusercontent.com/Jumpscale/jumpscale_core7/master/install/install.sh > /tmp/js7.sh && bash /tmp/js7.sh')
        print "jumpscale installed"

        cl.run('jsconfig hrdset -n whoami.git.login -v "%s"' % self.gitlabLogin)
        cl.run('jsconfig hrdset -n whoami.git.passwd -v "%s"' % urllib.quote_plus(self.gitlabPasswd))

        # create service required to connect to ovc reflector with ays
        data = {
            'instance.key.priv': j.system.fs.fileGetContents('/root/.ssh/id_rsa')
        }
        keyService = j.atyourservice.new(name='sshkey', instance='ovc_master', args=data)
        keyService.install()

        data = {
            'instance.ip': ip,
            'instance.ssh.port': 22,
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': keyService.instance,
            'instance.jumpscale': False,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        j.atyourservice.remove(name='node.ssh', instance='ovc_master')
        nodeService = j.atyourservice.new(name='node.ssh', instance='ovc_master', args=data)
        nodeService.install(reinstall=True)

        cloudspaceObj = self.api.getCloudspaceObj(spacesecret)
        data = {
            'instance.param.rootpasswd': masterPasswd,
            'instance.param.publicip.gateway': cloudspaceObj['publicipaddress'],
            'instance.param.publicip.netmask': '255.255.255.0',
            'instance.param.publicip.start': publicipStart,
            'instance.param.publicip.end': publicipEnd,
            'instance.param.dcpm.url': dcpmUrl,
            'instance.param.ovs.url': ovsUrl,
            'instance.param.portal.url': portalUrl,
            'instance.param.oauth.url': oauthUrl,
            'instance.param.defense.url': defenseUrl
        }
        master = j.atyourservice.new(name='cb_master_aio', args=data, parent=nodeService)
        master.consume('node', nodeService.instance)
        master.install(deps=True)

        content = j.system.fs.fileGetContents('%s/keys/reflector_guest.pub' % repoPath)
        cl.file_append('/root/.ssh/.ssh/authorized_keys', content)
