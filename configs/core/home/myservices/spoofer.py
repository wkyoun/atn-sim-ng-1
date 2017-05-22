#
# CORE
# Copyright (c)2010-2012 the Boeing Company.
# See the LICENSE file included in this distribution.
#
''' Sample user-defined service.
'''

import os

from core.service import CoreService, addservice
from core.misc.ipaddr import IPv4Prefix, IPv6Prefix


class AdsbSpoofer(CoreService):
    ''' This is a sample user-defined service.
    '''
    # a unique name is required, without spaces
    _name = "AdsbReplay"
    # you can create your own group here
    _group = "Security"
    # list of other services this service depends on
    _depends = ()
    # per-node directories
    _dirs = ()
    # generated files (without a full path this file goes in the node's dir,
    #  e.g. /tmp/pycore.12345/n1.conf/)
    _configs = ('ghost.sh', )
    # this controls the starting order vs other enabled services
    _startindex = 50
    # list of startup commands, also may be generated during startup
    _startup = ('sh ghost.sh',)
    # list of shutdown commands
    _shutdown = ('pkill python',)

    @classmethod
    def generateconfig(cls, node, filename, services):
        ''' Return a string that will be written to filename, or sent to the
            GUI for user customization.
        '''
        # get lat/lng position
        l_lat, l_lng, l_alt = node.session.location.getgeo(node.position.x, node.position.y, node.position.z)

        cfg = "#!/bin/sh\n"
        cfg += "# auto-generated by AdsbSpoofer (adsb_spoofer.py)\n"
        cfg += "sleep 15\n"
        #cfg += "python -m atn.surveillance.adsb.security.adsb_ghost --rewrite-icao24 --flood\n"
        cfg += "python -m atn.surveillance.adsb.security.adsb_ghost {} {} {} --rewrite-icao24 \n".format(l_lat, l_lng, l_alt)

        return cfg

    @staticmethod
    def subnetentry(x):
        ''' Generate a subnet declaration block given an IPv4 prefix string
            for inclusion in the config file.
        '''
        if x.find(":") >= 0:
            # this is an IPv6 address
            return ""
        else:
            net = IPv4Prefix(x)
            return 'echo "  network %s"' % (net)

# this line is required to add the above class to the list of available services
addservice(AdsbSpoofer)
