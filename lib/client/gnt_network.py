#
#

# Copyright (C) 2011 Google Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

"""IP pool related commands"""

# pylint: disable-msg=W0401,W0614
# W0401: Wildcard import ganeti.cli
# W0614: Unused import %s from wildcard import (since we need cli)

from ganeti.cli import *
from ganeti import constants
from ganeti import opcodes
from ganeti import utils
from textwrap import wrap


#: default list of fields for L{ListNetworks}
_LIST_DEF_FIELDS = ["name", "network", "gateway", "group_cnt", "group_links"]


def AddNetwork(opts, args):
  """Add a network to the cluster.

  @param opts: the command line options selected by the user
  @type args: list
  @param args: a list of length 1 with the link name the pool to create
  @rtype: int
  @return: the desired exit code

  """
  (network_name, ) = args
  if opts.reserved_ips is not None:
    if opts.reserved_ips == "":
      opts.reserved_ips = []
    else:
      opts.reserved_ips = utils.UnescapeAndSplit(opts.reserved_ips, sep=",")

  op = opcodes.OpNetworkAdd(network_name=network_name,
                            gateway=opts.gateway,
                            network=opts.network,
                            reserved_ips=opts.reserved_ips)
  SubmitOpCode(op, opts=opts)


def MapNetwork(opts, args):
  """Map a network to a node group.

  @param opts: the command line options selected by the user
  @type args: list
  @param args: a list of length 3 with the link name the pool to create
  @rtype: int
  @return: the desired exit code

  """
  op = opcodes.OpGroupSetParams(group_name=args[1],
                                network=[constants.DDM_ADD,
                                         args[0], args[2]])
  SubmitOpCode(op, opts=opts)


def UnmapNetwork(opts, args):
  """Unmap a network from a node group.

  @param opts: the command line options selected by the user
  @type args: list
  @param args: a list of length 3 with the link name the pool to create
  @rtype: int
  @return: the desired exit code

  """
  op = opcodes.OpGroupSetParams(group_name=args[1],
                                network=[constants.DDM_REMOVE,
                                         args[0], None])
  SubmitOpCode(op, opts=opts)

def ListNetworks(opts, args):
  """List Ip pools and their properties.

  @param opts: the command line options selected by the user
  @type args: list
  @param args: networks to list, or empty for all
  @rtype: int
  @return: the desired exit code

  """
  desired_fields = ParseFields(opts.output, _LIST_DEF_FIELDS)
  fmtoverride = {
    "group_links": (",".join, False),
    "inst_list": (",".join, False),
  }

  return GenericList(constants.QR_NETWORK, desired_fields, args, None,
                     opts.separator, not opts.no_headers,
                     verbose=opts.verbose, format_override=fmtoverride)


def ListNetworkFields(opts, args):
  """List network fields.

  @param opts: the command line options selected by the user
  @type args: list
  @param args: fields to list, or empty for all
  @rtype: int
  @return: the desired exit code

  """
  return GenericListFields(constants.QR_NETWORK, args, opts.separator,
                           not opts.no_headers)


def ShowNetworkConfig(opts, args):
  """Show network information.

  @param opts: the command line options selected by the user
  @type args: list
  @param args: should either be an empty list, in which case
      we show information about all nodes, or should contain
      a list of networks (names or UUIDs) to be queried for information
  @rtype: int
  @return: the desired exit code

  """
  cl = GetClient()
  result = cl.QueryNetworks(fields=["name", "network", "gateway",
                                    "free_count", "reserved_count",
                                    "map", "group_links", "inst_list",
                                    "external_reservations"],
                            names=args, use_locking=False)

  for (name, network, gateway, free_count, reserved_count,
       map, group_links, instances, ext_res) in result:
    size = free_count + reserved_count
    ToStdout("Network name: %s", name)
    ToStdout("  subnet: %s", network)
    ToStdout("  gateway: %s", gateway)
    ToStdout("  size: %d", size)
    ToStdout("  free: %d (%.2f%%)", free_count,
             100 * float(free_count)/float(size))
    ToStdout("  usage map:")
    idx = 0
    for line in wrap(map, width=64):
      ToStdout("     %s %s %d", str(idx).rjust(3), line.ljust(64), idx + 63)
      idx += 64
    ToStdout("         (X) used    (.) free")

    if ext_res:
      ToStdout("  externally reserved IPs:")
      for line in wrap(ext_res, width=64):
        ToStdout("    %s" % line)

    if group_links:
      ToStdout("  connected to node groups:")
      for conn in group_links:
        group, link = conn.split(":")
        ToStdout("    %s (link %s)", group, link)
    else:
      ToStdout("  not connected to any node group")

    if instances:
      ToStdout("  used by %d instances:", len(instances))
      for inst in instances:
        ToStdout("    %s", inst)
    else:
      ToStdout("  not used by any instances")


def SetNetworkParams(opts, args):
  """Modifies an IP address pool's parameters.

  @param opts: the command line options selected by the user
  @type args: list
  @param args: should contain only one element, the node group name

  @rtype: int
  @return: the desired exit code

  """
  all_changes = {
    "gateway": opts.gateway,
    "reserved_ips": opts.reserved_ips,
  }

  if all_changes.values().count(None) == len(all_changes):
    ToStderr("Please give at least one of the parameters.")
    return 1

  op = opcodes.OpNetworkSetParams(network_name=args[0],
                                  # pylint: disable-msg=W0142
                                  **all_changes)
  result = SubmitOrSend(op, opts)

  if result:
    ToStdout("Modified ip pool %s", args[0])
    for param, data in result:
      ToStdout(" - %-5s -> %s", param, data)

  return 0


def RemoveNetwork(opts, args):
  """Remove an IP address pool from the cluster.

  @param opts: the command line options selected by the user
  @type args: list
  @param args: a list of length 1 with the id of the IP address pool to remove
  @rtype: int
  @return: the desired exit code

  """
  (network_name,) = args
  op = opcodes.OpNetworkRemove(network_name=network_name, force=opts.force)
  SubmitOpCode(op, opts=opts)


commands = {
  "add": (
    AddNetwork, ARGS_ONE_NETWORK,
    [DRY_RUN_OPT, NETWORK_OPT, GATEWAY_OPT, RESERVED_IPS_OPT],
    "<network_name>", "Add a new IP network to the cluster"),
  "list": (
    ListNetworks, ARGS_MANY_NETWORKS,
    [NOHDR_OPT, SEP_OPT, FIELDS_OPT, VERBOSE_OPT],
    "[<network_id>...]",
    "Lists the IP networks in the cluster. The available fields can be shown"
    " using the \"list-fields\" command (see the man page for details)."
    " The default list is (in order): %s." % utils.CommaJoin(_LIST_DEF_FIELDS)),
  "list-fields": (
    ListNetworkFields, [ArgUnknown()], [NOHDR_OPT, SEP_OPT], "[fields...]",
    "Lists all available fields for networks"),
  #
  #"list-maps"
  #
  #"info"
  "info": (
    ShowNetworkConfig, ARGS_MANY_NETWORKS, [],
    "[<network_name>...]", "Show information about the network(s)"),
  #
  #"modify": (
  #  SetNetworkParams, ARGS_ONE_NETWORK,
  #  [DRY_RUN_OPT, SUBMIT_OPT, RESERVED_IPS_OPT, NETWORK_OPT, GATEWAY_OPT],
  #  "<network_name>", "Alters the parameters of a network"),
  "connect": (
    MapNetwork,
    [ArgNetwork(min=1, max=1), ArgGroup(min=1, max=1),
     ArgUnknown(min=1, max=1)],
    [],
    "<network_name> <node_group> <link_name>",
    "Map a given network to a link of a specified node group"),
  "disconnect": (
    UnmapNetwork,
    [ArgNetwork(min=1, max=1), ArgGroup(min=1, max=1)],
    [],
    "<network_name> <node_group>",
    "Unmap a given network from a specified node group"),
  #"remove": (
  #  RemoveNetwork, ARGS_ONE_NETWORK, [FORCE_OPT, DRY_RUN_OPT],
  #  "[--dry-run] <network_id>",
  #  "Remove an (empty) network from the cluster"),
}


def Main():
  return GenericMain(commands)
