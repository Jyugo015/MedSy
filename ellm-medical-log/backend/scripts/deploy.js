const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    const [deployer] = await ethers.getSigners();
    console.log("Deploying contract with address:", deployer.address);

    //   const balance = await deployer.getBalance();
    //   console.log("Account balance:", balance.toString());

    const Contract = await ethers.getContractFactory("MedicalRecord");
    const contract = await Contract.deploy();
    await contract.waitForDeployment();

    const deployedAddress = await contract.getAddress();
    console.log("Contract deployed at:", deployedAddress);

    // Save contract address and ABI
    const contractsDir = path.join(__dirname, "../frontend/src/contracts");
    if (!fs.existsSync(contractsDir)) {
        fs.mkdirSync(contractsDir, { recursive: true });
    }

    fs.writeFileSync(
        path.join(contractsDir, "contract-address.json"),
        JSON.stringify({ address: contract.deployedAddress }, null, 2)
    );

    fs.writeFileSync(
        path.join(contractsDir, "abi.json"),
        JSON.stringify(contract.interface.format("json"), null, 2)
    );
}

main().catch((error) => {
    console.error("Deployment failed:", error);
    process.exitCode = 1;
});
