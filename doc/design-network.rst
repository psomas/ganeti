Network management
==================
::

 gnt-network add --network=192.0.2.0/24 --gateway=192.0.2.1 \
 		--v6-network=2001:648:2ffc::/64 --v6-gateway=2001:648:2ffc::1 \
 		public

 gnt-network reserve-ips public 192.0.2.2 192.0.2.10-192.0.2.20

 gnt-network connect public nodegroup1 link100
 gnt-network connect public nodegroup2 link200
 gnt-network disconnect public nodegroup1 (only permitted if no instances are
                                           currently using this network in the group)
 
 gnt-network list
  Name		IPv4 Network	IPv4 Gateway	      IPv6 Network		   IPv6Gateway
  public		 192.0.2.0/24	192.0.2.1	2001:db8:dead:beef::/64		2001:db8:dead:beef::1
  private	 10.0.1.0/24	   -			 -				-
 
 gnt-network list-connected
  Network	Node Group	Link
  public		nodegroup1	link100
  public		nodegroup2 	link200
  private	nodegroup1	link50
 
 gnt-network list-connected private
  Network	Node Group	Link
  private	nodegroup1	link50
 
 gnt-network info public
  Name: public
  IPv4 Network: 192.0.2.0/24
  IPv4 Gateway: 192.0.2.1
  IPv6 Network: 2001:db8:dead:beef::/64
  IPv6 Gateway: 2001:db8:dead:beef::1
  Connected to: nodegroup1 (link100), nodegroup2 (link200)
  Total IPv4 count: 256
  Free address count: 201 (80% free)
  IPv4 pool status: XXX.........XXXXXXXXXXXXXX...XX.............
                    XXX..........XXX...........................X
                    ....XXX..........XXX.....................XXX
                                            X: occupied  .: free
  Used by 22 instances:
   inst1
   inst2
   inst32
   ..
 
NIC "network" parameter
-----------------------

1. "network" takes precedence over "link"

2. manually setting "link" on a nic with existing "network" is not permitted

3. as a safety guard, setting a "network" parameter on a nic with a "link" is only
   permitted if the network's link on the instance's node group is the same as
   the current nic's link

4. "link" is updated on startup according to the network -> nodegroup mapping

Default nic "network" parameter
add default "network" argument? How do we deal with transitions?
-> network and link may not be set at the same time
-> setting network will unset link and vice-versa
-> setting network is only permitted iff:

   all NICs with a "default" link would result in having the same link right after setting "network".
     i.e.: for instance in all_instances:
		for nic in instance.nics:
			if nic.link == instance.primary_node.group.networks[network]:
				...
			else:
				raise errors.OpPrereqError

IAllocator changes
------------------

 - Make it network-aware, same as storage-aware
 - Both, network and storage will act as *constraints*, i.e. "place me a node
   that has access to network x and storage pool y on the cluster". The
   iallocator will thus rule out node groups based on these constraints.


Helper methods in lib/config.py
-------------------------------

 - ConfigWriter.GetInstancesByNodeGroup(group_uuid)
 - ConfigWriter.GetInstancesInfoByNodeGroup(group_uuid)
