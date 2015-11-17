from JumpScale import j
from ConfigParser import SafeConfigParser
import cStringIO as StringIO

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

    def configure(self, serviceObj):
        import JumpScale.grid
        import JumpScale.portal
        # set billing role
        roles = j.application.config.getList('grid.node.roles')
        ovcEnvironment = serviceObj.hrd.get('instance.param.ovc.environment')
        if 'billing' not in roles:
            roles.append('billing')
            j.application.config.set('grid.node.roles', roles)
            j.atyourservice.get(name='jsagent', instance='main').restart()

        # set navigation
        portal = j.atyourservice.get(name='portal', instance='main')
        portal.stop()
        portalurl = serviceObj.hrd.get('instance.param.portal.url')
        portallinks = {
                'ays': {
                    'name': 'At Your Service',
                    'url': '/AYS',
                    'scope': 'admin',
                    'theme': 'light',
                    },
                'wiki_gcb': {
                    'name': 'End User',
                    'url': portalurl,
                    'scope': 'user',
                    'theme': 'dark',
                    'external': 'false'},
                'ovs': {
                    'name': 'Storage',
                    'url': serviceObj.hrd.get('instance.param.ovs.url'),
                    'scope': 'ovs_admin',
                    'theme': 'light',
                    'external': 'true'},
                'grafana': {
                    'name': 'Statistics',
                    'url': '/grafana',
                    'scope': 'admin',
                    'theme': 'light',
                    'external': 'true'},
                'dcpm': {
                    'name': 'Power Management',
                    'url': serviceObj.hrd.get('instance.param.dcpm.url'),
                    'scope': 'dcpm_admin',
                    'theme': 'light',
                    'external': 'true'},
                'grid': {
                    'name': 'Grid',
                    'url': '/grid',
                    'scope': 'admin',
                    'theme': 'light'},
                'system': {
                    'name': 'System',
                    'url': '/system',
                    'scope': 'admin',
                    'theme': 'light'},
                'cbgrid': {
                    'name': 'Cloud Broker',
                    'url': '/cbgrid',
                    'scope': 'admin',
                    'theme': 'light'},
                }
        for linkid, data in portallinks.iteritems():
            if data['url']:
                portal.hrd.set('instance.navigationlinks.%s' % linkid, data)
        portal.hrd.set('instance.param.cfg.defaultspace', 'wiki_gcb')
        portal.start()

        ccl = j.clients.osis.getNamespace('cloudbroker')
        scl = j.clients.osis.getNamespace('system')

        # setup user/groups
        for groupname in ('user', 'ovs_admin'):
            if not scl.group.search({'id': groupname})[0]:
                group = scl.group.new()
                group.gid = j.application.whoAmI.gid
                group.id = groupname
                group.users = ['admin']
                scl.group.set(group)

        # set location
        if not ccl.location.search({'gid': j.application.whoAmI.gid})[0]:
            loc = ccl.location.new()
            loc.gid = j.application.whoAmI.gid
            loc.name = ovcEnvironment
            loc.flag = 'black'
            loc.locationCode = ovcEnvironment
            ccl.location.set(loc)
        # set grid
        if not scl.grid.exists(j.application.whoAmI.gid):
            grid = scl.grid.new()
            grid.id = j.application.whoAmI.gid
            grid.name = ovcEnvironment
            scl.grid.set(grid)

        j.clients.portal.getByInstance('main')

        # register networks
        start = 201
        end = 250
        j.apps.libcloud.libvirt.registerNetworkIdRange(j.application.whoAmI.gid, start,end)
        # sync images
        j.apps.cloudbroker.iaas.syncAvailableImagesToCloudbroker()
        j.apps.cloudbroker.iaas.syncAvailableSizesToCloudbroker()
        # register public ips
        import netaddr
        netmask = serviceObj.hrd.get('instance.param.publicip.netmask')
        start = serviceObj.hrd.get('instance.param.publicip.start')
        end = serviceObj.hrd.get('instance.param.publicip.end')
        gateway = serviceObj.hrd.get('instance.param.publicip.gateway')
        netip = netaddr.IPNetwork('%s/%s' % (gateway, netmask))
        network = str(netip.cidr)
        if not ccl.publicipv4pool.exists(network):
            pool = ccl.publicipv4pool.new()
            pool.gid = j.application.whoAmI.gid
            pool.id = network
            pool.subnetmask = netmask
            pool.gateway = gateway
            pubips = [ str(ip) for ip in netaddr.IPRange(start, end) ]
            pool.pubips = pubips
            pool.network = str(netip.network)
            ccl.publicipv4pool.set(pool)

        oauthServerHRD = j.atyourservice.get(name='oauthserver').hrd
        oauthClientHRD = j.atyourservice.get(name='oauth_client').hrd
        portalSecret = oauthServerHRD.get('instance.oauth.clients.portal.secret')
        oauthClientHRD.set('instance.oauth.client.secret', portalSecret)

        #configure grafana for oauth
        grafana = j.atyourservice.get(name='grafana')
        grafanaSecret = oauthServerHRD.get('instance.oauth.clients.grafana.secret')
        grafana.stop()
        cfgfile = '/opt/grafana/conf/defaults.ini'
        cfgcontent = j.system.fs.fileGetContents(cfgfile)
        fp = StringIO.StringIO('[global]\n' + cfgcontent)
        parser = SafeConfigParser()
        parser.readfp(fp)
        parser.set('server', 'root_url', '%s/grafana' % portalurl)
        parser.set('users', 'auto_assign_org_role', 'Editor')
        parser.set('auth.github', 'enabled', 'true')
        parser.set('auth.github', 'allow_sign_up', 'true')
        parser.set('auth.github', 'client_id', 'grafana')
        parser.set('auth.github', 'client_secret', grafanaSecret)
        parser.set('auth.github', 'scopes', 'admin')
        parser.set('auth.github', 'auth_url', '%s/login/oauth/authorize' % portalurl)
        parser.set('auth.github', 'token_url', 'http://127.0.0.1:8010/login/oauth/access_token')
        parser.set('auth.github', 'api_url', 'http://127.0.0.1:8010/user')

        fpout = StringIO.StringIO()
        parser.write(fpout)
        content = fpout.getvalue().replace('[global]', '')
        j.system.fs.writeFile(cfgfile, content)
        grafana.start()


