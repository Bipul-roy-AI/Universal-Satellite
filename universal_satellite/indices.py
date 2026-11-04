"""Versioned spectral-index registry and restricted arithmetic interpreter.

Formula data: Awesome Spectral Indices, MIT, copyright David Montero Loaiza.
No Python eval, attribute access, function calls or executable registry content.
"""
import ast
from functools import lru_cache
from importlib.resources import files
import json
import math
import operator

ROOT = files('universal_satellite').joinpath('data')
REGISTRY = json.loads(ROOT.joinpath('indices.json').read_text())['SpectralIndices']
CONSTANTS = json.loads(ROOT.joinpath('constants.json').read_text())
ALIASES = {'A':'aerosol','B':'blue','G':'green','G1':'green1','R':'red','RE1':'rededge',
           'RE2':'rededge2','RE3':'rededge3','N':'nir','N2':'nir08','S1':'swir16',
           'S2':'swir22','T':'thermal','T1':'thermal1','Y':'yellow',
           'VV':'vv','VH':'vh','HH':'hh','HV':'hv'}
OPERATORS = {ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
             ast.Div:operator.truediv,ast.Pow:operator.pow}
from collections import Counter
_COUNTS = Counter(key.lower() for key in REGISTRY)
NAMES = {key.lower() if _COUNTS[key.lower()]==1 else key:key for key in REGISTRY}

def normalize(name):
    if isinstance(name,str):
        if name in NAMES: return name
        if name.lower() in NAMES: return name.lower()
    raise ValueError(f'Unknown index or ambiguous name {name!r}; use the indices command.')

def definition(name):
    try:
        return REGISTRY[NAMES[normalize(name)]]
    except (KeyError, AttributeError):
        raise ValueError(f'Unknown index {name!r}; use the indices command.') from None


def required_bands(name):
    return tuple(ALIASES.get(x,x) for x in definition(name)['bands'] if x not in CONSTANTS)


def parameters(name, supplied=None):
    spec = definition(name)
    supplied = {} if supplied is None else supplied
    expected = {x for x in spec['bands'] if x in CONSTANTS}
    if not isinstance(supplied, dict) or set(supplied) - expected:
        raise ValueError(f'Parameters for {name}: {sorted(expected)}')
    result = {}
    for key in expected:
        # Scene-dependent coefficients must be explicit, including RWI's n.
        value = supplied.get(key, None if key == 'n' else CONSTANTS[key]['default'])
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(f'Provide finite parameter {key}: {CONSTANTS[key]["description"]}')
        result[key] = value
    return result


@lru_cache(maxsize=512)
def expression(formula):
    tree = ast.parse(formula, mode='eval')
    allowed = (ast.Expression,ast.BinOp,ast.UnaryOp,ast.USub,ast.UAdd,ast.Name,ast.Load,ast.Constant,*OPERATORS)
    if any(not isinstance(node,allowed) for node in ast.walk(tree)):
        raise ValueError('Index formula contains unsupported syntax')
    return tree.body


def _calculate(node, values):
    if isinstance(node,ast.Constant) and isinstance(node.value,(float,int)):
        return node.value
    if isinstance(node,ast.Name):
        return values[node.id]
    if isinstance(node,ast.BinOp):
        return OPERATORS[type(node.op)](_calculate(node.left,values),_calculate(node.right,values))
    if isinstance(node,ast.UnaryOp):
        value = _calculate(node.operand,values)
        return -value if isinstance(node.op,ast.USub) else value
    raise ValueError('Unsupported formula node')


def evaluate(name, bands, *, constants=None):
    """Evaluate calibrated scalars/arrays; invalid arithmetic becomes NaN.

    All array inputs must have equal shapes. Kernel inputs are precomputed kernel
    values, SAR inputs must use the units required by the referenced formula;
    wavelengths/scene-specific constants are never inferred from sensor names.
    """
    import numpy as np
    spec = definition(name)
    required = required_bands(name)
    if set(bands) != set(required):
        raise ValueError(f'{name.upper()} requires exactly these bands: {", ".join(required)}.')
    values = {k:np.float64(v) for k,v in parameters(name,constants).items()}
    arrays = []
    for symbol in spec['bands']:
        if symbol not in CONSTANTS:
            value = np.ma.asarray(bands[ALIASES.get(symbol,symbol)],dtype='float64').filled(np.nan)
            values[symbol] = value
            arrays.append(value)
    if len({a.shape for a in arrays}) != 1:
        raise ValueError('Index inputs must have equal shapes; implicit broadcasting is disabled')
    with np.errstate(all='ignore'):
        result = np.asarray(_calculate(expression(spec['formula']),values),dtype='float64')
    valid = np.isfinite(result)
    for a in arrays:
        valid = valid & np.isfinite(a)
    return np.where(valid,result,np.nan)


INDEX_BANDS = {name: required_bands(name) for name in NAMES}
BAND_NAMES = sorted({b for v in INDEX_BANDS.values() for b in v})
