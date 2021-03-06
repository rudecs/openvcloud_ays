from JumpScale import j

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
        from JumpScale.lib import ovsnetconfig
        import libvirt
        # configure the package

        basenetwork = j.atyourservice.findServices('openvcloud', 'basenetwork')[0]
        # basenetwork = jpd.getInstance('main')
        hrd = basenetwork.hrd

        vxbackend_backplane = hrd.get('instance.netconfig.vxbackend.interfacename')

        vxbackend_vlan = hrd.get('instance.netconfig.vxbackend.vlanid')

        for network in ('mgmt', 'vxbackend', 'gw_mgmt'):
            key = 'instance.netconfig.%s.ipaddr' % network
            if hrd.exists(key):
                ip = hrd.get(key).strip()
                if ip:
                    j.system.ovsnetconfig.configureStaticAddress(network, ip)

        j.system.ovsnetconfig.newBridge('gw_mgmt')
        j.system.ovsnetconfig.newVlanBridge('vxbackend', vxbackend_backplane, vxbackend_vlan, mtu=2000)

        gwmgmtxml = '''
     <network>
            <name>gw_mgmt</name>
            <forward mode="bridge"/>
            <bridge name='gw_mgmt'/>
            <virtualport type='openvswitch'/>
        </network>'''

        conn = libvirt.open()

        networks = conn.listAllNetworks()
        for net in networks:
            if net.isActive() != 0:
                net.destroy()
            try:
                net.undefine()
            except:
                pass

        private = conn.networkDefineXML(gwmgmtxml)
        private.create()
        private.setAutostart(True)
