from JumpScale import j

ActionsBase=j.packages.getActionsBaseClass()

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


    def configure(self, **kwargs):
        import JumpScale.portal
        cl = j.core.portal.getClientByInstance('cloudbroker')
        osiscl = j.core.osis.getClientByInstance('main')
        osis_size = j.core.osis.getClientForCategory(osiscl, 'cloudbroker', 'size')
        osis_lsize = j.core.osis.getClientForCategory(osiscl, 'libvirt', 'size')
        cl.getActor('libcloud', 'libvirt')
        cl.getActor('cloudapi','accounts')
        cl.getActor('cloudapi','cloudspaces')

        #A size is also needed in the cloudbroker
        sizecbs = [('10GB at SSD Speed, Unlimited Transfer - 7.5 USD/month', 512, 1),
                 ('10GB at SSD Speed, Unlimited Transfer - 15 USD/month', 1024, 1),
                 ('10GB at SSD Speed, Unlimited Transfer - 18 USD/month', 2048, 2),
                 ('10GB at SSD Speed, Unlimited Transfer - 36 USD/month', 4096, 2),
                 ('10GB at SSD Speed, Unlimited Transfer - 70 USD/month', 8192, 4),
                 ('10GB at SSD Speed, Unlimited Transfer - 140 USD/month', 16384, 8)]

        for sizecb in sizecbs:
            if osis_size.search({'description': sizecb[0]})[0]:
                continue
            sizecbobj = dict()
            sizecbobj['description'] = sizecb[0]
            sizecbobj['memory'] = sizecb[1]
            sizecbobj['vcpus'] = sizecb[2]
            osis_size.set(sizecbobj)

        disksizes = [10,15,20,25,30,40,50,60,70,80,90,100]
        for i in disksizes:
            for sizecb in sizecbs:
                if osis_lsize.search({'memory': sizecb[1], 'disk': i})[0]:
                    continue
                size = dict()
                size['disk'] = i
                size['memory'] = sizecb[1]
                size['name'] = '%i-%i' % (sizecb[1], i)
                size['vcpus'] = sizecb[2]
