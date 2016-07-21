from JumpScale import j
import json
ActionsBase = j.atyourservice.getActionsBaseClass()


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

    # in next version of the service, we have to sandbox openvstorage and don't rely on apt
    DJANGO_SETTINGS = '/opt/OpenvStorage/webapps/api/settings.py'

    def configure(self, serviceObj):
        j.do.execute('''sed -i.bak "s/^ALLOWED_HOSTS.*$/ALLOWED_HOSTS = ['*']/" %s''' % self.DJANGO_SETTINGS)
        
        if serviceObj.hrd.get('instance.oauth.id') != '':
            # setting up ovs.json
            config = None

            with open('/opt/OpenvStorage/config/ovs.json', 'r') as f:
                config = json.load(f)
                
                # oauth2 stuff
                oauth = {
                    'mode': 'remote',
                    'authorize_uri': serviceObj.hrd.get('instance.oauth.authorize_uri'),
                    'token_uri': serviceObj.hrd.get('instance.oauth.token_uri'),
                    'client_id': serviceObj.hrd.get('instance.oauth.id'),
                    'client_secret': serviceObj.hrd.get('instance.oauth.secret'),
                    'scope': 'ovs_admin'
                }
                
                config['webapps']['oauth2'] = oauth
                
                # register stuff
                config['core']['registered'] = True

            with open('/opt/OpenvStorage/config/ovs.json', 'w') as f:
                json.dump(config, f, indent=4)
        
        j.do.execute('restart ovs-webapp-api')
        return True
