To start the frontend, launch a simple HTTP server (from the `kernel-workshop` directory) with:

```
python -m http.server
```

The frontend looks for a `block_frequencies.json` file in the 
[`data/op_code`](../data/op_code/) directory. The data should be
structured such as in [`block_frequencies.json.example`](../data/op_code/block_frequencies.json.example).

Then navigate to `http://localhost:8000/frontend/public/index.html` in your web browser.
