=======
Hotplug
=======

.. contents:: :depth: 4

This is a design document detailing the implementation of device
hotplugging in Ganeti. An initial implementation will target the KVM
hypervisor.


Current state and shortcomings
==============================

Currently, Ganeti supports addition/removal/modification of devices
(NICs, Disks) but the actual modification takes place only after we
reboot the instance. To this end an instance cannot change network, get
a new disk etc.  without a hard reboot.

Traditional code does not name devices nor places them in specific
PCI slots. Devices are appended in kvm command and Ganeti lets KVM
decide where to place them. This means that there is a possibility
a device that resides in PCI slot 5, after a reboot (due to a device
removal) to be moved to another PCI slot and probably get renamed as
well (due to udev, etc.). In the following hotplug design, we could
address this issue by keeping track of PCI reservations but for
the time being this is not such an important issue.

In order migration to succeed, the -incoming process should be started
with exactly the same machine version, CPU architecture and PCI
configuration with the running process. Migration is based on kvm
runtime files created during instance creation. Upon hotplugging the PCI
configuration of an instance is changed. Runtime files should be updated
correspondingly. Currently NICs are correctly treated separately,
contrary to disks that are included in kvm_cmd part of runtime file. We
have to change the format of the runtime file so that disks are a
separate list too.


Design decisions
----------------

Who decides where to hotplug each device? As long as this is a
hypervisor specific matter, there is no point for the master node to
decide such a thing. Master node just has to request noded to hotplug a
device.  To this end hypervisor specific code should parse the current
PCI configuration (i.e. info pci QEMU monitor command), find the first
available slot and hotplug the device.  Having noded to decide where to
hotplug a device we ensure that no error will occur due to duplicate
slot assignement (if masterd keeps track of PCI reservations and noded
fails to return the PCI slot that the device was plugged into then next
hotplug will fail).

Where to place the devices upon instance creation? QEMU has by default
4 preoccupied PCI slots. To this end hypervisor could pick the remaining
ones for disks and NICs. Because same device placement after reboot is
meaningless, each time could pick different ones (just like kvm does
currently; first the disks and then the NICs).

Should we keep track of devices PCI slots? Currently this is not the case. We
could track this down (by adding a pci slot in NIC and Disk objects) and
letting hypervisor return the PCI address chosen for each device. This would
mean that each device would be placed at the same PCI slot after reboot.
Additionally the whole instance configuration should be returned with pci slots
filled after instance start and each instance should keep track of current PCI
reservations. We decide not to go towards this direction in order to keep it
simple and do not add hypervisor specific info to configuration data
(``pci_reservations`` at instance level and ``pci`` at device level). Still pci
slots of devices chosen during instance creation/modification should be noted
to runtime files (for migrations issues) but there is no need to add them in
configuration data.

How to deal with existing instances? Firstly a cfgupgrade should add
``dev_idxs`` at instance level so that devices can be named properly.
Migration and hotplugging of existing instances in a cluster after
installing the version that supports hotplug will not be supported until
we run a specific script in all nodes that adds a new entry for the
block devices (e.g. []) in existing runtime files or else until instances
suffer a hard reboot.


Proposed changes
----------------

QEMU exposes 32 PCI slots to the instance. Disks and NICs occupy some of
these slots. Recent versions of QEMU have introduced monitor commands
that allow addition/removal of PCI devices. Devices are referenced based
on theirs name and/or position on the virtual PCI bus. Based on that we
add a new slot in instances ``dev_idxs``, that is needed for unique device
naming. To keep track of device naming we add a new slot ``idx`` to
devices (NICs/Disks). To keep track where each device is plugged into
we add a new slot ``pci`` to devices (used only in runtime files).

We propose to make use of QEMU 1.0 monitor commands so that
modifications to devices take effect instantly without the need for hard
reboot. The only change exposed to the end-user will be the addition of
a ``--hotplug`` option to the gnt-instance modify command.


Configuration changes
+++++++++++++++++++++

We propose the introduction of a new instance level slot,
``dev_idxs``, containing the following data:

- disks
- nics

Those two values are strictly increasing upon instance modification and
will be used for unique device naming. This slot will be initialized
upon instance creation depending the number of devices the instance
primarily uses.

The ``NIC`` and ``Disk`` objects get two extra slots: ``idx`` and
``pci``.  Both are integers and the first is used for device naming
(e.g.  virtio-net-pci.%d % nic.idx) and the second is the pci slot that
the device gets plugged to.

In order to be able to live migrate successfully, runtime files should be
updated every time a live modification (hotplug) takes place. To this
end we change the format of runtime files in case hotplug is enabled.
The disk state is no longer recorded as part of kvm_cmd. Disks are
tread ed separately. just as we treat NICs right now. We insert and
remove entries to reflect the current PCI configuration.


Backend changes
+++++++++++++++

Introduce 4 new RPC calls:

- hot_add_nic
- hot_del_nic
- hot_add_disk
- hot_del_disk


Hypervisor changes
++++++++++++++++++

We implement hotplug on top of the kvm hypervisor. We take advantage of
QEMU 1.0 monitor commands (device_add, device_del, drive_add, drive_del,
netdev_add, netdev_del). QEMU refers to devices based on their id. We
use ``idx`` to name them properly. If a device is about to be hotplugged
we parse the output of  ``info pci`` and find the occupied pci slots. We
chose the first available and this value is appended to the correponding
NIC entry in runtime file.

Concerning NIC handling, we build on the top of the existing logic
(first create a tap with _OpenTap() and then pass its file descriptor to
the kvm process). To this end we need to pass access rights to the
corresponding file descriptor over the monitor socket (UNIX domain
socket). The open file is passed as a socket-level control message (SCM),
using the ``fdsend`` python library.


User interface
++++++++++++++

One new option is introduced ``--hotplug`` which forces live
modifications during gnt-instance modify.


Enabling hotplug
^^^^^^^^^^^^^^^^
Hotplug is optional during gnt-instance modify. Still though existing
instances in the cluster should suffer a hard reboot or a specific
script should change their runtime format before they can support
hotplugging of devices.


NIC hotplug
^^^^^^^^^^^
The user can add/modify/remove NICs either with hotplugging or not. If a
NIC is to be added a tap is created first and configured properly with
kvm-vif-bridge script. Then the instance gets a new network interface.
When modifying a NIC it gets temporary removed and a new one is added in
its place with the new configuration. When removing a NIC the
corresponding tap gets removed as well.

::

 gnt-instance modify --net add --hotplug test
 gnt-instance modify --net 1:mac=aa:00:00:55:44:33 --hotplug test
 gnt-instance modify --net 1:remove --hotplug test


Disk hotplug
^^^^^^^^^^^^
The user can add and remove disks with hotplugging or not. The initial
implementation does not support disk modification but only
addition/deletion with hotplugging.

::

 gnt-instance modify --disk add:size=1G --hotplug test
 gnt-instance modify --net 1:remove --hotplug test

.. vim: set textwidth=72 :
.. Local Variables:
.. mode: rst
.. fill-column: 72
.. End:
