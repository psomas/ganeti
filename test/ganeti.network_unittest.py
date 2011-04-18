#!/usr/bin/python
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
# 0.0510-1301, USA.


"""Script for unittesting the network module"""


import unittest

from ganeti import objects
from ganeti import network
from ganeti import errors

import testutils

class TestNetwork(unittest.TestCase):
  def testNetwork(self):
    net = network.ipaddr.IPNetwork("192.0.2.0/24")
    gateway = network.ipaddr.IPAddress("192.0.2.1")

    res = network.bitarray(net.numhosts)
    res.setall(False)
    ext = network.bitarray(net.numhosts)
    ext.setall(False)

    extres = [0, -1, -2]
    for idx in extres:
      ext[idx] = True

    obj = objects.Network(network=str(net), gateway=str(gateway),
                        reservations=network.b64encode(res.tostring()),
                        ext_reservations=network.b64encode(ext.tostring()),
                        family=4)

    pool = network.AddressPool(obj)

    free = pool.GetFreeCount()
    reserved = pool.GetReservedCount()
    self.assertEqual(free, net.numhosts - len(extres))
    self.assertEqual(reserved, len(extres))

    # Our network is not full and must be valid
    self.assertEqual(pool.IsFull(), False)
    self.assertEqual(pool.Validate(), True)

    # Network address must be reserved
    self.assertEqual(pool.IsReserved(net[extres[0]]), True)
    self.assertRaises(errors.AddressPoolError, pool.Reserve, net[extres[0]])

    # Release a reserved address and check count consistency
    pool.Release(net[extres[-1]], external=True)
    self.assertEqual(pool.GetFreeCount(), free + 1)
    self.assertEqual(pool.GetReservedCount(), reserved - 1)

    # Check that free addresses are returned in order
    self.assertEqual(pool.GetFreeAddress(), str(net[1]))
    self.assertEqual(pool.GetFreeAddress(), str(net[2]))


    # GenerateFree should return an iterator generating
    # at most 64 free addresses
    i = 0
    itr = pool.GenerateFree()

    while True:
      try:
        itr()
        i += 1
      except errors.AddressPoolError:
        break
      except StopIteration:
        break

    self.assertEqual(i, 64)

    # Check to see if we can actually exhaust the space
    addresses = []
    def exhaust(addresses):
      for i in range(0, 255):
        addresses.append(pool.GetFreeAddress())

    self.assertRaises(errors.AddressPoolError, exhaust, addresses)

    # Check that all reservations where taken from the proper pool
    self.assertEqual(pool.reservations.count(True), len(addresses) + 2)

    # Check that we didn't generate any duplicates
    self.assertEqual(len(addresses), len(set(addresses)))

    # Check serialization and de-serialization
    new_pool = network.AddressPool(obj)
    self.assertEqual(new_pool.reservations.to01(), pool.reservations.to01())
    self.assertEqual(new_pool.ext_reservations.to01(),
                     pool.ext_reservations.to01())


if __name__ == '__main__':
  testutils.GanetiTestProgram()
