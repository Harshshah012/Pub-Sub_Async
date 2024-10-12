import asyncio
import json
import logging
import os
import sys
import signal
import socket

logging.basicConfig(filename='peer_node.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class PeerNode:
    def __init__(self, config):
        self.peer_id = None
        self.peer_ip = config['peer_node'].get('ip', '127.0.0.1')
        self.base_port = config['peer_node']['base_port']
        self.peer_port = self.find_available_port()
        self.indexing_server_ip = config['indexing_server']['ip']
        self.indexing_server_port = config['indexing_server']['port']
        self.last_read_index = {}  # {topic_name: last_read_index}
        self.subscribed_topics = set()
        self.reader = None
        self.writer = None
        self.server_socket = None

    def find_available_port(self):
        port = self.base_port
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((self.peer_ip, port))
                return port
            except socket.error:
                port += 1

    async def start(self):
        await self.start_server()
        if await self.connect_to_server() and await self.register():
            await self.main_menu()
        else:
            print("Failed to connect to the indexing server or register. Exiting.")

    async def start_server(self):
        self.server_socket = await asyncio.start_server(
            self.handle_client, self.peer_ip, self.peer_port)
        logger.info(f"Peer node listening on {self.peer_ip}:{self.peer_port}")

    async def handle_client(self, reader, writer):
        data = await reader.read(4096)
        message = json.loads(data.decode())
        if message['action'] == 'pull_messages':
            await self.handle_pull_messages(message, writer)
        writer.close()
        await writer.wait_closed()

    async def handle_pull_messages(self, message, writer):
        topic = message['topic']
        response = {'status': 'error', 'message': 'Topic not found'}
        writer.write(json.dumps(response).encode())
        await writer.drain()

    async def connect_to_server(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.indexing_server_ip, self.indexing_server_port)
            logger.info(f"Connected to indexing server at {self.indexing_server_ip}:{self.indexing_server_port}")
            return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    async def get_peer_id(self):
        while True:
            peer_id = input("Enter your peer ID: ")
            if peer_id.strip():
                return peer_id
            else:
                print("Peer ID cannot be empty. Please try again.")

    async def register(self):
    # Directly use the already assigned peer_id (generated in the test)
        if not self.peer_id:
            print("Error: Peer ID not set.")
            return False

        message = {"action": "register", "peer_id": self.peer_id, "ip": self.peer_ip, "port": self.peer_port}
        response = await self.send_message(message)
        if response['status'] in ["registered", "logged_in"]:
            logger.info(f"{response['message']}")
            print(f"{response['message']}")
            return True
        else:
            logger.error(f"Registration failed: {response['message']}")
            print(f"Registration failed: {response['message']}")
            return False

    async def deregister(self):
        message = {"action": "unregister", "peer_id": self.peer_id}
        response = await self.send_message(message)
        if response['status'] == "unregistered":
            logger.info(f"Successfully deregistered peer {self.peer_id}")
            print(f"Successfully deregistered peer {self.peer_id}")
            return True
        else:
            logger.error(f"Deregistration failed: {response['message']}")
            print(f"Deregistration failed: {response['message']}")
            return False

    async def send_message(self, message):
        if not self.writer:
            await self.connect_to_server()  # Ensure we are connected before sending

        self.writer.write(json.dumps(message).encode())
        await self.writer.drain()
        data = await self.reader.read(4096)
        response = json.loads(data.decode())
        logger.info(f"Sent message: {message}, Received response: {response}")
        return response

    async def create_topic(self, topic_name):
        message = {
            "action": "create_topic",
            "topic": topic_name,
            "peer_id": self.peer_id
        }
        response = await self.send_message(message)
        if response.get('status') == 'topic_created':
            return "Topic created successfully"
        elif response.get('status') == 'error':
            return response.get('message')
        return "Unknown error"


    async def delete_topic(self, topic_name):
        message = {"action": "delete_topic", "topic": topic_name, "peer_id": self.peer_id}
        response = await self.send_message(message)
        if response['status'] == "topic_deleted":
            print(f"Topic '{topic_name}' deleted successfully.")
        else:
            print(f"Error deleting topic: {response['message']}")

    async def send_message_to_topic(self, topic_name, message_content):
        message = {
            "action": "send_message",
            "topic": topic_name,
            "content": message_content,
            "peer_id": self.peer_id
        }
        response = await self.send_message(message)
        if response['status'] == "message_sent":
            print(f"Message sent to topic '{topic_name}': {message_content}")
        else:
            print(f"Error sending message to topic: {response['message']}")

    async def subscribe_topic(self, topic_name):
        message = {"action": "subscribe", "topic": topic_name, "peer_id": self.peer_id}
        response = await self.send_message(message)
        if response.get("status") == "subscribed":
            self.subscribed_topics.add(topic_name)
            print(f"Subscribed to topic '{topic_name}'.")
        else:
            print(f"Error subscribing to topic: {response.get('message')}")

    async def pull_messages(self, topic_name):
        if topic_name not in self.subscribed_topics:
            print(f"Not subscribed to topic '{topic_name}'")
            return None

        last_read = self.last_read_index.get(topic_name, -1)
        message = {
            "action": "get_messages",
            "topic": topic_name,
            "peer_id": self.peer_id,
            "last_read": last_read
        }
        response = await self.send_message(message)
        
        if response.get("status") == "messages_retrieved":
            messages = response.get("messages", [])
            if messages:
                print(f"New messages from topic '{topic_name}':")
                for index, sender, content in messages:
                    print(f"  {sender}: {content}")
                    self.last_read_index[topic_name] = index
                return messages  # Ensure messages are returned
            else:
                print(f"No new messages in topic '{topic_name}'")
                return []
        else:
            print(f"Error retrieving messages: {response.get('message')}")
            return None

    async def view_subscribed_topics(self):
        print("Subscribed Topics:", list(self.subscribed_topics))

    async def view_created_topics(self):
        message = {"action": "view_created_topics", "peer_id": self.peer_id}
        response = await self.send_message(message)
        if response['status'] == "created_topics":
            topics = response['topics']
            print("Created Topics:", topics)
        else:
            print(f"Error fetching created topics: {response['message']}")

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        if self.server_socket:
            self.server_socket.close()
            await self.server_socket.wait_closed()
        logger.info("Connection closed.")

    async def main_menu(self):
        while True:
            print("\nMain Menu:")
            print("1. Publisher")
            print("2. Subscriber")
            print("3. Deregister")
            print("4. Exit")
            choice = input("Choose an option (1-4): ")

            if choice == '1':
                await self.run_publisher()
            elif choice == '2':
                await self.run_subscriber()
            elif choice == '3':
                if await self.deregister():
                    print("Deregistered successfully. Exiting...")
                    break
            elif choice == '4':
                await self.close()
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please try again.")

    async def run_publisher(self):
        while True:
            print("\nPublisher Menu:")
            print("1. Create Topic")
            print("2. Delete Topic")
            print("3. Send Message")
            print("4. View Created Topics")
            print("5. Back to Main Menu")
            choice = input("Choose an option (1-5): ")

            if choice == '1':
                topic_name = input("Enter the topic name: ")
                await self.create_topic(topic_name)
            elif choice == '2':
                topic_name = input("Enter the topic name to delete: ")
                await self.delete_topic(topic_name)
            elif choice == '3':
                topic_name = input("Enter the topic name to send a message to: ")
                message_content = input("Enter your message: ")
                await self.send_message_to_topic(topic_name, message_content)
            elif choice == '4':
                await self.view_created_topics()
            elif choice == '5':
                break
            else:
                print("Invalid choice. Please try again.")

    async def run_subscriber(self):
        while True:
            print("\nSubscriber Menu:")
            print("1. Subscribe to Topic")
            print("2. Pull Messages")
            print("3. View Subscribed Topics")
            print("4. Back to Main Menu")
            choice = input("Choose an option (1-4): ")

            if choice == '1':
                topic_name = input("Enter the topic name to subscribe to: ")
                await self.subscribe_topic(topic_name)
            elif choice == '2':
                topic_name = input("Enter the topic name to pull messages from: ")
                await self.pull_messages(topic_name)
            elif choice == '3':
                await self.view_subscribed_topics()
            elif choice == '4':
                break
            else:
                print("Invalid choice. Please try again.")

def load_config(config_file='config.json'):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, config_file)
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found. Make sure '{config_file}' is in the directory: {script_dir}")
        sys.exit(1)

def signal_handler(sig, frame):
    logger.info("Received exit signal. Shutting down...")
    sys.exit(0)

async def main():
    config = load_config()
    peer_node = PeerNode(config)
    try:
        await peer_node.start()
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        await peer_node.close()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    asyncio.run(main())
