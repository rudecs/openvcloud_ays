from JumpScale import j

ActionsBase=j.atyourservice.getActionsBaseClassMgmt()

class Actions(ActionsBase):

    def configure(self,serviceObj):
	
	ms1 = j.tools.ms1.get('$(param.apiurl)')
        secret = ms1.getCloudspaceSecret("$(param.login)","$(param.passwd)","$(param.cloudspace)","$(param.location)")

        #this remembers the secret required to use ms1
        serviceObj.hrd.set("param.secret", secret)

        return True

