import json
import uuid
import requests
import sys
from typing import List, Optional

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

def get_ols_information(ols_code: str) -> dict:
    
    name = ols_code.split("/")[-2:]
    ontology = ["pso", "peco", "efo"]

    BASE = "https://www.ebi.ac.uk/ols4"
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
    if 'Tissue' in grounded_data and isinstance(grounded_data['Tissue'], str):
        term = grounded_data['Tissue']
        api_response = get_top_ontology_class_label(term,'HIGH',['PSO','PECO','EFO'])
         #! took the first api link here
        grounded_data['Tissue'] = get_ols_information(api_response[0])

    # Ground 'Treatment' labels
    if 'Treatment' in grounded_data and isinstance(grounded_data['Treatment'], list):
        grounded_treatments = []
        for term in grounded_data['Treatment']:
            api_response = get_top_ontology_class_label(term,'HIGH',['PECO'])
            # Check if the API found a grounded term.
            if api_response is not None:
                ## add ols label and desc
                #! took the first api link here
                ols_info = get_ols_information(api_response[0])
                grounded_treatments.append(ols_info)
                #grounded_treatments.append(api_response)
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
        'Treatment': ['heat', 'salt', 'dark']
    },
    {
        'id': str(uuid.uuid4()),
        'Tissue': 'leaves',
        'Treatment': ['high temperature stress', 'NaCl', 'dark']
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