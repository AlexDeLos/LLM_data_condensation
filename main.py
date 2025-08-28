import json
import uuid
import requests
import sys
from typing import List, Optional
from llm import llm_compare_labels
from classes import LabelMap

def get_top_ontology_class_label(term: str, min_confidence: str, ontologies: Optional[List[str]] = None) -> Optional[str]:
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
        response = requests.get(base_url, params=params, timeout=10)
        
        # Raise an exception for HTTP errors (4xx or 5xx).
        response.raise_for_status()
        
        # Parse the JSON response.
        annotations = response.json()

        # Find the first annotation that meets the confidence requirement.
        top_anotation = annotations[0]['semanticTags']
        return top_anotation
    except requests.exceptions.RequestException as e:
        print(f"Error during API call: {e}", file=sys.stderr)
    
    # Return None if no suitable match was found or an error occurred.
    return None

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
    if 'Tissue' in grounded_data and isinstance(grounded_data['Tissue'], str):
        term = grounded_data['Tissue']
        api_response = get_top_ontology_class_label(term,'HIGH',['PSO','PECO','EFO'])
        grounded_data['Tissue'] = api_response

    # Ground 'Treatment' labels
    if 'Treatment' in grounded_data and isinstance(grounded_data['Treatment'], list):
        grounded_treatments = []
        for term in grounded_data['Treatment']:
            api_response = get_top_ontology_class_label(term,'HIGH',['PECO'])
            # Check if the API found a grounded term.
            if api_response is not None:
                grounded_treatments.append(api_response)
            else:
                grounded_treatments.append(term)
        grounded_data['Treatment'] = grounded_treatments

    return grounded_data

# --- Example Usage ---

# Example input data
sample_data = [
    {
        'id': str(uuid.uuid4()),
        'Tissue': 'leaves',
        'Treatment': ['heat']
    },
    {
        'id': str(uuid.uuid4()),
        'Tissue': 'leaves',
        'Treatment': ['heat']
    },
    {
        'id': str(uuid.uuid4()),
        'Tissue': 'leaf',
        'Treatment': ['high temperature stress']
    },
    {
        'id': str(uuid.uuid4()),
        'Tissue': 'leaf',
        'Treatment': ['high temperature stress']
    }
]

# Process the data and ground the labels
print("Attempting to ground labels via Zooma API...")
grounded_data_list = [ground_labels_with_api_call(item) for item in sample_data]

# Print the results for comparison
print("Original data:")
print(json.dumps(sample_data, indent=2))
print("-" * 30)
print("Grounded data:")
print(json.dumps(grounded_data_list, indent=2))
# TODO: check LLM

grounded_data = [
    {
        'id': str(uuid.uuid4()),
        'Tissue': {
            'ID': 'PO_0025034',
            'Label': 'leaf',
            'Definition': 'A phyllome (phyllome) that is not associated with a reproductive structure.',
            'Exact Synonyms':[],
            'Related Synonyms':[],

        },
        'Treatment': [{
            'ID': 'EO_0007173',
            'Label': 'warm/hot temperature regimen',
            'Definition': 'The treatment involving an exposure to above optimal temperature, which may depend on the study type or the regional environment.',
            'Exact Synonyms':[],
            'Related Synonyms':[],

        }]
    },
    {
        'id': str(uuid.uuid4()),
        'Tissue': {
            'ID': 'PO_0025034',
            'Label': 'leaf',
            'Definition': 'A phyllome (phyllome) that is not associated with a reproductive structure.',
            'Exact Synonyms':[],
            'Related Synonyms':[],

        },
        'Treatment': [{
            'ID': 'EO_0007173',
            'Label': 'warm/hot temperature regimen',
            'Definition': 'The treatment involving an exposure to above optimal temperature, which may depend on the study type or the regional environment.',
            'Exact Synonyms':[],
            'Related Synonyms':[],

        }]
    },
    {
        'id': str(uuid.uuid4()),
        'Tissue': {
            'ID': 'PO_0025034',
            'Label': 'leaf',
            'Definition': 'A phyllome (phyllome) that is not associated with a reproductive structure.',
            'Exact Synonyms':'',
            'Related Synonyms':'',

        },
        'Treatment': [{
            'ID': 'ENVO_09200001',
            'Label': 'temperature of air',
            'Definition': 'The temperature of some air.',
            'Exact Synonyms':['air temperature'],
            'Related Synonyms':[],

        }]
    },
    {
        'id': str(uuid.uuid4()),
        'Tissue': {
            'ID': 'PO_0025034',
            'Label': 'leaf',
            'Definition': 'A phyllome (phyllome) that is not associated with a reproductive structure.',
            'Exact Synonyms':'',
            'Related Synonyms':'',

        },
        'Treatment': [{
            'ID': 'ENVO_09200001',
            'Label': 'temperature of air',
            'Definition': 'The temperature of some air.',
            'Exact Synonyms':['air temperature'],
            'Related Synonyms':[],

        }]
    }
]


def add_mapping(label,id):
    print(label,id)
    return





def check_gorundings(grounded_data,sample_data):
    grounded_data_list = []
    seen_maps = LabelMap()
    for grounded,og in zip(grounded_data,sample_data):
        seen_maps.check_past(og)
        if seen_maps.check_past(og):
            mask = llm_compare_labels(grounded,og,model='gemini-2.5-flash-lite')
            grounded_data_list.append(mask)
            seen_maps.add_mapping(og,grounded,mask)
        else:
            # these maps have been seen and approved already
            pass
    return grounded_data_list

    
print(check_gorundings(grounded_data,sample_data))