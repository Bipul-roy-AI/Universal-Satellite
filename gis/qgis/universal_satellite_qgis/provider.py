"""Native QGIS Processing provider."""

from qgis.core import QgsProcessingProvider

from .algorithms import RasterIndex, SearchScenes


class UniversalSatelliteProvider(QgsProcessingProvider):
    def id(self):
        return "universal_satellite"

    def name(self):
        return "Universal Satellite"

    def longName(self):
        return "Universal Satellite — archive discovery and raster indices"

    def loadAlgorithms(self):
        self.addAlgorithm(SearchScenes())
        self.addAlgorithm(RasterIndex())
