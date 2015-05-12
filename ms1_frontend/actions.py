from JumpScale import j

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
        """
        this gets executed before the files are downloaded & installed on appropriate spots
        """
        dest="$(system.paths.base)/apps/portals/$(instance.portal.instance)"
        if not j.system.fs.exists(dest):
            j.events.inputerror_critical("Could not find portal instance with name: $(instance.portal.instance), please install")
        return True

    def configure(self, serviceObj):
        service = j.atyourservice.findServices('jumpscale', 'portal', 'main')[0]
        service.restart()

        nginxcfg = '''
server {
    listen 80 default_server;
    gzip on;
    gzip_static always;

    location / {
        proxy_pass http://127.0.0.1:82;
        proxy_set_header        X-Real-IP       $remote_addr;
    }

    location ~ /rest(ext|extmachine|machine)*/libcloud {
        return 404;
    }

    location /jslib {
        expires 5m;
        add_header Pragma public;
        add_header Cache-Control "public, must-revalidate, proxy-revalidate";
        rewrite /jslib/(.*) /$1 break;
        root $(system.paths.base)/apps/portals/jslib/;
    }


    location /wiki_gcb/.files {
        expires 5m;
        add_header Pragma public;
        add_header Cache-Control "public, must-revalidate, proxy-revalidate";
        rewrite /wiki_gcb/.files/(.*) /$1 break;
        root $(system.paths.base)/apps/portals/main/base/wiki_gcb/.files/;
    }

}
        '''
        j.system.fs.createDir('/opt/nginx/cfg/sites-enabled')
        j.system.fs.writeFile('/opt/nginx/cfg/sites-enabled/ms1_fe', nginxcfg)

        service = j.atyourservice.findServices('jumpscale', 'nginx', 'main')[0]
        service.restart()