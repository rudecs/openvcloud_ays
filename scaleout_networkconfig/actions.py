from JumpScale import j

ActionsBase=j.atyourservice.getActionsBaseClass()

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
        from JumpScale.lib import ovsnetconfig
        import libvirt
        #configure the package
        hrd = serviceObj.hrd

        public_backplane = hrd.get('instance.netconfig.public_backplane.interfacename')
        gw_mgmt_backplane = hrd.get('instance.netconfig.gw_mgmt_backplane.interfacename')
        vxbackend_backplane = hrd.get('instance.netconfig.vxbackend.interfacename')

        gw_mgmt_vlan = hrd.get('instance.netconfig.gw_mgmt.vlanid')
        vxbackend_vlan = hrd.get('instance.netconfig.vxbackend.vlanid')
        public_vlan= hrd.get('instance.netconfig.public.vlanid')

        # removing existings ports and bridge
        ports = j.system.process.execute("ovs-appctl dpif/show | awk '/patch/{print $1}'")[1]
        if ports:
            print("Cleaning openswitch bridges found")
            ports = ports.strip().split("\n")

            for port in ports:
                j.system.process.execute("ovs-vsctl del-port %s" % port)

            for network in ('public', 'vxbackend', 'gw_mgmt'):
                j.system.process.execute("ovs-vsctl del-br %s" % network)

        for network in ('vxbackend', 'gw_mgmt'):
            key = 'instance.netconfig.%s.ipaddr' % network
            if hrd.exists(key):
                ip = hrd.get(key).strip()
                if ip:
                    mtu = None if network != 'vxbackend' else 2000
                    j.system.ovsnetconfig.configureStaticAddress(network, ip, mtu=mtu)

        j.system.ovsnetconfig.newVlanBridge('public', public_backplane, public_vlan)
        j.system.ovsnetconfig.newVlanBridge('gw_mgmt', gw_mgmt_backplane, gw_mgmt_vlan)
        j.system.ovsnetconfig.newVlanBridge('vxbackend', vxbackend_backplane, vxbackend_vlan,mtu=2000)

        publicxml = '''
     <network>
            <name>public</name>
            <forward mode="bridge"/>
            <bridge name='public'/>
            <virtualport type='openvswitch'/>
        </network>'''

        gwmgmtxml = '''
     <network>
            <name>gw_mgmt</name>
            <forward mode="bridge"/>
            <bridge name='gw_mgmt'/>
            <virtualport type='openvswitch'/>
        </network>'''

        mgmtxml = '''
     <network>
            <name>mgmt</name>
            <forward mode="bridge"/>
            <bridge name='backplane1'/>
            <virtualport type='openvswitch'/>
        </network>'''

        conn = libvirt.open()

        networks = conn.listAllNetworks()
        for net in networks:
            if net.isActive() <> 0:
                net.destroy()
            net.undefine()


        public = conn.networkDefineXML(publicxml)
        public.create()
        public.setAutostart(True)

        private = conn.networkDefineXML(gwmgmtxml)
        private.create()
        private.setAutostart(True)


        private = conn.networkDefineXML(mgmtxml)
        private.create()
        private.setAutostart(True)