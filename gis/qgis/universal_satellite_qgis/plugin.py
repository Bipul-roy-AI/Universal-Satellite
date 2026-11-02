"""Register and unregister this plugin's Processing provider."""

from qgis.core import QgsApplication

from .provider import UniversalSatelliteProvider


class UniversalSatellitePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initGui(self):
        self.provider = UniversalSatelliteProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
