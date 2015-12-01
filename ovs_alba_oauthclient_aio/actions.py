from JumpScale import j
import json
ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):
    def configure(self, serviceObj):
        masterService = j.application.getAppInstanceHRD(name='ovs_setup', instance='main', domain='openvcloud')
        masterNodeName = masterService.getStr('instance.ovs.masternode')
        
        # Building target nodes list
        hosts = ['ovc_master', 'ovc_proxy', 'ovc_reflector', 'ovc_dcpm']
        sshservices = j.atyourservice.findServices(name='node.ssh')
        sshservices.sort(key = lambda x: x.instance)
        nodes = []

        for ns in sshservices:
            if ns.instance not in hosts:
                nodes.append(ns)

        # Grab user access from on node (query ovs)
        masterNode = j.atyourservice.get(name='node.ssh', instance=masterNodeName)
        content = masterNode.execute('python /opt/code/git/0-complexity/openvcloud/scripts/ovs/alba-get-user.py')
        
        user = json.loads(content)
        
        if user.get('error'):
            print '[-] cannot grab credentials: %s' % user['error']
            return False
        
        # Installing service on each nodes
        for node in nodes:
            data = {
                'instance.client_id': user['client'],
                'instance.client_secret': user['secret']
            }
            
            temp = j.atyourservice.new(name='ovs_alba_oauthclient', args=data, parent=node)
            temp.consume('node', node.instance)
            temp.install(deps=True)
        
        return True
