from JumpScale import j

ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):
    def configure(self, serviceObject):
        roles = j.application.config.getList('grid.node.roles')
        change = False
        for role in ['controller']:
            if role not in roles:
                change = True
                roles.append(role)
        if change:
            j.application.config.set('grid.node.roles', roles)
            j.atyourservice.get(name='jsagent', instance='main').restart()

        def container_check(name):
            import docker
            client = docker.Client()
            for container in client.containers():
                for cname in container['Names']:
                    if cname.lstrip('/') == name:
                        if container['Status'].startswith('Up'):
                            return True
                        else:
                            client.start(container['Id'])
                            return True
            return False

        if not container_check('influxdb'):
            print('Pulling influxdb docker')
            j.system.process.execute('docker run -td -p 8083:8083 -p 8086:8086 -v influxdb:/optvar/data/influxdb --hostname influxdb --name influxdb jumpscale/ubuntu1604_influxdb')
        name = j.system.net.getHostname() + '-jsagent8'
        if not container_check(name):
            j.console.info('Pulling jsagent docker')
            j.system.process.execute('docker run -td -p 9021:22 --name {0} --hostname {0} jumpscale/core:8.1.1'.format(name))
            # start jsagent
            j.console.info('Starting jsagent')
            masteraddr = serviceObject.hrd.get('instance.param.master.addr')
            rootpassword = serviceObject.hrd.get('instance.param.rootpasswd')
            cmd = "j.tools.cuisine.local.apps.jsagent.install(start=True, gid={gid}, ctrl_addr='{masteraddr}', ctrl_port=4444, ctrl_passwd='{password}', reset=False)"
            cmd = cmd.format(gid=j.application.whoAmI.gid, masteraddr=masteraddr, password=rootpassword)
            j.system.process.execute('docker exec {} js "{}"'.format(name, cmd))

            # start pumper
            oknics = ['mgmt', 'pxeboot']

            def getmgmtip():
                netinfo = j.system.net.getNetworkInfo()
                for nic in netinfo:
                    if nic['name'] in oknics:
                        for ip, cidr in zip(nic['ip'], nic['cidr']):
                            return '{}/{}'.format(ip, cidr)

            networkcidr = getmgmtip()
            if networkcidr is None:
                raise RuntimeError("Failed to find network cidr")

            j.console.info('Starting pumper')
            cmd = "j.sal.ubuntu.apt_install('nmap');"
            cmd += "j.tools.cuisine.local.processmanager.ensure('influxdumper', '/opt/code/github/jumpscale/jumpscale_core8/shellcmds/influxdumper --influx-host 172.17.0.1 --scan-cidr {} --workers 40 --redis-port 9999')"
            cmd = cmd.format(networkcidr)
            j.system.process.execute('docker exec {} js "{}"'.format(name, cmd))
            j.console.info('Restarting container')
            j.system.process.execute('docker restart {}'.format(name))
