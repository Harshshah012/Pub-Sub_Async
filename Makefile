# Variables
INDEXING_SERVER = indexing_server.py
PEER_NODE = peer_node.py
TEST_1 = Test_1.py
TEST_2 = Test_2.py
TEST_3 = Test_3.py
CONFIG = config.json

# Targets
.PHONY: all run_indexing_server run_peer_node run_tests clean

# Default target: Run everything
all: run_indexing_server run_peer_node

# Run the indexing server
run_indexing_server:
	@echo "Starting the Indexing Server..."
	python3 $(INDEXING_SERVER) $(CONFIG)

# Run the peer node
run_peer_node:
	@echo "Starting a Peer Node..."
	python3 $(PEER_NODE) $(CONFIG)

# Run all the tests
run_tests:
	@echo "Running all tests..."
	python3 $(TEST_1)
	python3 $(TEST_2)
	python3 $(TEST_3)

# Stop the server using the PID file
stop_server:
	@if [ -f $(SERVER_PID_FILE) ]; then \
		kill `cat $(SERVER_PID_FILE)` && rm $(SERVER_PID_FILE); \
		echo "Server stopped."; \
	else \
		echo "No server running."; \
	fi

# Clean generated files or logs if any
clean:
	@echo "Cleaning up..."
	$(MAKE) stop_server  # Stop the server if it's running
	rm -f *.log