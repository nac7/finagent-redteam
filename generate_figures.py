#!/usr/bin/env python3
"""
Generate publication-quality figures from FinAgent Red-Team results.
Outputs high-res PDF figures ready for LaTeX inclusion.
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# Configure matplotlib for publication quality
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.format'] = 'pdf'
plt.rcParams['lines.linewidth'] = 1.5
plt.rcParams['axes.linewidth'] = 1.2

# Load results
results_file = Path('results/2026-06-07_generated-p6_3trials.json')
with open(results_file) as f:
    data = json.load(f)

# Create figures directory
figures_dir = Path('paper/figures')
figures_dir.mkdir(exist_ok=True)

# Extract data
models = []
asr_none = []
asr_advisory = []
asr_enforced = []
policy_uplift = []
enforcement_uplift = []

for model_data in data['models']:
    model_name = model_data['model']
    sc = model_data['scorecard']

    # Clean up model names for display
    display_name = model_name.replace('gemini-2.0-flash', 'Gemini 2.0')\
                              .replace('claude-sonnet-4-6', 'Claude\nSonnet')\
                              .replace('claude-haiku-4-5-20251001', 'Claude\nHaiku')\
                              .replace('llama-3.1-8b-instant', 'Llama 3.1')\
                              .replace('gemma2-9b-it', 'Gemma 2 9B')\
                              .replace('mistral:7b', 'Mistral 7B')\
                              .replace('qwen3:8b', 'Qwen 3 8B')

    models.append(display_name)
    asr_none.append(sc['asr_none'] * 100)
    asr_advisory.append(sc['asr_advisory'] * 100)
    asr_enforced.append(sc['asr_enforced'] * 100)
    policy_uplift.append(sc['policy_following_uplift'] * 100)
    enforcement_uplift.append(sc['enforcement_uplift'] * 100)

# ============================================================================
# FIGURE 1: ASR Across Postures (Grouped Bar Chart)
# ============================================================================

fig, ax = plt.subplots(figsize=(10, 5))

x = np.arange(len(models))
width = 0.25

bars1 = ax.bar(x - width, asr_none, width, label='No Policy', color='#e74c3c', alpha=0.8)
bars2 = ax.bar(x, asr_advisory, width, label='Advisory', color='#f39c12', alpha=0.8)
bars3 = ax.bar(x + width, asr_enforced, width, label='Enforced', color='#27ae60', alpha=0.8)

ax.set_xlabel('Model', fontsize=11, fontweight='bold')
ax.set_ylabel('Attack Success Rate (%)', fontsize=11, fontweight='bold')
ax.set_title('FinAgent Red-Team: ASR Across Control Postures', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(models, fontsize=10)
ax.legend(loc='upper left', fontsize=10)
ax.set_ylim([0, 95])
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Add value labels on bars
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.0f}%', ha='center', va='bottom', fontsize=8)

plt.tight_layout()
plt.savefig(figures_dir / 'fig1_asr_postures.pdf', bbox_inches='tight')
print("[OK] Saved: fig1_asr_postures.pdf")
plt.close()

# ============================================================================
# FIGURE 2: Per-Threat Heatmap (Advisory Posture)
# ============================================================================

# Extract per-threat data
threat_order = ['T2_unauthorized_transfer', 'T3_sanctions_evasion', 'T4_structuring',
                'T5_dual_approval_defeat', 'T6_data_exfiltration', 'T7_confused_deputy']
threat_labels = ['T1: Unauthorized\nTransfer', 'T2: Sanctions\nEvasion', 'T3: Payment\nStructuring',
                 'T4: Dual-Approval\nDefeat', 'T5: Data\nExfiltration', 'T6: Confused\nDeputy']

heatmap_data = np.zeros((len(threat_order), len(models)))

for i, threat in enumerate(threat_order):
    for j, model_data in enumerate(data['models']):
        for cat in model_data['categories']:
            if cat['category'] == threat:
                heatmap_data[i, j] = cat['asr_advisory'] * 100
                break

# Create heatmap
fig, ax = plt.subplots(figsize=(10, 5))

im = ax.imshow(heatmap_data, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=100)

ax.set_xticks(np.arange(len(models)))
ax.set_yticks(np.arange(len(threat_labels)))
ax.set_xticklabels(models, fontsize=10)
ax.set_yticklabels(threat_labels, fontsize=10)

plt.setp(ax.get_xticklabels(), rotation=0, ha="center")

# Add text annotations
for i in range(len(threat_order)):
    for j in range(len(models)):
        value = heatmap_data[i, j]
        text_color = 'white' if value > 50 else 'black'
        ax.text(j, i, f'{value:.0f}%', ha="center", va="center",
               color=text_color, fontsize=9, fontweight='bold')

# Add colorbar
cbar = plt.colorbar(im, ax=ax)
cbar.set_label('ASR (%)', rotation=270, labelpad=20, fontsize=10)

ax.set_title('FinAgent Red-Team: Per-Threat ASR Heatmap (Advisory Posture)',
            fontsize=12, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig(figures_dir / 'fig2_threat_heatmap.pdf', bbox_inches='tight')
print("[OK] Saved: fig2_threat_heatmap.pdf")
plt.close()

# ============================================================================
# FIGURE 3: Uplift Analysis (Policy vs Enforcement)
# ============================================================================

fig, ax = plt.subplots(figsize=(10, 5))

x = np.arange(len(models))
width = 0.35

bars1 = ax.bar(x - width/2, policy_uplift, width, label='Policy-Following Uplift',
              color='#3498db', alpha=0.8)
bars2 = ax.bar(x + width/2, enforcement_uplift, width, label='Enforcement Uplift',
              color='#e67e22', alpha=0.8)

ax.set_xlabel('Model', fontsize=11, fontweight='bold')
ax.set_ylabel('ASR Reduction (%)', fontsize=11, fontweight='bold')
ax.set_title('FinAgent Red-Team: Control Posture Uplift Analysis', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(models, fontsize=10)
ax.legend(loc='upper left', fontsize=10)
ax.set_ylim([0, 55])
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.0f}%', ha='center', va='bottom', fontsize=8)

plt.tight_layout()
plt.savefig(figures_dir / 'fig3_uplift.pdf', bbox_inches='tight')
print("[OK] Saved: fig3_uplift.pdf")
plt.close()

# ============================================================================
# FIGURE 4: Model Robustness Ranking (Advisory Posture)
# ============================================================================

fig, ax = plt.subplots(figsize=(8, 6))

# Sort by ASR (ascending = more robust)
sorted_indices = np.argsort(asr_advisory)
sorted_models = [models[i] for i in sorted_indices]
sorted_asr = [asr_advisory[i] for i in sorted_indices]

colors = ['#27ae60' if asr < 1 else '#f39c12' if asr < 30 else '#e74c3c' for asr in sorted_asr]

bars = ax.barh(sorted_models, sorted_asr, color=colors, alpha=0.8)

ax.set_xlabel('Attack Success Rate (%)', fontsize=11, fontweight='bold')
ax.set_title('FinAgent Red-Team: Model Robustness Ranking\n(Advisory Posture - Lower is Better)',
            fontsize=12, fontweight='bold')
ax.set_xlim([0, 50])
ax.grid(axis='x', alpha=0.3, linestyle='--')

# Add value labels
for i, (bar, val) in enumerate(zip(bars, sorted_asr)):
    ax.text(val + 1, bar.get_y() + bar.get_height()/2., f'{val:.1f}%',
           ha='left', va='center', fontsize=10, fontweight='bold')

# Add legend for color coding
green_patch = mpatches.Patch(color='#27ae60', label='Robust (< 5%)')
yellow_patch = mpatches.Patch(color='#f39c12', label='Moderate (5-30%)')
red_patch = mpatches.Patch(color='#e74c3c', label='Vulnerable (> 30%)')
ax.legend(handles=[green_patch, yellow_patch, red_patch], loc='lower right', fontsize=9)

plt.tight_layout()
plt.savefig(figures_dir / 'fig4_ranking.pdf', bbox_inches='tight')
print("[OK] Saved: fig4_ranking.pdf")
plt.close()

print("\n" + "="*60)
print("All figures generated successfully!")
print("="*60)
print(f"\nOutput location: {figures_dir.absolute()}")
print("\nFigures ready for LaTeX inclusion:")
print("  - fig1_asr_postures.pdf     (ASR across postures)")
print("  - fig2_threat_heatmap.pdf   (Per-threat breakdown)")
print("  - fig3_uplift.pdf           (Control effectiveness)")
print("  - fig4_ranking.pdf          (Model robustness ranking)")
