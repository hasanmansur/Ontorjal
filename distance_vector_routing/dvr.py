import threading
import time
import socket
import sys
import copy
import pprint

pp = pprint.PrettyPrinter(indent=2)

# global variables
turn = 1
convergence = 0
round = 1
update_occured = 0
nodes = {
    "0" : {"name": "A", "index": 0, "port": 10000, "update": 1},
    "1" : {"name": "B", "index": 1, "port": 10001, "update": 1},
    "2" : {"name": "C", "index": 2, "port": 10002, "update": 1},
    "3" : {"name": "D", "index": 3, "port": 10003, "update": 1},
    "4" : {"name": "E", "index": 4, "port": 10004, "update": 1}
}

updates = [1,1,1,1,1]

final_output = {"0":None, "1":None, "2":None, "3":None, "4":None}

final_round = 0

def set_next(next):
    global turn
    turn = next

def set_unset_update(value):
    global update_occured
    update_occured = value

def server_thread_task(port, old_dv_matrix, updated_dv_matrix, node_index):
    global round
    global final_round
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind the socket to the port
    server_address = ('localhost', port)
    #print('node %d server thread : starting up on %s port %s' % (node_index, server_address[0], server_address[1]))
    sock.bind(server_address)
    # Listen for incoming connections
    sock.listen(1)
    last_updated_dv_matrix = copy.deepcopy(updated_dv_matrix)
    while True:
        connection, client_address = sock.accept()
        try:
            while True:
                data = connection.recv(1024)
                if data:
                    message = data.decode()
                    from_node_index = int(message.split(":")[0])
                    received_dv_estimate = message.split(":")[1].split(",")
                    receiver = nodes[str(node_index)]["name"]
                    sender = nodes[str(from_node_index)]["name"]
                    print("Node %s received DV from %s"  % (receiver, sender))
                    for i in range(len(received_dv_estimate)):
                        received_dv_estimate[i] = int(received_dv_estimate[i])
                    #------------update neighbor's row-------------------
                    updated_dv_matrix[from_node_index] = received_dv_estimate
                    #print(updated_dv_matrix[from_node_index])
                    #------------recalculate own dv estimate-------------
                    self_row = updated_dv_matrix[node_index]
                    for i in range(len(self_row)):
                        if(i != node_index):
                            new_value = updated_dv_matrix[from_node_index][node_index] + updated_dv_matrix[from_node_index][i]
                            existing_value = updated_dv_matrix[node_index][i]
                            updated_dv_matrix[node_index][i] = min(new_value, existing_value)
                    #----------check if DV estimate is different---------
                    if(updated_dv_matrix[node_index] == last_updated_dv_matrix[node_index]):
                        print("No change in DV at node %s" % (receiver))
                    else:
                        updates[node_index] = 1
                        print("Updating DV matrix at node %s" % (receiver))
                        print("New DV matrix at node %s = " % (receiver))
                        pp.pprint(updated_dv_matrix)
                        last_updated_dv_matrix = copy.deepcopy(updated_dv_matrix)
                        final_round = round
                    #-----------sending data back to the client----------
                    connection.sendall(data)
                else:
                    break
        finally:
            # Clean up the connection
            connection.close()

def send_dv_to_neighbor(neighbor_name, port, fromNodeIndex, message):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect the socket to the port where the server is listening
    server_address = ('localhost', port)
    #print('connecting to %s port %s' % server_address)
    sock.connect(server_address)
    try:
        # Send data
        print("\nSending DV to node %s" % (neighbor_name))
        sock.sendall(message.encode())
        # response from server
        response = sock.recv(1024).decode()
        #print('received "%s"' % response)
    finally:
        #print('closing socket')
        sock.close()
        #print(response)
        return response

def init_nxn_matrix(n):
    initial_nxn_matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            row.append(999)
        initial_nxn_matrix.append(row)
    return initial_nxn_matrix

def populate_nxn_matrix(updated_dv_matrix, node_index, neighbor_info):
    for i in range(len(updated_dv_matrix[node_index])):
        if(i in neighbor_info.keys()):
            updated_dv_matrix[node_index][i] = neighbor_info[i]
    updated_dv_matrix[node_index][node_index] = 0

def create_server_thread(port, old_dv_matrix, updated_dv_matrix, node_index):
    server_thread = threading.Thread(target=server_thread_task, args=(port, old_dv_matrix, updated_dv_matrix, node_index), daemon=True)
    server_thread.start()
    time.sleep(2)

def create_dv_msg(updated_dv_matrix, node_index):
    weight_list = []
    for value in updated_dv_matrix[node_index]:
        weight_list.append(str(value))
    delimeter = ","
    dv_msg = str(node_index) + ":" + delimeter.join(weight_list)
    return dv_msg

def send_update(node_index, neighbor_info, updated_dv_matrix):
    dv_msg = create_dv_msg(updated_dv_matrix, node_index)
    neighbors = []
    for key in neighbor_info.keys():
        neighbors.append(key)
    neighbors.sort()
    #---------------
    bigger = []
    smaller = []
    for value in neighbors:
        if value > node_index:
            bigger.append(value)
        else:
            smaller.append(value)
    neighbors_list = bigger + smaller
    #---------------
    i = 0
    while i < len(neighbors_list):
        neighbor_port = nodes[str(neighbors_list[i])]["port"]
        neighbor_name = nodes[str(neighbors_list[i])]["name"]
        response = send_dv_to_neighbor(neighbor_name, neighbor_port, node_index, dv_msg)
        if(response):
            i += 1

def print_node_current_old_dv(node_index, updated_dv_matrix, old_dv_matrix, round):
    print("---------------------------------------------------------------------")
    print("Round %d : %s" % (round, nodes[str(node_index)]["name"]))
    #print("Current DV matrix = ", str(updated_dv_matrix))
    print("Current DV matrix = ")
    pp.pprint(updated_dv_matrix)
    #print("Last DV matrix = ", str(old_dv_matrix))
    print("Last DV matrix = ")
    pp.pprint(old_dv_matrix)

def node_thread(lock, node_index, port, neighbor_info):
    global turn
    global convergence
    global round
    global final_round
    print("node %s started" % nodes[str(node_index)]["name"])
    #initialize nxn matrix
    old_dv_matrix = init_nxn_matrix(5)
    #populate nxn matrix with neighbor info
    populate_nxn_matrix(old_dv_matrix, node_index, neighbor_info)
    updated_dv_matrix = copy.deepcopy(old_dv_matrix)
    #--------------server thread-------------------------
    create_server_thread(port, old_dv_matrix, updated_dv_matrix, node_index)
    #--------------server thread-------------------------
    while True:
        lock.acquire()
        if(turn == 1 and node_index == 0):
            if(convergence == 1):
                #print('nothing to do %s' % nodes[str(node_index)]["name"])
                set_next(2)
                final_output["0"] = updated_dv_matrix
                lock.release()
                break
            print_node_current_old_dv(node_index, updated_dv_matrix, old_dv_matrix, round)
            if(updates[node_index] == 1):
                print("Updated from last DV matrix or the same? Updated")
                #------------send data to neighbors----------------
                send_update(node_index, neighbor_info, updated_dv_matrix)
                #------------update 'update' flag------------------
                updates[node_index] = 0
                #-----------update the old dv----------------------
                old_dv_matrix = copy.deepcopy(updated_dv_matrix)
            else:
                print("Updated from last DV matrix or the same? Same")
            if(sum(updates) == 0):
                convergence = 1
                set_next(2)
                final_output["0"] = updated_dv_matrix
                lock.release()
                break
            else:
                set_next(2)
                round += 1
            time.sleep(1)
        if(turn == 2 and node_index == 1):
            if(convergence == 1):
                #print('nothing to do %s' % nodes[str(node_index)]["name"])
                set_next(3)
                final_output["1"] = updated_dv_matrix
                lock.release()
                break
            print_node_current_old_dv(node_index, updated_dv_matrix, old_dv_matrix, round)
            if(updates[node_index] == 1):
                print("Updated from last DV matrix or the same? Updated")
                #------------send data to neighbors----------------
                send_update(node_index, neighbor_info, updated_dv_matrix)
                #------------update 'update' flag------------------
                updates[node_index] = 0
                #-----------update the old dv----------------------
                old_dv_matrix = copy.deepcopy(updated_dv_matrix)
            else:
                print("Updated from last DV matrix or the same? Same")
            if(sum(updates) == 0):
                convergence = 1
                set_next(3)
                final_output["1"] = updated_dv_matrix
                lock.release()
                break
            else:
                set_next(3)
                round += 1
            time.sleep(1)
        if(turn == 3 and node_index == 2):
            if(convergence == 1):
                #print('nothing to do %s' % nodes[str(node_index)]["name"])
                set_next(4)
                final_output["2"] = updated_dv_matrix
                lock.release()
                break
            print_node_current_old_dv(node_index, updated_dv_matrix, old_dv_matrix, round)
            if(updates[node_index] == 1):
                print("Updated from last DV matrix or the same? Updated")
                #------------send data to neighbors----------------
                send_update(node_index, neighbor_info, updated_dv_matrix)
                #------------update 'update' flag------------------
                updates[node_index] = 0
                #-----------update the old dv----------------------
                old_dv_matrix = copy.deepcopy(updated_dv_matrix)
            else:
                print("Updated from last DV matrix or the same? Same")
            if(sum(updates) == 0):
                convergence = 1
                set_next(4)
                final_output["2"] = updated_dv_matrix
                lock.release()
                break
            else:
                set_next(4)
                round += 1
            time.sleep(1)
        if(turn == 4 and node_index == 3):
            if(convergence == 1):
                #print('nothing to do %s' % nodes[str(node_index)]["name"])
                set_next(5)
                final_output["3"] = updated_dv_matrix
                lock.release()
                break
            print_node_current_old_dv(node_index, updated_dv_matrix, old_dv_matrix, round)
            if(updates[node_index] == 1):
                print("Updated from last DV matrix or the same? Updated")
                #------------send data to neighbors----------------
                send_update(node_index, neighbor_info, updated_dv_matrix)
                #------------update 'update' flag------------------
                updates[node_index] = 0
                #-----------update the old dv----------------------
                old_dv_matrix = copy.deepcopy(updated_dv_matrix)
            else:
                print("Updated from last DV matrix or the same? Same")
            if(sum(updates) == 0):
                convergence = 1
                set_next(5)
                final_output["3"] = updated_dv_matrix
                lock.release()
                break
            else:
                set_next(5)
                round += 1
            time.sleep(1)
        if(turn == 5 and node_index == 4):
            if(convergence == 1):
                #print('nothing to do %s' % nodes[str(node_index)]["name"])
                set_next(1)
                final_output["4"] = updated_dv_matrix
                lock.release()
                break
            print_node_current_old_dv(node_index, updated_dv_matrix, old_dv_matrix, round)
            if(updates[node_index] == 1):
                print("Updated from last DV matrix or the same? Updated")
                #------------send data to neighbors----------------
                send_update(node_index, neighbor_info, updated_dv_matrix)
                #------------update 'update' flag------------------
                updates[node_index] = 0
                #-----------update the old dv----------------------
                old_dv_matrix = copy.deepcopy(updated_dv_matrix)
            else:
                print("Updated from last DV matrix or the same? Same")
            if(sum(updates) == 0):
                convergence = 1
                set_next(1)
                final_output["4"] = updated_dv_matrix
                lock.release()
                break
            else:
                set_next(1)
                round += 1
            time.sleep(1)
        lock.release()

def get_adjacency_matrix():
    file_name = "network1.txt"
    adjacency_matrix = []
    with open(file_name) as fp:
        lines = fp.readlines()
    for line in lines:
        row = line.strip().split()
        for i in range(len(row)):
            row[i] = int(row[i])
        adjacency_matrix.append(row)
    return adjacency_matrix

def get_neighbor_info_list(adjacency_matrix):
    neighbor_info_list = []
    for node_index in range(len(adjacency_matrix)):
        neighbor_info = {}
        for adj_node_index in range(len(adjacency_matrix[node_index])):
            if(adjacency_matrix[node_index][adj_node_index] != 0):
                neighbor_info[adj_node_index] = adjacency_matrix[node_index][adj_node_index]
        neighbor_info_list.append(neighbor_info)
    return neighbor_info_list

def main_task():
    #adjacency matrix & neighbor info
    adjacency_matrix= get_adjacency_matrix()
    neighbor_info_list = get_neighbor_info_list(adjacency_matrix)
    #print(neighbor_info_list)

    #node index
    nodeA_index = nodes["0"]["index"]
    nodeB_index = nodes["1"]["index"]
    nodeC_index = nodes["2"]["index"]
    nodeD_index = nodes["3"]["index"]
    nodeE_index = nodes["4"]["index"]

    #node ports
    nodeA_port = nodes["0"]["port"]
    nodeB_port = nodes["1"]["port"]
    nodeC_port = nodes["2"]["port"]
    nodeD_port = nodes["3"]["port"]
    nodeE_port = nodes["4"]["port"]

    # creating a lock
    lock = threading.Lock()

    # creating threads
    thread_A = threading.Thread(target=node_thread, args=(lock, nodeA_index, nodeA_port, neighbor_info_list[0]))
    thread_B = threading.Thread(target=node_thread, args=(lock, nodeB_index, nodeB_port, neighbor_info_list[1]))
    thread_C = threading.Thread(target=node_thread, args=(lock, nodeC_index, nodeC_port, neighbor_info_list[2]))
    thread_D = threading.Thread(target=node_thread, args=(lock, nodeD_index, nodeD_port, neighbor_info_list[3]))
    thread_E = threading.Thread(target=node_thread, args=(lock, nodeE_index, nodeE_port, neighbor_info_list[4]))

    # start threads
    thread_A.start()
    thread_B.start()
    thread_C.start()
    thread_D.start()
    thread_E.start()

    # wait until threads finish their job
    thread_A.join()
    thread_B.join()
    thread_C.join()
    thread_D.join()
    thread_E.join()

    #final output
    print("---------------------------------------------------------------------")
    print("Final output: \n")
    print("Node A DV = ")
    pp.pprint(final_output["0"])
    print("Node B DV = ")
    pp.pprint(final_output["1"])
    print("Node C DV = ")
    pp.pprint(final_output["2"])
    print("Node D DV = ")
    pp.pprint(final_output["3"])
    print("Node E DV = ")
    pp.pprint(final_output["4"])

    print("\nNumber of rounds till convergence (Round # when one of the nodes last updated its DV) = %d" % (final_round))
if __name__ == "__main__":
    main_task()
