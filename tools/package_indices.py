"""Refresh GIS menus and Node formula ASTs from the pinned Python registry."""
import ast
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from universal_satellite.indices import REGISTRY, CONSTANTS, INDEX_BANDS, BAND_NAMES, normalize

def tree(n):
    if isinstance(n,ast.Name):return {'symbol':n.id}
    if isinstance(n,ast.Constant):return {'number':n.value}
    if isinstance(n,ast.UnaryOp):return {'op':'neg' if isinstance(n.op,ast.USub) else 'pos','a':tree(n.operand)}
    if isinstance(n,ast.BinOp):return {'op':type(n.op).__name__,'a':tree(n.left),'b':tree(n.right)}
    raise ValueError('Unsupported formula syntax')

for folder in ['gis/arcgis','gis/qgis/universal_satellite_qgis']:
    (ROOT/folder/'indices.json').write_text(json.dumps({'indices':INDEX_BANDS,'bands':BAND_NAMES},indent=2)+'\n')
node={normalize(key):{**v,'expression':tree(ast.parse(v['formula'],mode='eval').body)} for key,v in REGISTRY.items()}
(ROOT/'javascript/data/indices.json').write_text(json.dumps(node,indent=2)+'\n')
(ROOT/'javascript/data/constants.json').write_text(json.dumps(CONSTANTS,indent=2)+'\n')
(ROOT/'javascript/data/LICENSE-spectral-indices.txt').write_text((ROOT/'universal_satellite/data/LICENSE-spectral-indices.txt').read_text())
(ROOT/'javascript/index-names.d.ts').write_text('export type IndexName = '+ ' | '.join(json.dumps(k) for k in INDEX_BANDS)+';\n')
