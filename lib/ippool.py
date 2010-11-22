#
#

# Copyright (C) 2010 Google Inc.
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


"""Ip address pool management functions.

"""

import base64
import ipaddr

from ganeti import errors

from bitarray import bitarray


class IPv4PoolError(Exception):
  """ Generic IPv4 pool error

  """


class IPv4PoolFull(IPv4PoolError):
  """ IPv4 pool-is-full error

  """


class IPv4Network(object):
  def __init__(self, net, gateway=None, pool=None):
    """ Initialize a new IPv4 address pool

    """
    self.net = ipaddr.IPv4Network(net)
    self.gateway = None
    self.size = 2**(32 - self.net.prefixlen)
    if self.size <= 2:
      raise IPv4PoolError("Subnet too small")

    if pool is None:
      self._pool = bitarray(self.size)
      self._pool.setall(False)
      self._pool[0] = True
      self._pool[-1] = True
    else:
      self._pool = bitarray()
      self._pool.fromstring(pool)

    if gateway is not None:
      self.gateway = ipaddr.IPv4Address(gateway)

      if not self.net.Contains(self.gateway):
        raise IPv4PoolError("Gateway must lie in the subnet")

      if pool is None:
        try:
          self.reserve(gateway)
        except IPv4PoolError:
          raise IPv4PoolError("Gateway cannot be network or broadcast")

  def __repr__(self):
    return "<IPv4Network: %s, gateway: %s, free: %d>" % (self.net, self.gateway,
                                                      self.free_count)

  def todict(self):
    """Convert an IPv4Network to a dictionary

    """
    d = {}
    d["net"] = str(self.net)
    if self.gateway is not None:
      d["gateway"] = str(self.gateway)

    # JSON can't handle binary data, so encode the pool using base64
    d["pool"] = base64.encodestring(self._pool.tostring()).strip()
    return d

  @classmethod
  def fromdict(cls, d):
    """Create an IPv4Network instance from a dictionary
    
    @type d: dict
    @param d: dictionary containing the pool data
    @rtype: IPv4Network
    @return: IPv4Network object for the specified pool

    """
    pool = None
    gateway = None
    if "pool" in d:
      pool = base64.decodestring(d["pool"])
    if "gateway" in d:
      gateway = d["gateway"]

    return cls(d["net"], gateway, pool)

  @property
  def full(self):
    """Check whether the pool is full

    """
    return self._pool.all()

  @property
  def reserved_count(self):
    """Get the count of reserved IPs

    """
    return self._pool.count(True)

  @property
  def free_count(self):
    """Get the count of free IPs

    """
    return self._pool.count(False)

  @property
  def map(self):
    """Return an intuitive textual representation of the pool status.

    """
    ipmap = ""
    for ip in self._pool:
      if ip:
        ipmap += "X"
      else:
        ipmap += "."
    return ipmap
      
  def _ip_index(self, address):
    addr = ipaddr.IPv4Address(address)

    if not self.net.Contains(addr):
      raise IPv4PoolError("%s does not contain %s" % (self.net, address))

    idx = int(addr) - int(self.net.network)
    return idx

  def _mark(self, address, value=True):
    idx = self._ip_index(address)
    self._pool[idx] = value

  def is_reserved(self, address):
    """Check whether an address is reserved

    """
    idx = self._ip_index(address)
    return self._pool[idx]

  def reserve(self, address):
    """Mark an address as used.

    Fail if the address is already marked as used
    """
    if self.is_reserved(address):
      raise IPv4PoolError("%s already reserved" % address)
    self._mark(address)
  
  def release(self, address):
    """Mark an address as free

    """
    self._mark(address, False)

  def get_free_address(self):
    """Return the first free address in the pool

    """
    if self.full:
      raise IPv4PoolFull("Pool is full")
    idx = self._pool.index(False)
    addr = str(self.net[idx])
    self.reserve(addr)
    return addr

  def __iter_free(self):
    for idx in self._pool.search("0", 64):
      yield str(self.net[idx])

  def generate_free(self):
    return self.__iter_free().next


def ParseIPv4Pool(value):
  """Parse an IP address pool definition

  @type value: str
  @param value: string representation of the user-id pool.
                The accepted input format is the following:
                <CIDR> <gateway>
                Example: 10.0.1.0/24 10.0.1.1

  @rtype: tuple
  @return: A tuple (start, end, prefix, gateway)

  """
  components = value.split()
  if len(components) != 2:
    raise errors.OpPrereqError("Invalid IP pool definition", errors.ECODE_INVAL)
  
  return IPv4Network(*components)

