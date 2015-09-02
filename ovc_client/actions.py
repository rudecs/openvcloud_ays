from JumpScale import j

ActionsBase=j.atyourservice.getActionsBaseClass()

class Actions(ActionsBase):

    """
    """
    def configure(self,serviceObj):
        """
        configure ms1
        """
        import JumpScale.lib.ms1

        ms1 = j.tools.ms1.get("$(instance.param.apiurl)")

        secret = ms1.getCloudspaceSecret("$(instance.param.login)","$(instance.param.passwd)","$(instance.param.cloudspace)","$(instance.param.location)")

        #this remembers the secret required to use ms1
        serviceObj.hrd.set("instance.param.secret",secret)

        return True

