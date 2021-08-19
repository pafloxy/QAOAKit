# `QAOAKit`: A Toolkit for Reproducible Application and Verification of QAOA

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

### Example

```python
import networkx as nx
from qiskit.providers.aer import AerSimulator
from QAOAKit import opt_angles_for_graph, angles_to_qaoa_format
from QAOAKit.qaoa import get_maxcut_qaoa_circuit

# build graph
G = nx.star_graph(5)
# grab optimal angles
p = 3
angles = angles_to_qaoa_format(opt_angles_for_graph(G,p))
# build circuit
qc = get_maxcut_qaoa_circuit(G, angles['beta'], angles['gamma'])
qc.measure_all()
# run circuit
backend = AerSimulator()
print(backend.run(qc).result().get_counts())
```

Almost all counts you get should correspond to one of the two optimal MaxCut solutions for star graph: `000001` or `111110`.

### Advanced usage

More advanced examples are available in `examples` folder:

- Using optimal parameters in state-of-the-art tensor network QAOA simulator [QTensor](https://github.com/danlkv/QTensor): `examples/qtensor_get_energy.py`
- Transfering parameters to large unseen instances: `examples/examples/Transferability to unseen instances.ipynb`


### Installation

#### Install from source

Optional: create an Anaconda environment

```
conda create -n qaoa python=3
conda activate qaoa
```

Note that current implementation requires significant amounts of RAM (~5GB) as it loads the entire dataset into memory.

```
git clone https://github.com/QAOAKit/QAOAKit.git
cd QAOAKit
pip install -e .
python -m QAOAKit.build_tables
pytest
```

If you have an issue like "Illegal Instruction (core dumped)", you may have to force pip to recompile Nauty binaries (`pip install --no-binary pynauty pynauty`) or install Nauty separately: https://pallini.di.uniroma1.it/

You can set up the linter to run before every commit.
```
pip install pre-commit
pre-commit install
```
