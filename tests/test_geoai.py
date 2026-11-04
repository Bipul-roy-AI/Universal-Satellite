import unittest
import test_raster as raster_fixtures

@unittest.skipUnless(raster_fixtures.RASTER_AVAILABLE,'Raster dependencies required')
class GeoAITests(unittest.TestCase):
    setUp=raster_fixtures.RasterTests.setUp
    raster=raster_fixtures.RasterTests.raster
    def test_sample_values_and_mask(self):
        from universal_satellite.geoai import RasterDataset
        a=self.raster('a',[[10,-9999]],scale=.1)
        b=self.raster('b',[[4,5]],scale=.1)
        ds=RasterDataset([{'optical':[a,b]}])
        sample=ds[0]['optical']
        self.assertEqual(len(ds),1)
        self.assertEqual(sample['data'].shape,(2,1,2))
        self.np.testing.assert_allclose(sample['data'],[[[1,0]],[[.4,.5]]])
        self.assertEqual(sample['valid'].tolist(),[[[True,False]],[[True,True]]])
        with self.assertRaises(ValueError):RasterDataset([{'optical':[a,b]}],max_pixels=1)[0]
