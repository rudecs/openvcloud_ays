from JumpScale import j
import urllib
from StringIO import StringIO
import os

ActionsBase = j.atyourservice.getActionsBaseClass()

class Actions(ActionsBase):

    def prepare(self, serviceObj):
        self.host = serviceObj.hrd.getStr('instance.host')
        self.rootpwd = serviceObj.hrd.getStr('instance.master.rootpasswd')

        # self.dcpmIpAddress = serviceObj.hrd.getStr('instance.dcpm.ipadress')
        self.dcpmPort = serviceObj.hrd.getStr('instance.dcpm.port')

        self.bootrappIpAddress = serviceObj.hrd.get('instance.bootstrapp.ipadress')
        self.bootrappPort = serviceObj.hrd.get('instance.bootstrapp.port')
        
        self.rootdomain = serviceObj.hrd.get('instance.param.domain')
        self.rootenv = serviceObj.hrd.getStr('instance.param.main.host')
        self.repoPath = serviceObj.hrd.getStr('instance.param.repo.path')
        
        # checking for ssh-agent
        if not os.environ.get('SSH_AUTH_SOCK'):
            print '[-] ssh agent seems not loaded, please check your keys'
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
            'boot':    self.defaultServerName('bootstrapp', serviceObj.hrd.get('instance.bootstrapp.servername')),
            'safe':    self.defaultServerName('safekeeper', serviceObj.hrd.getStr('instance.safekeeper.servername')),
            'ovs':     self.defaultServerName('ovs', serviceObj.hrd.getStr('instance.ovs.servername')),
            'dcpm':    self.defaultServerName('dcpm', serviceObj.hrd.getStr('instance.dcpm.servername')),
            'defense': self.defaultServerName('defense', serviceObj.hrd.getStr('instance.defense.servername')),
            'novnc':   self.defaultServerName('novnc', serviceObj.hrd.getStr('instance.novnc.servername')),
            'grafana': self.grafanaServerName
        }
        
        self.urls = {
            'ovs':     'https://' + self.servers['ovs'],
            'dcpm':    'https://' + self.servers['dcpm'],
            'defense': 'https://' + self.servers['defense'],
            'grafana': 'https://' + self.servers['grafana'],
            'novnc':   'https://' + self.servers['novnc'],
            'safe':    'https://' + self.servers['safe'],
            'oauth':   'https://%s' % (self.host),
            'portal':  'https://%s' % (self.host)
        }
        
        self.network = {
            'gateway': serviceObj.hrd.getStr('instance.publicip.gateway'),
            'start':   serviceObj.hrd.getStr('instance.publicip.start'),
            'end':     serviceObj.hrd.getStr('instance.publicip.end'),
            'netmask': serviceObj.hrd.getStr('instance.publicip.netmask')
        }
        
        self.smtp = {
            'server': serviceObj.hrd.getStr('instance.smtp.server'),
            'port':   serviceObj.hrd.getStr('instance.smtp.port'),
            'login':  serviceObj.hrd.getStr('instance.smtp.login'),
            'passwd': serviceObj.hrd.getStr('instance.smtp.passwd'),
            'sender': serviceObj.hrd.getStr('instance.smtp.sender')
        }
        
        self.machines = {
            'master':    self.getMachineService('ovc_master'),
            'proxy':     self.getMachineService('ovc_proxy'),
            'reflector': self.getMachineService('ovc_reflector'),
            'dcpm':      self.getMachineService('ovc_dcpm')
        }
        
        self.grid = {
            'id': serviceObj.hrd.getInt('instance.grid.id'),
        }
        
        self.ssl = {
            'root':    serviceObj.hrd.getStr('instance.ssl.root'),
            'ovs':     serviceObj.hrd.getStr('instance.ssl.ovs'),
            'novnc':   serviceObj.hrd.getStr('instance.ssl.novnc'),
            'defense': serviceObj.hrd.getStr('instance.ssl.defense'),
        }
        
        print '[+] root domain: %s' % self.rootdomain
        print '[+] environment: %s' % self.rootenv
        print '[+] --------------------------'
        print '[+] oauth   url: %s' % self.urls['oauth']
        print '[+] portal  url: %s' % self.urls['portal']
        print '[+] dcpm    url: %s' % self.urls['dcpm']
        print '[+] ovs     url: %s' % self.urls['ovs']
        print '[+] defense url: %s' % self.urls['defense']
        print '[+] novnc   url: %s' % self.urls['novnc']
        print '[+] grafana url: %s' % self.urls['grafana']
        print '[+] smtp server: %s' % self.smtp['server']
        print '[+] --------------------------'
        print '[+] master   : %s' % self.machines['master']
        print '[+] proxy    : %s' % self.machines['proxy']
        print '[+] reflector: %s' % self.machines['reflector']
        print '[+] dcpm     : %s' % self.machines['dcpm']
        print '[+] --------------------------'
        
        if self.machines['reflector'] == None:
            self.warning('direct access environment, no reflector found')

    def configure(self, serviceObj):
        parent = None
        
        def reflector():
            self.initReflectorVM(self.machines['reflector'], self.repoPath)
        
        if self.machines['reflector']:
            j.actions.start(description='configure reflector', action=reflector, category='openvlcoud', name='configure_reflector', serviceObj=serviceObj)
            
        else:
            # no reflector, setting up bootstrap without it
            self.warning('skipping reflector configuration, setting up bootstrap')
            fakeReflector = {
                'localip': 'not used (no reflector)',
                'publicip': 'not used (no reflector)',
                'publicport': 'not used (no reflector)',
                'service': '', # need to be empty
            }
            self.setupBootstrap(self.repoPath, fakeReflector)
            

        def master():
            self.initMasterVM(self.machines['master'], self.rootpwd, self.network, self.urls, self.repoPath, self.smtp, self.grid)
        
        j.actions.start(description='configure master', action=master, category='openvlcoud', name='configure_master', serviceObj=serviceObj)
        
        def dcpm():
            self.initDCPMVM(self.machines['dcpm'])
        
        j.actions.start(description='configure dcpm', action=dcpm, category='openvlcoud', name='configure_dcpm', serviceObj=serviceObj)
        
        def proxy():
            self.initProxyVM(self.machines['proxy'], self.host, self.servers, self.dcpmPort, self.bootrappIpAddress, self.bootrappPort, self.ssl)
        
        j.actions.start(description='configure proxy', action=proxy, category='openvlcoud', name='configure_proxy', serviceObj=serviceObj)
    
    """
    Console tools
    """
    def enableQuiet(self):
        j.remote.cuisine.api.fabric.state.output['stdout'] = False
        j.remote.cuisine.api.fabric.state.output['running'] = False
    
    def disableQuiet(self):
        j.remote.cuisine.api.fabric.state.output['stdout'] = True
        j.remote.cuisine.api.fabric.state.output['running'] = True
    
    # FIXME: move me
    def info(self, text):
        print '\033[1;36m[*] %s\033[0m' % text
        
    def warning(self, text):
        print '\033[1;33m[-] %s\033[0m' % text

    def success(self, text):
        print '\033[1;32m[+] %s\033[0m' % text
    
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
        remoteHrd  = j.application.getAppInstanceHRD(name='node.ssh', instance=remote)
        remoteHost = remoteHrd.getStr('instance.ip')
        
        remotePath = '/opt/jumpscale7/hrd/apps/%s/service.hrd' % service
        localPath  = '%s/services/jumpscale__%s__%s/%s/' % (self.repoPath, 'node.ssh', remote, service)
        
        print '[+] copy back: %s:%s -> %s' % (remoteHost, remotePath, localPath)
        j.do.execute('scp %s:%s %s' % (remoteHost, remotePath, localPath))

    def setupBootstrap(self, repoPath, reflector):
        print "[+] bootstrap reflector private ip: %s" % reflector['localip']
        print "[+] bootstrap reflector public ip: %s" % reflector['publicip']
        print "[+] bootstrap reflector ssh port: %s" % reflector['publicport']

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
        
        bootrapp = j.atyourservice.remove(name='bootstrapp') # override service
        bootrapp = j.atyourservice.new(name='bootstrapp', args=data)
        bootrapp.install()
    
    def initReflectorVM(self, parent, repoPath):
        self.info('configuring: reflector')
        
        reflector = self.getMachine('ovc_reflector')
        reflector['service'] = 'jumpscale__node.ssh__ovc_reflector'
        
        self.setupBootstrap(repoPath, reflector)

    def initProxyVM(self, parent, host, servers, dcpmPort, bootrappIpAddress, bootrappPort, ssl):
        self.info('configuring: proxy')
        
        proxyip = self.getMachineAddress('ovc_proxy')
        print '[+] ovc_proxy: %s' % proxyip
        
        masterip = self.getMachineAddress('ovc_master')
        print '[+] ovc_master: %s' % masterip
        
        dcpmip = self.getMachineAddress('ovc_dcpm')
        print '[+] ovc_dcpm: %s' % dcpmip
        
        print '[+] master domain: %s' % self.rootdomain

        data = {
            'instance.host': host,
            'instance.domain': self.rootdomain,
            'instance.master.ipadress': masterip,
            'instance.dcpm.ipadress': dcpmip,
            'instance.dcpm.port': dcpmPort,

            'instance.bootstrapp.servername': servers['boot'],
            'instance.ovs.servername': servers['ovs'],
            'instance.defense.servername': servers['defense'],
            'instance.novnc.servername': servers['novnc'],
            'instance.grafana.servername': servers['grafana'],
            'instance.dcpm.servername': servers['dcpm'],
            
            'instance.ssl.root': ssl['root'],
            'instance.ssl.ovs': ssl['ovs'],
            'instance.ssl.novnc': ssl['novnc'],
            'instance.ssl.defense': ssl['defense'],
        }
        
        ssloffloader = j.atyourservice.new(name='ssloffloader', args=data, parent=parent)
        ssloffloader.consume('node', parent.instance)
        ssloffloader.install(deps=True)

    def initMasterVM(self, parent, masterPasswd, network, urls, repoPath, smtp, grid):
        self.info('configuring: master')
        
        print '[+] network: %s -> %s' % (network['start'], network['end'])
        print '[+] gateway: %s, netmask: %s' % (network['gateway'], network['netmask'])
        print '[+] master password: %s' % masterPasswd
        
        data = {
            'instance.param.rootpasswd': masterPasswd,
            'instance.param.publicip.gateway': network['gateway'],
            'instance.param.publicip.netmask': network['netmask'],
            'instance.param.publicip.start': network['start'],
            'instance.param.publicip.end': network['end'],
            'instance.param.dcpm.url': urls['dcpm'],
            'instance.param.ovs.url': urls['ovs'],
            'instance.param.ovc.environment': self.rootenv,
            'instance.param.portal.url': urls['portal'],
            'instance.param.oauth.url': urls['oauth'],
            'instance.param.defense.url': urls['defense'],
            'instance.param.grafana.url': urls['grafana'],
            'instance.param.safekeeper.url': urls['safe'],
            'instance.param.smtp.server': smtp['server'],
            'instance.param.smtp.port': smtp['port'],
            'instance.param.smtp.login': smtp['login'],
            'instance.param.smtp.passwd': smtp['passwd'],
            'instance.param.smtp.sender': smtp['sender'],
            'instance.param.grid.id': grid['id'],
        }
        
        master = j.atyourservice.new(name='cb_master_aio', args=data, parent=parent)
        master.consume('node', parent.instance)
        master.install(deps=True)
        
        # FIXME
        # Copy needed file from master to ovcgit
        # Theses files are generated on the master and not synced back to ovcgit
        self.copyBack('ovc_master', 'jumpscale__oauth_client__oauth')
        self.copyBack('ovc_master', 'jumpscale__portal__main')

    def initDCPMVM(self, parent):
        self.info('configuring: dcpm')
        # Nothing to do now, not used
        return
