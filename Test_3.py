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

# Function to measure latency of an API call
async def measure_latency(func, *args):
    start_time = time.time()
    await func(*args)
    end_time = time.time()
    return end_time - start_time

# Function to measure throughput of an API (number of operations per second)
def calculate_throughput(num_operations, total_time):
    return num_operations / total_time if total_time > 0 else 0

# Function to benchmark the registration API
async def benchmark_registration(peer_id):
    peer = PeerNode(config)
    peer.peer_id = str(peer_id)
    latency = await measure_latency(peer.register)
    return latency

# Function to benchmark other APIs
async def benchmark_api(peer, api_func, *args):
    latency = await measure_latency(api_func, *args)
    return latency

# Function to run benchmarks for all APIs
async def benchmark_apis(num_peers):
    topic_names = [f"T{i}" for i in range(1, 101)]  # Use T1 to T100 for testing
    peers = []
    results = {}

    for peer_id in range(1, num_peers + 1):
        peer = PeerNode(config)
        peer.peer_id = str(peer_id)
        await peer.register()
        print(f"Peer {peer.peer_id} registered.")

        # Benchmark registration
        results[f"registration_peer_{peer_id}"] = await benchmark_registration(peer_id)

        # Benchmark topic creation
        topic = random.choice(topic_names)
        results[f"create_topic_peer_{peer_id}"] = await benchmark_api(peer, peer.create_topic, topic)

        # Benchmark subscription
        results[f"subscribe_topic_peer_{peer_id}"] = await benchmark_api(peer, peer.subscribe_topic, topic)

        # Benchmark message sending
        message = f"Message from peer {peer_id}"
        results[f"send_message_peer_{peer_id}"] = await benchmark_api(peer, peer.send_message_to_topic, topic, message)

        # Benchmark message pulling
        results[f"pull_message_peer_{peer_id}"] = await benchmark_api(peer, peer.pull_messages, topic)

        # **Benchmark topic deletion**
        results[f"delete_topic_peer_{peer_id}"] = await benchmark_api(peer, peer.delete_topic, topic)

        # **Benchmark unregistration**
        results[f"unregister_peer_{peer_id}"] = await benchmark_api(peer, peer.deregister)

        peers.append(peer)

    return results

# Function to run the benchmarking tests
async def run_benchmark(num_peers):
    # Start the indexing server and redirect logs to a file
    server_process = await start_indexing_server('indexing_server.log')

    try:
        # Run API benchmarks for the specified number of peers
        results = await benchmark_apis(num_peers)

        # Calculate throughput based on latency results
        throughput_results = {}
        for api, latency in results.items():
            throughput = calculate_throughput(1, latency)  # 1 operation per latency
            throughput_results[api] = throughput

        return results, throughput_results

    finally:
        # Stop the server once the tests are complete
        stop_indexing_server(server_process)

# Function to plot latency and throughput
def plot_results(peer_configs, latency_data, throughput_data, metric):
    plt.figure()

    for peer_count in peer_configs:
        latencies = latency_data[peer_count]
        throughputs = throughput_data[peer_count]

        if metric == "latency":
            plt.plot(list(latencies.keys()), list(latencies.values()), label=f"{peer_count} peers", marker='o')
        elif metric == "throughput":
            plt.plot(list(throughputs.keys()), list(throughputs.values()), label=f"{peer_count} peers", marker='o')

    plt.xlabel('API Operation')
    plt.ylabel(f'{metric.capitalize()} (seconds)' if metric == "latency" else 'Throughput (operations/sec)')
    plt.title(f'{metric.capitalize()} vs API Operation')
    plt.xticks(rotation=90)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{metric}_vs_api_operations.png')
    plt.show()

# Main function to run the benchmarking test
async def main():
    peer_configs = [1, 8]  # Test with 1 peer and 8 peers
    latency_data = {}
    throughput_data = {}

    # Run the benchmark for each peer configuration
    for num_peers in peer_configs:
        print(f"Running benchmark with {num_peers} peers...")
        latency_results, throughput_results = await run_benchmark(num_peers)

        # Store the results
        latency_data[num_peers] = latency_results
        throughput_data[num_peers] = throughput_results

    # Plot latency and throughput results
    plot_results(peer_configs, latency_data, throughput_data, "latency")
    plot_results(peer_configs, latency_data, throughput_data, "throughput")

# Run the main test function
asyncio.run(main())
