import asyncio
import json
import logging
import os
import signal
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IndexingServer:
    def __init__(self, config):
        self.host = config['indexing_server']['ip']
        self.port = config['indexing_server']['port']
        self.peers = {}  # peer_id: (ip, port)
        self.topics = {}  # topic_name: {host_peer: peer_id, subscribers: set(peer_ids)}
        self.messages = {}  # topic_name: [(index, peer_id, content)]
        self.registered_peers_file = 'registered_peers.json'
        self.load_registered_peers()

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logger.info(f"Indexing server starting on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        logger.info(f"New connection from {addr}")
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                message = json.loads(data.decode())
                action = message.get("action")
                peer_id = message.get("peer_id")
                if not action or not peer_id:
                    response = {"status": "error", "message": "Missing 'action' or 'peer_id'."}
                else:
                    response = await self.process_action(action, message, peer_id)
                writer.write(json.dumps(response).encode())
                await writer.drain()
        except Exception as e:
            logger.error(f"Error handling client {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"Connection closed for {addr}")

    async def process_action(self, action, message, peer_id):
        actions = {
            "register": self.register_peer,
            "unregister": self.unregister_peer,
            "create_topic": self.create_topic,
            "delete_topic": self.delete_topic,
            "subscribe": self.subscribe_topic,
            "send_message": self.send_message,
            "get_messages": self.get_messages,
            "view_subscribed_topics": self.view_subscribed_topics,
            "view_created_topics": self.view_created_topics,
            "get_topic_host": self.get_topic_host
        }
        handler = actions.get(action)
        if handler:
            return await handler(message, peer_id)
        return {"status": "error", "message": f"Unknown action '{action}'."}

    async def register_peer(self, message, peer_id):
        if peer_id in self.peers:
            logger.info(f"Peer {peer_id} already registered. Logging in.")
            return {"status": "logged_in", "message": f"Peer {peer_id} already registered. Logging in."}
        self.peers[peer_id] = (message.get('ip'), message.get('port'))
        self.save_registered_peers()
        logger.info(f"New user {peer_id} registered from {self.peers[peer_id]}")
        return {"status": "registered", "message": f"New user {peer_id} registered and logged in successfully."}

    async def unregister_peer(self, message, peer_id):
        if peer_id not in self.peers:
            return {"status": "error", "message": f"Peer {peer_id} does not exist."}
        del self.peers[peer_id]
        self.save_registered_peers()
        for topic, data in list(self.topics.items()):
            if data['host_peer'] == peer_id:
                new_host = self.select_new_host(peer_id)
                if new_host:
                    data['host_peer'] = new_host
                    logger.info(f"Topic '{topic}' reassigned to peer {new_host}")
                else:
                    del self.topics[topic]
                    if topic in self.messages:
                        del self.messages[topic]
                    logger.info(f"Topic '{topic}' deleted due to no available hosts")
            data['subscribers'].discard(peer_id)
        logger.info(f"Unregistered peer {peer_id}")
        return {"status": "unregistered", "message": f"Peer {peer_id} unregistered successfully."}

    def select_new_host(self, old_host):
        available_peers = [p for p in self.peers if p != old_host]
        return available_peers[0] if available_peers else None

    async def create_topic(self, message, peer_id):
        topic = message.get("topic")
        if not topic:
            return {"status": "error", "message": "Missing 'topic' field."}
        if topic in self.topics:
            return {"status": "error", "message": f"Topic '{topic}' already exists."}
        self.topics[topic] = {'host_peer': peer_id, 'subscribers': set()}
        self.messages[topic] = []
        logger.info(f"Peer {peer_id} created topic '{topic}'")
        return {"status": "topic_created", "message": f"Topic '{topic}' created successfully."}

    async def delete_topic(self, message, peer_id):
        topic = message.get("topic")
        if not topic:
            return {"status": "error", "message": "Missing 'topic' field."}
        if topic not in self.topics:
            return {"status": "error", "message": f"Topic '{topic}' does not exist."}
        if self.topics[topic]['host_peer'] != peer_id:
            return {"status": "error", "message": f"Peer {peer_id} is not the host of topic '{topic}'."}
        del self.topics[topic]
        if topic in self.messages:
            del self.messages[topic]
        logger.info(f"Peer {peer_id} deleted topic '{topic}'")
        return {"status": "topic_deleted", "message": f"Topic '{topic}' deleted successfully."}

    async def subscribe_topic(self, message, peer_id):
        topic = message.get("topic")
        if not topic:
            return {"status": "error", "message": "Missing 'topic' field."}
        if topic not in self.topics:
            return {"status": "error", "message": f"Topic '{topic}' does not exist."}
        self.topics[topic]['subscribers'].add(peer_id)
        host_peer_id = self.topics[topic]['host_peer']
        host_ip, host_port = self.peers[host_peer_id]
        logger.info(f"Peer {peer_id} subscribed to topic '{topic}'")
        return {
            "status": "subscribed",
            "message": f"Subscribed to topic '{topic}' successfully.",
            "host_peer": {"id": host_peer_id, "ip": host_ip, "port": host_port}
        }

    async def send_message(self, message, peer_id):
        topic = message.get("topic")
        content = message.get("content")
        
        # Check if both topic and content are provided
        if not topic or not content:
            return {"status": "error", "message": "Missing 'topic' or 'content' field."}
        
        # Check if the topic exists
        if topic not in self.topics:
            return {"status": "error", "message": f"Topic '{topic}' does not exist."}

        # Allow any peer to send a message to the topic (remove the host restriction)
        if topic not in self.messages:
            self.messages[topic] = []
        
        index = len(self.messages[topic])
        self.messages[topic].append((index, peer_id, content))
        
        # Log and return success message
        logger.info(f"Peer {peer_id} sent message to topic '{topic}': {content}")
        return {"status": "message_sent", "message": "Message sent successfully."}


    async def get_messages(self, message, peer_id):
        topic = message.get("topic")
        last_read = message.get("last_read", -1)
        if not topic:
            return {"status": "error", "message": "Missing 'topic' field."}
        if topic not in self.topics:
            return {"status": "error", "message": f"Topic '{topic}' does not exist."}
        if peer_id not in self.topics[topic]['subscribers']:
            return {"status": "error", "message": f"Peer {peer_id} is not subscribed to topic '{topic}'."}
        
        new_messages = [
            (index, sender, content) 
            for index, sender, content in self.messages.get(topic, []) 
            if index > last_read
        ]
        logger.info(f"Peer {peer_id} retrieved messages from topic '{topic}'")
        return {"status": "messages_retrieved", "messages": new_messages}

    async def view_subscribed_topics(self, message, peer_id):
        subscribed = [topic for topic, data in self.topics.items() if peer_id in data['subscribers']]
        logger.info(f"Peer {peer_id} viewed subscribed topics: {subscribed}")
        return {"status": "subscribed_topics", "topics": subscribed}

    async def view_created_topics(self, message, peer_id):
        created_topics = list(self.topics.keys())
        logger.info(f"Viewed created topics: {created_topics}")
        return {"status": "created_topics", "topics": created_topics}

    async def get_topic_host(self, message, peer_id):
        topic = message.get("topic")
        if not topic:
            return {"status": "error", "message": "Missing 'topic' field."}
        if topic not in self.topics:
            return {"status": "error", "message": f"Topic '{topic}' does not exist."}
        host_peer = self.topics[topic]['host_peer']
        return {"status": "success", "host_peer": host_peer}

    def load_registered_peers(self):
        try:
            with open(self.registered_peers_file, 'r') as f:
                self.peers = json.load(f)
            logger.info(f"Loaded {len(self.peers)} registered peers from file")
        except FileNotFoundError:
            logger.warning("Registered peers file not found. Starting with empty peer list.")
        except json.JSONDecodeError:
            logger.error("Error decoding registered peers file. Starting with empty peer list.")

    def save_registered_peers(self):
        with open(self.registered_peers_file, 'w') as f:
            json.dump(self.peers, f)
        logger.info("Saved registered peers to file")

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

if __name__ == '__main__':
    config = load_config()
    server = IndexingServer(config)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    asyncio.run(server.start())