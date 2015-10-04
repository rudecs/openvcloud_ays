from JumpScale import j
import contoml
import ConfigParser
import StringIO

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

    def configure(self, serviceObj):
        print '[+] loading configuration'

        instance = serviceObj.hrd.get("instance.arakoon.instance")
        arakoonHRD = j.application.getAppInstanceHRD("arakoon_client", instance)
        arakoon = arakoonHRD.getList("instance.cluster")

        vdiskroot = serviceObj.hrd.getStr("instance.param.vdiskroot")
        cifspath = serviceObj.hrd.getStr("instance.param.cifspath")
        refresh = serviceObj.hrd.getInt("instance.param.refresh")
        blockSize = serviceObj.hrd.getInt("instance.param.blocksize")
        timeout = serviceObj.hrd.getInt('instance.param.timeout')

        print '[+] configuring samba'

        smb = j.ssh.samba.get(j.ssh.connect())
        smb.addShare('vnasfs', cifspath, {'public': 'yes', 'writable': 'yes'})
        smb.commitShare()

        print '[+] building this vnaslb settings'

        fn = j.system.fs.joinPaths(serviceObj.hrd.get('service.git.export.1')['dest'], 'config.toml')
        cfg = contoml.new()
        cfg['Gobal'] = {'Debug': False}
        cfg['Fuse'] = {
            'nVdisksRoot': vdiskroot,
            'CifsRoot': cifspath,
            'Refresh': refresh,
            'BlockSize': blockSize,
            'Timeout': timeout,
        }
        cfg['Arakoon'] = {
            'ClientID': arakoonHRD.getStr('instance.clusterid'),
            'ClusterID': arakoonHRD.getStr('instance.clusterid')
        }
        cfg['Arakoon.Nodes'] = {}
        from ipdb import set_trace;set_trace()
        for node in arakoon:
            item = arakoonHRD.get("instance." + node)
            cfg['Arakoon.Nodes.%s' % node] = {
                'ID': node,
                'Host': item['ip'],
                'Port': item['client_port']
            }

        j.system.fs.writeFile(filename=fn, contents=cfg.dumps())

        print '[+] creating paths'

        if not j.system.fs.exists(vdiskroot):
            j.system.fs.createDir(vdiskroot)

        if not j.system.fs.exists(cifspath):
            j.system.fs.createDir(cifspath)

        return True

    def build(self, serviceObj):
        go = j.atyourservice.getService(name='go')
        go.actions.buildProjectGodep(go, 'https://git.aydo.com/0-complexity/vnaslb')
        gopath = go.hrd.getStr('instance.gopath')

        binary = j.system.fs.joinPaths(gopath, 'bin', 'vnaslb')
        dest = '/opt/code/git/binary/vnaslb'
        j.system.fs.createDir(dest)
        j.system.fs.copyFile(binary, dest)