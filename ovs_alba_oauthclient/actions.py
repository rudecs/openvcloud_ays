from JumpScale import j
import json
ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):
    def configure(self, serviceObj):
        masterService = j.application.getAppInstanceHRD(name='ovs_setup', instance='main', domain='openvcloud')
        masterNodeName = masterService.getStr('instance.ovs.masternode')
        
        masterNode = j.atyourservice.get(name='node.ssh', instance=masterNodeName)
        content = masterNode.execute('python /opt/code/git/0-complexity/openvcloud/scripts/ovs/alba-get-user.py')
        
        user = json.loads(content)
        
        if user.get('error'):
            print '[-] cannot grab credentials: %s' % user['error']
            return False
        
        serviceObj.hrd.set('instance.client_id', user['client'])
        serviceObj.hrd.set('instance.client_secret', user['secret'])
        
        return True
