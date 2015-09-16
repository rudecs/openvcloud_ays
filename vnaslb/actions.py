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
        hrd = j.application.getAppInstanceHRD("arakoon_client", instance)
        arakoon = hrd.getList("instance.cluster")

        vdiskroot = serviceObj.hrd.get("instance.param.vdiskroot")
        cifspath = serviceObj.hrd.get("instance.param.cifspath")
        refresh = serviceObj.hrd.get("instance.param.refresh")
        blockSize = serviceObj.hrd.get("instance.param.blocksize")

        # print '[+] building arakoon config files'

        # config = ConfigParser.RawConfigParser()

        # config.add_section('global')
        # config.set('global', 'cluster_id', hrd.get("instance.clusterid"))
        # config.set('global', 'cluster', hrd.get("instance.cluster"))

        # for node in arakoon:
        #     item = hrd.getDictFromPrefix("instance." + node)

        #     config.add_section(node)
        #     config.set(node, 'ip', item['ip'])
        #     config.set(node, 'client_port', item['client_port'])
        #     config.set(node, 'messaging_port', item['messaging_port'])
        #     config.set(node, 'home', item['home'])
        #     config.set(node, 'log_level', 'info')


        # with open('/tmp/arakoon.ini', 'wb') as configfile:
        #     config.write(configfile)


        print '[+] configuring samba'

        smb = j.ssh.samba.get(j.ssh.connect())
        smb.addShare('vnasfs', cifspath, {'public': 'yes', 'writable': 'yes'})
        smb.commitShare()

        print '[+] building this vnaslb settings'

        """
        !! FIXME !!
        toml = contoml.new()

        # global
        toml['']['ClusterID']  = hrd.get("instance.clusterid")
        toml['']['ClientID']   = "vdisk_client"
        toml['']['VdisksRoot'] = vdiskroot
        toml['']['VdisksMountpoint']  = vdiskmount
        toml['']['CifsMountedVolume'] = cifspath

        # nodes
        for i in range(0, nodes):
            name = 'node%d' % (i + 1)

            toml['Nodes'][name] = {
                'ID': name,
                'Host': address[i],
                'Port': 4000
            }

        # vdisk
        for i in range(0, vdisks):
            diskid = i + 1
            name = 'vdisk%d' % diskid
            toml['vdisks'][name] = {'id':  diskid}

        toml.dump('/tmp/config.toml')
        """

        fn = j.system.fs.joinPaths(serviceObj.hrd.get('service.git.export.1')['dest'], 'config.toml')

        output = StringIO.StringIO()
        output.write('ClusterID = "%s"' % hrd.get("instance.clusterid"))
        output.write('\nClientID = "vdisk_client"')
        output.write('\nVdisksRoot = "%s"' % vdiskroot)
        output.write('\nCifsRoot = "%s"' % cifspath)
        output.write('\nRefresh = %s' % refresh)
        output.write('\nBlockSize = "%s"' % blockSize)
        output.write('\n\n')
        output.write('\n[Nodes]')

        for node in arakoon:
            item = hrd.getDictFromPrefix("instance." + node)

            output.write('\n[Nodes.%s]' % node)
            output.write('\nHost = "%s"' % item['ip'])
            output.write('\nID = "%s"' % node)
            output.write('\nPort = %s' % item['client_port'])

        output.write("\n\n")
        j.system.fs.writeFile(filename=fn, contents=output.getvalue(), append=False)
        output.close()

        print '[+] creating paths'

        if not j.system.fs.exists(vdiskroot):
            j.system.fs.createDir(vdiskroot)

        if not j.system.fs.exists(cifspath):
            j.system.fs.createDir(cifspath)

        return True
