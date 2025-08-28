import json
import uuid
import requests
import sys
from typing import List, Optional
from llm import llm_compare_labels
from classes import LabelMap
from functools import lru_cache
from copy import deepcopy
from tqdm import tqdm

def load_json(path:str):
    with open(path, 'r') as file:
        object = json.load(file)
    return object

@lru_cache(maxsize=64)
def get_top_ontology_class_label(term: str, min_confidence: str, ontologies: Optional[tuple] = None) -> Optional[str]:
    """
    Searches the Zooma API for an ontology class label based on a term,
    minimum confidence, and a set of specified ontologies.

    Args:
        term (str): The term to search for (e.g., "mus musculus").
        min_confidence (str): The minimum confidence level required.
                              Should be "HIGH", "MEDIUM", or "LOW".
        ontologies (list[str], optional): A list of ontology acronyms to filter by
                                         (e.g., ["efo", "go"]). Defaults to None.

    Returns:
        Optional[str]: The top ontology class label, or None if no match is found.
    """
    # Base URL for the Zooma V2 annotation service.
    base_url = "https://www.ebi.ac.uk/spot/zooma/v2/api/services/annotate"
    # Define confidence levels for comparison.
    CONFIDENCE_MAP = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    try:
        #TODO: this is not connected
        min_confidence_level = CONFIDENCE_MAP[min_confidence.upper()]
    except KeyError:
        print(f"Invalid confidence level '{min_confidence}'. Must be HIGH, MEDIUM, or LOW.", file=sys.stderr)
        return None

    # Construct the query parameters.
    params = {
        "propertyValue": term
    }

    # Add the ontology filter if provided.
    if ontologies:
        # Zooma expects a comma-separated list of ontologies within a filter.
        ontology_filter = f"ontologies:[{','.join(ontologies)}]"
        # The documentation suggests using 'filter' as the parameter name.
        params["filter"] = ontology_filter

    try:
        # Make the GET request to the Zooma API with a timeout.
        response = requests.get(base_url, params=params, timeout=30)
        
        # Raise an exception for HTTP errors (4xx or 5xx).
        response.raise_for_status()
        
        # Parse the JSON response.
        annotations = response.json()

        # Find the first annotation that meets the confidence requirement.
        try:
            top_anotation = annotations[0]['semanticTags']
        except:
            top_anotation = None
        return top_anotation
    except requests.exceptions.RequestException as e:
        print(f"Error during API call: {e}", file=sys.stderr)
    
    # Return None if no suitable match was found or an error occurred.
    return None

@lru_cache(maxsize=64)
def get_ols_information(ols_code: str) -> dict:
    
    ols_parts = ols_code.split("/")
    name = ols_parts[-2:]
    ontology = ["pso", "peco", "efo"]
    
    BASE = "https://www.ebi.ac.uk/ols4"
    if ols_parts[-3] == "www.ebi.ac.uk":
        iri = ols_code
    else:
        iri = "http%3A%2F%2Fpurl.obolibrary.org%2F" + name[0] + "%2F" + name[1]

    output_dict = {
        "uniq_id" : None,
        "label" : None,
        "description" : None,
        "synonyms" : None
    }

    for ON in ontology:
        resp = requests.get(
                f"{BASE}/api/ontologies/{ON}/terms?iri={iri}",
            )
        if resp.status_code == 404:
            continue  # not in this ontology, try the next one
        else:
            data = resp.json()["_embedded"]["terms"][0]
            output_dict["uniq_id"] = name[1]
            output_dict["label"] = data["label"]
            output_dict["description"] = data["description"]
            output_dict["synonyms"] = data["synonyms"]
    
    return output_dict
    
def ground_labels_with_api_call(data: dict) -> dict:
    """
    Grounds labels in a dictionary by making a real ontology API call.

    Args:
        data (dict): A dictionary containing 'Tissue' and 'Treatment' fields.

    Returns:
        dict: A new dictionary with grounded labels.
    """
    grounded_data = data.copy()

    # Ground 'Tissue' label
    if 'tissue' in grounded_data and isinstance(grounded_data['tissue'], str):
        term = grounded_data['tissue']
        api_response = get_top_ontology_class_label(term,'HIGH',('PSO','PECO','EFO'))
         #! took the first api link here
        grounded_data['tissue'] = get_ols_information(api_response[0])

    # Ground 'Treatment' labels
    if 'treatment' in grounded_data and isinstance(grounded_data['treatment'], list):
        grounded_treatments = []
        for term in grounded_data['treatment']:
            api_response = get_top_ontology_class_label(term,'MEDIUM',('PSO','PECO','EFO'))
            # Check if the API found a grounded term.
            if api_response is not None:
                ## add ols label and desc
                #! took the first api link here
                ols_info = get_ols_information(api_response[0])
                grounded_treatments.append(ols_info)
                #grounded_treatments.append(api_response)
            else:
                grounded_treatments.append({
                                            "uniq_id" : None,
                                            "label" : None,
                                            "description" : None,
                                            "synonyms" : None
                                        })
        grounded_data['treatment'] = grounded_treatments

    return grounded_data


sample_data = load_json('labels.json')[50:100]

# Keep only dict items
sample_data = [item for item in sample_data if isinstance(item, dict)]

# Remove 'medium' if it exists
for sample in sample_data:
    if 'medium' in sample:
        del sample['medium']
# Process the data and ground the labels
print("Attempting to ground labels via Zooma API...")
# grounded_data = [ground_labels_with_api_call(item) for item in sample_data]
grounded_data = []
for item in tqdm(sample_data):
    grounded_data.append(ground_labels_with_api_call(item))

# save the result of the grounded data

with open(f'grounded.json', 'w') as handle:
    json.dump(grounded_data, handle)

# check LLM

def check_groundings(grounded_data, sample_data):
    grounded_data_list = []
    seen_maps = LabelMap('saves')

    for grounded, og in tqdm(list(zip(grounded_data, sample_data)), total=len(sample_data)):
        if seen_maps.check_past(og):
            mask = llm_compare_labels(
                grounded, og, model='gemini-2.5-flash', provider='google_genai'
            )
            grounded_with_mask = deepcopy(grounded)
            grounded_with_mask['mask'] = mask

            grounded_data_list.append(grounded_with_mask)
            seen_maps.add_mapping(og, grounded, mask)
        else:
            # these maps have been seen and approved already
            grounded_data_list.append(grounded)  # keep the original

    seen_maps.save_map()
    return grounded_data_list

print(check_groundings(grounded_data, sample_data))


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

    print(f"Manual corrections and corrected grounded data saved in '{maps_path}' folder.")
    print(f"Tissue corrections applied: {list(manual_corrections['tissue'].keys())}")
    print(f"Treatment corrections applied: {list(manual_corrections['treatment'].keys())}")

    return manual_corrections, corrected_data


# -----------------------------
# Workflow
# -----------------------------

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

