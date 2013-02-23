======================
Device UUIDs and Names
======================

.. contents:: :depth: 4

This is a design document detailing the implementation of assigning
UUIDs and names to devices (Disks/NICs) and the ability to reference
to them using either those identifiers or their current index.

Current state and shortcomings
==============================

Currently one can reference a device only by using its current
index (first disk, second NIC, etc.) This approach presents some
shortcomings:

a) There is a race condition when two modifications take place at the
   same time. For example, when both modify an instance with 3 NICs,
   and both reference the second NIC, and the first one removes it,
   the second will act on the previously third NIC which now is the
   second!

b) In order to do a modification most of the times the current
   configuration must me fetched first to ensure you reference to
   the correct device.

c) There is no easy way to store device configuration outside Ganeti,
   and use the RAPI to make safe modifications on existing devices.


Proposed changes
----------------

In order to deal with the above shortcomings, we propose to extend
the existing device referencing mechanism by using either UUIDs or names.
To this end each device (Disk/NIC) will get a UUID by Ganeti upon
creation. Names will be optional and provided by the user. Renaming
a device will be also supported.

The user will be able to reference devices using either index, UUID.
Name referencing will be deferred in future patches because
name uniqueness should be ensured first, which is not that trivial.
Until then name will be only an extra attribute for every device.

To make this change easier we drop all relevant code that
supports the deprecated format of modify command (add|remove:...) and
allow only new style:

ident:action,key=value

where ident can be index (-1 for the last device), UUID, or name and
action should be add, modify, or remove.

Patches on top of the core implementation should export UUIDs and
names in queries and hooks too.

Configuration changes
+++++++++++++++++++++

Disk and NIC config objects get two extra slots:

- uuid
- name


Hook variables
^^^^^^^^^^^^^^

During instance related operations:

``INSTANCE_NICn_NAME``
  The friendly name of the NIC

``INSTANCE_NICn_UUID``
  The UUID of the NIC

``INSTANCE_DISKn_NAME``
  The friendly name of the Disk

``INSTANCE_DISKn_UUID``
  The UUID of the Disk

.. vim: set textwidth=72 :
.. Local Variables:
.. mode: rst
.. fill-column: 72
.. End:
