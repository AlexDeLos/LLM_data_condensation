import requests
import json
import sys
from typing import List, Optional, Tuple

def get_top_ontology_class_label(term: str, min_confidence: str, ontologies: Optional[List[str]] = None) -> Optional[Tuple[str, str]]:
    """
    Searches the Zooma API for an ontology class label and ID based on a term,
    minimum confidence, and a set of specified ontologies.

    Args:
        term (str): The term to search for (e.g., "mus musculus").
        min_confidence (str): The minimum confidence level required.
                              Should be "HIGH", "MEDIUM", or "LOW".
        ontologies (list[str], optional): A list of ontology acronyms to filter by
                                         (e.g., ["efo", "go"]). Defaults to None.

    Returns:
        Optional[Tuple[str, str]]: A tuple of the top ontology class ID (URI)
                                   and the class label, or None if no match is found.
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
        for annotation in annotations:
            annotation_confidence = annotation.get("confidence", "LOW")
            
            if annotation_confidence.upper() in CONFIDENCE_MAP:
                current_confidence_level = CONFIDENCE_MAP[annotation_confidence.upper()]
                
                if current_confidence_level >= min_confidence_level:
                    # The inferredTerm object might be at the top level or nested
                    # within the 'derivedFrom' object. We need to check both.
                    inferred_term_container = annotation.get("inferredTerm") or annotation.get("derivedFrom", {}).get("inferredTerm")
                    
                    # Extract the semantic tag (ID) from the main or derivedFrom object.
                    semantic_tags = annotation.get("semanticTags") or annotation.get("derivedFrom", {}).get("semanticTags")

                    # Extract the label from the inferred term container.
                    label = inferred_term_container.get("label") if inferred_term_container else None
                    
                    # The semanticTags is a list, we'll take the first one as the ID.
                    ontology_id = semantic_tags[0] if semantic_tags else None

                    if label and ontology_id:
                        return (ontology_id, label)
                    
    except requests.exceptions.RequestException as e:
        print(f"Error during API call: {e}", file=sys.stderr)
    
    # Return None if no suitable match was found or an error occurred.
    return None

# --- Example Usage ---

# Example 1: Search for 'heart' with high confidence in the UBERON ontology.
term_1 = "heart"
confidence_1 = "HIGH"
ontologies_1 = ["uberon"]
result_1 = get_top_ontology_class_label(term_1, confidence_1, ontologies=ontologies_1)
print(f"Term: '{term_1}', Confidence: '{confidence_1}', Ontologies: {ontologies_1}")
print(f"Top class label and ID: {result_1}\n")

# Example 2: Search for 'cell' with medium confidence in the GO ontology.
term_2 = "cell"
confidence_2 = "MEDIUM"
ontologies_2 = ["go"]
result_2 = get_top_ontology_class_label(term_2, confidence_2, ontologies=ontologies_2)
print(f"Term: '{term_2}', Confidence: '{confidence_2}', Ontologies: {ontologies_2}")
print(f"Top class label and ID: {result_2}\n")

# Example 3: Search for a term with no specific ontology filter.
term_3 = "lung adenocarcinoma"
confidence_3 = "LOW"
result_3 = get_top_ontology_class_label(term_3, confidence_3)
print(f"Term: '{term_3}', Confidence: '{confidence_3}', Ontologies: None")
print(f"Top class label and ID: {result_3}\n")
