# Medical Log Blockchain

## create metamask account at chrome

## create .env
BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545

CONTRACT_ADDRESS=

FLASK_DEBUG=True

OWNER_ADDRESS=

PRIVATE_KEY=

FLASK_PORT=5001

## open termianl
cd backend
npm install -g ganache

ganache --chain.chainId 1337

## open another terminal
npx hardhat run scripts/deploy.js --network localhost

Deploying contract with address: xxx (copy and put at .env OWNER_ADDRESS)

Contract deployed at: xxx (copy and put at .env CONTRACT_ADDRESS)

Go to previous terminal, copy and put PRIVATE KEY .env based on OWNER_ADDRESS
