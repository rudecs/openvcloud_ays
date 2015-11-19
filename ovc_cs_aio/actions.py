from JumpScale import j
import urllib
from StringIO import StringIO

ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):

    def prepare(self, serviceObj):
        self.host = serviceObj.hrd.getStr('instance.host')
        self.dcpmServerName = serviceObj.hrd.getStr('instance.dcpm.servername')
        self.ovsServerName = serviceObj.hrd.getStr('instance.ovs.servername')
        self.defenseServerName = serviceObj.hrd.getStr('instance.defense.servername')
        self.novncServerName = serviceObj.hrd.getStr('instance.novnc.servername')
        self.grafanaServerName = serviceObj.hrd.getStr('instance.grafana.servername')
        self.safekeeperServerName = serviceObj.hrd.getStr('instance.safekeeper.servername')

        # self.dcpmIpAddress = serviceObj.hrd.getStr('instance.dcpm.ipadress')
        self.dcpmPort = serviceObj.hrd.getStr('instance.dcpm.port')

        self.bootrappIpAddress = serviceObj.hrd.get('instance.bootstrapp.ipadress')
        self.bootrappPort = serviceObj.hrd.get('instance.bootstrapp.port')
        self.bootrappServerName = serviceObj.hrd.get('instance.bootstrapp.servername')
        
        self.rootdomain = 'demo.greenitglobe.com'
        self.rootenv = serviceObj.hrd.getStr('instance.param.main.host')
        
        if self.bootrappServerName == 'auto':
            self.bootrappServerName = 'bootstrap-%s.%s' % (self.rootenv, self.rootdomain)
        
        if self.host == 'auto':
            self.host = '%s.%s' % (self.rootenv, self.rootdomain)
            self.oauthUrl = 'https://%s' % (self.host)
            self.portalUrl = 'https://%s' % (self.host)
        else:
            self.oauthUrl = 'https://' + serviceObj.hrd.getStr('instance.host')
            self.portalUrl = 'https://' + serviceObj.hrd.getStr('instance.host')
        
        if self.dcpmServerName == 'auto':
            self.dcpmServerName = 'dcpm-%s.%s' % (self.rootenv, self.rootdomain)

        self.dcpmUrl = 'https://' + self.dcpmServerName
        
        if self.ovsServerName == 'auto':
            self.ovsServerName = 'ovs-%s.%s' % (self.rootenv, self.rootdomain)
        
        self.ovsUrl = 'https://' + self.ovsServerName
        
        if self.defenseServerName == 'auto':
            self.defenseServerName = 'defense-%s.%s' % (self.rootenv, self.rootdomain)
            
        self.defenseUrl = 'https://' + self.defenseServerName
        
        if self.novncServerName == 'auto':
            self.novncServerName = 'novnc-%s.%s' % (self.rootenv, self.rootdomain)
        
        self.novncUrl = 'https://' + self.novncServerName
        
        # grafana is redirected with /grafana/...
        if self.grafanaServerName == 'auto':
            self.grafanaServerName = '%s.%s/grafana' % (self.rootenv, self.rootdomain)
        
        self.grafanaUrl = 'https://' + self.grafanaServerName
        
        if self.safekeeperServerName == 'auto':
            self.safekeeperServerName = 'safekeeper-%s.%s' % (self.rootenv, self.rootdomain)
        
        self.safekeeperUrl = 'https://' + self.safekeeperServerName

        gitlabConnection = serviceObj.hrd.getStr('instance.gitlab_client.connection')
        gitlabClientHRD = j.application.getAppInstanceHRD(name='gitlab_client', instance=gitlabConnection)
        
        self.gitlabLogin = gitlabClientHRD.getStr('instance.gitlab.client.login')
        self.gitlabPasswd = gitlabClientHRD.getStr('instance.gitlab.client.passwd')

        self.repoPath = serviceObj.hrd.getStr('instance.param.repo.path')
        
        self.smtp = {
            'server': serviceObj.hrd.getStr('instance.smtp.server'),
            'port': serviceObj.hrd.getStr('instance.smtp.port'),
            'login': serviceObj.hrd.getStr('instance.smtp.login'),
            'passwd': serviceObj.hrd.getStr('instance.smtp.passwd'),
            'sender': serviceObj.hrd.getStr('instance.smtp.sender'),
        }
        
        print '[+] root domain: %s' % self.rootdomain
        print '[+] environment: %s' % self.rootenv
        print '[+] oauth   url: %s' % self.oauthUrl
        print '[+] portal  url: %s' % self.portalUrl
        print '[+] dcpm    url: %s' % self.dcpmUrl
        print '[+] ovs     url: %s' % self.ovsUrl
        print '[+] defense url: %s' % self.defenseUrl
        print '[+] novnc   url: %s' % self.novncUrl
        print '[+] grafana url: %s' % self.grafanaUrl
        print '[+] smtp server: %s' % self.smtp['server']

    def configure(self, serviceObj):
        ms1Connection = serviceObj.hrd.getStr('instance.ms1_client.connection')
        ms1clHRD = j.application.getAppInstanceHRD(name='ms1_client', instance=ms1Connection)
        spacesecret = ms1clHRD.getStr('instance.param.secret')

        self.api = j.tools.ms1.get()
        delete = serviceObj.hrd.getBool('instance.param.override')

        def reflector():
            # install reflector
            reflectorPassphrase = serviceObj.hrd.getStr('instance.reflector.root.passphrase')
            self.initReflectorVM(spacesecret, reflectorPassphrase, self.repoPath, delete=delete)
        j.actions.start(description='install reflector vm', action=reflector, category='openvlcoud', name='install_reflector', serviceObj=serviceObj)


        """
        def proxy():
            # install proxy
            self.initProxyVM(spacesecret, self.host, self.dcpmServerName,
                             self.dcpmIpAddress, self.dcpmPort,
                             self.ovsServerName,
                             self.defenseServerName, self.novncServerName,
                             self.bootrappIpAddress, self.bootrappPort, self.bootrappServerName,
                             delete=delete)
        j.actions.start(description='install proxy vm', action=proxy, category='openvlcoud', name='install_proxy', serviceObj=serviceObj)
        """

        def master():
            # install
            rootpasswd = serviceObj.hrd.getStr('instance.master.rootpasswd')
            ipGateway = serviceObj.hrd.getStr('instance.publicip.gateway')
            ipNetmask = serviceObj.hrd.getStr('instance.publicip.netmask')
            ipStart = serviceObj.hrd.getStr('instance.publicip.start')
            ipEnd = serviceObj.hrd.getStr('instance.publicip.end')
            self.initMasterVM(spacesecret, rootpasswd,
                              ipGateway, ipNetmask, ipStart, ipEnd,
                              self.dcpmUrl, self.ovsUrl, self.portalUrl, self.oauthUrl,
                              self.defenseUrl, self.repoPath, self.grafanaUrl, self.safekeeperUrl, self.smtp,
                              delete=delete)
        j.actions.start(description='install master vm', action=master, category='openvlcoud', name='install_master', serviceObj=serviceObj)
        
        def dcpm():
            # install reflector
            rootpasswd = serviceObj.hrd.getStr('instance.master.rootpasswd')
            self.initDCPMVM(spacesecret, self.repoPath, delete=delete)
        j.actions.start(description='install dcpm vm', action=dcpm, category='openvlcoud', name='install_dcpm', serviceObj=serviceObj)
        
        def proxy():
            # install proxy
            self.initProxyVM(spacesecret, self.host, self.dcpmServerName, self.dcpmPort,
                             self.ovsServerName,
                             self.defenseServerName, self.novncServerName,
                             self.bootrappIpAddress, self.bootrappPort, self.bootrappServerName,
                             self.grafanaServerName, delete=delete)
        j.actions.start(description='install proxy vm', action=proxy, category='openvlcoud', name='install_proxy', serviceObj=serviceObj)
    
    def installJumpscale(self, cl):
        # install Jumpscale
        print "[+] installing jumpscale"
        cl.run('curl https://raw.githubusercontent.com/Jumpscale/jumpscale_core7/master/install/install.sh > /tmp/js7.sh && bash /tmp/js7.sh')
        print "[+] jumpscale installed"
        
    def setupGit(self, cl):
        cl.run('jsconfig hrdset -n whoami.git.login -v "%s"' % self.gitlabLogin)
        cl.run('jsconfig hrdset -n whoami.git.passwd -v "%s"' % urllib.quote_plus(self.gitlabPasswd))
    
    def setupHost(self, host, address):
        hosts = StringIO('\n'.join(line.strip() for line in open('/etc/hosts'))).getvalue()
        
        # FIXME: should replace ip if already exists
        if not host in hosts:
            j.system.fs.writeFile('/etc/hosts', ("\n%s\t%s\n" % (address, host)), True)
    
    def copyBack(self, remote, service):
        remoteHrd  = j.application.getAppInstanceHRD(name='node.ssh', instance=remote)
        remoteHost = remoteHrd.getStr('instance.ip')
        
        remotePath = '/opt/jumpscale7/hrd/apps/%s/service.hrd' % service
        localPath  = '%s/services/jumpscale__node.ssh__%s/%s/' % (self.repoPath, remote, service)
        
        print '[+] copy back: %s:%s -> %s' % (remoteHost, remotePath, localPath)
        j.do.execute('scp %s:%s %s' % (remoteHost, remotePath, localPath))

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

        # create ovc_reflector vm
        try:
            _, pubIP, sshPort = self.api.createMachine(spacesecret, 'ovc_reflector', memsize='0.5', ssdsize='10', imagename='ubuntu.14.04.x64',sshkey='/root/.ssh/id_rsa.pub',delete=delete)
        except Exception as e:
            if e.message.find('Could not create machine it does already exist') == -1:
                raise e
        machine = self.api.getMachineObject(spacesecret, 'ovc_reflector')
        privIP = machine['interfaces'][0]['ipAddress']
        
        # FIXME: why sshPort not well defined ?
        ports = self.api.listPortforwarding(spacesecret, 'ovc_reflector')
        for fw in ports:
            if fw['localPort'] == '22':
                sshPort = fw['publicPort']

        vspace = self.api.getCloudspaceObj(spacesecret)
        pubIP = vspace['publicipaddress']
        
        # saving ip to hosts
        self.setupHost('reflector', privIP)

        cl = j.ssh.connect(privIP, 22, keypath='/root/.ssh/id_rsa')

        self.installJumpscale(cl)
        self.setupGit(cl)

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

        # configure ssh to let master connect to the node through reflector
        content = cl.file_read('/etc/ssh/sshd_config')
        if content.find('GatewayPorts clientspecified') == -1:
            cl.file_append('/etc/ssh/sshd_config', "\nGatewayPorts clientspecified\n")
            
            print '[+] restarting ssh'
            cl.run('service ssh restart')


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
        
        print "[+] bootstrap: private ip: %s" % privIP
        print "[+] bootstrap: public ip : %s" % pubIP
        print "[+] reflector ssh port: %s" % sshPort

        # install bootrapp on git vm
        data = {
            'instance.listen.port': 5000,
            'instance.ovc_git': repoPath,
            'instance.master.name': 'jumpscale__node.ssh__ovc_master',
            'instance.reflector.ip.priv': privIP,
            'instance.reflector.ip.pub': pubIP,
            'instance.reflector.port': sshPort,
            'instance.reflector.name': 'jumpscale__node.ssh__ovc_reflector',
            'instance.reflector.user': 'guest'
        }
        bootrapp = j.atyourservice.remove(name='bootstrapp') # override service
        bootrapp = j.atyourservice.new(name='bootstrapp', args=data)
        bootrapp.install()
        # expose port of bootrapp
        self.api.createTcpPortForwardRule(spacesecret, 'ovc_git', 5000, pubipport=5000)

    def initProxyVM(self, spacesecret, host, dcpmServerName, dcpmPort, ovsServerName, defenseServerName, novncServerName, bootrappIpAddress, bootrappPort, bootrappServerName,
        grafanaServerName, delete=False):
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
        
        print '[+] grabbing ovc_proxy address'
        proxyvm = self.api.getMachineObject(spacesecret, 'ovc_proxy')
        proxyip = proxyvm['interfaces'][0]['ipAddress']
        print '[+] ovc_proxy is %s' % proxyip
        
        print '[+] grabbing ovc_master address'
        mastervm = self.api.getMachineObject(spacesecret, 'ovc_master')
        masterip = mastervm['interfaces'][0]['ipAddress']
        print '[+] ovc_master is %s' % masterip
        
        print '[+] grabbing ovc_reflector address'
        reflectvm = self.api.getMachineObject(spacesecret, 'ovc_reflector')
        reflectip = reflectvm['interfaces'][0]['ipAddress']
        print '[+] ovc_reflector is %s' % reflectip
        
        print '[+] grabbing ovc_dcpm address'
        dcpmvm = self.api.getMachineObject(spacesecret, 'ovc_dcpm')
        dcpmip = dcpmvm['interfaces'][0]['ipAddress']
        print '[+] ovc_dcpm is %s' % dcpmip

        # portforward 80 and 443 to 80 and 443 on ovc_proxy
        self.api.createTcpPortForwardRule(spacesecret, 'ovc_proxy', 80, pubipport=80)
        self.api.createTcpPortForwardRule(spacesecret, 'ovc_proxy', 443, pubipport=443)
        
        # saving ip to hosts
        self.setupHost('proxy', proxyip)

        cl = j.ssh.connect(proxyip, 22, keypath='/root/.ssh/id_rsa')

        self.installJumpscale(cl)
        self.setupGit(cl)

        # create service required to connect to ovc reflector with ays
        data = {
            'instance.key.priv': j.system.fs.fileGetContents('/root/.ssh/id_rsa')
        }
        keyService = j.atyourservice.new(name='sshkey', instance='ovc_proxy', args=data)
        keyService.install()

        data = {
            'instance.ip': proxyip,
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
            'instance.master.ipadress': masterip,
            'instance.dcpm.servername': dcpmServerName,
            'instance.dcpm.ipadress': dcpmip,
            'instance.dcpm.port': dcpmPort,
            'instance.bootstrapp.ipadress': bootrappIpAddress,
            'instance.bootstrapp.port': bootrappPort,
            'instance.bootstrapp.servername': bootrappServerName,
            'instance.ovs.servername': ovsServerName,
            'instance.defense.servername': defenseServerName,
            'instance.novnc.servername': novncServerName,
            'instance.grafana.servername': grafanaServerName,
            'instance.reflector.ipadress': reflectip,
        }
        ssloffloader = j.atyourservice.new(name='ssloffloader', args=data, parent=nodeService)
        ssloffloader.consume('node', nodeService.instance)
        ssloffloader.install(deps=True)

    def initMasterVM(self, spacesecret, masterPasswd, publicGateway, publicNetmask, publicipStart, publicipEnd, dcpmUrl, ovsUrl, portalUrl, oauthUrl, defenseUrl, repoPath, grafanaUrl, safekeeperUrl, smtp, delete=False):
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

        # portforward 4444 to 4444 ovc_master and 5544
        self.api.createTcpPortForwardRule(spacesecret, 'ovc_master', 4444, pubipport=4444)
        self.api.createTcpPortForwardRule(spacesecret, 'ovc_master', 5544, pubipport=5544)
        
        # FIXME: should not expose statsd port
        self.api.createTcpPortForwardRule(spacesecret, 'ovc_master', 8127, pubipport=8127)
        
        # saving ip to hosts
        self.setupHost('master', ip)

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

        self.installJumpscale(cl)
        self.setupGit(cl)

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
            'instance.param.publicip.gateway': publicGateway,
            'instance.param.publicip.netmask': publicNetmask,
            'instance.param.publicip.start': publicipStart,
            'instance.param.publicip.end': publicipEnd,
            'instance.param.dcpm.url': dcpmUrl,
            'instance.param.ovs.url': ovsUrl,
            'instance.param.ovc.environment': self.rootenv,
            'instance.param.portal.url': portalUrl,
            'instance.param.oauth.url': oauthUrl,
            'instance.param.defense.url': defenseUrl,
            'instance.param.grafana.url': grafanaUrl,
            'instance.param.safekeeper.url': safekeeperUrl,
            'instance.param.smtp.server': smtp['server'],
            'instance.param.smtp.port': smtp['port'],
            'instance.param.smtp.login': smtp['login'],
            'instance.param.smtp.passwd': smtp['passwd'],
            'instance.param.smtp.sender': smtp['sender'],
        }
        master = j.atyourservice.new(name='cb_master_aio', args=data, parent=nodeService)
        master.consume('node', nodeService.instance)
        master.install(deps=True)
        
        # FIXME
        # Copy needed file from master to ovcgit
        # Theses files are generated on the master and not synced back to ovcgit
        self.copyBack('ovc_master', 'jumpscale__oauth_client__oauth')
        self.copyBack('ovc_master', 'jumpscale__portal__main')

    def initDCPMVM(self, spacesecret, repoPath, delete=False):
        """
        this methods need to be run from the ovc_dcpm VM

        will do following:
            - create vmachine
            - install JumpScale
            - create keypair for root
            - copy keypair in ovc_dcpm keys directory
            - install dcpm service
        """

        # create ovc_git vm
        try:
            self.api.createMachine(spacesecret, 'ovc_dcpm', memsize='0.5', ssdsize='10', imagename='ubuntu.14.04.x64',sshkey='/root/.ssh/id_rsa.pub',delete=delete)
        except Exception as e:
            if e.message.find('Could not create machine it does already exist') == -1:
                raise e
        machine = self.api.getMachineObject(spacesecret, 'ovc_dcpm')
        ip = machine['interfaces'][0]['ipAddress']

        cl = j.ssh.connect(ip, 22, keypath='/root/.ssh/id_rsa')
        
        # saving ip to hosts
        self.setupHost('dcpm', ip)


        # generate key pair on the vm
        print 'generate keypair on the vm'
        cl.ssh_keygen('root', keytype='rsa')
        keys = {
            '/root/.ssh/id_rsa': '%s/keys/master_dcpm' % repoPath,
            '/root/.ssh/id_rsa.pub': '%s/keys/master_dcpm.pub' % repoPath,
        }
        for source, destination in keys.iteritems():
            content = cl.file_read(source)
            j.system.fs.writeFile(filename=destination, contents=content)

        self.installJumpscale(cl)
        self.setupGit(cl)

        # create service required to connect to ovc reflector with ays
        data = {
            'instance.key.priv': j.system.fs.fileGetContents('/root/.ssh/id_rsa')
        }
        keyService = j.atyourservice.new(name='sshkey', instance='ovc_dcpm', args=data)
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
        j.atyourservice.remove(name='node.ssh', instance='ovc_dcpm')
        nodeService = j.atyourservice.new(name='node.ssh', instance='ovc_dcpm', args=data)
        nodeService.install(reinstall=True)
        
        """
        # FIXME: manual installation until fixed
        dcpm = j.atyourservice.new(name='dcpm', parent=nodeService)
        dcpm.consume('node', nodeService.instance)
        dcpm.install()
        """
