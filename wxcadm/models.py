from collections import namedtuple

LocationEmergencySettings = namedtuple('LocationEmergencySettings', 'integration routing')
""" Enhanced Emergency Call Settings (i.e. RedSky settings) for a Location

Attributes:
    integration (bool): Whether the RedSky integration is enabled to receive HELD data
    routing (bool): Whether 911 calls are routed to RedSky

"""