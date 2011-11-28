gnt-network(8) Ganeti | Version @GANETI_VERSION@
================================================

Name
----

gnt-network - Ganeti network administration

Synopsis
--------

**gnt-network** {command} [arguments...]

DESCRIPTION
-----------

The **gnt-network** command is used for network definition administration
in the Ganeti system.

COMMANDS
--------

ADD
~~~

| **add**
| [--network=*NETWORK*]
| [--gateway=*GATEWAY*]
| {*network*}

Creates a new network with the given name. The network will be unused
initially. To connect it to a node group, use ``gnt-network connect``.

The ``--network`` option allows you to specify the network in a CIDR notation.

The ``--gateway`` option allows you to specify the default gateway for this
network.

MODIFY
~~~~~~

| **modify**
| [--node-parameters=*NDPARAMS*]
| [--alloc-policy=*POLICY*]
| {*group*}

Modifies some parameters from the node group.

The ``--node-parameters`` and ``--alloc-policy`` optiosn are documented
in the **add** command above.

REMOVE
~~~~~~

| **remove** {*group*}

Deletes the indicated node group, which must be empty. There must always be at
least one group, so the last group cannot be removed.

LIST
~~~~

| **list** [--no-headers] [--separator=*SEPARATOR*] [-v]
| [-o *[+]FIELD,...*] [network...]

Lists all existing node groups in the cluster.

The ``--no-headers`` option will skip the initial header line. The
``--separator`` option takes an argument which denotes what will be
used between the output fields. Both these options are to help
scripting.

The ``-v`` option activates verbose mode, which changes the display of
special field states (see **ganeti(7)**).

The ``-o`` option takes a comma-separated list of output fields.
If the value of the option starts with the character ``+``, the new
fields will be added to the default list. This allows to quickly
see the default list plus a few other fields, instead of retyping
the entire list of fields.

The available fields and their meaning are:

name
    the group name

uuid
    the group's UUID

node_cnt
    the number of nodes in the node group

node_list
    the list of nodes that belong to this group

pinst_cnt
    the number of primary instances in the group (i.e., the number of
    primary instances nodes in this group have)

pinst_list
    the list of primary instances in the group

alloc_policy
    the current allocation policy for the group

ctime
    the creation time of the group; note that this field contains spaces
    and as such it's harder to parse

    if this attribute is not present (e.g. when upgrading from older
    versions), then "N/A" will be shown instead

mtime
    the last modification time of the group; note that this field
    contains spaces and as such it's harder to parse

serial_no
    the so called 'serial number' of the group; this is a numeric field
    that is incremented each time the node is modified, and it can be
    used to detect modifications

If no group names are given, then all groups are included. Otherwise,
only the named groups will be listed.

LIST-FIELDS
~~~~~~~~~~~

**list-fields** [field...]

List available fields for node groups.

RENAME
~~~~~~

| **rename** {*oldname*} {*newname*}

Renames a given group from *oldname* to *newname*.

INFO
~~~~

| **info** [network...]

Displays information about a given network.

CONNECT
~~~~~~~
| **connect** {*network*} {*group*} {*link*}

Connect a network to a given nodegroup's link.

DISCONNECT
~~~~~~~~~~
| **disconnect** {*network*} {*group*}
