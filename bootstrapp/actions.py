from JumpScale import j
import requests

ActionsBase=j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):

    def prepare(self, serviceObj):
        path = '$(system.paths.base)/apps/bootstrapp'
        if not j.system.fs.exists(path=path):
            j.system.fs.createDir(path)

    def configure(self, serviceObj):
        ps = serviceObj.hrd.getDictFromPrefix('service.process')['1']
        args2 = ps['args']
        args2 = '--gitpath $(instance.ovc_git) --hrd %s' % serviceObj.hrd.path
        ps['args'] = args2
        serviceObj.hrd.save()
