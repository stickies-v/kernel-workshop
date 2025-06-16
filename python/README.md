# Python Workshop

`bitcoinkernel` exposes a C API. It mostly operates on pointers (which
usually, but not always) are managed by the user. This combined with the
fact that C does not have classes makes the API quite different from how
one would organize a Python API.

Wrapper libraries (such as [`py-bitcoinkernel`](https://github.com/stickies-v/py-bitcoinkernel))
hide this "awkwardness" and expose a much more concise, Pythonic
interface. To give maximum insight into the `bitcoinkernel` API, we
will use the raw API in this workshop, while also offering a
[`wrapped/`](./src/wrapped/) version using the `py-bitcoinkernel` library
to highlight the difference. The `wrapped` version can be used as a 
guideline, too.

Both versions use shared code from the [`common/`](./src/common/)
library, which you shouldn't have to modify in this workshop.

## Prerequisites

- Python 3.10 or later
- A Bitcoin Core datadir of the chain you are interested in. For this
  workshop, signet or mainnet are recommended. Because `bitcoind`
  requires exclusive access to the datadir, it is recommended you copy
  the `blocks/` and `chainstate/` directories to a separate directory
  for this workshop.
- `py-bitcoinkernel` and `bitcoinkernel` are dependencies of this
  project, and are installed automatically when you install the python
  package. Please refer to the `py-bitcoinkernel` [installation
  instructions](https://github.com/stickies-v/py-bitcoinkernel?tab=readme-ov-file#installation)
  for more information.

### Installation

```
cd python
python -m venv .venv
source .venv/bin/activate
pip install -e . -v
```

## Running the workshop

1. Complete the code in the [`./src/raw/main.py`](./src/raw/main.py)
   file.
2. Run the application (see [args.py](./src/common/args.py) for more
   information on which arguments are available), as e.g.:
   ```sh
   raw --start_height=-10 --datadir=/tmp/kernel-workshop
   ```
3. If the application runs successfully, you should see a
   `block_frequencies.json` file in the `data/op_code/frequency/`
   directory, containing the frequency of each TapScript OP_CODE in the
   specified blocks.
4. Optionally, visualize the results with the [frontend](../frontend/).

> [!NOTE] The solutions can be found in the
> [`main.py`](https://github.com/stickies-v/kernel-workshop/blob/solutions/python/src/raw/main.py)
> file in the `solutions` branch.
