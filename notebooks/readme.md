# Notebooks

Jupyter notebooks for exploratory data analysis and experiments.

## Notebook Guidelines

- The first cell must contain all imports required by the notebook.
- If the notebook uses shared file paths, configuration values, or parameters, the
  second cell must define them as global constants.
- Break work into small, logically separated cells.
- Data loading should appear after the imports and constants cells.
- Do not wrap the entire notebook in functions.
- Use functions only when reuse is likely or logic becomes repetitive.
- Keep notebook logic simple and readable for exploratory analysis.
- The notebook must support Run All in execution order without logical errors.
- Prefer fast failure over silent logical errors.
- Notebook work is iterative: adding new cells and revising earlier cells is acceptable,
  but the final state must remain rerunnable.
