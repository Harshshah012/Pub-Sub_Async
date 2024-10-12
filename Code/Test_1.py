import json
import asyncio
import string
import subprocess
import os
from peer_node_test import PeerNode  # Adjust based on your actual PeerNode structure

# Load configuration from the config file
with open('config.json') as config_file:
    config = json.load(config_file)

async def start_indexing_server(log_file='indexing_server.log'):
    # Start the indexing server as a subprocess with redirected output
    print("Starting indexing server...")
    with open(log_file, 'w') as log:
        server_process = subprocess.Popen(
            ['python3', 'indexing_server.py'],  # Adjust according to your server file
            stdout=log,
            stderr=subprocess.STDOUT
        )
        await asyncio.sleep(2)  # Wait for the server to start
        print("Indexing server started.\n")
    return server_process

async def peer_operations(peer_id, topic_names):
    # Initialize PeerNode with config
    peer = PeerNode(config)

    # Set sequential Peer ID and register
    peer.peer_id = str(peer_id)  # Convert integer to string for consistency
    await peer.register()
    print(f"New user {peer.peer_id} registered and logged in successfully.")
    print(f"Peer {peer.peer_id} registered.\n")

    # Create topics
    for topic_name in topic_names:
        create_response = await peer.create_topic(topic_name)
        if create_response is None:
            print(f"Peer {peer.peer_id} failed to create {topic_name}. No response received.")
        elif "already exists" in create_response:
            print(f"Peer {peer.peer_id} tried to create {topic_name}, but it already exists.")
        else:
            print(f"Peer {peer.peer_id} created {topic_name}")

    # Spacing after topic creation
    print("\n")

    # Subscribe to all topics
    for topic_name in topic_names:
        await peer.subscribe_topic(topic_name)
        print(f"Peer {peer.peer_id} subscribed to {topic_name}")

    # Spacing after subscription
    print("\n")

    # Simulate sending a message to all topics
    for topic_name in topic_names:
        message_content = f"Message from peer {peer.peer_id}"
        await peer.send_message_to_topic(topic_name, message_content)
        print(f"Peer {peer.peer_id} sent message to topic {topic_name}: {message_content}")

    # Spacing after message sending
    print("\n")

    # Pull messages from all topics
    for topic_name in topic_names:
        messages = await peer.pull_messages(topic_name)
        if messages:
            print(f"Peer {peer.peer_id} pulled messages from {topic_name}:")
            for index, sender, content in messages:
                print(f"  [{index}] {sender}: {content}")
        else:
            print(f"Peer {peer.peer_id} pulled no new messages from {topic_name}")

    # Spacing after pulling messages
    print("\n")

    # Delete all topics created by this peer
    for topic_name in topic_names:
        delete_response = await peer.delete_topic(topic_name)
        if delete_response:
            print(f"Peer {peer.peer_id} deleted topic {topic_name}")
        else:
            print(f"Peer {peer.peer_id} failed to delete topic {topic_name}")

    # Spacing after topic deletion
    print("\n")

async def main():
    # Start the indexing server and redirect logs to a file
    server_process = await start_indexing_server('indexing_server.log')

    topic_names = ["x", "y", "z"]  # Example topics
    peers = []

    # Create and run multiple peers with sequential IDs
    for peer_id in range(1, 4):  # Deploying at least 3 peers
        peer_task = asyncio.create_task(peer_operations(peer_id, topic_names))
        peers.append(peer_task)

    # Wait for all peer operations to complete
    await asyncio.gather(*peers)

    # Terminate the indexing server after peers are done
    server_process.terminate()
    server_process.wait()  # Wait for the server process to finish
    print("Indexing server stopped.")

# Run the main test function
asyncio.run(main())
