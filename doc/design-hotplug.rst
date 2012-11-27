=======
Hotplug
=======

.. contents:: :depth: 4

This is a design document detailing the implementation of device
hotplugging in Ganeti. The logic used is hypervisor agnostic but still
the initial implementation will target the KVM hypervisor. The
implementation adds ``python-fdsend`` as a new dependency.


Current state and shortcomings
==============================

Currently, Ganeti supports addition/removal/modification of devices
(NICs, Disks) but the actual modification takes place only after
rebooting the instance. To this end an instance cannot change network,
get a new disk etc. without a hard reboot.

Until now, in case of KVM hypervisor, code does not name devices nor
places them in specific PCI slots. Devices are appended in the KVM
command and Ganeti lets KVM decide where to place them. This means that
there is a possibility a device that resides in PCI slot 5, after a
reboot (due to another device removal) to be moved to another PCI slot
and probably get renamed too (due to udev rules, etc.).

In order migration to succeed, the process on the target node should be
started with exactly the same machine version, CPU architecture and PCI
configuration with the running process. During instance creation/startup
ganeti creates a KVM runtime file with all the necessary information to
generate the KVM command. This runtime file is used during instance
migration to start a new identical KVM process. The current format
includes the fixed part of the final KVM command a list of NICs',
and hvparams dict. It does not favor easy manipulations concerning
disks, because they are encapsulated in the fixed KVM command.

Proposed changes
================

For the case of the KVM hypervisor, QEMU exposes 32 PCI slots to the
instance. Disks and NICs occupy some of these slots. Recent versions of
QEMU have introduced monitor commands that allow addition/removal of PCI
devices. Devices are referenced based on their name or position on the
virtual PCI bus. To be able to use these commands, we need to be able to
assign each device a unique name. For that we build on top of devices'
UUIDs.

Finally, to keep track where each device is plugged into, we add the
``pci`` slot to Disk and NIC objects, but we save it only in runtime
files, since it is hypervisor specific info.

We propose to make use of QEMU 1.0 monitor commands so that
modifications to devices take effect instantly without the need for hard
reboot. The only change exposed to the end-user will be the addition of
a ``--hotplug`` option to the ``gnt-instance modify`` command.

Upon hotplugging the PCI configuration of an instance is changed.
Runtime files should be updated correspondingly. Currently this is
impossible in case of disk hotplug because disks are included in command
line entry of the runtime file, contrary to NICs that are correctly
treated separately. We change the format of runtime files, we remove
disks from the fixed KVM command and create new entry containing them
only. KVM options concerning disk are generated during
``_ExecuteKVMCommand()``, just like NICs.

Design decisions
================

Which should be each device ID? Currently KVM does not support arbitrary
IDs for devices; supported are only names starting with a letter, max 32
chars length, and only including '.' '_' special chars. To this end we
use a helper function that converts UUID to accepted device id. For the
sake of simplicity and readability we use the part of UUID until the
first dash and insert a "x" at the beginning of the string.

Who decides where to hotplug each device? As long as this is a
hypervisor specific matter, there is no point for the master node to
decide such a thing. Master node just has to request noded to hotplug a
device. To this end, hypervisor specific code should parse the current
PCI configuration (i.e. ``info pci`` QEMU monitor command), find the first
available slot and hotplug the device. Having noded to decide where to
hotplug a device we ensure that no error will occur due to duplicate
slot assignment (if masterd keeps track of PCI reservations and noded
fails to return the PCI slot that the device was plugged into then next
hotplug will fail).

Where should we keep track of devices' PCI slots? As already mentioned,
we must keep track of devices PCI slots to successfully migrate
instances. First option is to save this info to config data, which would
allow us to place each device at the same PCI slot after reboot. This
would require to make the hypervisor return the PCI slot chosen for each
device, and storing this information to config data. Additionally the
whole instance configuration should be returned with PCI slots filled
after instance start and each instance should keep track of current PCI
reservations. We decide not to go towards this direction in order to
keep it simple and do not add hypervisor specific info to configuration
data (``pci_reservations`` at instance level and ``pci`` at device
level). For the aforementioned reason, we decide to store this info only
in KVM runtime files.

Where to place the devices upon instance startup? QEMU has by default 4
pre-occupied PCI slots. So, hypervisor can use the remaining ones for
disks and NICs. Currently, PCI configuration is not preserved after
reboot.  Each time an instance starts, KVM assigns PCI slots to devices
based on their ordering in Ganeti configuration, i.e. the second disk
will be placed after the first, the third NIC after the second, etc.
Since we decided that there is no need to keep track of devices PCI
slots, there is no need to change current functionality.

How to deal with existing instances? Migration and hotplugging of
existing instances in a cluster after installing the version that
supports hotplug will not be supported until we run a specific script in
all nodes that adds a new entry for the block devices (e.g. []) in
existing runtime files or else until instances suffer a hard reboot.


Configuration changes
---------------------

The ``NIC`` and ``Disk`` objects get one extra slot: ``pci``. It refers to
PCI slot that the device gets plugged into.

In order to be able to live migrate successfully, runtime files should
be updated every time a live modification (hotplug) takes place. To this
end we change the format of runtime files. The KVM options referring to
instance's disks are no longer recorded as part of the KVM command line.
Disks are treated separately, just as we treat NICs right now. We insert
and remove entries to reflect the current PCI configuration.


Backend changes
---------------

Introduce 4 new RPC calls:

- hot_add_nic
- hot_del_nic
- hot_add_disk
- hot_del_disk


Hypervisor changes
------------------

We implement hotplug on top of the KVM hypervisor. We take advantage of
QEMU 1.0 monitor commands (``device_add``, ``device_del``,
``drive_add``, ``drive_del``, ``netdev_add``,`` netdev_del``). QEMU
refers to devices based on their id. We use ``uuid`` to name them
properly. If a device is about to be hotplugged we parse the output of
``info pci`` and find the occupied PCI slots. We choose the first
available and the whole device object is appended to the corresponding
entry in the runtime file.

Concerning NIC handling, we build on the top of the existing logic
(first create a tap with _OpenTap() and then pass its file descriptor to
the KVM process). To this end we need to pass access rights to the
corresponding file descriptor over the monitor socket (UNIX domain
socket). The open file is passed as a socket-level control message
(SCM), using the ``fdsend`` python library.


User interface
--------------

The new ``--hotplug`` option to gnt-instance modify is introduced, which
forces live modifications.


Enabling hotplug
++++++++++++++++

Hotplug will be optional during gnt-instance modify.  For existing
instances inside an old ganeti cluster we have two options after
upgrading to a version that supports hotplugging:

1. Instances in the cluster should be hard rebooted or

2. A specific script should change their runtime format before they can
support hotplugging of devices.

If neither happens these instances will not support migration nor
hotplug.


NIC hotplug
+++++++++++

The user can add/modify/remove NICs either with hotplugging or not. If a
NIC is to be added a tap is created first and configured properly with
kvm-vif-bridge script. Then the instance gets a new network interface.
Since there is no QEMU monitor command to modify a NIC, we modify a NIC
by temporary removing the existing one and adding a new with the new
configuration. When removing a NIC the corresponding tap gets removed as
well.

::

 gnt-instance modify --net add --hotplug test
 gnt-instance modify --net 1:mac=aa:00:00:55:44:33 --hotplug test
 gnt-instance modify --net 1:remove --hotplug test


Disk hotplug
++++++++++++

The user can add and remove disks with hotplugging or not. QEMU monitor
supports resizing of disks, however the initial implementation will
support only disk addition/deletion.

::

 gnt-instance modify --disk add:size=1G --hotplug test
 gnt-instance modify --net 1:remove --hotplug test

.. vim: set textwidth=72 :
.. Local Variables:
.. mode: rst
.. fill-column: 72
.. End:
