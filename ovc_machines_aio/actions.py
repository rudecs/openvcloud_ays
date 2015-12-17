from JumpScale import j
import urllib
from StringIO import StringIO
import re

ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):

    def prepare(self, serviceObj):
        self.basessh = '/root/.ssh/id_rsa.pub'
        
        self.host = serviceObj.hrd.getStr('instance.host')

        self.bootstrappPort = serviceObj.hrd.get('instance.bootstrapp.port')
        
        self.rootdomain = 'demo.greenitglobe.com'
        self.rootenv = serviceObj.hrd.getStr('instance.param.main.host')
        self.repoPath = serviceObj.hrd.getStr('instance.param.repo.path')
        
        # FIXME
        self.target = 'node.ssh'
        
        print '[+] root domain: %s' % self.rootdomain
        print '[+] environment: %s' % self.rootenv

    def configure(self, serviceObj):
        ms1Connection = serviceObj.hrd.getStr('instance.ms1_client.connection')
        ms1clHRD = j.application.getAppInstanceHRD(name='ms1_client', instance=ms1Connection)
        
        self.ms1_spacesecret = ms1clHRD.getStr('instance.param.secret')
        self.ms1_cloudspace  = ms1clHRD.getStr('instance.param.cloudspace')
        self.ms1_baseimage   = 'ubuntu.14.04.x64'
        self.ms1_location    = ms1clHRD.getStr('instance.param.location')

        print '[+] loading mothiership1 settings'
        self.ms1_api = j.tools.ms1.get()
        self.ms1_api.setCloudspace(self.ms1_spacesecret, self.ms1_cloudspace, self.ms1_location)
        
        delete = serviceObj.hrd.getBool('instance.param.override')

        def reflector():
            self.initReflectorVM(self.bootstrappPort, self.repoPath, delete=delete)
        
        j.actions.start(description='install reflector vm', action=reflector, category='openvlcoud', name='install_reflector', serviceObj=serviceObj)

        def master():
            self.initMasterVM(self.repoPath, delete=delete)
        
        j.actions.start(description='install master vm', action=master, category='openvlcoud', name='install_master', serviceObj=serviceObj)
        
        def dcpm():
            self.initDCPMVM(self.repoPath, delete=delete)
        
        j.actions.start(description='install dcpm vm', action=dcpm, category='openvlcoud', name='install_dcpm', serviceObj=serviceObj)
        
        def proxy():
            self.initProxyVM(self.repoPath, delete=delete)
        
        j.actions.start(description='install proxy vm', action=proxy, category='openvlcoud', name='install_proxy', serviceObj=serviceObj)
    
    """
    Setup Tools
    """
    def installJumpscale(self, cl):
        # install Jumpscale
        print "[+] installing jumpscale"
        cl.run('curl https://raw.githubusercontent.com/Jumpscale/jumpscale_core7/master/install/install.sh > /tmp/js7.sh && bash /tmp/js7.sh')
        print "[+] jumpscale installed"
        
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
        
        print '[+] updating local /etc/hosts'
        j.system.fs.writeFile('/etc/hosts', ("\n%s\t%s\n" % (address, host)), True)
    
    def nodeInstall(self, hostname, ip, keyInstance):
        print '[+] installing node service: %s, %s' % (hostname, ip)
        
        data = {
            'instance.ip': ip,
            'instance.ssh.port': 22,
            'instance.login': 'root',
            'instance.password': '',
            'instance.sshkey': keyInstance,
            'instance.jumpscale': False,
            'instance.ssh.shell': '/bin/bash -l -c'
        }
        
        j.atyourservice.remove(name=self.target, instance=hostname)
        nodeService = j.atyourservice.new(name=self.target, instance=hostname, args=data)
        nodeService.install(reinstall=True)
    
    def keyInstall(self, hostname):
        data = {
            'instance.key.priv': j.system.fs.fileGetContents('/root/.ssh/id_rsa')
        }
        
        keyService = j.atyourservice.new(name='sshkey', instance=hostname, args=data)
        keyService.install()
        
        return keyService.instance
    
    def sshKeyGrabber(self, remote, keys):
        for source, destination in keys.iteritems():
            print '[+] importing key (%s -> %s)' % (source, destination)
            content = remote.file_read(source)
            j.system.fs.writeFile(filename=destination, contents=content)
            j.system.fs.chmod(destination, 0o600)
        
    def sshKeygen(self, remote, hostname, repo, extrakeys=None):
        print '[+] generating ssh keys'
        
        remote.ssh_keygen('root', keytype='rsa')
        
        keys = {
            '/root/.ssh/id_rsa': '%s/keys/%s_root' % (repo, hostname),
            '/root/.ssh/id_rsa.pub': '%s/keys/%s_root.pub' % (repo, hostname),
        }
        
        if extrakeys is not None:
            keys.update(extrakeys)
        
        self.sshKeyGrabber(remote, keys)
    
    def sshSetup(self, remote):
        print '[+] configuring ssh daemon'
        content = remote.file_read('/etc/ssh/sshd_config')
        
        if content.find('GatewayPorts clientspecified') == -1:
            remote.file_append('/etc/ssh/sshd_config', "\nGatewayPorts clientspecified\n")
            
            print '[+] restarting ssh'
            remote.run('service ssh restart')
    
    def defaultConfig(self, remote, hostname, machinename, localip, repoPath):
        self.setupHost(hostname, localip)
        self.sshKeygen(remote, hostname, repoPath)

        self.installJumpscale(remote)
        self.setupGit(remote)

        keyInstance = self.keyInstall(machinename)
        self.nodeInstall(machinename, localip, keyInstance)
    
    def _ms1_createMachine(self, hostname, memsize, ssdsize, delete):
        try:
            self.ms1_api.createMachine(self.ms1_spacesecret, hostname, memsize=memsize, ssdsize=ssdsize, imagename=self.ms1_baseimage, sshkey=self.basessh, delete=delete)
        
        except Exception as e:
            if e.message.find('Could not create machine it does already exist') == -1:
                raise e
    
    def _ms1_getMachine(self, hostname):
        item = self.ms1_api.getMachineObject(self.ms1_spacesecret, hostname)
        data = {
            'hostname': item['name'],
            'localip': item['interfaces'][0]['ipAddress'],
            'image': item['osImage']
        }
        
        return data
    
    def _ms1_portForward(self, hostname, localport, publicport):
        return self.ms1_api.createTcpPortForwardRule(self.ms1_spacesecret, hostname, localport, pubipport=publicport)
    
    def getMachine(self, hostname):
        print '[+] grabbing settings for: %s' % hostname
        
        # FIXME: check self.target
        return self._ms1_getMachine(hostname)
    
    def createMachine(self, hostname, memsize, ssdsize, delete):
        print '[+] initializing: %s (RAM: %s GB, Disk: %s GB)' % (hostname, memsize, ssdsize)
        
        # FIXME: check self.target
        return self._ms1_createMachine(hostname, str(memsize), str(ssdsize), delete)
    
    def createPortForward(self, hostname, localport, publicport):
        print '[+] port forwarding: %s (%s -> %s)' % (hostname, publicport, localport)
        
        # FIXME: check self.target
        return self._ms1_portForward(hostname, localport, publicport)
        
    """
    Machines settings
    """
    def initReflectorVM(self, bootstrapPort, repoPath, delete=False):
        self.createMachine('ovc_reflector', 0.5, 10, delete)
        machine = self.getMachine('ovc_reflector')
        
        self.createPortForward('ovc_git', bootstrapPort, bootstrapPort)

        cl = j.ssh.connect(machine['localip'], 22, keypath='/root/.ssh/id_rsa')
        
        self.defaultConfig(cl, 'reflector', 'ovc_reflector', machine['localip'], repoPath)
        
        # extra gest user and sshkey
        cl.user_ensure('guest', home='/home/guest', shell='/bin/bash')
        cl.ssh_keygen('guest', keytype='rsa')
        
        extrakeys = {
            '/home/guest/.ssh/id_rsa': '%s/keys/reflector_guest' % repoPath,
            '/home/guest/.ssh/id_rsa.pub': '%s/keys/reflector_guest.pub' % repoPath
        }
        
        self.sshKeyGrabber(cl, extrakeys)

    def initProxyVM(self, repoPath, delete=False):
        self.createMachine('ovc_proxy', 0.5, 10, delete)
        machine = self.getMachine('ovc_proxy')
        
        self.createPortForward('ovc_proxy', 80, 80)
        self.createPortForward('ovc_proxy', 443, 443)
        
        cl = j.ssh.connect(machine['localip'], 22, keypath='/root/.ssh/id_rsa')
        
        self.defaultConfig(cl, 'proxy', 'ovc_proxy', machine['localip'], repoPath)

    def initMasterVM(self, repoPath, delete=False):
        self.createMachine('ovc_master', 4, 40, delete)
        machine = self.getMachine('ovc_master')
        
        self.createPortForward('ovc_master', 4444, 4444)
        self.createPortForward('ovc_master', 5544, 5544)
        self.createPortForward('ovc_master', 8127, 8127)
        
        cl = j.ssh.connect(machine['localip'], 22, keypath='/root/.ssh/id_rsa')
        
        self.defaultConfig(cl, 'master', 'ovc_master', machine['localip'], repoPath)

    def initDCPMVM(self, repoPath, delete=False):
        self.createMachine('ovc_dcpm', 0.5, 10, delete)
        machine = self.getMachine('ovc_dcpm')

        cl = j.ssh.connect(machine['localip'], 22, keypath='/root/.ssh/id_rsa')
        
        self.defaultConfig(cl, 'dcpm', 'ovc_dcpm', machine['localip'], repoPath)
