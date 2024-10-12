# Advance Operating Systems CS 550 
# Programming Assignment 2
# Name: Harsh Shah
# P2P Publisher-Subscriber System

This Assignment implements a P2P (Peer-to-Peer) Publisher-Subscriber system with an Indexing Server that manages the topics and connected peers. Each peer can either publish or subscribe to topics, while the indexing server keeps track of the topics across the peer nodes.

## Project Structure

- `indexing_server.py`: The central server that tracks all topics across peer nodes and handles requests for topic registration and subscription.
- `peer_node.py`: A peer node that can either publish or subscribe to topics. Each peer connects to the indexing server and communicates with other peers.
- `config.json`: Configuration file containing the IP addresses and ports for the indexing server and peer nodes.
- 'Test_1.py', 'Test_2.py', 'Test_3.py': These are the testing files which test the indexing server and peer node against various test scenarios.
- There is a 'peer_node_test.py' file in the Code folder. This file is a little modified version of 'peer_node.py' file. Only thing being different is that, it does not ask for the input of Peer ID, it takes input for the same directly from the TEST files. This is done to run the tests smoothly without any errors.

## Setup and Usage

### Prerequisites

- Python 3.x
- Required Python packages (you can install these with pip if necessary):
  - `socket`
  - `json`
  - `threading`

### Configuration

Before running the system, ensure that the `config.json` file is correctly configured to an empty port on your network, e.g. '8080'

# Usage through makefile
1. Run the indexing server by using the makefile provided. Simply open terminal in the Code folder and then run the following command: "make"
2. Run the peer node by using the makefile provided. Simply open a new terminal in the Code folder and then run the following command: "make run_peer_node"
3. Run all the test files by using the makefile provided. Simply open terminal in the Code folder and then run the following command: "make run_tests"

# Manually using the server and peer.
1. Run the indexing server by running the following command in the terminal: "python indexing_server.py/ python3 indexing_server.py".
2. Run the peer node by running the following command in the terminal: "python peer_node.py/ python3 peer_node.py'.
3. Run the test files by running the following command in the terminal: "python Test_1.py/ python3 Test_1.py'.
4. Run the test files by running the following command in the terminal: "python Test_2.py/ python3 Test_2.py'.
5. Run the test files by running the following command in the terminal: "python Test_3.py/ python3 Test_3.py'.

# Usage:
1. Choose between Publisher and Subscriber mode from the main menu.
2. Follow the prompts to register, login, create topics, send messages, and pull messages.

