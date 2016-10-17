from JumpScale import j
import os, base64
import json

ActionsBase=j.atyourservice.getActionsBaseClass()

class Actions(ActionsBase):
    """
    process for install
    -------------------
    step1: prepare actions
    step2: check_requirements action
    step3: download files & copy on right location (hrd info is used)
    step4: configure action
    step5: check_uptime_local to see if process stops  (uses timeout $process.stop.timeout)
    step5b: if check uptime was true will do stop action and retry the check_uptime_local check
    step5c: if check uptime was true even after stop will do halt action and retry the check_uptime_local check
    step6: use the info in the hrd to start the application
    step7: do check_uptime_local to see if process starts
    step7b: do monitor_local to see if package healthy installed & running
    step7c: do monitor_remote to see if package healthy installed & running, but this time test is done from central location
    """

    def prepare(self,serviceObj):
        return True

    def configure(self, serviceObj):
        docker = j.tools.docker
        docker.connectRemoteTCP('172.17.0.1', 2375) # FIXME

        source = '/opt/jumpscale7/var/lib/dockers/openvcloud/'
        image = serviceObj.hrd.get('instance.image.name')

        jsbranch = j.clients.git.get('/opt/code/github/jumpscale7/jumpscale_core7').getBranchOrTag()[1]
        aysbranch = j.clients.git.get('/opt/code/github/jumpscale7/ays_jumpscale7').getBranchOrTag()[1]
        ovcbranch = j.clients.git.get('/opt/code/github/0-complexity/openvcloud').getBranchOrTag()[1]

        print '[+] jumpscale branch : %s' % jsbranch
        print '[+] ays repo branch  : %s' % aysbranch
        print '[+] openvcloud branch: %s' % ovcbranch

        # setting hrd info
        serviceObj.hrd.set('instance.jsbranch', jsbranch)
        serviceObj.hrd.set('instance.aysbranch', aysbranch)
        serviceObj.hrd.set('instance.ovcbranch', ovcbranch)

        print '[+] patching docker file'
        serviceObj.hrd.applyOnFile("%s/buildconfig" % source)

        print '[+] source: %s' % source
        print '[+] building the image: %s' % image
        response = [line for line in docker.client.build(source, image)]

        lastline = response.pop()
        stream = json.loads(lastline)

        if stream.get('errorDetail'):
            raise RuntimeError(response)

        status = stream['stream'].replace('\n', '')

        print '[+] %s' % status

        return True
