from JumpScale import j
import os

ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):

    def prepare(self, serviceObj):
        self.host = serviceObj.hrd.getStr('instance.host')
        self.rootpwd = serviceObj.hrd.getStr('instance.master.rootpasswd')

        self.bootrappIpAddress = serviceObj.hrd.get('instance.bootstrapp.ipadress')
        self.bootrappPort = serviceObj.hrd.get('instance.bootstrapp.port')

        self.rootdomain = serviceObj.hrd.get('instance.param.domain')
        self.rootenv = serviceObj.hrd.getStr('instance.param.main.host')
        self.repoPath = serviceObj.hrd.getStr('instance.param.repo.path')

        # checking for ssh-agent
        if not os.environ.get('SSH_AUTH_SOCK'):
            j.console.warning('ssh agent seems not loaded, please check your keys')
            j.application.stop()

        # custom servers name
        if self.host == 'auto':
            self.host = '%s.%s' % (self.rootenv, self.rootdomain)
        else:
            self.host = serviceObj.hrd.getStr('instance.host')

        # grafana is redirected with /grafana/...
        self.grafanaServerName = serviceObj.hrd.getStr('instance.grafana.servername')

        if self.grafanaServerName == 'auto':
            self.grafanaServerName = '%s.%s/grafana' % (self.rootenv, self.rootdomain)

        # servers settings
        self.servers = {
            'boot': self.defaultServerName('bootstrapp', serviceObj.hrd.get('instance.bootstrapp.servername')),
            'ovs': self.defaultServerName('ovs', serviceObj.hrd.getStr('instance.ovs.servername')),
            'novnc': self.defaultServerName('novnc', serviceObj.hrd.getStr('instance.novnc.servername')),
            'grafana': self.grafanaServerName
        }

        self.urls = {
            'ovs': 'https://' + self.servers['ovs'],
            'grafana': 'https://' + self.servers['grafana'],
            'novnc': 'https://' + self.servers['novnc'],
            'portal': 'https://%s' % (self.host)
        }

        self.itsyouonline = serviceObj.hrd.getDictFromPrefix('instance.itsyouonline')

        self.smtp = {
            'server': serviceObj.hrd.getStr('instance.smtp.server'),
            'port': serviceObj.hrd.getStr('instance.smtp.port'),
            'login': serviceObj.hrd.getStr('instance.smtp.login'),
            'passwd': serviceObj.hrd.getStr('instance.smtp.passwd'),
            'sender': serviceObj.hrd.getStr('instance.smtp.sender')
        }

        self.machines = {
            'master': self.getMachineService('ovc_master'),
            'proxy': self.getMachineService('ovc_proxy'),
            'reflector': self.getMachineService('ovc_reflector'),
        }

        self.grid = {
            'id': serviceObj.hrd.getInt('instance.grid.id'),
        }

        self.ssl = {
            'root': serviceObj.hrd.getStr('instance.ssl.root'),
            'ovs': serviceObj.hrd.getStr('instance.ssl.ovs'),
            'novnc': serviceObj.hrd.getStr('instance.ssl.novnc'),
        }

        j.console.info('root domain: %s' % self.rootdomain)
        j.console.info('environment: %s' % self.rootenv)
        j.console.info('--------------------------')
        j.console.info('portal  url: %s' % self.urls['portal'])
        j.console.info('ovs     url: %s' % self.urls['ovs'])
        j.console.info('novnc   url: %s' % self.urls['novnc'])
        j.console.info('grafana url: %s' % self.urls['grafana'])
        j.console.info('smtp server: %s' % self.smtp['server'])
        j.console.info('--------------------------')
        j.console.info('master   : %s' % self.machines['master'])
        j.console.info('proxy    : %s' % self.machines['proxy'])
        j.console.info('reflector: %s' % self.machines['reflector'])
        j.console.info('--------------------------')

        if self.machines['reflector'] is None:
            j.console.warning('direct access environment, no reflector found')

    def configure(self, serviceObj):

        def reflector():
            self.initReflectorVM(self.machines['reflector'], self.repoPath)

        if self.machines['reflector']:
            j.actions.start(description='configure reflector', action=reflector, category='openvlcoud',
                            name='configure_reflector', serviceObj=serviceObj)

        else:
            # no reflector, setting up bootstrap without it
            j.console.warning('skipping reflector configuration, setting up bootstrap')
            fakeReflector = {
                'localip': 'not used (no reflector)',
                'publicip': 'not used (no reflector)',
                'publicport': 'not used (no reflector)',
                'service': '',  # need to be empty
            }
            self.setupBootstrap(self.repoPath, fakeReflector)

        def master():
            self.initMasterVM(self.machines['master'], self.rootpwd, self.urls,
                              self.repoPath, self.smtp, self.grid, self.itsyouonline)

        j.actions.start(description='configure master', action=master, category='openvlcoud',
                        name='configure_master', serviceObj=serviceObj)

        # setting up agent on reflector
        if self.machines['reflector']:
            reflector = self.machines['reflector']
            masterip = self.getMachineAddress('ovc_master')
            data_reflector = {
                'instance.param.rootpasswd': self.rootpwd,
                'instance.param.master.addr': masterip,
                'instance.param.grid.id': self.grid['id'],
            }
            temp = j.atyourservice.new(name='cb_reflector', args=data_reflector, parent=reflector)
            temp.consume('node', reflector.instance)
            temp.install(deps=True)

        def proxy():
            self.initProxyVM(self.machines['proxy'], self.host, self.servers,
                             self.bootrappIpAddress, self.bootrappPort, self.ssl)

        j.actions.start(description='configure proxy', action=proxy, category='openvlcoud',
                        name='configure_proxy', serviceObj=serviceObj)

    """
    Console tools
    """

    def enableQuiet(self):
        j.remote.cuisine.api.fabric.state.output['stdout'] = False
        j.remote.cuisine.api.fabric.state.output['running'] = False

    def disableQuiet(self):
        j.remote.cuisine.api.fabric.state.output['stdout'] = True
        j.remote.cuisine.api.fabric.state.output['running'] = True

    """
    Configuration tools
    """

    def defaultServerName(self, item, name):
        if name == 'auto':
            return '%s-%s.%s' % (item, self.rootenv, self.rootdomain)

        return name

    def getMachineService(self, name):
        sshservices = j.atyourservice.findServices(instance=name)
        nodeservices = filter(lambda x: x.name.startswith('node.'), sshservices)

        if len(nodeservices) == 1:
            return nodeservices[0]

        return None

    def getMachine(self, name):
        machine = self.getMachineService(name)

        if machine is None:
            return {}

        temp = machine.hrd.getHRDAsDict()

        data = {
            'hostname': temp['service.instance'],
            'localport': temp['instance.ssh.port'],
            'localip': temp['instance.ip'],
            'publicip': temp['instance.publicip'],
            'publicport': temp['instance.ssh.publicport'],
            'image': ''
        }

        return data

    def getMachineAddress(self, name):
        machine = self.getMachine(name)

        if machine.get('localip'):
            return machine['localip']

        return None

    def copyBack(self, remote, service):
        remoteHrd = j.application.getAppInstanceHRD(name='node.ssh', instance=remote)
        remoteHost = remoteHrd.getStr('instance.ip')

        remotePath = '/opt/jumpscale7/hrd/apps/%s/service.hrd' % service
        localPath = '%s/services/jumpscale__%s__%s/%s/' % (self.repoPath, 'node.ssh', remote, service)

        j.console.info('copy back: %s:%s -> %s' % (remoteHost, remotePath, localPath))
        j.do.execute('scp %s:%s %s' % (remoteHost, remotePath, localPath))

    def setupBootstrap(self, repoPath, reflector):
        j.console.info("bootstrap reflector private ip: %s" % reflector['localip'])
        j.console.info("bootstrap reflector public ip: %s" % reflector['publicip'])
        j.console.info("bootstrap reflector ssh port: %s" % reflector['publicport'])

        # install bootrapp on git vm
        data = {
            'instance.listen.port': 5000,
            'instance.ovc_git': repoPath,
            'instance.master.name': 'jumpscale__node.ssh__ovc_master',
            'instance.reflector.ip.priv': reflector['localip'],
            'instance.reflector.ip.pub': reflector['publicip'],
            'instance.reflector.port': reflector['publicport'],
            'instance.reflector.name': reflector['service'],
            'instance.reflector.user': 'guest'
        }

        bootrapp = j.atyourservice.remove(name='bootstrapp')  # override service
        bootrapp = j.atyourservice.new(name='bootstrapp', args=data)
        bootrapp.install()

    def initReflectorVM(self, parent, repoPath):
        j.console.info('configuring: reflector')

        reflector = self.getMachine('ovc_reflector')
        reflector['service'] = 'jumpscale__node.ssh__ovc_reflector'

        self.setupBootstrap(repoPath, reflector)

    def initProxyVM(self, parent, host, servers, bootrappIpAddress, bootrappPort, ssl):
        j.console.info('configuring: proxy')

        proxyip = self.getMachineAddress('ovc_proxy')
        j.console.info('ovc_proxy: %s' % proxyip)

        masterip = self.getMachineAddress('ovc_master')
        j.console.info('ovc_master: %s' % masterip)

        j.console.info('master domain: %s' % self.rootdomain)

        data = {
            'instance.host': host,
            'instance.domain': self.rootdomain,
            'instance.master.ipadress': masterip,

            'instance.bootstrapp.servername': servers['boot'],
            'instance.ovs.servername': servers['ovs'],
            'instance.novnc.servername': servers['novnc'],
            'instance.grafana.servername': servers['grafana'],

            'instance.ssl.root': ssl['root'],
            'instance.ssl.ovs': ssl['ovs'],
            'instance.ssl.novnc': ssl['novnc'],
        }

        ssloffloader = j.atyourservice.new(name='ssloffloader', args=data, parent=parent)
        ssloffloader.consume('node', parent.instance)
        ssloffloader.install(deps=True)

    def initMasterVM(self, parent, masterPasswd, urls, repoPath, smtp, grid, itsyouonline):
        j.console.info('configuring: master')

        j.console.info('master password: %s' % masterPasswd)

        data = {
            'instance.param.rootpasswd': masterPasswd,
            'instance.param.ovs.url': urls['ovs'],
            'instance.param.ovc.environment': self.rootenv,
            'instance.param.portal.url': urls['portal'],
            'instance.param.grafana.url': urls['grafana'],
            'instance.param.smtp.server': smtp['server'],
            'instance.param.smtp.port': smtp['port'],
            'instance.param.smtp.login': smtp['login'],
            'instance.param.smtp.passwd': smtp['passwd'],
            'instance.param.smtp.sender': smtp['sender'],
            'instance.param.grid.id': grid['id'],
            'instance.param.itsyouonline.client_id': itsyouonline['client_id'],
            'instance.param.itsyouonline.client_secret': itsyouonline['client_secret'],
        }

        master = j.atyourservice.new(name='cb_master_aio', args=data, parent=parent)
        master.consume('node', parent.instance)
        master.install(deps=True)

        # FIXME
        # Copy needed file from master to ovcgit
        # Theses files are generated on the master and not synced back to ovcgit
        self.copyBack('ovc_master', 'jumpscale__portal__main')
        self.copyBack('ovc_master', 'openvcloud__ovc_itsyouonline__main')
