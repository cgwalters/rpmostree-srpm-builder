#!/usr/bin/python3
#
# Some code derived from dnf-plugins-core builddep.py
#
# Copyright (C) 2013-2015  Red Hat, Inc.
# Copyright (C) 2015 Igor Gnatenko
# Copyright (C) 2018 Colin Walters <walters@verbum.org>
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.

import os, sys, subprocess
import argparse
import rpm

parser = argparse.ArgumentParser()
parser.add_argument("--contextdir", '-d', help="Directory with rpm-ostree container state",
                    action='store', required=True)
parser.add_argument("--rpmrepo", '-r', help="Name of rpm-md repository to enable",
                    action='append', default=[], required=True)
parser.add_argument("srpm", help="Path to source rpm")

args = parser.parse_args()

def _rpm_dep2reldep_str(rpm_dep):
    return rpm_dep.DNEVR()[2:]

class SRPM(object):
    def __init__(self, ts, fd):
        self._h = ts.hdrFromFdno(fd)
        if not self._h[rpm.RPMTAG_SOURCEPACKAGE]:
            raise Exception("Not a source package")

    def name(self):
        return self._h[rpm.RPMTAG_NAME].decode('utf-8')

    def deps(self):
        ds = self._h.dsFromHeader('requirename')
        deps = []
        for dep in ds:
            reldep_str = _rpm_dep2reldep_str(dep)
            if reldep_str.startswith('rpmlib('):
                continue
            deps.append(reldep_str)
        return deps

# Blah, why does parsing a SRPM require a ts?  Hopefully this doesn't
# try to open up the host's rpmdb.
ts = rpm.TransactionSet('/')
ts.setVSFlags((rpm._RPMVSF_NOSIGNATURES|rpm._RPMVSF_NODIGESTS))

deps = []
name = None
with open(args.srpm) as f:
    srpm = SRPM(ts, f.fileno())
    name = srpm.name()
    deps = srpm.deps()

print(name)
print(deps)

confpath = '{}/buildroot-{}.conf'.format(args.contextdir, name)
with open(confpath, 'w') as o:
    o.write('[tree]\nref=buildroot-{}\npackages={};\nrepos={};\n'.format(
        name, ';'.join(deps), ';'.join(args.rpmrepo)))
subprocess.check_call(['rpm-ostree', 'ex', 'container', 'assemble', os.path.basename(confpath)],
                      cwd=args.contextdir)
