import requests
from SPARQLWrapper import SPARQLWrapper, JSON
import json 


def get_entity(Q: list[str], L, sparql_endpoint):
    """Get entities from Wiki Data SPARQL Services 

    Args:
      Q: list of wikidata entity ids 
      L: language of the returned labels 
    
    Returns:

    """
    q_values = " ".join(f"wd:{q}" for q in Q)

    sparql_endpoint.setQuery(f"""
SELECT ?item ?itemLabel ?itemLabel_en ?alsoKnownAs WHERE {{
  VALUES ?item {{ {q_values} }}

  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "{L}" .
    bd:serviceParam wikibase:language "en".
  }}

  OPTIONAL {{
    ?item skos:altLabel ?alsoKnownAs .
    FILTER(LANG(?alsoKnownAs) = "{L}")
  }}
}}
    """)

    sparql_endpoint.setReturnFormat(JSON)
    results = sparql_endpoint.query().convert()
    return results['results']['bindings'] 

def extract_values(row):
    """ entity entity id label and alias from row of WikiQL Data

    Args:
        row: row of SPARQL data 

    Returns:
        entity_id, entity_label, enitity_alias
    """
    entity_id = row['item']['value'].split('entity/')[-1]

    entity_label = row.get('itemLabel', {}).get('value')
    if entity_label == entity_id:
        entity_label = None

    # Fall back to the English label if the target-language label is missing
    if entity_label is None:
        entity_label = row.get('itemLabel_en', {}).get('value')

    entity_alias = row.get('alsoKnownAs', {}).get('value')

    return entity_id, entity_label, entity_alias