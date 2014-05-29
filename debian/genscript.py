#!/usr/bin/python

# Generate postinst/postrm for ganeti using doc/users/*

import os
import sys


def read_list(fname):
    with open(fname, "r") as f:
        return [ l.strip() for l in f ]

def read_pairs(fname):
    with open(fname, "r") as f:
        return [ l.strip().split(None, 1) for l in f ]

if len(sys.argv) != 3 or sys.argv[1] not in ('postinst', 'postrm'):
    sys.stderr.write("Usage: %s postinst|postrm DIR\n" % sys.argv[0])
    sys.exit(1)

root = os.path.join(sys.argv[2], 'doc/users')
debian_root = os.path.dirname(__file__)

out = ""
if sys.argv[1] == "postinst":
    out += "\t# Groups\n"
    for group in read_list(os.path.join(root, "groups")):
        out += "\taddgroup --quiet --system \"%s\"\n" % group
    out += "\n"

    out += "\t# Users\n"
    for user, group in read_pairs(os.path.join(root, "users")):
        out += "\tadduser --quiet --system --ingroup \"%s\" --no-create-home" \
               " --disabled-password --disabled-login" \
               " --home /var/lib/ganeti \"%s\"\n" % (group, user)
    out += "\n"

    out += "\t# Group memberships\n"
    for user, group in read_pairs(os.path.join(root, "groupmemberships")):
        out += "\tadduser --quiet \"%s\" \"%s\"\n" % (user, group)

elif sys.argv[1] == "postrm":
    out += "\t# Users\n"
    for user, _ in read_pairs(os.path.join(root, "users")):
        out += "\tdeluser --quiet --system \"%s\" || true\n" % user
    out += "\n"

    out += "\t# Groups\n"
    for group in read_list(os.path.join(root, "groups")):
        out += "\tdelgroup --quiet --system \"%s\" || true\n" % group
    out += "\n"


with open(os.path.join(debian_root, "ganeti.%s.in" % sys.argv[1])) as script:
    done = False
    for line in script:
        if line.strip() == "#GANETI_USERS#" and not done:
            sys.stdout.write(out)
            done = True
        else:
            sys.stdout.write(line)
