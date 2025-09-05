# Generate 5-level tree excluding common library folders
tree -L 5 -I "node_modules|venv|env|__pycache__|.git|dist|build|*.egg-info|site-packages" > clean_tree_5.txt

# Generate 7-level tree excluding common library folders
tree -L 7 -I "node_modules|venv|env|__pycache__|.git|dist|build|*.egg-info|site-packages" > clean_tree_7.txt