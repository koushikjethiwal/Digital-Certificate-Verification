import hashlib
import json
import time
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

class Block:
    """
    A Block represents a single record in the blockchain.
    Think of it as a page in a ledger.
    """
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index            # Position of the block in the chain
        self.timestamp = timestamp    # Time when the block was created
        self.data = data              # The actual certificate hash or data
        self.previous_hash = previous_hash  # The link to the previous block
        self.hash = self.calculate_hash()    # The unique fingerprint of this block

    def calculate_hash(self):
        """
        Creates a SHA-256 hash of the block's contents.
        If any single character in the block changes, the hash changes completely.
        """
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash
        }, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self):
        """Convert block to dictionary for JSON storage."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash
        }

class Blockchain:
    """
    The Blockchain manages the list of blocks and ensures they are linked correctly.
    """
    def __init__(self, storage_file=None):
        if storage_file is None:
            self.storage_file = os.path.join(PROJECT_ROOT, "data", "blockchain.json")
        else:
            self.storage_file = storage_file
        self.chain = []
        self.load_chain()

    def create_genesis_block(self):
        """
        The first block in every blockchain is called the 'Genesis Block'.
        It has no previous block, so its previous_hash is "0".
        """
        return Block(0, time.time(), "Genesis Block", "0")

    def add_block(self, data):
        """
        Adds a new block to the chain.
        The new block MUST point to the hash of the previous block.
        """
        previous_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            data=data,
            previous_hash=previous_block.hash
        )
        self.chain.append(new_block)
        self.save_chain()
        return new_block

    def is_chain_valid(self):
        """
        The most important function. It checks if the chain is unbroken.
        1. It re-calculates the hash of every block to see if data was changed.
        2. It checks if the 'previous_hash' of block N matches the 'hash' of block N-1.
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]

            # Check 1: Has the data in the current block been tampered with?
            if current.hash != current.calculate_hash():
                return False, f"Block {i} has been modified!"

            # Check 2: Is the link to the previous block broken?
            if current.previous_hash != previous.hash:
                return False, f"Block {i} is not linked to Block {i-1} correctly!"

        return True, "Blockchain is valid."

    def save_chain(self):
        """Saves the blockchain to a JSON file so data persists after restart."""
        try:
            # Ensure the data directory exists
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            with open(self.storage_file, "w") as f:
                json.dump([block.to_dict() for block in self.chain], f, indent=4)
        except Exception as e:
            print(f"Error saving blockchain: {e}")

    def load_chain(self):
        """Loads the blockchain from the JSON file."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r") as f:
                    data = json.load(f)
                    if not data:
                        self.initialize_new_chain()
                        return

                    self.chain = []
                    for item in data:
                        block = Block(item['index'], item['timestamp'], item['data'], item['previous_hash'])
                        block.hash = item['hash'] # Keep the stored hash for verification
                        self.chain.append(block)

                    # Basic sanity check: first block must be Genesis
                    if not self.chain or self.chain[0].data != "Genesis Block":
                        print("Blockchain corrupted: Genesis block missing. Initializing new chain.")
                        self.initialize_new_chain()
            except (json.JSONDecodeError, KeyError, Exception) as e:
                print(f"Error loading blockchain: {e}. Initializing new chain.")
                self.initialize_new_chain()
        else:
            self.initialize_new_chain()

    def initialize_new_chain(self):
        """Starts a fresh chain with a Genesis block."""
        self.chain = [self.create_genesis_block()]
        self.save_chain()
