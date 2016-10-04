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
            j.system.process.execute('docker run -td -p 8083:8083 -p 8086:8086 -v influxdb:/optvar/data/influxdb --name influxdb jumpscale/ubuntu1604_influxdb')
        if not container_check('jsagent'):
            print('Pulling jsagent docker')
            j.system.process.execute('docker run -td -p 9022:22 --name jsagent jumpscale/ubuntu1604_jsagent')
