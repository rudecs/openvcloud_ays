from JumpScale import j

ActionsBase=j.atyourservice.getActionsBaseClass()

import JumpScale.lib.ms1
import JumpScale.baselib.remote.cuisine
from JumpScale.baselib.atyourservice.ActionsBaseNode import ActionsBaseNode

class Actions(ActionsBaseNode):

    def _getSpaceSecret(self, serviceObj):
        ovsClientHRD = j.application.getAppInstanceHRD(domain='openvcloud', name="ovc_client", instance="$(instance.ovc.connection)")
        spacesecret = ovsClientHRD.get("instance.param.secret", '')
        if True or spacesecret == '':
            ms1Service = j.atyourservice.get(name='ovc_client', instance="$(instance.ovc.connection)")
            ms1Service.configure()
            spacesecret = ms1Service.hrd.get("instance.param.secret")
            if spacesecret == '':
                j.events.opserror_critical('impossible to retreive ms1 space secret', category='atyourservice')
        return spacesecret

    def getCoudClient(self):
        ovsClientHRD = j.application.getAppInstanceHRD(domain='openvcloud', name="ovc_client", instance="$(instance.ovc.connection)")
        return j.tools.ms1.get(ovsClientHRD.get('instance.param.apiurl'))

    def configure(self, serviceObj):
        """
        create a vm on ms1
        """
        def createmachine():
            cloudCl = self.getCoudClient()
            spacesecret = self._getSpaceSecret(serviceObj)
            _, sshkey = self.getSSHKey(serviceObj)
            stackId = serviceObj.hrd.get('instance.stackid', None)
            machineid, ip, port = cloudCl.createMachine(spacesecret, "$(instance.name)", memsize="$(instance.memsize)", \
                ssdsize=$(instance.ssdsize), vsansize=0, description='',imagename="$(instance.imagename)",
                delete=False, sshkey=sshkey, stackId=stackId)

            serviceObj.hrd.set("instance.machine.id",machineid)
            serviceObj.hrd.set("instance.ip",ip)
            serviceObj.hrd.set("instance.ssh.port",port)

        j.actions.start(retry=1, name="createmachine", description='createmachine', cmds='', action=createmachine, \
                        actionRecover=None, actionArgs={}, errorMessage='', die=True, stdOutput=True, serviceObj=serviceObj)

        # only do the rest if we want to install jumpscale
        if serviceObj.hrd.getBool('instance.jumpscale'):
            self.installJumpscale(serviceObj)

    def removedata(self, serviceObj):
        """
        delete vmachine
        """
        ovsClientHRD = j.application.getAppInstanceHRD("ovc_client","$(instance.ovc.connection)")
        spacesecret = ovsClientHRD.get("instance.param.secret")
        cloudCl = self.getCoudClient()
        cloudCl.deleteMachine(spacesecret, "$(instance.name)")

        return True

    def start(self, serviceObj):
        if serviceObj.hrd.get('instance.machine.id', '') != '':
            cloudCl = self.getCoudClient()
            spacesecret = self._getSpaceSecret(serviceObj)
            cloudCl.startMachine(spacesecret, serviceObj.hrd.getStr('instance.name'))

    def stop(self, serviceObj):
        if serviceObj.hrd.get('instance.machine.id') != '':
            cloudCl = self.getCoudClient()
            spacesecret = self._getSpaceSecret(serviceObj)
            cloudCl.stopMachine(spacesecret, serviceObj.hrd.getStr('instance.name'))

    def addDisk(self, serviceObj, name, size, description=None, type='D'):
        if serviceObj.hrd.exists('instance.machine.id') != '':
            vmName = serviceObj.hrd.getStr('instance.name')
            cloudCl = self.getCoudClient()
            spacesecret = self._getSpaceSecret(serviceObj)
            cloudCl.addDisk(spacesecret, vmName, name, size=size, description=description, type=type)