# OpenvCloud installation

## LXC preparation for compute node or AIO install
### Modules

Load openvswitch tun and kvm modules on host operation system. Needs to hapen each time you reboot your host.
```
modprobe tun
modprobe kvm 
modprobe openvswitch
```
### Devices
In the container create /dev/kvm/ and /dev/net/tun Needs to happen only once in the lifetime of the container.
```sh
mkdir -p /dev/net
mknod /dev/net/tun c 10 200
mknod /dev/kvm c 10 232
```

## Master

### Install Jumpscale
```sh
curl https://raw.githubusercontent.com/Jumpscale/jumpscale_core7/master/install/install.sh > /tmp/js7.sh && bash /tmp/js7.sh
```

### Add openvcloud domain
edit `/opt/jumpscale7/hrd/system/atyourservice.hrd`
```
metadata.jumpscale             =
    url:'https://github.com/Jumpscale/ays_jumpscale7',
# add this domain
metadata.openvcloud           =
    url:'https://git.aydo.com/0-complexity/openvcloud_ays',
```

### Install cb_master_aio

```
ays install -n cb_master_aio
Please provide value for param.publicip.gateway of type str
: 192.168.57.254
Please provide value for param.publicip.netmask of type str
: 255.255.255.0
Please provide value for param.publicip.start of type str
: 192.168.57.200
Please provide value for param.publicip.end of type str
: 192.168.57.240

Please provide value for mothership1.cloudbroker.defense_proxy of type str
: http://192.168.57.7/
Please provide value for cloudbroker.portalurl of type str
: http://192.168.57.7:82
Please provide value for param.vncproxy.publichostport of type str
: 192.168.57.7:8091
```

## SSL offloader

### Install Jumpscale
```curl https://raw.githubusercontent.com/Jumpscale/jumpscale_core7/master/install/install.sh > /tmp/js7.sh && bash /tmp/js7.sh```

### Add openvcloud domain
edit ```/opt/jumpscale7/hrd/system/atyourservice.hrd```
```
metadata.jumpscale             =
    url:'https://github.com/Jumpscale/ays_jumpscale7',

# add this domain
metadata.openvcloud           =
    url:'https://git.aydo.com/0-complexity/openvcloud_ays',
```

### Install ssloffloader
```ays install -n ssloffloader```

```
ost for which the ssl is being offloaded
 [environment.demo.greenitglobe.com]: demo3.demo.greenitglobe.com
ipaddress of the master node [192.168.103.254]:
servername DCPM is exposed at [dcpmenvironment.demo.greenitglobe.com]: dcpm3.demo.greenitglobe.com
internal server/port DCPM is running on
 [192.168.103.251:80]: 192.168.103.252:80
servername OVS is exposed at [ovsenvironment.demo.greenitglobe.com]: ovs3.demo.greenitglobe.com
servername OVS is exposed at [defenseenvironment.demo.greenitglobe.com]: defense3.demo.greenitglobe.com
```

## CPU Node

### Install Jumpscale
```curl https://raw.githubusercontent.com/Jumpscale/jumpscale_core7/master/install/install.sh > /tmp/js7.sh && bash /tmp/js7.sh```

### Add openvcloud domain
edit ```/opt/jumpscale7/hrd/system/atyourservice.hrd```
```
metadata.jumpscale             =
    url:'https://github.com/Jumpscale/ays_jumpscale7',

# add this domain
metadata.openvcloud           =
    url:'https://git.aydo.com/0-complexity/openvcloud_ays',

```

### Install cb_cpunode_aio
```ays install -n cb_cpunode_aio```

Fill in the public IP of the cloudspace where the master is installed:
```
PORTAL_CLIENT: Address [localhost]:
```