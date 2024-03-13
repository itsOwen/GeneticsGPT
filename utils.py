from typing import Dict, List, Union, Any

def get_values(search_hits: Union[Dict[Any, Any], List[Any]], search_key: str) -> List:
    results = []
    def extract(data: Union[Dict[Any, Any], List[Any]]):
        if isinstance(data, dict):
            for key, value in data.items():
                if key == search_key:
                    results.append(value)
                extract(value)
        elif isinstance(data, list):
            for item in data:
                extract(item)

    extract(search_hits)
    return results