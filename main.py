import json
import uuid
import requests
import sys
from typing import List, Optional
from llm import llm_compare_labels
from classes import LabelMap
from functools import lru_cache

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

    # Construct the query parameters.
    params = {
        "propertyValue": term
    }

    # Add the ontology filter if provided.
    if ontologies:
        # Zooma expects a comma-separated list of ontologies within a filter.
        ontology_filter = f"ontologies:[{ontologies.lower()}]" #TODO: make this work if multiple ontologies
        # The documentation suggests using 'filter' as the parameter name.
        params["filter"] = ontology_filter

    try:
        # Make the GET request to the Zooma API with a timeout.
        response = requests.get(base_url, params=params, timeout=10)
        
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
    ontology = ["pso", "peco", "efo","po"]
    
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
        api_response = get_top_ontology_class_label(term,'HIGH',('PO'))
         #! took the first api link here
        if api_response:
            grounded_data['tissue'] = get_ols_information()
        else:
            grounded_data['tissue'] ={
                                            "uniq_id" :'NA',
                                            "label" : None,
                                            "description" : None,
                                            "synonyms" : None
                                        }

    # Ground 'Treatment' labels
    if 'treatment' in grounded_data and isinstance(grounded_data['treatment'], list):
        grounded_treatments = []
        for term in grounded_data['treatment']:
            api_response = get_top_ontology_class_label(term,'MEDIUM',('PSO'))
            # Check if the API found a grounded term.
            if api_response is not None:
                ## add ols label and desc
                #! took the first api link here
                ols_info = get_ols_information(api_response[0])
                grounded_treatments.append(ols_info)
                #grounded_treatments.append(api_response)
            else:
                grounded_treatments.append({
                                            "uniq_id" : 'NA',
                                            "label" : None,
                                            "description" : None,
                                            "synonyms" : None
                                        })
        grounded_data['treatment'] = grounded_treatments

    return grounded_data


sample_data = load_json('labels.json')#[180:200]
for sample in sample_data:
    del sample['medium']
# Process the data and ground the labels

grounded_data = []
for item in tqdm(sample_data):
    grounded_data.append(ground_labels_with_api_call(item))

# save the result of the grounded data

with open(f'grounded.json', 'w') as handle:
    json.dump(grounded_data, handle)
grounded_data = load_json('grounded.json')
# check LLM

def check_gorundings(grounded_data,sample_data):
    grounded_data_list = []
    seen_maps = LabelMap('saves')
    for grounded,og in tqdm(zip(grounded_data,sample_data)):
        if seen_maps.check_past(og):
            mask = llm_compare_labels(grounded,og) #! this can crash when parsing we need to have better error recovery
            grounded_data_list.append(mask)
            seen_maps.add_mapping(og,grounded,mask)
        else:
            # these maps have been seen and approved already
            pass
    seen_maps.save_map()
    return grounded_data_list

    
print(check_gorundings(grounded_data,sample_data))