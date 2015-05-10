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
        import JumpScale.lib.ovsnetconfig
        hrd = serviceObj.hrd

        backplanes = hrd.getList('instance.netconfig.backplanes.names')
        def getBackplaneInfo(backplane):
            backplanehrd = 'instance.netconfig.backplanes.%s' % backplane
            backplane_bondinterfaces = None
            backplane_bondname = None
            backplane_interface = None
            bondkey = backplanehrd + '.bond' + '.name'
            if hrd.exists(bondkey):
                backplane_bondinterfaces = hrd.getList(backplanehrd + '.bond' + '.interfaces')
                backplane_bondname = hrd.get(bondkey)
            else:
                backplaneinterfacekey = backplanehrd + '.backplaneinterface'
                if hrd.exists(backplaneinterfacekey):
                     backplane_interface = hrd.get(backplaneinterfacekey)
            return backplane_interface, backplane_bondinterfaces, backplane_bondname

        # unconfigure existing network interfaces first
        for backplane_name in backplanes:
            backplanehrd = 'instance.netconfig.backplanes.%s' % backplane_name
            backplane_interface, backplane_bondinterfaces, backplane_bondname = getBackplaneInfo(backplane_name)
            if backplane_interface:
                j.system.process.execute('ifdown %s' % backplane_interface)
            elif backplane_bondinterfaces:
                for interface in backplane_bondinterfaces:
                    j.system.process.execute('ifdown %s' % backplane_interface)

        # configure network erases /etc/network/interfaces
        j.system.ovsnetconfig.initNetworkInterfaces()
        for backplane_name in backplanes:
            backplanehrd = 'instance.netconfig.backplanes.%s' % backplane_name
            backplane_interface, backplane_bondinterfaces, backplane_bondname = getBackplaneInfo(backplane_name)
            backplane_hasip = False
            if not (backplane_interface or backplane_bondname):
                raise  Exception("Incorrect config there should be a backplaneinterface or a bond defined in the backplane config")
            ipconfighrd = backplanehrd + '.backplaneipconfig'
            if hrd.exists(ipconfighrd):
                backplane_ip_config = hrd.getDict(ipconfighrd)
                backplane_hasip = True
            if backplane_hasip:
                if backplane_interface:
                    j.system.ovsnetconfig.setBackplane(backplane_interface,  backplane_name, ipaddr=backplane_ip_config['address'],gw=backplane_ip_config['gateway'])
                else:
                    j.system.ovsnetconfig.setBackplaneWithBond(backplane_bondname, backplane_bondinterfaces, backplane_name, ipaddr=backplane_ip_config['address'],gw=backplane_ip_config['gateway'])
            else:
                if backplane_interface:
                    j.system.ovsnetconfig.setBackplaneNoAddress(backplane_interface, backplane_name)
                else:
                    j.system.ovsnetconfig.setBackplaneNoAddressWithBond(backplane_bondname, backplane_bondinterfaces, backplane_name)
        j.system.ovsnetconfig.applyconfig() 
