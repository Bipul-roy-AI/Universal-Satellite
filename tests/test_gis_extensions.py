import sys,types,unittest
from unittest.mock import Mock,patch
from test_gis_contract import fake_qgis,load_module,ROOT
from universal_satellite.indices import INDEX_BANDS

class ExtendedGisTests(unittest.TestCase):
    def test_qgis_full_index_routes_three_bands_and_constants(self):
        with patch.dict(sys.modules,fake_qgis()):
            module=load_module('qgis_extended',ROOT/'gis/qgis/universal_satellite_qgis/algorithms.py')
            tool=module.SpectralIndex()
            tool.parameterAsEnum=Mock(return_value=list(INDEX_BANDS).index('evi'))
            tool.parameterAsFile=Mock(side_effect=lambda p,key,c:key+'.tif')
            tool.parameterAsFileOutput=Mock(return_value='out.tif')
            tool.parameterAsString=Mock(return_value='{"g":2.5}')
            feedback=Mock();feedback.isCanceled.return_value=False
            with patch('universal_satellite.raster.compute_index') as compute:
                self.assertEqual(tool.processAlgorithm({},None,feedback),{'OUTPUT':'out.tif'})
                compute.assert_called_once_with('evi','out.tif',constants={'g':2.5},nir='nir.tif',red='red.tif',blue='blue.tif')
    def test_arcgis_dynamic_required_fields_and_three_band_execute(self):
        arcpy=types.ModuleType('arcpy');arcpy.ExecuteError=RuntimeError
        arcpy.Parameter=lambda **kwargs:types.SimpleNamespace(**kwargs,filter=types.SimpleNamespace(),valueAsText=None)
        with patch.dict(sys.modules,{'arcpy':arcpy}):
            module=load_module('arcgis_extended',ROOT/'gis/arcgis/UniversalSatellite.pyt')
            tool=module.SpectralIndex();params=tool.getParameterInfo()
            params[0].valueAsText='evi';params[1].valueAsText='out.tif';params[2].valueAsText='{}'
            for p in params[3:]:p.valueAsText=p.name+'.tif'
            tool.updateParameters(params)
            self.assertEqual({p.name for p in params[3:] if p.enabled},{'nir','red','blue'})
            with patch('universal_satellite.raster.compute_index') as compute:
                tool.execute(params,Mock())
                compute.assert_called_once_with('evi','out.tif',constants={},nir='nir.tif',red='red.tif',blue='blue.tif')
