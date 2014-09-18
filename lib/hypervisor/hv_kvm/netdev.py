#
#

# Copyright (C) 2014 Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""KVM hypervisor tap device helpers

"""

import os
import logging
import struct
import fcntl

from ganeti import errors


# TUN/TAP driver constants, taken from <linux/if_tun.h>
# They are architecture-independent and already hardcoded in qemu-kvm source,
# so we can safely include them here.
TUNSETIFF = 0x400454ca
TUNGETIFF = 0x800454d2
TUNGETFEATURES = 0x800454cf
IFF_TAP = 0x0002
IFF_NO_PI = 0x1000
IFF_ONE_QUEUE = 0x2000
IFF_VNET_HDR = 0x4000


def _GetTunFeatures(fd, _ioctl=fcntl.ioctl):
  """Retrieves supported TUN features from file descriptor.

  @see: L{_ProbeTapVnetHdr}

  """
  req = struct.pack("I", 0)
  try:
    buf = _ioctl(fd, TUNGETFEATURES, req)
  except EnvironmentError, err:
    logging.warning("ioctl(TUNGETFEATURES) failed: %s", err)
    return None
  else:
    (flags, ) = struct.unpack("I", buf)
    return flags


def _ProbeTapVnetHdr(fd, _features_fn=_GetTunFeatures):
  """Check whether to enable the IFF_VNET_HDR flag.

  To do this, _all_ of the following conditions must be met:
   1. TUNGETFEATURES ioctl() *must* be implemented
   2. TUNGETFEATURES ioctl() result *must* contain the IFF_VNET_HDR flag
   3. TUNGETIFF ioctl() *must* be implemented; reading the kernel code in
      drivers/net/tun.c there is no way to test this until after the tap device
      has been created using TUNSETIFF, and there is no way to change the
      IFF_VNET_HDR flag after creating the interface, catch-22! However both
      TUNGETIFF and TUNGETFEATURES were introduced in kernel version 2.6.27,
      thus we can expect TUNGETIFF to be present if TUNGETFEATURES is.

   @type fd: int
   @param fd: the file descriptor of /dev/net/tun

  """
  flags = _features_fn(fd)

  if flags is None:
    # Not supported
    return False

  result = bool(flags & IFF_VNET_HDR)

  if not result:
    logging.warning("Kernel does not support IFF_VNET_HDR, not enabling")

  return result


def OpenTap(vnet_hdr=True, name=""):
  """Open a new tap device and return its file descriptor.

  This is intended to be used by a qemu-type hypervisor together with the -net
  tap,fd=<fd> command line parameter.

  @type vnet_hdr: boolean
  @param vnet_hdr: Enable the VNET Header

  @type name: string
  @param name: name for the TAP interface being created; if an empty
               string is passed, the OS will generate a unique name

  @return: (ifname, tapfd)
  @rtype: tuple

  """
  try:
    tapfd = os.open("/dev/net/tun", os.O_RDWR)
  except EnvironmentError:
    raise errors.HypervisorError("Failed to open /dev/net/tun")

  flags = IFF_TAP | IFF_NO_PI | IFF_ONE_QUEUE

  if vnet_hdr and _ProbeTapVnetHdr(tapfd):
    flags |= IFF_VNET_HDR

  # The struct ifreq ioctl request (see netdevice(7))
  ifr = struct.pack("16sh", name, flags)

  try:
    res = fcntl.ioctl(tapfd, TUNSETIFF, ifr)
  except EnvironmentError, err:
    raise errors.HypervisorError("Failed to allocate a new TAP device: %s" %
                                 err)

  # Get the interface name from the ioctl
  ifname = struct.unpack("16sh", res)[0].strip("\x00")
  return (ifname, tapfd)
