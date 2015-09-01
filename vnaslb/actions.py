from JumpScale import j
import contoml
import ConfigParser

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
        instance = serviceObj.hrd.get("instance.arakoon.instance")
        hrd = j.application.getAppInstanceHRD("arakoon_client", instance)
        arakoon = hrd.getList("instance.cluster")
        
        # temp = j.clients.arakoon.getByInstance(arakoon)
        
        address = hrd.getList("instance.cluster")
        # current = temp.hrd.get("instance.param.arakoon.this")
        current = 'debug'
        print address
        
        # address = ["1.1.1.1", "2.2.2.2"]
        # current = "1.1.1.1"
        
        nodes = len(address)
        vdisks = int(serviceObj.hrd.get("instance.param.vdisks"))
        
        print '[+] building arakoon config files (node %s)' % current
        
        config = ConfigParser.RawConfigParser()
        
        config.add_section('global')
        config.set('global', 'cluster_id', hrd.get("instance.clusterid"))
        config.set('global', 'cluster', hrd.get("instance.cluster"))

        
        for node in address:
            item = hrd.get("instance." + node)
            
            config.add_section(node)
            config.set(node, 'ip', item['ip'])
            config.set(node, 'client_port', item['client_port'])
            config.set(node, 'messaging_port', item['messaging_port'])
            config.set(node, 'home', item['home'])
            config.set(node, 'log_level', 'info')
            
        
        with open('/tmp/arakoon.ini', 'wb') as configfile:
            config.write(configfile)
        
        print '[+] starting this arakoon node'
        # TODO: Launch Arakoon
        
        # pip install --upgrade contoml
        print '[+] building this vnaslb settings'
        
        vdiskroot  = "/home/ahmedna/vnasstor/vnasdisks/"
        vdiskmount = "/mnt/stor/"
        cifspath   = "/mnt/cifs/vnasgw"
        
        """
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
        
        fn = "/opt/code/git/binary/vnaslb/config.toml"
        
        j.system.fs.writeFile(fn, "ClusterID = \"" + hrd.get("instance.clusterid") + "\"", False)
        j.system.fs.writeFile(fn, "\nClientID = \"vdisk_client\"", True)
        j.system.fs.writeFile(fn, "\nVdisksRoot = \"" + vdiskroot + "\"", True)
        j.system.fs.writeFile(fn, "\nVdisksMountpoint = \"" + vdiskroot + "\"", True)
        j.system.fs.writeFile(fn, "\nCifsMountedVolume = \"" + vdiskmount + "\"", True)
        j.system.fs.writeFile(fn, "\n\n", True)
        j.system.fs.writeFile(fn, "\n[Nodes]", True)
        
        for i in range(0, nodes):
            name = 'node%d' % (i + 1)
            item = hrd.get("instance." + name)
            
            j.system.fs.writeFile(fn, "\n[Nodes." + name + "]", True)
            j.system.fs.writeFile(fn, "\nHost = \"" + item['ip'] + "\"", True)
            j.system.fs.writeFile(fn, "\nID = \"" + name + "\"", True)
            j.system.fs.writeFile(fn, "\nPort = 4000", True)
            
        j.system.fs.writeFile(fn, "\n\n", True)
        j.system.fs.writeFile(fn, "\n[vdisks]", True)
        
        for i in range(0, vdisks):
            diskid = i + 1
            name = 'vdisk%d' % diskid
            
            j.system.fs.writeFile(fn, "\n[vdisks." + name + "]", True)
            j.system.fs.writeFile(fn, "\nid = " + `diskid`, True)
        
        j.system.fs.writeFile(fn, "\n\n", True)
            
        return True
