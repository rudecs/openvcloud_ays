from JumpScale import j

ActionsBase=j.atyourservice.getActionsBaseClassMgmt()

import JumpScale.lib.ms1

class Actions(ActionsBase):

    def init(self, serviceObj, args):
        """
        will install a node over ssh
        """
        ActionsBase.init(self, serviceObj, args)

        def findDep(depkey):
            if serviceObj.originator is not None and serviceObj.originator._producers != {} and depkey in serviceObj.originator._producers:
                res = serviceObj.originator._producers[depkey]
            elif serviceObj._producers!={} and depkey in serviceObj._producers:
                res = serviceObj._producers[depkey]
            else:
                # we need to check if there is a specific consumption specified, if not check generic one
                res = j.atyourservice.findServices(role=depkey)

            if len(res) == 0:
                # not deployed yet
                j.events.inputerror_critical("Could not find dependency, please install.\nI am %s, I am trying to depend on %s" % (serviceObj, depkey))
            elif len(res) > 1:
                j.events.inputerror_critical("Found more than 1 dependent ays, please specify, cannot fullfil dependency requirement.\nI am %s, I am trying to depend on %s" % (serviceObj, depkey))
            else:
                serv = res[0]
            return serv

        sshkey = findDep('sshkey')
        serviceObj.consume(sshkey)
        args["ssh.key.public"] = sshkey.hrd.get("key.pub")
        serviceObj.consume(findDep('ovc_client'))

    def consume(self, serviceObj, producer):
        if producer.role == 'ovc_client':
            serviceObj.hrd.set('ovc.cloudspace.secret', producer.hrd.getStr('param.secret'))
            serviceObj.hrd.set('ovc.api.url', producer.hrd.getStr('param.apiurl'))

    def getCloudClient(self, serviceObj):
        return j.tools.ms1.get(serviceObj.hrd.get('ovc.api.url'))

    def configure(self, serviceObj):
        """
        create a vm on ms1
        """
        cloudCl = self.getCloudClient(serviceObj)
        spacesecret = serviceObj.hrd.getStr('ovc.cloudspace.secret')
        stackId = serviceObj.hrd.get('stackid', None)
        diskNbr = serviceObj.hrd.getInt('disks.nbr')
        diskSize = serviceObj.hrd.getInt('disks.size')
        delete = serviceObj.hrd.getBool('force')
        disks = [diskSize for _ in range(diskNbr)]
        machineid, ip, port = cloudCl.createMachine(spacesecret, "$(instance)", memsize="$(memsize)", \
            ssdsize='$(ssdsize)', vsansize=0, description='',imagename="$(imagename)",
            delete=delete, sshkey='$(ssh.key.public)', stackId=stackId, datadisks=disks)

        serviceObj.hrd.set("machine.id",machineid)
        serviceObj.hrd.set("node.tcp.addr",ip)
        serviceObj.hrd.set("ssh.port",port)

        cl = self.getSSHClient(serviceObj)
        cl.run("rm -f /root/.ssh/known_hosts")
        cl.run("ssh-keyscan github.com >> /root/.ssh/known_hosts")
        cl.run("ssh-keyscan git.aydo.com >> /root/.ssh/known_hosts")
        cl.run("mkdir -p /etc/ays/local/")

        jsbranch = serviceObj.hrd.get('jumpscale.branch')

        if  serviceObj.hrd.getBool('jumpscale.install',default=False):
            print "apt-get update & upgrade, can take a while"
            cl.run("apt-get update")
            # cl.run("apt-get upgrade -fy")
            cl.run("apt-get install curl tmux git -fy")

            cl.fabric.api.env['shell_env']["JSBRANCH"] = jsbranch
            cl.fabric.api.env['shell_env']["AYSBRANCH"] = jsbranch

            if  serviceObj.hrd.getBool('jumpscale.reset',default=False):
                print "WILL RESET JUMPSCALE"
                cl.run("rm -rf /opt/jumpscale7/hrd/apps")
                cl.run("rm -rf /opt/code/github/jumpscale/jumpscale_core7")
                cl.run("rm -rf /opt/code/github/jumpscale/ays_jumpscale7")

            elif serviceObj.hrd.getBool('jumpscale.update',default=True):
                cl.run("cd /opt/code/github/jumpscale/jumpscale_core7;git pull origin %s"%jsbranch)

            cl.run('git config --global user.name "jumpscale"')
            cl.run('git config --global user.email "jumpscale@fake.com"')

            cl.run("curl https://raw.githubusercontent.com/Jumpscale/jumpscale_core7/%s/install/install.sh > /tmp/js7.sh && bash /tmp/js7.sh" % jsbranch)

        elif serviceObj.hrd.getBool('jumpscale.update',default=False):
            print "update jumpscale (git)"
            cl.run("cd /opt/code/github/jumpscale/jumpscale_core7;git pull origin %s"%jsbranch)

        return 'nr'  # don't restart service after install

    def getSSHClient(self, serviceObj):
        """
        @rvalue ssh client object connected to the node
        """
        ip=serviceObj.hrd.get("node.tcp.addr")
        port=serviceObj.hrd.getInt("ssh.port")
        login = 'root'
        password = ''

        c = j.remote.cuisine
        c.fabric.env['forward_agent'] = True

        if login and login.strip() != '':
            c.fabric.env['user'] = login

        if password and password.strip() != '':
            connection = c.connect(ip, port, passwd=password)
        else:
            connection = c.connect(ip, port)

        return connection

    def removedata(self, serviceObj):
        """
        delete vmachine
        """
        spacesecret = serviceObj.hrd.getStr('ovc.cloudspace.secret')
        cloudCl = self.getCloudClient(serviceObj)
        cloudCl.deleteMachine(spacesecret, "$(name)")

        return True

    def start(self, serviceObj):
        if serviceObj.hrd.get('machine.id', '') != '':
            cloudCl = self.getCloudClient(serviceObj)
            spacesecret = serviceObj.hrd.getStr('ovc.cloudspace.secret')
            cloudCl.startMachine(spacesecret, '$(instance)')

    def stop(self, serviceObj):
        if serviceObj.hrd.get('machine.id') != '':
            cloudCl = self.getCloudClient(serviceObj)
            spacesecret = serviceObj.hrd.getStr('ovc.cloudspace.secret')
            cloudCl.stopMachine(spacesecret, '$(instance)')

    def addDisk(self, serviceObj, name, size, description=None, type='D'):
        if serviceObj.hrd.exists('machine.id') != '':
            cloudCl = self.getCloudClient(serviceObj)
            spacesecret = serviceObj.hrd.getStr('ovc.cloudspace.secret')
            cloudCl.addDisk(spacesecret, '$(instance)', name, size=size, description=description, type=type)
