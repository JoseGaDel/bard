"""
This module contains a set of tools for working with JSON data. It includes functions for querying,
filtering, and manipulating JSON data structures. The tools provided here are designed to be
flexible and easy to use, allowing users to perform complex operations on JSON data with minimal effort.
"""

import json
from typing import List, Dict, Any, Callable
from operator import itemgetter
import re

class QueryInspector:
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    def select(self, path: str) -> 'QueryInspector':
        """
        Select a specific path in the JSON structure.
        
        Args:
            - path (str): The dot-separated path to the desired data.
        
        Returns:
            - QueryInspector: A new query object with the selected data.
        """
        # Split the path by dots to handle nested structures
        parts = path.split('.')
        result = self.data
        for part in parts:
            # Handle list indices if present in the path
            if part.endswith(']'):
                key, index = part[:-1].split('[')
                result = result[key][int(index)]
            else:
                result = result[part]
        # Return a new QueryInspector object with the selected data
        return QueryInspector(result)

    def filter(self, condition: Callable[[Dict[str, Any]], bool]) -> 'QueryInspector':
        """
        Filter the current data based on a condition.
        
        Args:
            - condition (Callable[[Dict[str, Any]], bool]): A function that returns True for items to keep.
        
        Returns:
            - QueryInspector: A new query object with the filtered data.
        """
        if isinstance(self.data, list):
            # Filter the list based on the condition
            filtered = [item for item in self.data if condition(item)]
        elif isinstance(self.data, dict):
            # Filter the dictionary based on the condition
            filtered = self.data if condition(self.data) else {}
        else:
            filtered = self.data
        return QueryInspector(filtered)

    def map(self, func: Callable[[Dict[str, Any]], Any]) -> 'QueryInspector':
        """
        Apply a function to each item in the data.
        
        Args:
            - func (Callable[[Dict[str, Any]], Any]): A function to apply to each item.
        
        Returns:
            - QueryInspector: A new query object with the mapped data.
        """
        if isinstance(self.data, list):
            mapped = [func(item) for item in self.data]
        elif isinstance(self.data, dict):
            mapped = func(self.data)
        else:
            mapped = self.data
        return QueryInspector(mapped)

    def flatten(self) -> 'QueryInspector':
        """
        Flatten nested lists into a single list.
        
        Returns:
            - QueryInspector: A new query object with the flattened data.
        """
        flattened = []
        def flat(x):
            # By writing it as a function, we can use it recursively to flatten nested lists
            # which is a very natural way to handle lists of lists.
            if isinstance(x, list):
                for item in x:
                    flat(item)
            else:
                flattened.append(x)
        # Recursively flatten the nested lists
        flat(self.data)
        return QueryInspector(flattened)

    def sort(self, key: str, reverse: bool = False) -> 'QueryInspector':
        """
        Sort the data based on a key.
        
        Args:
            - key (str): The key to sort by.
            - reverse (bool): Whether to sort in descending order.
        
        Returns:
            - QueryInspector: A new query object with the sorted data.
        """
        if isinstance(self.data, list):
            # Sort the list of dictionaries by the specified key
            sorted_data = sorted(self.data, key=itemgetter(key), reverse=reverse)
        else:
            sorted_data = self.data
        return QueryInspector(sorted_data)

    def get(self) -> Any:
        """Get the final result."""
        # This simple method returns the current state of the data
        return self.data


def load_json(file_path: str) -> Dict[str, Any]:
    # Function to save ourselves some typing when loading JSON files
    with open(file_path, 'r') as f:
        return json.load(f)

from typing import Dict, List, Tuple, Union, Any, Callable, Set
import operator
from collections import defaultdict


def compare_dicts(paths_and_contents: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Compare contents across multiple paths and provide detailed difference analysis.

    Args:
        - paths_and_contents (List[Tuple[str, Dict[str, Any]]]): A list of tuples with the path and the content of the JSON file.

    Returns:
        - Dict[str, Any]: A dictionary with the comparison results.
    """
    def make_hashable(value):
        if isinstance(value, list):
            return tuple(make_hashable(v) for v in value)
        elif isinstance(value, dict):
            return tuple(sorted((k, make_hashable(v)) for k, v in value.items()))
        else:
            return value

    all_keys = set().union(*(content.keys() for _, content in paths_and_contents))
    value_to_paths = defaultdict(list)
    
    for path, content in paths_and_contents:
        key_value_pairs = tuple(sorted((k, make_hashable(content.get(k))) for k in all_keys))
        value_to_paths[key_value_pairs].append(path)
    
    result = {
        "unique_combinations": [],
        "shared_values": {},
        "unique_values": defaultdict(dict)
    }

    for key_value_pairs, paths in value_to_paths.items():
        combination = dict(key_value_pairs)
        result["unique_combinations"].append({
            "paths": paths,
            "values": combination
        })

        for key, value in key_value_pairs:
            if key not in result["shared_values"]:
                result["shared_values"][key] = value
            elif result["shared_values"][key] != value:
                result["shared_values"][key] = "MULTIPLE_VALUES"
                
            if result["shared_values"][key] == "MULTIPLE_VALUES":
                if len(paths) == 1:
                    result["unique_values"][paths[0]][key] = value
    
    return result

JSONValue = Union[Dict[str, 'JSONValue'], List['JSONValue'], str, int, float, bool, None]

class Condition:
    """
    Class to represent a simple condition. It is used to implement filtering logic
    based on a key-value pair. So, for example, to filter objects where the key 'A'
    has the value 1, you would create a Condition object with key='A' and value=1:
    Condition('A', 1)
    """
    OPERATORS = {
        '==': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        'in': lambda x, y: x in y,
        'contains': lambda x, y: str(y) in str(x),
        'startswith': lambda x, y: str(x).startswith(str(y)),
        'endswith': lambda x, y: str(x).endswith(str(y)),
        'exist': lambda x, y: True,
        'exists': lambda x, y: True  # Alias for 'exist' so the user can use either
    }

    def __init__(self, condition_str: str):
        self.condition_str = condition_str
        self.key, self.op, self.value, self.negated = self._parse_condition(condition_str)

    def _parse_condition(self, condition_str: str) -> Tuple[str, str, Any, bool]:
        # Regular expression to match the condition string, including optional 'not'
        pattern = r'(\w+)\s*(not\s+)?(==|!=|<|<=|>|>=|contains|in|startswith|endswith|exists?)\s*(.*)'
        match = re.match(pattern, condition_str.strip())
        
        if not match:
            raise ValueError(f"Invalid condition string: {condition_str}")
        
        key, negation, op, value = match.groups()
        negated = negation is not None
        
        # If the operator is 'exists', we don't need to parse the value
        if op in ['exist', 'exists']:
            return key.strip(), 'exists', None, negated
        
        # Parse lists for 'in' operator
        if op == 'in' and value.startswith('[') and value.endswith(']'):
            value = [v.strip().strip("'\"") for v in value[1:-1].split(',')]
            value = [int(v) if v.isdigit() else float(v) if v.replace('.', '', 1).isdigit() else v for v in value]
        else:
            # Clean up the value and convert it to the appropriate type
            value = value.strip()
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '', 1).isdigit():
                value = float(value)
            else:
                # Remove quotes if present
                value = value.strip("'\"")
        
        return key.strip(), op.strip(), value, negated

    def check(self, obj: Dict[str, Any]) -> bool:
        if self.key not in obj:
            return self.negated if self.op in ['exist', 'exists'] else False
        if self.op not in self.OPERATORS:
            raise ValueError(f"Unsupported operator: {self.op}")
        
        if self.op in ['exist', 'exists']:
            result = self.key in obj
        else:
            left_operand = obj[self.key]
            right_operand = self.value

            if self.op == 'in':
                result = left_operand in right_operand
            elif isinstance(left_operand, bool):
                result = self.OPERATORS[self.op](left_operand, bool(right_operand))
            else:
                result = self.OPERATORS[self.op](left_operand, right_operand)
        
        return not result if self.negated else result

class LogicalOp:
    """
    Class to represent a logical operator. It is used to implement logical operations.
    So, for example, to create the logic "(A AND B) OR C", you would create a LogicalOp
    using the Condition objects for A, B, and C:
    LogicalOp('OR', [LogicalOp('AND', [Condition('A', Value), Condition('B', Value)]), Condition('C', Value)])

    """
    def __init__(self, op: str, operands: List[Union['LogicalOp', Condition]]):
        self.op = op
        self.operands = operands

    def check(self, obj: Dict[str, Any]) -> bool:
        if self.op == 'AND':
            return all(operand.check(obj) for operand in self.operands)
        elif self.op == 'OR':
            return any(operand.check(obj) for operand in self.operands)
        else:
            raise ValueError("Invalid logical operator. Use 'AND' or 'OR'.")
        

def parse_path(path: str) -> List[Union[str, int]]:
    """Parse a path string into a list of keys and indices."""
    elements = []
    for element in re.findall(r'\[(\d+)\]|([^\[\].]+)', path):
        if element[0]:  # It's a list index
            elements.append(int(element[0]))
        else:  # It's a dict key
            elements.append(element[1])
    return elements


def parse_logic(logic_str: str) -> Union[LogicalOp, Condition]:
    """
    Function to parse a logical expression string into a logical expression tree. With this, 
    the user can specify complex logical conditions to filter JSON data structures using simple
    syntax instead of directly using the classes LogicalOp and Condition. For example, instead
    of creating a LogicalOp object like this:

        complex_logic = LogicalOp('AND', [
            LogicalOp('AND', [
                Condition('extinct == false'),
                Condition('rank == family')
            ]),
            Condition('ancestry contains 261866')
        ])
    
    The user just needs to write the logical expression as a string:
        logic_str = "extinct == false && rank == family && ancestry contains 261866"
    """
    def tokenize(s: str) -> List[str]:
        tokens = re.findall(r'\(|\)|&&|\|\||(?:[^()&|]+)', s)
        return [token.strip() for token in tokens if token.strip()]  # Remove whitespace and empty tokens
    
    def parse_expression(tokens: List[str]) -> Union[LogicalOp, Condition]:
        index = [0]  # hold the current index
        
        def parse():
            if tokens[index[0]] == '(':
                index[0] += 1
                result = parse_or()
                index[0] += 1  # skip closing parenthesis
                return result
            else:
                condition = Condition(tokens[index[0]])
                index[0] += 1
                return condition
        
        def parse_or():
            left = parse_and()
            while index[0] < len(tokens) and tokens[index[0]] == '||':
                index[0] += 1
                right = parse_and()
                left = LogicalOp('OR', [left, right])
            return left
        
        def parse_and():
            left = parse()
            while index[0] < len(tokens) and tokens[index[0]] == '&&':
                index[0] += 1
                right = parse()
                left = LogicalOp('AND', [left, right])
            return left
        
        return parse_or()
    
    tokens = tokenize(logic_str)
    return parse_expression(tokens)



def path_finder(
    data: JSONValue,
    logic: str,
    start_point: str = "",
    return_content: bool = False,
    compare_results: bool = False
) -> Union[List[Union[str, Tuple[str, JSONValue]]], Tuple[List[Union[str, Tuple[str, JSONValue]]], Dict[str, Set[Any]]]]:
    """
    Find paths to elements in a JSON-like data structure that satisfy complex logical conditions.

    This function traverses a JSON data structure and returns paths (and optionally content)
    of elements that match the specified logical conditions. It supports complex logical expressions,
    so the user has flexible filtering options. The user can search for specific characteristics
    within the data without needing to know the exact structure of the JSON. A starting path
    can be specified to limit the search to a specific sub-structure.

    Parameters:
        - data (JSONValue): The JSON-like data structure to search.
        - logic (str): A string representing the logical expression defining the search criteria.
            Supports complex conditions using AND (&&) and OR (||) operators, as well as parentheses.
        - start_point (str): The path from which to start the search. Default is "" (search from root).
        - return_content (bool): If True, return both the path and the content of matching elements.
            If False, return only the paths. Default is False.
        - compare_results (bool): If True and multiple results are found, return information about 
            differing values between the results. Default is False.

    Returns:
    If compare_results is False:
        - List[Union[str, Tuple[str, JSONValue]]]: A list of paths (as strings) to matching elements,
            or a list of tuples containing paths and content if return_content is True.
    If compare_results is True:
        - Tuple[List[Union[str, Tuple[str, JSONValue]]], Dict[str, Set[Any]]]: A tuple containing
            the list of results (as above) and a dictionary of keys with differing values across the results.

    Examples:
    1. Simple condition:
        result = path_finder(data, "ancestry == 1/2/15/116/261864")

    2. Multiple conditions with AND logic:
        result = path_finder(data, "ancestry == 1/2/15/116/261864 && rank == infraclass")

    3. Complex logical expression:
        complex_logic = "(ancestry == 1/2/15/116/261864 && rank == infraclass) || scientificName == Neoptera"
        result = path_finder(data, complex_logic, return_content=True)

    4. Search from a specific starting point:
        result = path_finder(data, "observations_count exists", start_point="result[1]", return_content=True)

    This function allows for arbitrarily complex logical expressions, enabling precise filtering
    of JSON data. It can handle nested structures and return multiple matches. The returned paths
    use bracket notation for list indices and dot notation for dictionary keys.

    Supported operators:
    - Comparison: ==, !=, <, <=, >, >=
    - Logical: && (AND), || (OR)
    - String operations: contains, startswith, endswith
    - Membership: in
    - Existence: exists
    - Negation: not (prefix)

    Note:
    - The function traverses the entire data structure, so it may be time-consuming for very large datasets.
    - When return_content is True, the entire matching sub-structure is returned, not just the specified fields.
    - The logic string is case-sensitive for field names and string values.
    """
    
    def get_nested_item(obj: JSONValue, path: List[Union[str, int]]) -> JSONValue:
        for key in path:
            if isinstance(obj, dict):
                obj = obj.get(key, {})
            elif isinstance(obj, list):
                try:
                    obj = obj[key]  # key is already an int here
                except (IndexError, ValueError):
                    return {}
            else:
                return {}
        return obj

    def search(current: JSONValue, path: List[Union[str, int]]) -> List[Tuple[List[Union[str, int]], JSONValue]]:
        results = []
        if isinstance(current, dict):
            if logic_tree.check(current):
                results.append((path, current))
            for k, v in current.items():
                results.extend(search(v, path + [k]))
        elif isinstance(current, list):
            for i, item in enumerate(current):
                results.extend(search(item, path + [i]))
        return results

    def format_path(path: List[Union[str, int]]) -> str:
        formatted = []
        for item in path:
            if isinstance(item, int):
                formatted.append(f"[{item}]")
            else:
                if formatted and not formatted[-1].endswith(']'):
                    formatted.append('.')
                formatted.append(item)
        return ''.join(formatted)

    # Parse the logic string into a logic tree
    logic_tree = parse_logic(logic)

    # Parse start_point to a list
    start_point_list = parse_path(start_point) if start_point else []

    # Get the nested item to start the search from
    start_item = get_nested_item(data, start_point_list)

    # Perform the search from the starting point
    all_results = search(start_item, start_point_list)
    
    if compare_results and len(all_results) > 1:
        comparison = compare_dicts([(format_path(path), content) for path, content in all_results])
        if return_content:
            return [(format_path(path), content) for path, content in all_results], comparison
        else:
            return [format_path(path) for path, _ in all_results], comparison
    else:
        if return_content:
            return [(format_path(path), content) for path, content in all_results]
        else:
            return [format_path(path) for path, _ in all_results]
        


def filter_results(
    previous_results: List[Tuple[str, Dict[str, Any]]],
    logic: str,
    return_content: bool = True
) -> List[Union[str, Tuple[str, Dict[str, Any]]]]:
    """
    Apply additional filtering on the results of a previous path_finder call.

    Parameters:
        - previous_results (List[Tuple[str, Dict[str, Any]]]): Results from a previous path_finder call.
        - logic (str): A string representing the logical expression for additional filtering.
        - return_content (bool): If True, return both the path and the content of matching elements.
            If False, return only the paths. Default is True.

    Returns:
        - List[Union[str, Tuple[str, Dict[str, Any]]]]: Filtered results based on the new logic.
    """
    logic_tree = parse_logic(logic)

    filtered_results = []
    for path, content in previous_results:
        if logic_tree.check(content):
            if return_content:
                filtered_results.append((path, content))
            else:
                filtered_results.append(path)

    return filtered_results


def comparison_results(
    results: Union[Tuple[List[Union[str, Tuple[str, Dict[str, Any]]]], Dict[str, Any]], List[Union[str, Tuple[str, Dict[str, Any]]]], Dict[str, Any]],
    logic_str: str = "",
    start_point: str = ""
):
    """
    Print a formatted comparison of path_finder results.

    Parameters:
        - results: Can be either:
            • A tuple of (paths_and_contents, comparison)
            • A list of paths_and_contents
            • A dictionary of comparison results
        - logic_str: The logic string used in the path_finder call (optional)
        - start_point: The start point used in the path_finder call (optional)
    """
    
    if isinstance(results, tuple) and len(results) == 2:
        paths_and_contents, comparison = results
    elif isinstance(results, list):
        paths_and_contents = results
        comparison = compare_dicts(paths_and_contents)
    elif isinstance(results, dict):
        comparison = results
        paths_and_contents = []
    else:
        raise ValueError("Invalid input format for results")

    # Print paths
    if paths_and_contents:
        print(f"Paths and contents found (logic: '{logic_str}', starting from '{start_point}') (found {len(paths_and_contents)}):")
        for item in paths_and_contents:
            if isinstance(item, tuple):
                print(f"Path: {item[0]}")
            else:
                print(f"Path: {item}")
        print()

    # Print comparison results
    print(f"Comparison results")
    
    print("\n______________________\nUnique combinations:\n______________________\n")
    for combo in comparison["unique_combinations"]:
        print(f"Paths: {combo['paths']}")
        print("Unique values:")
        for key, value in combo['values'].items():
            if comparison["shared_values"].get(key) == "MULTIPLE_VALUES":
                print(f"  {key}: {value}")
        print()

    print("\n______________________\nShared values across all paths:\n______________________\n")
    for key, value in comparison["shared_values"].items():
        if value != "MULTIPLE_VALUES":
            print(f"{key}: {value}")

    print("\n______________________\nUnique values for individual paths:\n______________________\n")
    for path, unique_values in comparison["unique_values"].items():
        if unique_values:
            print(f"Path: {path}")
            for key, value in unique_values.items():
                print(f"  {key}: {value}")
            print()
    


from typing import Callable, Any, List, Dict, Union
from functools import reduce


# Basic operations
def filter_by_condition(condition: Callable[[Any], bool]) -> Callable[[List[Any]], List[Any]]:
    return lambda data: [item for item in data if condition(item)]

def map_function(func: Callable[[Any], Any]) -> Callable[[List[Any]], List[Any]]:
    return lambda data: [func(item) for item in data]

def reduce_function(func: Callable[[Any, Any], Any], initial: Any) -> Callable[[List[Any]], Any]:
    return lambda data: reduce(func, data, initial)

# Composition function
def compose(*funcs):
    return reduce(lambda f, g: lambda x: f(g(x)), funcs, lambda x: x)

# ************* This function needs to be updated to use the new logic parsing  *************
def apply_operations(data: JSONValue, operations: Callable[[Any], Any], start_point: str = "") -> Any:
    # Reuse the path_finder function to get the starting point
    start_items = path_finder(data, Condition("", ""), start_point=start_point, return_content=True)
    if not start_items:
        return None
    
    # Apply operations to the first matching item
    start_item = start_items[0][1]
    return operations(start_item)

# Example usage functions
def get_attribute(what_to_search: str, value_to_search: str, attribute: str) -> Callable[[List[Dict]], int]:
    """
    Function to get the sum of a specific attribute in a list of dictionaries based on a condition.
    The condition is defined by the key-value pair 'what_to_search'='value_to_search'. An example could be
    to find the observation count for a specific 'iconic_taxon_name' in a list of observations:
    get_observation_count('iconic_taxon_name','Mollusca', 'observation_count')
    """
    return compose(
        lambda data: [item for sublist in data for item in sublist.get('results', [])],  # Flatten results
        filter_by_condition(lambda x: x.get(what_to_search) == value_to_search),
        map_function(lambda x: x.get(attribute, 0)),
        reduce_function(lambda x, y: x + y, 0)
    )

def get_max_observation_species() -> Callable[[List[Dict]], List[str]]:
    return compose(
        lambda data: [sublist.get('results', []) for sublist in data],  # Get all results
        map_function(
            lambda results: max(results, key=lambda x: x.get('observation_count', 0))['species']
            if results else None
        )
    )
