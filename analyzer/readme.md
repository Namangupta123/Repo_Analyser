# SystemLab Repository Analyzer

The analyzer is an independent Python package that produces a deterministic file dependency graph from a local repository or a public GitHub repository.

```bash
python -m pip install -e ".[dev]"
python -m repo_analyzer ./path/to/repository
python -m repo_analyzer https://github.com/owner/repository --output ./analysis
```

Each run writes `graph.json`, `report.json`, and `errors.json`. The analyzer does not depend on the SystemLab backend or frontend.
