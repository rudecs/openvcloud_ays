from JumpScale import j
import requests

ActionsBase=j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):

    def configure(self, serviceObj):
        cl = j.remote.cuisine.connect('localhost', 22, '$(instance.passwd)')
        if not j.system.fs.exists(path='/root/.ssh/id_dsa.pub'):
            cl.ssh_keygen('root', keytype='dsa')

        hostname = j.system.net.getHostname()
        data = {
            'key.pub': j.system.fs.fileGetContents('/root/.ssh/id_dsa.pub'),
            'hostname': hostname,
            'login': 'root'
        }

        # make request to the bootstrapp
        resp = requests.post('$(instance.bootstrapp.addr)', json=data)
        if resp.status_code < 200 or resp.status_code > 299:
            msg = resp.json()['error']
            j.events.opserror_critical(msg, category='bootstrap_node')

        data = resp.json()
        cl.ssh_authorize('root', data['master.key'])
        cl.ssh_authorize('root', data['reflector.key'])

        # create reverse tunnel to reflector
        args = {
            'instance.remote.bind': data['reflector.ip.priv'],
            'instance.remote.address': data['reflector.ip.pub'],
            'instance.remote.connection.port': 22,
            'instance.remote.login': data['reflector.user'],
            'instance.remote.port': data['autossh.remote.port'],
            'instance.local.address': 'localhost',
            'instance.local.port': 22}
        autossh = j.atyourservice.new(name='autossh', instance=hostname, args=args)
        autossh.install()