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
        serviceObj.hrd.set("node,tcp.addr",ip)
        serviceObj.hrd.set("ssh.port",port)

        # only do the rest if we want to install jumpscale
        #if serviceObj.hrd.getBool('jumpscale'):
        #    self.installJumpscale(serviceObj)
	return 'nr' # don't restart service after install

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
