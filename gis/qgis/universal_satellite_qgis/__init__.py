"""QGIS plugin entry point; core package is installed in QGIS's Python."""


def classFactory(iface):
    from .plugin import UniversalSatellitePlugin

    return UniversalSatellitePlugin(iface)
