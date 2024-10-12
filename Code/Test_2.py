import json
import asyncio
import time
import random
import subprocess
import matplotlib.pyplot as plt
from peer_node_test import PeerNode  # Adjust based on your actual PeerNode structure

# Load configuration from the config file
with open('config.json') as config_file:
    config = json.load(config_file)

# Function to start the indexing server
async def start_indexing_server(log_file='indexing_server.log'):
    print("Starting indexing server...")
    with open(log_file, 'w') as log:
        server_process = subprocess.Popen(
            ['python3', 'indexing_server.py'],  # Adjust according to your server file
            stdout=log,
            stderr=subprocess.STDOUT
        )
        await asyncio.sleep(2)  # Wait for the server to initialize
        print("Indexing server started.\n")
    return server_process

# Function to stop the indexing server
def stop_indexing_server(server_process):
    server_process.terminate()
    server_process.wait()
    print("Indexing server stopped.")

# Function to generate sequential topic names in the format T1, T2, T3, ...
def generate_sequential_topic(index):
    return f"T{index}"

# Function to populate the indexing server with at least 1 million topics
async def populate_indexing_server(num_topics=10000):
    print(f"Populating indexing server with {num_topics} topics...")
    peer = PeerNode(config)
    peer.peer_id = "populator"  # A dummy peer for populating the server
    await peer.register()
    for i in range(1, num_topics + 1):
        topic_name = generate_sequential_topic(i)
        await peer.create_topic(topic_name)
    print(f"Finished populating {num_topics} topics.\n")

# Function to measure response time for querying topics
async def query_topic_response_time(peer, topic_name, num_requests):
    start_time = time.time()
    for _ in range(num_requests):
        await peer.pull_messages(topic_name)  # Simulate querying a topic
    end_time = time.time()
    avg_response_time = (end_time - start_time) / num_requests
    return avg_response_time

async def peer_query_operation(peer_id, topic_names, num_requests):
    # Initialize PeerNode with config
    peer = PeerNode(config)
    peer.peer_id = str(peer_id)
    await peer.register()

    # Randomly select a topic for querying
    random_topic = random.choice(topic_names)
    
    # Subscribe to the topic before querying
    await peer.subscribe_topic(random_topic)
    print(f"Peer {peer.peer_id} subscribed to {random_topic}")

    # Measure average response time for querying the topic
    avg_response_time = await query_topic_response_time(peer, random_topic, num_requests)
    print(f"Peer {peer.peer_id} average response time for {num_requests} queries: {avg_response_time:.6f} seconds.")
    return avg_response_time


async def run_test(num_peers, num_requests):
    # Create topic names T1, T2, ..., T1000 for testing
    topic_names = [generate_sequential_topic(i) for i in range(1, 1001)]
    peers = []
    response_times = []

    # Create and run multiple peers
    for peer_id in range(1, num_peers + 1):
        peer_task = asyncio.create_task(peer_query_operation(peer_id, topic_names, num_requests))
        peers.append(peer_task)

    # Wait for all peer operations to complete
    results = await asyncio.gather(*peers)

    # Calculate the overall average response time across all peers
    overall_avg_time = sum(results) / len(results)
    print(f"Overall average response time for {num_peers} peers: {overall_avg_time:.6f} seconds.\n")

    return overall_avg_time

async def main():
    # Start the indexing server and redirect logs to a file
    server_process = await start_indexing_server('indexing_server.log')

    try:
        # Populate the server with 1 million topics (or adjust as needed)
        await populate_indexing_server(num_topics=10000)

        # Test cases with different number of peers
        peer_configs = [2, 4, 8]
        num_requests = 1000  # Each peer makes 100 requests
        avg_response_times = []

        # Run the test for each peer configuration
        for num_peers in peer_configs:
            print(f"Running test with {num_peers} peers...")
            avg_time = await run_test(num_peers, num_requests)
            avg_response_times.append(avg_time)

        # Plot the results
        plt.plot(peer_configs, avg_response_times, marker='o')
        plt.xlabel('Number of Peers')
        plt.ylabel('Average Response Time (seconds)')
        plt.title('Average Response Time vs Number of Peers')
        plt.grid(True)
        plt.savefig('response_time_vs_peers.png')
        plt.show()

    finally:
        # Stop the server once the tests are complete
        stop_indexing_server(server_process)

# Run the main test function
asyncio.run(main())
