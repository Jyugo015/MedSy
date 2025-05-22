let isLoggedIn = false;

function staffLogin() {
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  // Simulate login check
  if (username === "staff" && password === "clinic123") {
    document.getElementById("loginContainer").classList.add("hidden");
    document.getElementById("roleAssignmentContainer").classList.add("hidden");
    document.getElementById("mainPanel").classList.remove("hidden");
    isLoggedIn = true;
  } else if (username === "admin" && password === "admin123") {
    document.getElementById("loginContainer").classList.add("hidden");
    document.getElementById("roleAssignmentContainer").classList.remove("hidden");
    document.getElementById("mainPanel").classList.add("hidden");
    isLoggedIn = true;
  } else {
    document.getElementById("loginError").classList.remove("hidden");
  }
}

function toggleAddRecord() {
  const panel = document.getElementById("addRecordPanel");
  panel.classList.toggle("hidden");
}

// function viewRecords() {
//   const patientID = document.getElementById("patientID").value;
//   if (!patientID) return alert("Please enter a Patient ID");

//   fetch(`/api/records/${patientID}`)
//     .then((res) => res.json())
//     .then((data) => {
//       document.getElementById("recordsDisplay").textContent = JSON.stringify(
//         data,
//         null,
//         2
//       );
//       document.getElementById("recordsPanel").classList.remove("hidden");
//     })
//     .catch((err) => alert("Error fetching records."));
// }

function viewRecords() {
  const patientID = document.getElementById("patientID").value;
  if (!patientID) return alert("Please enter a Patient ID");

  const senderAddress = "0xDaeA53C2A027A7Ba7906FE7d37B44462d8847bec";
  const token = "fake-auth-token";

  fetch(`/api/records/${patientID}`, {
    method: "GET",
    headers: {
      Authorization: token,
      "X-User-Address": senderAddress,
    },
  })
    .then((res) => res.json())
    .then((data) => {
      document.getElementById("recordsDisplay").textContent = JSON.stringify(
        data,
        null,
        2
      );
      document.getElementById("recordsPanel").classList.remove("hidden");
    })
    .catch((err) => alert("Error fetching records."));
}

document.getElementById("recordForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const formData = new FormData(this);

  // Upload file to IPFS
  const uploadRes = await fetch("/api/upload_to_ipfs", {
    method: "POST",
    body: formData,
  });

  const { ipfsHash } = await uploadRes.json();
  if (!ipfsHash) return alert("Failed to upload to IPFS");

  const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
  const senderAddress = accounts[0];

  const data = {
    patientAddress: formData.get("patientAddress"),
    condition: formData.get("condition"),
    diagnosis: formData.get("diagnosis"),
    treatment: formData.get("treatment"),
    ipfsHash,
    timestamp: Date.now()
  };

  const msg = JSON.stringify(data);

  // Sign message
  const signature = await window.ethereum.request({
    method: "personal_sign",
    params: [msg, senderAddress],
  });

  // Send signed data to backend
  const res = await fetch("/api/records/signed", {
    method: "POST",
    headers: {
      Authorization: "fake-auth-token",
      "Content-Type": "application/json",
      "X-User-Address": senderAddress,
    },
    body: JSON.stringify({
      data,
      signature
    }),
  });

  const result = await res.json();
  if (res.ok) {
    alert("Record saved successfully (off-chain)");
    this.reset();
  } else {
    alert("Error: " + result.error);
  }
});


// async function uploadFileToIPFS(file) {
//   const formData = new FormData();
//   formData.append("file", file);

//   const res = await fetch("/api/upload_to_ipfs", {
//     method: "POST",
//     body: formData
//   });

//   const data = await res.json();
//   return data.ipfs_hash || "";
// }


// document.getElementById("recordForm").addEventListener("submit", async function (e) {
//   e.preventDefault();

//   const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
//   const senderAddress = accounts[0];

//   const form = new FormData(this);
//   const payload = {
//     patientAddress: form.get("patientAddress"),
//     condition: form.get("condition"),
//     diagnosis: form.get("diagnosis"),
//     treatment: form.get("treatment"),
//     senderAddress: senderAddress,
//     ipfsHash: await uploadFileToIPFS(form.get("file")) // optional if using IPFS
//   };

//   const txResponse = await fetch("/api/records/prepare_tx", {
//     method: "POST",
//     headers: {
//       Authorization: "fake-auth-token",
//       "Content-Type": "application/json",
//       "X-User-Address": senderAddress,
//     },
//     body: JSON.stringify(payload)
//   });

//   const tx = await txResponse.json();

//   if (tx.error) {
//     alert(tx.error);
//     return;
//   }

//   // Send transaction using Metamask
//   const txHash = await window.ethereum.request({
//     method: 'eth_sendTransaction',
//     params: [tx]
//   });

//   alert("Transaction sent: " + txHash);
// });


async function setCurrentAddress() {
  try {
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    const currentAddress = accounts[0];
    const addressInput = document.getElementById("addressInput");
    addressInput.value = currentAddress;
    addressInput.readOnly = true;
  } catch (err) {
    console.error("MetaMask not connected or rejected:", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const addressInput = document.getElementById("addressInput");
  const radioButtons = document.querySelectorAll('input[name="addressOption"]');

  // Set current address on load (default)
  setCurrentAddress();

  radioButtons.forEach(radio => {
    radio.addEventListener("change", (e) => {
      if (e.target.value === "current") {
        setCurrentAddress();
      } else {
        addressInput.value = "";
        addressInput.readOnly = false;
        addressInput.placeholder = "Enter wallet address";
      }
    });
  });
});

// Submit handler
document.getElementById("addRoleForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const form = new FormData(this);
  const address = form.get("address");
  const role = form.get("role");

  const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
  const senderAddress = accounts[0];

  const res = await fetch("/api/admin/add_role", {
    method: "POST",
    headers: {
      Authorization: "fake-auth-token",
      "X-User-Address": senderAddress,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ role, address })
  });

  const result = await res.json();
  alert(result.message || result.error);
});
