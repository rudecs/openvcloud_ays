# iPXE Boot image:

This image is build with: (https://github.com/openvcloud/ipxe-vm)[https://github.com/openvcloud/ipxe-vm]

## Using this image to boot (Zero-OS)[https://github.com/zero-os/home]

It is not possible to pass custom cloud-init data to the create of virtual machine. 
When passing the `ipxe` key one is able to pass a url pointing to a (ipxe)[http://ipxe.org/scripting/] script.  
Currently only `chain` and `initrd` commands are implemented.

Combining this with (bootstrap)[https://bootstrap.gig.tech/] service you can boot up a Zero-OS image of your choice with custom kernel params for `organization` and `zerotierid`

Example cloud-init:
```yaml
ipxe: https://bootstrap.gig.tech/ipxe/master/<myzerotierid>/organization=<my iyo org>%20customkernelparam=customvalue
```
