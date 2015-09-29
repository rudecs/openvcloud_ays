from JumpScale import j

ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):

    def configure(self, serviceObj):
        privateKey = j.system.fs.fileGetContents("/root/.ssh/id_rsa")
        publicKey = j.system.fs.fileGetContents("/root/.ssh/id_rsa.pub")

        cl = j.tools.ms1.get('$(instance.api.url)', '$(instance.api.port)')
        spaceSecret = cl.getCloudspaceSecret('$(instance.ovc.login)','$(instance.ovc.passwd)','$(instance.ovc.cloudspace)',location='$(instance.ovc.location)')
        id, ip, port = cl.createMachine(spaceSecret, 'master', memsize=2, ssdsize=40, vsansize=0, description='master vm of system space', imagename='ubuntu 14.04 x64', delete=True, sshkey=publicKey, hostname='master')

        data = {
            'instance.key.priv':privateKey,
            'instance.key.pub':publicKey,
        }
        sshkey = j.atyourservice.new(name='sshkey', instance='system_master', args=data)
        sshkey.install()


        obj = cl.getMachineObject(spaceSecret,'master')
        data = {
            'instance.ip': ip,
            'instance.ssh.port': port,
            'instance.jumpscale': False,
            'instance.login': 'root',
            'instance.password':'',  # use key
            'sshkey': 'system_master',
            'ssh.shell': '/bin/bash -l -c'
        }
        node = j.atyourservice.new(name='node.ssh', instance='system_master', args=data)
        node.install()
        ssh = node.actions.getSSHClient(node)
        ssh.ssh_keygen('root', 'rsa')
        masterKey = ssh.file_read('/root/.ssh/id_rsa.pub').strip()

        with ssh.fabric.api.shell_env(JSBRANCH='ays_unstable', AYSBRANCH='ays_unstable'):
            ssh.run('curl https://raw.githubusercontent.com/Jumpscale/jumpscale_core7/master/install/install.sh > /tmp/js7.sh && bash /tmp/js7.sh')

        # authorize the master machine to ssh into the cpu nodes
        for i in range(1, 5):
            name = '%s-%02d' % ('$(instance.ovc.env)', i)
            cpunode = j.atyourservice.findServices(instance=name, name='node.ssh')[0]
            nodeCl = cpunode.actions.getSSHClient(cpunode)
            nodeCl.ssh_authorize('root', key)