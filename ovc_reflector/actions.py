from JumpScale import j

ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):

    def configure(self, serviceObj):
        """
        generate SSH key with passphrase for root
        create user guest
        generate SSH key for guest
        """
        rootPath = '/root/.ssh/id_rsa'
        guestPath = '/home/guest/.ssh/id_rsa'

        j.system.platform.ubuntu.generateLocalSSHKeyPair(passphrase='$(instance.root.passphrase)', path=rootPath, type='rsa', overwrite=True)

        j.system.unix.addSystemUser('guest', groupname=None, shell='/bin/bash', homedir=None)
        j.system.platform.ubuntu.generateLocalSSHKeyPair(path=rootPath, type='rsa', overwrite=True)