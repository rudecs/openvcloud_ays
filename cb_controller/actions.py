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
        if not container_check('jsagent'):
            print('Pulling jsagent docker')
            j.system.process.execute('docker run -td -p 9022:22 --name jsagent --hostname controller_jsagent8 jumpscale/ubuntu1604_jsagent')
            # update docker
            print('Updating jsagent code')
            j.system.process.execute('docker exec -i jsagent bash -c "cd /opt/code/github/jumpscale/jumpscale_core8; git pull"')

            # start jsagent
            print('Starting jsagent')
            masteraddr = serviceObject.hrd.get('instance.param.master.addr')
            rootpassword = serviceObject.hrd.get('instance.param.rootpasswd')
            cmd = "j.tools.cuisine.local.processmanager.ensure('jsagent', 'jspython jsagent.py --grid-id {gid} --controller-ip {masteraddr} --controller-port 4444 --controller-password {password}', path='/opt/jumpscale8/')"
            cmd = cmd.format(gid=j.application.whoAmI.gid, masteraddr=masteraddr, password=rootpassword)
            j.system.process.execute('docker exec -i jsagent js "{}"'.format(cmd))

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

            print('Starting pumper')
            cmd = "j.tools.cuisine.local.processmanager.ensure('jsagent', '/opt/code/github/jumpscale/jumpscale_core8/shellcmds/influxdumper --influx-host 172.17.0.1 --scan-cidr {} --workers 20 --redis-port 9999')"
            cmd = cmd.format(networkcidr)
            j.system.process.execute('docker exec -i jsagent js "{}"'.format(cmd))
