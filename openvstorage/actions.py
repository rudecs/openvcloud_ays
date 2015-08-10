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

    def installOVS(self):
        packages = ['ntp', 'kvm', 'libvirt0', 'python-libvirt', 'virtinst', 'openvstorage-hc']
        j.system.fs.writeFile(filename="/etc/apt/sources.list.d/openvstorage.list", contents="deb http://apt-ovs.cloudfounders.com alpha/", append=False)
        j.system.platform.ubuntu.updatePackageMetadata()
        j.system.platform.ubuntu.install(' '.join(packages))

    def configure(self, serviceObj):

        # choose if master node or extra node install
        if not serviceObj.hrd.getBool('instance.joincluster', True) or \
           serviceObj.hrd.get('instance.masterip') == '':
            # master install
            serviceObj.hrd.set('instance.joinCluster', False)
            serviceObj.hrd.set('instance.masterip', serviceObj.hrd.getStr('instance.targetip'))
            serviceObj.hrd.set('instance.masterpasswd', serviceObj.hrd.getStr('instance.targetpasswd'))
        else:
            # extra node install
            serviceObj.hrd.set('instance.joinCluster', True)

        serviceObj.hrd.save()
        self.installOVS()

        j.system.fs.copyFile("/opt/code/git/binary/openvstorage/openvstorage/openvstorage_preconfig.cfg", "/tmp/openvstorage_preconfig.cfg")
        serviceObj.hrd.applyOnFile("/tmp/openvstorage_preconfig.cfg")

        j.do.execute('''sed -i.bak "s/^ALLOWED_HOSTS.*$/ALLOWED_HOSTS = ['*']/" %s''' % self.DJANGO_SETTINGS)

        try:
            oauthHRD = j.application.getAppInstanceHRD(name='oauthserver', instance='main', domain='')
            oauthURL = oauthHRD.get('instance.oauth.url')
            oauthURL = oauthURL.strip('/')
            authorize_uri = '%s/login/oauth/authorize' % oauthURL
            token_uri = '%s/login/oauth/access_token' % oauthURL

            config = None
            with open('/opt/OpenvStorage/config/ovs.json', 'r') as f:
                config = json.load(f)
                oauth = {
                    'mode': 'remote',
                    'authorize_uri': authorize_uri,
                    'token_uri': token_uri,
                    'client_id': oauthHRD.get('instance.oauth.clients.ovs.id'),
                    'client_secret': oauthHRD.get('instance.oauth.clients.ovs.secret'),
                    'scope': 'ovs_admin'
                }
                config['webapps']['oauth2'] = oauth
            with open('/opt/OpenvStorage/config/ovs.json', 'w') as f:
                json.dump(config, f, indent=4)
        except:
            # oauthserver is not installed, so don't configure oauth in ovs
            pass

        j.do.execute('ovs setup')

        return True
