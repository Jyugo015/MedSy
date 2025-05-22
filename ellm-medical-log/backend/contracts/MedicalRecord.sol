// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MedicalRecord {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    struct Record {
        string condition;
        string diagnosis;
        string treatment;
        string ipfsHash;
        uint timestamp;
    }

    mapping(address => Record[]) public patientRecords;
    mapping(address => bool) public doctors;
    mapping(address => bool) public nurses;
    mapping(address => bool) public staff;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not the contract owner");
        _;
    }

    function assignRole(address _user, string memory _role) public onlyOwner {
        if (compareStrings(_role, "doctor")) {
            doctors[_user] = true;
        } else if (compareStrings(_role, "nurse")) {
            nurses[_user] = true;
        } else if (compareStrings(_role, "staff")) {
            staff[_user] = true;
        } else {
            revert("Invalid role");
        }
    }

    function addMedicalRecord(
        address _patient,
        string memory _condition,
        string memory _diagnosis,
        string memory _treatment,
        string memory _ipfsHash
    ) public {
        require(
            doctors[msg.sender] || nurses[msg.sender] || staff[msg.sender],
            "Not authorized to add"
        );

        patientRecords[_patient].push(Record({
            condition: _condition,
            diagnosis: _diagnosis,
            treatment: _treatment,
            ipfsHash: _ipfsHash,
            timestamp: block.timestamp
        }));
    }

    function getPatientRecords(address _patient) public view returns (Record[] memory) {
        require(
            msg.sender == _patient ||
            doctors[msg.sender] ||
            nurses[msg.sender] ||
            staff[msg.sender],
            "Access denied"
        );

        return patientRecords[_patient];
    }

    function compareStrings(string memory a, string memory b) internal pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }

    function isDoctor(address _addr) public view returns (bool) {
        return doctors[_addr];
    }

    function isNurse(address _addr) public view returns (bool) {
        return nurses[_addr];
    }

    function isStaff(address _addr) public view returns (bool) {
        return staff[_addr];
    }
}