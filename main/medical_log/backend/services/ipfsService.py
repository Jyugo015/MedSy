# import ipfshttpclient

# class IPFSService:
#     def __init__(self):
#         # Connect to IPFS (make sure your IPFS daemon is running)
#         self.client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')

#     def upload_file(self, file_bytes):
#         result = self.client.add_bytes(file_bytes)
#         return result  # This returns just the IPFS hash

# ipfs_service = IPFSService()
# services/ipfsService.py
import requests

class IPFSService:
    def __init__(self, api_url='http://127.0.0.1:5001/api/v0'):
        self.api_url = api_url

    def upload_file(self, file_bytes):
        files = {'file': file_bytes}
        response = requests.post(f'{self.api_url}/add', files=files)

        if response.status_code == 200:
            ipfs_hash = response.json()['Hash']
            return ipfs_hash
        else:
            raise Exception('Failed to upload file to IPFS')

# Create a singleton
ipfs_service = IPFSService()
