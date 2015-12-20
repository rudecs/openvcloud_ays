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
            instance = serviceObj.hrd.getStr('instance.ms1_client.connection')
            ms1config = j.application.getAppInstanceHRD(name='ms1_client', instance=instance)
            
            ms1 = {
                'secret': ms1config.getStr('instance.param.secret'),
                'location': ms1config.getStr('instance.param.location'),
                'cloudspace': ms1config.getStr('instance.param.cloudspace')
            }
            
            self.vm = j.clients.vm.get(self.target, ms1)
            """
            self.ms1_spacesecret = ms1clHRD.getStr('instance.param.secret')
            self.ms1_cloudspace  = ms1clHRD.getStr('instance.param.cloudspace')
            self.ms1_baseimage   = 'ubuntu.14.04.x64'
            self.ms1_location    = ms1clHRD.getStr('instance.param.location')
            
            print '[+] loading mothiership1 settings'
            self.ms1_api = j.tools.ms1.get()
            self.ms1_api.setCloudspace(self.ms1_spacesecret, self.ms1_cloudspace, self.ms1_location)
            """

        elif self.target == 'docker':
            docker = {
                'remote': '172.17.0.1',
                'port': '2375',
                'public': '192.168.0.9'
            }
            
            self.vm = j.clients.vm.get(self.target, docker)
            """
            print '[+] loading docker settings'
            self.docker = j.tools.docker
            self.docker.connectRemoteTCP('172.17.0.1', 2375)
            self.dock_baseimage = 'jumpscale/ubuntu1404'
            self.docking = {}
            """
        
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
    Console tools
    """
    """
    def enableQuiet(self, remote=None):
        j.remote.cuisine.api.fabric.state.output['stdout'] = False
        j.remote.cuisine.api.fabric.state.output['running'] = False
        
        if remote:
            remote.fabric.state.output['stdout'] = False
            remote.fabric.state.output['running'] = False
    
    def disableQuiet(self, remote=None):
        j.remote.cuisine.api.fabric.state.output['stdout'] = True
        j.remote.cuisine.api.fabric.state.output['running'] = True
        
        if remote:
            remote.fabric.state.output['stdout'] = True
            remote.fabric.state.output['running'] = True
    """
    
    """
    # FIXME: move me
    def info(self, text):
        print '\033[1;36m[*] %s\033[0m' % text
        
    def warning(self, text):
        print '\033[1;33m[-] %s\033[0m' % text

    def success(self, text):
        print '\033[1;32m[+] %s\033[0m' % text
    """
    
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
    #
    # machine creation
    #
    def _ms1_createMachine(self, hostname, memsize, ssdsize, delete):
        try:
            self.ms1_api.createMachine(self.ms1_spacesecret, hostname, memsize=memsize, ssdsize=ssdsize, imagename=self.ms1_baseimage, sshkey=self.basessh, delete=delete)
        
        except Exception as e:
            if e.message.find('Could not create machine it does already exist') == -1:
                raise e
    
    def _docker_createMachine(self, hostname, memsize):
        self.docking[hostname] = {
            'memsize': memsize,
            'status': 'waiting',
            'ports': []
        }
        
        return self.docking[hostname]
    
    #
    # machine grabber
    #
    def _ms1_getMachine(self, hostname):
        item = self.ms1_api.getMachineObject(self.ms1_spacesecret, hostname)
        ports = self.ms1_api.listPortforwarding(self.ms1_spacesecret, hostname)
        
        for fw in ports:
            if fw['localPort'] == '22':
                sshforward = fw
        
        data = {
            'hostname': item['name'],
            'localport': sshforward['localPort'],
            'localip': str(item['interfaces'][0]['ipAddress']),
            'publicip': sshforward['publicIp'],
            'publicport': str(sshforward['publicPort']),
            'image': item['osImage']
        }
        
        return data
    
    def _docker_getMachine(self, hostname):
        dock = self.docker.client.inspect_container(hostname)
        
        data = {
            'hostname': dock['Config']['Hostname'],
            'localport': 22,
            'localip': dock['NetworkSettings']['IPAddress'],
            'publicip': '192.168.0.9', # FIXME
            'publicport': dock['HostConfig']['PortBindings']['22/tcp'][0]['HostPort'],
            'image': dock['Config']['Image']
        }
        
        return data
    
    #
    # machine commit
    #
    def _docker_commit(self, hostname):
        if self.docking.get(hostname) == None:
            return False
        
        # building exposed ports
        ports = ' '.join(self.docking[hostname]['ports'])
        
        port = self.docker.create(name=hostname, ports=ports, base=self.dock_baseimage, mapping=False)
        return self._docker_getMachine(hostname)
    
    #
    # ports forwarder
    #
    def _ms1_portForward(self, hostname, localport, publicport):
        return self.ms1_api.createTcpPortForwardRule(self.ms1_spacesecret, hostname, localport, pubipport=publicport)
    
    def _docker_portForward(self, hostname, localport, publicport):
        if self.docking.get(hostname) == None:
            raise NameError('Hostname "%s" seems not ready for docker settings' % hostname)
            
        self.docking[hostname]['ports'].append('%s:%s' % (localport, publicport))
        return True
    
    #
    # public interface
    #
    def getMachine(self, hostname):
        print '[+] grabbing settings for: %s' % hostname
        
        if self.target == 'node.ssh':
            return self._ms1_getMachine(hostname)
        
        raise NameError('Target "%s" is not supported' % self.target)
    
    def createMachine(self, hostname, memsize, ssdsize, delete):
        self.info('initializing: %s (RAM: %s GB, Disk: %s GB)' % (hostname, memsize, ssdsize))
        
        if self.target == 'node.ssh':
            return self._ms1_createMachine(hostname, str(memsize), str(ssdsize), delete)
        
        if self.target == 'node.docker':
            return self._docker_createMachine(hostname, memsize)
        
        raise NameError('Target "%s" is not supported' % self.target)
    
    def createPortForward(self, hostname, localport, publicport):
        self.info('port forwarding: %s (%s -> %s)' % (hostname, publicport, localport))
        
        if self.target == 'node.ssh':
            return self._ms1_portForward(hostname, localport, publicport)
        
        if self.target == 'node.docker':
            return self._docker_portForward(hostname, localport, publicport)
        
        raise NameError('Target "%s" is not supported' % self.target)
    
    def commitMachine(self, hostname):
        self.info('commit: %s' % hostname)
        
        if self.target == 'node.ssh':
            return self.getMachine(hostname)
        
        if self.target == 'node.docker':
            return self._docker_commit(hostname)
        
        raise NameError('Target "%s" is not supported' % self.target)
    
    """
    
    
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
