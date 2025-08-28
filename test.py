import requests
import json
import sys
from typing import Optional

def get_ontology_object_description(obolibrary_url: str) -> Optional[str]:
    """
    Fetches the description of an ontology object given its OBO Library URL.

    Args:
        obolibrary_url (str): The full URL of the OBO Library term
                              (e.g., "http://purl.obolibrary.org/obo/PO_0025034").

    Returns:
        Optional[str]: The description of the ontology object, or None if
                       the description cannot be retrieved or an error occurs.
    """
    # OLS API endpoint for retrieving term details by IRI (Internationalized Resource Identifier).
    ols_api_base_url = "https://www.ebi.ac.uk/ols4/api/terms"

    # The OLS API uses 'iri' as the parameter name for the ontology term URL.
    params = {
        "iri": obolibrary_url
    }

    try:
        # Make the GET request to the OLS API with a timeout.
        response = requests.get(ols_api_base_url, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx).

        data = response.json()

        # OLS responses typically embed the terms in a '_embedded' field.
        # We expect a list of terms, usually just one for a specific IRI.
        terms = data.get("_embedded", {}).get("terms")

        if terms and len(terms) > 0:
            # The description is typically in the 'description' field of the term object.
            # It might be a list or a string, so we'll handle both.
            description = terms[0].get("description")
            if isinstance(description, list) and description:
                return description[0]  # Return the first description if it's a list.
            elif isinstance(description, str):
                return description
            else:
                return None  # No valid description found.
        else:
            print(f"No term found for URL: {obolibrary_url}", file=sys.stderr)
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error during OLS API call for {obolibrary_url}: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"Failed to decode JSON response for {obolibrary_url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred for {obolibrary_url}: {e}", file=sys.stderr)
        return None

## Example Usage

# Example OBO Library URLs from your Grounded data:
url_1 = "http://purl.obolibrary.org/obo/PO_0025034"  # Plant anatomy ontology - Leaf
url_2 = "http://purl.obolibrary.org/obo/EO_0007173"  # Environment Ontology - heat treatment
url_3 = "http://purl.obolibrary.org/obo/CHEBI_26710" # ChEBI - sodium chloride (salt)
url_4 = "http://purl.obolibrary.org/obo/EO_0007270"  # Environment Ontology - low light

print(f"Fetching description for {url_1}...")
description_1 = get_ontology_object_description(url_1)
print(f"Description for PO_0025034 (Leaf): {description_1}\n")

print(f"Fetching description for {url_2}...")
description_2 = get_ontology_object_description(url_2)
print(f"Description for EO_0007173 (Heat treatment): {description_2}\n")

print(f"Fetching description for {url_3}...")
description_3 = get_ontology_object_description(url_3)
print(f"Description for CHEBI_26710 (Sodium chloride): {description_3}\n")

print(f"Fetching description for {url_4}...")
description_4 = get_ontology_object_description(url_4)
print(f"Description for EO_0007270 (Low light): {description_4}\n")

# Example of a URL that might not exist or have a description
url_invalid = "http://purl.obolibrary.org/obo/FAKE_0000000"
print(f"Fetching description for {url_invalid}...")
description_invalid = get_ontology_object_description(url_invalid)
print(f"Description for FAKE_0000000: {description_invalid}\n")