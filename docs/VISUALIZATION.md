# Memory Visualization Guide

This guide explains how to visualize memory embeddings exported from the relational state engine.

## Overview

The MCP server provides an `export_embeddings` tool that exports 384-dimensional embedding vectors with metadata. These embeddings can be reduced to 2D or 3D for visualization using dimensionality reduction techniques.

**Recommended Tools**:
- **UMAP** (Uniform Manifold Approximation and Projection) - Best for preserving global structure
- **t-SNE** (t-Distributed Stochastic Neighbor Embedding) - Good for local structure
- **PCA** (Principal Component Analysis) - Fast, linear reduction

## Quick Start

### 1. Export Embeddings

```bash
curl -X POST http://localhost:8000/mcp/tools/export_embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "rob-mosher",
    "max_entries": 1000,
    "include_metadata": true
  }' > embeddings.json
```

### 2. Visualize with Python

```python
import json
import umap
import matplotlib.pyplot as plt

# Load data
with open('embeddings.json') as f:
    data = json.load(f)

embeddings = [e['embedding'] for e in data['embeddings']]
types = [e['type'] for e in data['embeddings']]

# Reduce to 2D
reducer = umap.UMAP(n_components=2)
coords_2d = reducer.fit_transform(embeddings)

# Plot
for mem_type in set(types):
    mask = [t == mem_type for t in types]
    plt.scatter(
        coords_2d[mask, 0],
        coords_2d[mask, 1],
        label=mem_type,
        alpha=0.6
    )
plt.legend()
plt.savefig('embeddings.png', dpi=300)
```

## Python Visualization Examples

### Option 1: UMAP (Recommended)

UMAP preserves both local and global structure better than t-SNE.

```python
import json
import umap
import matplotlib.pyplot as plt
import pandas as pd

# Load embeddings
with open('embeddings.json') as f:
    data = json.load(f)

# Extract data
embeddings = [e['embedding'] for e in data['embeddings']]
metadata = pd.DataFrame([
    {
        'author': e['author'],
        'type': e['type'],
        'promotion_depth': e['promotion_depth'],
        'timestamp': e['timestamp'],
        'preview': e['content_preview'][:50]
    }
    for e in data['embeddings']
])

# Reduce to 2D with UMAP
reducer = umap.UMAP(
    n_components=2,
    n_neighbors=15,
    min_dist=0.1,
    metric='cosine',
    random_state=42
)
coords_2d = reducer.fit_transform(embeddings)

# Create figure with subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Plot 1: Color by type
for mem_type in metadata['type'].unique():
    mask = metadata['type'] == mem_type
    ax1.scatter(
        coords_2d[mask, 0],
        coords_2d[mask, 1],
        label=mem_type,
        alpha=0.6,
        s=50
    )
ax1.legend()
ax1.set_title('Memory Embeddings by Type')
ax1.set_xlabel('UMAP Dimension 1')
ax1.set_ylabel('UMAP Dimension 2')

# Plot 2: Color by author
for author in metadata['author'].unique():
    mask = metadata['author'] == author
    ax2.scatter(
        coords_2d[mask, 0],
        coords_2d[mask, 1],
        label=author,
        alpha=0.6,
        s=50
    )
ax2.legend()
ax2.set_title('Memory Embeddings by Author')
ax2.set_xlabel('UMAP Dimension 1')
ax2.set_ylabel('UMAP Dimension 2')

plt.tight_layout()
plt.savefig('memory_embeddings_umap.png', dpi=300, bbox_inches='tight')
print("Saved to memory_embeddings_umap.png")
```

### Option 2: t-SNE

Good for exploring local structure and clusters.

```python
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

# Reduce to 2D with t-SNE
tsne = TSNE(
    n_components=2,
    perplexity=30,
    learning_rate=200,
    n_iter=1000,
    random_state=42
)
coords_2d = tsne.fit_transform(embeddings)

# Plot
plt.figure(figsize=(12, 8))
for mem_type in metadata['type'].unique():
    mask = metadata['type'] == mem_type
    plt.scatter(
        coords_2d[mask, 0],
        coords_2d[mask, 1],
        label=mem_type,
        alpha=0.6,
        s=50
    )
plt.legend()
plt.title('Memory Embeddings (t-SNE)')
plt.xlabel('t-SNE Dimension 1')
plt.ylabel('t-SNE Dimension 2')
plt.savefig('memory_embeddings_tsne.png', dpi=300)
```

### Option 3: PCA (Fastest)

Linear dimensionality reduction - fast but may not capture complex structure.

```python
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# Reduce to 2D with PCA
pca = PCA(n_components=2, random_state=42)
coords_2d = pca.fit_transform(embeddings)

# Show variance explained
print(f"Variance explained: {pca.explained_variance_ratio_.sum():.2%}")

# Plot
plt.figure(figsize=(12, 8))
for mem_type in metadata['type'].unique():
    mask = metadata['type'] == mem_type
    plt.scatter(
        coords_2d[mask, 0],
        coords_2d[mask, 1],
        label=mem_type,
        alpha=0.6,
        s=50
    )
plt.legend()
plt.title('Memory Embeddings (PCA)')
plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%})')
plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%})')
plt.savefig('memory_embeddings_pca.png', dpi=300)
```

## Interactive Visualization with Plotly

Create interactive HTML visualizations:

```python
import plotly.express as px
import pandas as pd

# Prepare data
df_coords = metadata.copy()
df_coords['x'] = coords_2d[:, 0]
df_coords['y'] = coords_2d[:, 1]

# Interactive scatter plot
fig = px.scatter(
    df_coords,
    x='x',
    y='y',
    color='type',
    hover_data=['author', 'timestamp', 'preview'],
    title='Interactive Memory Embeddings (UMAP 2D)',
    labels={'x': 'UMAP Dimension 1', 'y': 'UMAP Dimension 2'}
)

# Update layout
fig.update_layout(
    width=1200,
    height=800,
    hovermode='closest'
)

# Save as HTML
fig.write_html('embeddings_interactive.html')
print("Saved to embeddings_interactive.html - open in browser")
```

## 3D Visualization

Visualize in 3D for additional insight:

```python
import plotly.express as px

# Reduce to 3D with UMAP
reducer_3d = umap.UMAP(n_components=3, random_state=42)
coords_3d = reducer_3d.fit_transform(embeddings)

# Prepare data
df_3d = metadata.copy()
df_3d['x'] = coords_3d[:, 0]
df_3d['y'] = coords_3d[:, 1]
df_3d['z'] = coords_3d[:, 2]

# 3D scatter plot
fig = px.scatter_3d(
    df_3d,
    x='x',
    y='y',
    z='z',
    color='type',
    hover_data=['author', 'preview'],
    title='Memory Embeddings (UMAP 3D)'
)

fig.update_layout(
    scene=dict(
        xaxis_title='UMAP Dimension 1',
        yaxis_title='UMAP Dimension 2',
        zaxis_title='UMAP Dimension 3'
    ),
    width=1200,
    height=800
)

fig.write_html('embeddings_3d.html')
print("Saved to embeddings_3d.html")
```

## Clustering Analysis

Identify clusters in the embedding space:

```python
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt

# Cluster embeddings
clustering = DBSCAN(eps=0.5, min_samples=3).fit(coords_2d)
labels = clustering.labels_

# Add to metadata
metadata['cluster'] = labels

# Plot clusters
plt.figure(figsize=(12, 8))
unique_labels = set(labels)
colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)))

for k, col in zip(unique_labels, colors):
    if k == -1:
        # Noise points
        col = [0, 0, 0, 1]
        label = 'Noise'
    else:
        label = f'Cluster {k}'

    class_member_mask = (labels == k)
    xy = coords_2d[class_member_mask]
    plt.scatter(xy[:, 0], xy[:, 1], c=[col], label=label, alpha=0.6, s=50)

plt.legend()
plt.title('Memory Clusters (DBSCAN)')
plt.xlabel('UMAP Dimension 1')
plt.ylabel('UMAP Dimension 2')
plt.savefig('memory_clusters.png', dpi=300)

# Analyze clusters
print("\nCluster Distribution:")
print(metadata['cluster'].value_counts().sort_index())
```

## Time-based Animation

Animate memory evolution over time:

```python
import plotly.express as px
import pandas as pd

# Prepare data with timestamps
df_coords['timestamp'] = pd.to_datetime(df_coords['timestamp'])
df_coords = df_coords.sort_values('timestamp')
df_coords['date'] = df_coords['timestamp'].dt.date.astype(str)

# Create animation
fig = px.scatter(
    df_coords,
    x='x',
    y='y',
    animation_frame='date',
    color='type',
    hover_data=['author', 'preview'],
    title='Memory Evolution Over Time',
    labels={'x': 'UMAP Dimension 1', 'y': 'UMAP Dimension 2'}
)

fig.update_layout(width=1200, height=800)
fig.write_html('embeddings_timeline.html')
print("Saved to embeddings_timeline.html - use slider to see evolution")
```

## Heatmap Visualization

Visualize density of memories:

```python
import seaborn as sns
import numpy as np

# Create 2D histogram
plt.figure(figsize=(12, 8))
plt.hexbin(coords_2d[:, 0], coords_2d[:, 1], gridsize=30, cmap='YlOrRd')
plt.colorbar(label='Memory Count')
plt.title('Memory Density Heatmap')
plt.xlabel('UMAP Dimension 1')
plt.ylabel('UMAP Dimension 2')
plt.savefig('memory_heatmap.png', dpi=300)
```

## Comparing Multiple Entities

Compare embeddings across different entities:

```python
# Export for each entity
entities = ["rob-mosher", "claude-sonnet-4.5"]
all_embeddings = []
all_metadata = []

for entity in entities:
    # (Use curl to export for each entity)
    # ... load data ...
    all_embeddings.extend(embeddings)
    all_metadata.extend(metadata)

# Reduce all together
reducer = umap.UMAP(n_components=2, random_state=42)
all_coords = reducer.fit_transform(all_embeddings)

# Plot with entity colors
plt.figure(figsize=(12, 8))
for entity in entities:
    mask = [m['author'] == entity for m in all_metadata]
    plt.scatter(
        all_coords[mask, 0],
        all_coords[mask, 1],
        label=entity,
        alpha=0.6,
        s=50
    )
plt.legend()
plt.title('Memory Embeddings Across Entities')
plt.savefig('entity_comparison.png', dpi=300)
```

## Installation

Install required packages:

```bash
# Basic visualization
pip install umap-learn matplotlib pandas

# Interactive visualization
pip install plotly

# Advanced analysis
pip install scikit-learn seaborn
```

## Complete Script

Save as `visualize_memories.py`:

```python
#!/usr/bin/env python3
"""
Visualize memory embeddings from relational state engine.

Usage:
    python visualize_memories.py embeddings.json
"""
import sys
import json
import umap
import matplotlib.pyplot as plt
import pandas as pd

def main(embeddings_file):
    # Load data
    with open(embeddings_file) as f:
        data = json.load(f)

    print(f"Loaded {data['total_exported']} embeddings")
    print(f"Embedding dimension: {data['embedding_dim']}")

    # Extract embeddings and metadata
    embeddings = [e['embedding'] for e in data['embeddings']]
    metadata = pd.DataFrame([
        {
            'author': e['author'],
            'type': e['type'],
            'promotion_depth': e['promotion_depth'],
            'timestamp': e['timestamp'],
        }
        for e in data['embeddings']
    ])

    # Reduce to 2D
    print("Reducing to 2D with UMAP...")
    reducer = umap.UMAP(n_components=2, random_state=42)
    coords_2d = reducer.fit_transform(embeddings)

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # By type
    for mem_type in metadata['type'].unique():
        mask = metadata['type'] == mem_type
        ax1.scatter(coords_2d[mask, 0], coords_2d[mask, 1], label=mem_type, alpha=0.6)
    ax1.legend()
    ax1.set_title('By Type')
    ax1.set_xlabel('UMAP 1')
    ax1.set_ylabel('UMAP 2')

    # By author
    for author in metadata['author'].unique():
        mask = metadata['author'] == author
        ax2.scatter(coords_2d[mask, 0], coords_2d[mask, 1], label=author, alpha=0.6)
    ax2.legend()
    ax2.set_title('By Author')
    ax2.set_xlabel('UMAP 1')
    ax2.set_ylabel('UMAP 2')

    plt.tight_layout()
    output_file = embeddings_file.replace('.json', '_viz.png')
    plt.savefig(output_file, dpi=300)
    print(f"Saved visualization to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python visualize_memories.py embeddings.json")
        sys.exit(1)
    main(sys.argv[1])
```

Run with:
```bash
python visualize_memories.py embeddings.json
```

## Tips and Best Practices

### UMAP Parameters

- **`n_neighbors`** (default: 15): Controls local vs global structure
  - Smaller (5-10): Emphasizes local structure
  - Larger (30-50): Emphasizes global structure

- **`min_dist`** (default: 0.1): Minimum distance between points
  - Smaller (0.0-0.1): Tighter clusters
  - Larger (0.3-0.5): More spread out

- **`metric`** (default: 'euclidean'): Distance metric
  - 'cosine': Good for high-dimensional embeddings (recommended)
  - 'euclidean': Standard distance

### Performance

- **Large datasets** (>10K embeddings): Use PCA first to reduce to ~50 dimensions, then apply UMAP
- **Memory constraints**: Use `low_memory=True` in UMAP
- **Reproducibility**: Always set `random_state=42`

### Interpretation

- **Clusters**: Points close together are semantically similar
- **Outliers**: Points far from others may be unique or unusual memories
- **Paths**: Gradients may show semantic evolution over time
- **Colors**: Use consistent color schemes across visualizations

## JavaScript Visualization

For web-based visualization with D3.js:

```javascript
// Load embeddings.json via fetch
fetch('embeddings.json')
  .then(r => r.json())
  .then(data => {
    // Use PCA (via ml.js) or send to Python backend for UMAP
    // Then visualize with D3.js scatter plot
    // (Full example at docs/examples/d3_visualization.html)
  });
```

## Next Steps

- Explore clustering to find memory themes
- Track semantic drift over time
- Compare entity-specific memory patterns
- Build interactive dashboards with Plotly Dash or Streamlit

---

**Impact Above Origin** 🤠
