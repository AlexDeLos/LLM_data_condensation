# import json
# import uuid
# import requests
# import sys
# from typing import List, Optional
# from llm import llm_compare_labels
# from classes import LabelMap
# from functools import lru_cache
# from copy import deepcopy
# from tqdm import tqdm

def load_json(path:str):
    with open(path, 'r') as file:
        object = json.load(file)
    return object

#######################################
# USER MANUAL CORRECTION
#######################################

import os
import json
import copy
from collections import defaultdict
from itertools import zip_longest
import plotly.graph_objects as go
from classes import LabelMap


# -----------------------------
# Generic Sankey plotting
# -----------------------------
def plot_sankey(grounded_data, sample_data, flag_map=None, title="Sankey Plot", output_file="sankey.html"):
    source_labels = []
    target_labels = []
    colors = []

    for grounded, og in zip(grounded_data, sample_data):
        # Tissue
        tissue_dict = grounded.get('tissue') or {}
        ground_label = tissue_dict.get('label', str(tissue_dict)) if isinstance(tissue_dict, dict) else str(tissue_dict)
        orig_tissue = og.get('tissue', 'Unknown')

        source_labels.append(orig_tissue)
        target_labels.append(ground_label)
        colors.append('red' if flag_map and orig_tissue in flag_map.get('tissue', {}) else 'blue')

        # Treatments
        orig_treatments = og.get('treatment', [])
        ground_treatments = grounded.get('treatment', [])

        for o, g in zip_longest(orig_treatments, ground_treatments, fillvalue={}):
            g_label = g.get('label', str(g)) if isinstance(g, dict) else str(g)
            source_labels.append(o)
            target_labels.append(g_label)
            colors.append('red' if flag_map and o in flag_map.get('treatment', {}) else 'blue')

    labels = list(set(source_labels + target_labels))
    label_indices = {l: i for i, l in enumerate(labels)}
    sources = [label_indices[s] for s in source_labels]
    targets = [label_indices[t] for t in target_labels]
    values = [1] * len(sources)

    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=20, label=labels, color="lightgrey"),
        link=dict(source=sources, target=targets, value=values, color=colors)
    )])
    fig.update_layout(title_text=title, font_size=10)
    fig.write_html(output_file, auto_open=True)


# -----------------------------
# Manual correction for LLM-flagged false labels
# -----------------------------
def manual_correction(grounded_data, sample_data, maps_path='saves'):
    os.makedirs(maps_path, exist_ok=True)

    seen_maps = LabelMap(maps_path)
    bad_map = seen_maps.map_bad

    manual_corrections = {'tissue': {}, 'treatment': {}}
    tissue_pool = defaultdict(list)
    treatment_pool = defaultdict(list)

    corrected_data = copy.deepcopy(grounded_data)

    # Collect items flagged as bad
    for grounded, og in zip(corrected_data, sample_data):
        tissue_label = og.get('tissue', 'Unknown')
        if tissue_label in bad_map:
            tissue_pool[tissue_label].append(grounded)

        for term, grd in zip_longest(og.get('treatment', []), grounded.get('treatment', []), fillvalue={}):
            if term in bad_map:
                treatment_pool[term].append(grd)

    if not tissue_pool and not treatment_pool:
        print("Nothing to correct: all groundings are good.")
        # Save empty corrections
        with open(os.path.join(maps_path, 'manual_corrections.json'), 'w') as f:
            json.dump(manual_corrections, f, indent=4)
        with open(os.path.join(maps_path, 'corrected_grounded_data.json'), 'w') as f:
            json.dump(corrected_data, f, indent=4)
        return manual_corrections, corrected_data

    # Tissue corrections
    for orig, lst in tissue_pool.items():
        new_label = input(f"Correct tissue '{orig}' (Enter to skip): ").strip()
        if new_label:
            manual_corrections['tissue'][orig] = new_label
            for grd in lst:
                t = grd.get('tissue', {})
                if isinstance(t, dict):
                    t['label'] = new_label
                else:
                    grd['tissue'] = {'label': new_label}

    # Treatment corrections
    for orig, lst in treatment_pool.items():
        new_label = input(f"Correct treatment '{orig}' (Enter to skip): ").strip()
        if new_label:
            manual_corrections['treatment'][orig] = new_label
            for grd in lst:
                if isinstance(grd, dict):
                    grd['label'] = new_label
                else:
                    grd = {'label': new_label}

    # Save manual corrections and corrected data
    with open(os.path.join(maps_path, 'manual_corrections.json'), 'w') as f:
        json.dump(manual_corrections, f, indent=4)
    with open(os.path.join(maps_path, 'corrected_grounded_data.json'), 'w') as f:
        json.dump(corrected_data, f, indent=4)
    #TODO: keep the maps in seen_maps updated and save them as such
    #? TODO: link the corrections to the ontology?
    print(f"Manual corrections and corrected grounded data saved in '{maps_path}' folder.")
    print(f"Tissue corrections applied: {list(manual_corrections['tissue'].keys())}")
    print(f"Treatment corrections applied: {list(manual_corrections['treatment'].keys())}")

    return manual_corrections, corrected_data


# -----------------------------
# Workflow
# -----------------------------
sample_data = load_json('labels.json')[500:600]
# grounded_data = load_json('grounded.json')
grounded_data = load_json('saves/corrected_grounded_data.json')

# Initialize LabelMap once
seen_maps = LabelMap('saves')

# Sankey before manual corrections
plot_sankey(grounded_data, sample_data, flag_map={'tissue': seen_maps.map_bad, 'treatment': seen_maps.map_bad},
            title="Original → Grounded Labels (Red = flagged bad)", output_file="saves/sankey_before.html")

# Manual corrections
manual_corrections, corrected_grounded_data = manual_correction(grounded_data, sample_data, maps_path='saves')

# Sankey after manual corrections
plot_sankey(corrected_grounded_data, sample_data, flag_map=manual_corrections,
            title="Corrected → Grounded Labels (Red = previously flagged)", output_file="saves/sankey_after.html")

