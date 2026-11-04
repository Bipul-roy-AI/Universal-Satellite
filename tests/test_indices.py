import unittest
from universal_satellite.indices import evaluate, definition, expression, INDEX_BANDS, REGISTRY, parameters

class IndexTests(unittest.TestCase):
    def test_known_values(self):
        self.assertAlmostEqual(float(evaluate('ndvi',{'nir':0.8,'red':0.2})),0.6)
        self.assertAlmostEqual(float(evaluate('savi',{'nir':0.8,'red':0.2},constants={'L':0.5})),0.6)
        self.assertAlmostEqual(float(evaluate('ndrei',{'nir':0.8,'rededge':0.2})),0.6)
    def test_invalid_math_and_shape(self):
        import numpy as np
        self.assertTrue(np.isnan(evaluate('ndvi',{'nir':0,'red':0})))
        with self.assertRaises(ValueError): evaluate('ndvi',{'nir':[1,2],'red':1})
        with self.assertRaises(ValueError): expression('__import__("os").getcwd()')
    def test_all_registry_formulas_execute(self):
        import numpy as np
        for name, bands in INDEX_BANDS.items():
            with self.subTest(name=name):
                constants = {x:2.0 for x in definition(name)['bands'] if x not in bands and x in __import__('universal_satellite.indices',fromlist=['CONSTANTS']).CONSTANTS}
                actual = evaluate(name,{b:np.array([0.2,0.8]) for b in bands},constants=constants)
                self.assertEqual(actual.shape,(2,))
                self.assertTrue(definition(name)['reference'].startswith('http'))
    def test_required_wavelengths_not_guessed(self):
        with self.assertRaises(ValueError): parameters('ndgi')

    def test_case_collisions_remain_distinct(self):
        self.assertEqual(len(INDEX_BANDS),len(REGISTRY))
        self.assertNotEqual(definition('BAI')['formula'],definition('BaI')['formula'])
        self.assertNotEqual(definition('MSR705')['formula'],definition('mSR705')['formula'])
        with self.assertRaises(ValueError): definition('bai')
