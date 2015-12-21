from JumpScale import j
import urllib
from StringIO import StringIO
import re

ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):
    def prepare(self, serviceObj):        
        self.host = serviceObj.hrd.getStr('instance.host')

        self.bootstrappPort = serviceObj.hrd.get('instance.bootstrapp.port')
        
        self.rootdomain = 'demo.greenitglobe.com'
        self.rootenv = serviceObj.hrd.getStr('instance.param.main.host')
        self.repoPath = serviceObj.hrd.getStr('instance.param.repo.path')
        self.quiet = serviceObj.hrd.getBool('instance.param.quiet')
        
        # default to docker
        self.target = 'docker'
        self.vm = None
        
        clients = j.atyourservice.findServices(name='ms1_client', instance='main')
        if len(clients) > 0:
            self.target = 'ms1'
        
        print '[+] root domain: %s' % self.rootdomain
        print '[+] environment: %s' % self.rootenv
        print '[+] target node: %s' % self.target

    def configure(self, serviceObj):
        if self.target == 'ms1':
            ms1config = j.application.getAppInstanceHRD(name='ms1_client', instance='main')
            
            ms1 = {
                'secret': ms1config.getStr('instance.param.secret'),
                'location': ms1config.getStr('instance.param.location'),
                'cloudspace': ms1config.getStr('instance.param.cloudspace')
            }
            
            self.vm = j.clients.vm.get(self.target, ms1)

        elif self.target == 'docker':
            dockconfig = j.application.getAppInstanceHRD(name='docker_client', instance='main')
            
            docker = {
                'remote': dockconfig.getStr('instance.remote.host'),
                'port': dockconfig.getStr('instance.remote.port'),
                'public': dockconfig.getStr('instance.public.address'),
            }
            
            self.vm = j.clients.vm.get(self.target, docker)
        
        else:
            raise NameError('Target "%s" is not supported' % self.target)
        
        delete = serviceObj.hrd.getBool('instance.param.override')
        
        if self.quiet:
            self.vm.enableQuiet()

        def reflector():
            self.initReflectorVM(self.bootstrappPort, self.repoPath, delete=delete)
        
        j.actions.start(description='install reflector vm', action=reflector, category='openvlcoud', name='install_reflector', serviceObj=serviceObj)
        self.vm.success('reflector spawned')

        def master():
            self.initMasterVM(self.repoPath, delete=delete)
        
        j.actions.start(description='install master vm', action=master, category='openvlcoud', name='install_master', serviceObj=serviceObj)
        self.vm.success('master spawned')
        
        def proxy():
            self.initProxyVM(self.repoPath, delete=delete)
        
        j.actions.start(description='install proxy vm', action=proxy, category='openvlcoud', name='install_proxy', serviceObj=serviceObj)
        self.vm.success('proxy spawned')
        
        def dcpm():
            self.initDCPMVM(self.repoPath, delete=delete)
        
        j.actions.start(description='install dcpm vm', action=dcpm, category='openvlcoud', name='install_dcpm', serviceObj=serviceObj)
        self.vm.success('dcpm spawned')
    
    """
    Setup tools
    """
    def installJumpscale(self, cl):
        cl.run('curl https://raw.githubusercontent.com/Jumpscale/jumpscale_core7/master/install/install.sh > /tmp/js7.sh && bash /tmp/js7.sh')
        
    def setupGit(self, cl):
        cl.run('jsconfig hrdset -n whoami.git.login -v "ssh"')
        cl.run('jsconfig hrdset -n whoami.git.passwd -v "ssh"')
        
        allowhosts = ["github.com", "git.aydo.com"]
            
        for host in allowhosts:
            cl.run('echo "Host %s" >> /root/.ssh/config' % host)
            cl.run('echo "    StrictHostKeyChecking no" >> /root/.ssh/config')
            cl.run('echo "" >> /root/.ssh/config')
    
    def setupHost(self, host, address):
        hosts = StringIO('\n'.join(line.strip() for line in open('/etc/hosts'))).getvalue()
        
        # removing existing host
        hosts = re.sub(r'.*\t%s' % host, '', hosts)
        hosts = re.sub(r'\n\n', '\n', hosts)
        j.system.fs.writeFile('/etc/hosts', hosts, False)
        
        self.vm.message('updating local /etc/hosts')
        j.system.fs.writeFile('/etc/hosts', ("\n%s\t%s\n" % (address, host)), True)
    
    def nodeInstall(self, hostname, network, keyInstance):
        self.vm.message('installing node service: %s, %s' % (hostname, network['localip']))
        
        data = {
            'instance.ip': network['localip'],
            'instance.ssh.port': network['localport'],
            'instance.publicip': network['publicip'],
            'instance.ssh.publicport': network['publicport'],
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': keyInstance,
            'instance.jumpscale': False,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        
        j.atyourservice.remove(name='node.ssh', instance=hostname)
        nodeService = j.atyourservice.new(name='node.ssh', instance=hostname, args=data)
        nodeService.install(reinstall=True)
        
        return nodeService
    
    def keyInstall(self, hostname):
        data = {
            'instance.key.priv': j.system.fs.fileGetContents('/root/.ssh/id_rsa')
        }
        
        keyService = j.atyourservice.new(name='sshkey', instance=hostname, args=data)
        keyService.install()
        
        return keyService.instance
    
    def sshKeyGrabber(self, remote, keys):
        for source, destination in keys.iteritems():
            self.vm.message('importing key (%s -> %s)' % (source, destination))
            content = remote.file_read(source)
            j.system.fs.writeFile(filename=destination, contents=content)
            j.system.fs.chmod(destination, 0o600)
        
    def sshKeygen(self, remote, hostname, repo, extrakeys=None):
        remote.ssh_keygen('root', keytype='rsa')
        
        keys = {
            '/root/.ssh/id_rsa': '%s/keys/%s_root' % (repo, hostname),
            '/root/.ssh/id_rsa.pub': '%s/keys/%s_root.pub' % (repo, hostname),
        }
        
        if extrakeys is not None:
            keys.update(extrakeys)
        
        self.sshKeyGrabber(remote, keys)
    
    def sshSetup(self, remote):
        self.vm.message('configuring ssh daemon')
        content = remote.file_read('/etc/ssh/sshd_config')
        
        if content.find('GatewayPorts clientspecified') == -1:
            remote.file_append('/etc/ssh/sshd_config', "\nGatewayPorts clientspecified\n")
            
            self.vm.message('restarting ssh')
            remote.run('service ssh restart')
    
    def defaultConfig(self, remote, hostname, machinename, network, repoPath):
        if self.quiet:
            self.vm.enableQuiet(remote)
        
        self.vm.message('setting up host configuration')
        self.setupHost(hostname, network['localip'])
        
        self.vm.message('generating ssh keys')
        self.sshKeygen(remote, hostname, repoPath)

        self.vm.message('installing jumpscale')
        self.installJumpscale(remote)
        
        self.vm.message('setting up git credentials')
        self.setupGit(remote)

        self.vm.message('initializing node sshkey')
        keyInstance = self.keyInstall(machinename)
        service = self.nodeInstall(machinename, network, keyInstance)
        
        return service    
    
    """
    Machines settings
    """
    def initReflectorVM(self, bootstrapPort, repoPath, delete=False):
        self.vm.createMachine('ovc_reflector', 0.5, 10, delete)
        self.vm.createPortForward('ovc_reflector', bootstrapPort, bootstrapPort)
        machine = self.vm.commitMachine('ovc_reflector')        

        cl = j.ssh.connect(machine['localip'], 22, keypath='/root/.ssh/id_rsa')
        
        self.defaultConfig(cl, 'reflector', 'ovc_reflector', machine, repoPath)
        
        # extra gest user and sshkey
        cl.user_ensure('guest', home='/home/guest', shell='/bin/bash')
        cl.ssh_keygen('guest', keytype='rsa')
        
        extrakeys = {
            '/home/guest/.ssh/id_rsa': '%s/keys/reflector_guest' % repoPath,
            '/home/guest/.ssh/id_rsa.pub': '%s/keys/reflector_guest.pub' % repoPath
        }
        
        self.sshKeyGrabber(cl, extrakeys)

    def initProxyVM(self, repoPath, delete=False):
        self.vm.createMachine('ovc_proxy', 0.5, 10, delete)
        self.vm.createPortForward('ovc_proxy', 80, 80)
        self.vm.createPortForward('ovc_proxy', 443, 443)
        machine = self.vm.commitMachine('ovc_proxy')
        
        cl = j.ssh.connect(machine['localip'], 22, keypath='/root/.ssh/id_rsa')
        
        self.defaultConfig(cl, 'proxy', 'ovc_proxy', machine, repoPath)

    def initMasterVM(self, repoPath, delete=False):
        self.vm.createMachine('ovc_master', 4, 40, delete)
        self.vm.createPortForward('ovc_master', 4444, 4444)
        self.vm.createPortForward('ovc_master', 5544, 5544)
        self.vm.createPortForward('ovc_master', 8127, 8127)
        machine = self.vm.commitMachine('ovc_master')
        
        cl = j.ssh.connect(machine['localip'], 22, keypath='/root/.ssh/id_rsa')
        
        self.defaultConfig(cl, 'master', 'ovc_master', machine, repoPath)

    def initDCPMVM(self, repoPath, delete=False):
        self.vm.createMachine('ovc_dcpm', 0.5, 10, delete)
        machine = self.vm.commitMachine('ovc_dcpm')

        cl = j.ssh.connect(machine['localip'], 22, keypath='/root/.ssh/id_rsa')
        
        self.defaultConfig(cl, 'dcpm', 'ovc_dcpm', machine, repoPath)
