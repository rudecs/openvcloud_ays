from JumpScale import j
import requests

ActionsBase=j.atyourservice.getActionsBaseClass()


class Actions(ActionsBase):

    def configure(self, serviceObj):
        keyapth = '/root/.ssh/id_rsa'
        if not j.system.fs.exists(path=keyapth):
            j.system.platform.ubuntu.generateLocalSSHKeyPair(passphrase='', type='rsa', overwrite=False, path=keyapth)

        hostname = j.system.net.getHostname()
        data = {
            'key.pub': j.system.fs.fileGetContents(keyapth+'.pub'),
            'hostname': hostname,
            'login': 'root',
            'nid': serviceObj.hrd.getInt('instance.node.id')
        }

        # make request to the bootstrapp
        resp = requests.post('$(instance.bootstrapp.addr)', json=data)
        if resp.status_code < 200 or resp.status_code > 299:
            msg = resp.json()['message']
            j.events.opserror_critical(msg, category='bootstrap_node')

        data = resp.json()
        j.system.fs.writeFile('/root/.ssh/authorized_keys', '\n'+data['master.key'], append=True)
        j.system.fs.writeFile('/root/.ssh/authorized_keys', '\n'+data['git.key'], append=True)
        
        # if we don't have remote port, we don't need ssh tunnel
        # we skip autossh install
        if data['autossh.remote.port'] == 0:
            return True

        # create reverse tunnel to reflector
        args = {
            'instance.remote.bind': data['reflector.ip.priv'],
            'instance.remote.address': data['reflector.ip.pub'],
            'instance.remote.connection.port': data['reflector.port'],
            'instance.remote.login': data['reflector.user'],
            'instance.remote.port': data['autossh.remote.port'],
            'instance.local.address': 'localhost',
            'instance.local.port': 22}
        autossh = j.atyourservice.new(name='autossh', instance=hostname, args=args)
        autossh.install()
