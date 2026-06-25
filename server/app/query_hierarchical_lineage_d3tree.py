from cmflib.cmfquery import CmfQuery
from collections import deque, defaultdict

class UniqueQueue:
    def __init__(self):
        self.queue = deque()
        self.seen = set()
    
    def enqueue(self, value):
        if value not in self.seen:
            self.queue.append(value)
            self.seen.add(value)
    
    def dequeue(self):
        if self.queue:
            value = self.queue.popleft()
            self.seen.remove(value)
            return value
        raise IndexError("dequeue from an empty queue")
    
    def __len__(self):
        return len(self.queue)
    
    def __contains__(self, value):
        return value in self.seen
    
def query_hierarchical_tree_lineage(query: CmfQuery, pipeline_name: str, dict_of_exe_id: dict, uuid: str):
    # Safety Check: Return early if frontend sends 'undefined'
    if not uuid or uuid.lower() == "undefined":
        return {"error": "Invalid execution UUID provided."}

    pipeline_id = query.get_pipeline_id(pipeline_name)
    df = dict_of_exe_id[pipeline_name]
    
    # Finding execution_id by comparing Execution_uuid and short uuid
    result = df[df['Execution_uuid'].str[:4] == uuid]
    execution_id = result["id"].tolist() 
    
    # Return error if no execution ID is found for the given uuid
    if not execution_id:  
        return {"error": f"uuid '{uuid}' does not match any execution in pipeline '{pipeline_name}'"}
        
    parents_set = set()
    queue = UniqueQueue()
    dict_parents = {}
    
    # Fetch first-hop parent IDs
    parents = query.get_one_hop_parent_executions_ids(execution_id, pipeline_id)
    if parents is None:
        parents = []
        
    # --- FIX APPLIED HERE: Use execution_id[0] instead of the list ---
    dict_parents[execution_id[0]] = list(set(parents))
    parents_set.add(execution_id[0])
    
    for i in set(parents):
        queue.enqueue(i)
        parents_set.add(i)

    # Traverse upstream through the queue hierarchy
    while len(queue) > 0:
        exe_id = queue.dequeue()
        parents = query.get_one_hop_parent_executions_ids([exe_id], pipeline_id)
        if parents is None:
            parents = [] 
        dict_parents[exe_id] = list(set(parents))
        for i in set(parents):
            queue.enqueue(i)
            parents_set.add(i)
    
    # Extract metadata for every unique parent execution id discovered
    df_meta = query.get_executions_with_execution_ids(list(parents_set))
    df_meta['name_uuid'] = df_meta['Execution_type_name'] + '_' + df_meta['Execution_uuid'] 
    
    # Create the map {"id": "name_uuid"}
    result_dict = df_meta.set_index('id')['name_uuid'].to_dict()

    # Pass the data map to your existing topological sort parser
    data_organized = topological_sort(dict_parents, result_dict)
    return data_organized

def topological_sort(input_data: dict, arti_exe_dict: dict) -> list:
    # Initialize in-degree of all nodes to 0
    in_degree = {node: 0 for node in input_data}
    # Initialize adjacency list
    adj_list = defaultdict(list)

    # Fill the adjacency list and in-degree dictionary
    for node, dependencies in input_data.items():
        for dep in dependencies:
            adj_list[dep].append(node)
            in_degree[node] += 1

    # Queue for nodes with in-degree 0
    zero_in_degree_queue = deque([node for node, degree in in_degree.items() if degree == 0])
    topo_sorted_nodes = []

    while zero_in_degree_queue:
        current_node = zero_in_degree_queue.popleft()
        topo_sorted_nodes.append(current_node)
        for neighbor in adj_list[current_node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                zero_in_degree_queue.append(neighbor)
    # Transform sorted nodes into the required output format
    parent_dict = defaultdict(list)
    # creating list of list which contains dictionary of {"id":1,parents:"execution_name"}
    for id_val in topo_sorted_nodes:   # topo_sorted_nodes = ['1','2','3','4']
        if id_val in input_data:       # input_data = {"child_id":[parents_id]}, for example {"4":['3','7','9']}
            parents = tuple(sorted(input_data[id_val]))
            # {tuple(parents): {'id':execution_name,'parents':["exec_1","exec_2","exec_3"]}
            # append id,parents to key with same parents to get all child in same list
            parent_dict[parents].append({'id':arti_exe_dict[id_val],'parents': [arti_exe_dict[parent] for parent in input_data[id_val]]})
    output_data= list(parent_dict.values()) 
    return output_data