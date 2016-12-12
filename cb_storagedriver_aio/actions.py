from JumpScale import j

ActionsBase = j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):

    def configure(self, serviceObject):
        roles = j.application.config.getList('grid.node.roles')
        change = False
        storageroles = ['storagedriver']
        if 'MASTER' in j.system.process.execute('ovs config get "ovs/framework/hosts/$(cat /etc/openvstorage_id)/type"')[1]:
            storageroles.append('storagemaster')
        for role in storageroles:
            if role not in roles:
                change = True
                roles.append(role)
        if change:
            j.application.config.set('grid.node.roles', roles)
            j.atyourservice.get(name='jsagent', instance='main').restart()

        j.atyourservice.get(name='nginx').restart()
