"""Native QGIS Processing provider."""

from qgis.core import QgsProcessingProvider

from .algorithms import DownloadAssets, RasterIndex, SearchScenes, SpectralIndex, EnvironmentalProfile, CropRaster


class UniversalSatelliteProvider(QgsProcessingProvider):
    def id(self):
        return "universal_satellite"

    def name(self):
        return "Universal Satellite"

    def longName(self):
        return "Universal Satellite — archive discovery, image downloads and raster indices"

    def loadAlgorithms(self):
        self.addAlgorithm(SearchScenes())
        self.addAlgorithm(DownloadAssets())
        self.addAlgorithm(RasterIndex())
        self.addAlgorithm(SpectralIndex())
        self.addAlgorithm(EnvironmentalProfile())
        self.addAlgorithm(CropRaster())
