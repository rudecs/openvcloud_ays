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
        print('Pulling influxdb docker')
        j.system.process.execute('docker run -td -p 8083:8083 -p 8086:8086 -v influxdb:/optvar/data/influxdb --name influxdb jumpscale/ubuntu1604_influxdb')
        print('Pulling jsagent docker')
        j.system.process.execute('docker run -td -p 9022:22 --name jsagent jumpscale/ubuntu1604_jsagent')
