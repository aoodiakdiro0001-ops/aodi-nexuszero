// SPDX-License-Identifier: MIT
// Aodı-NexusZero — optional public anchor for the local sha256 seal chain.
// Pin the head hash of your local chain here; anyone can then verify the
// chain head on-chain while all artifacts stay on your machines.
pragma solidity ^0.8.20;

contract NexusSeal {
    struct Entry {
        bytes32 head;
        uint64  size;
        uint64  timestamp;
    }

    mapping(address => Entry) private latest;
    mapping(address => bytes32[]) private history;

    event Anchored(address indexed owner, bytes32 head, uint64 size);

    function anchor(bytes32 head, uint64 size) external {
        latest[msg.sender] = Entry(head, size, uint64(block.timestamp));
        history[msg.sender].push(head);
        emit Anchored(msg.sender, head, size);
    }

    function get(address owner) external view
        returns (bytes32 head, uint64 size, uint64 timestamp)
    {
        Entry memory e = latest[owner];
        return (e.head, e.size, e.timestamp);
    }

    function historyOf(address owner) external view returns (bytes32[] memory) {
        return history[owner];
    }
}
