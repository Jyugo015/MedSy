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

async function viewRecords() {
  const recordsPanel = document.getElementById("recordsPanel");
  const display = document.getElementById("recordsDisplay");

  recordsPanel.classList.add("hidden");

  const patientAddress = document.getElementById("patientID").value;

  const viewer = await window.ethereum.request({ method: 'eth_requestAccounts' });

  const response = await fetch(`/api/patient/${patientAddress}/records?viewer=${viewer[0]}`);
  const records = await response.json();

  if (!response.ok) {
    console.error("Error:", records.error);
    alert(records.error);
    return;
  }

  // Display in UI
  console.log("Patient Records:", records);

  let html = `<h3>Medical Records</h3>`;

  if (records.length === 0) {
    html += `<pre id="recordsDisplay" class="records-display">No records found.</pre>`
  } else {
    const record = records[0];
    // records.forEach((record, index) => {
      const date = new Date(record.timestamp * 1000).toLocaleString();
      // <caption style="text-align: left; font-weight: bold; padding: 4px;">Record ${index + 1}</caption>
      html += `
        <table border="1" style="width: 100%; border-collapse: collapse; margin-bottom: 1em;">
          <tr><td><strong>Condition</strong></td><td>${record.condition}</td></tr>
          <tr><td><strong>Diagnosis</strong></td><td>${record.diagnosis}</td></tr>
          <tr><td><strong>Treatment</strong></td><td>${record.treatment}</td></tr>
          <tr>
            <td><strong>Report</strong></td>
            <td><a href="https://ipfs.io/ipfs/${record.ipfsHash}" target="_blank">Download</a></td>
          </tr>
          <tr><td><strong>Timestamp</strong></td><td>${date}</td></tr>
        </table>
      `;
    // });
  }

  recordsPanel.innerHTML = html;
  recordsPanel.classList.remove("hidden");

  // const patientID = document.getElementById("patientID").value;
  // if (!patientID) return alert("Please enter a Patient ID");

  // const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
  // const senderAddress = accounts[0];
  // const token = "fake-auth-token";

  // const message = "I authorize Dr. Smith to access my medical records";
  // const signature = await window.ethereum.request({
  //   method: "personal_sign",
  //   params: [message, patientID],
  // });

  // const response = await fetch("/api/patient/authorize", {
  //   method: "POST",
  //   headers: {
  //     "Content-Type": "application/json",
  //   },
  //   body: JSON.stringify({
  //     message: message,
  //     signature: signature,
  //     address: patientID, // the patient's address
  //   }),
  // });

  // const data = await response.json();
  // console.log(data); // should say { success: true }

  // fetch(`/api/records/${patientID}`, {
  //   method: "GET",
  //   headers: {
  //     Authorization: token,
  //     "X-User-Address": senderAddress,
  //   },
  // })
  //   .then((res) => res.json())
  //   .then((data) => {
  //     document.getElementById("recordsDisplay").textContent = JSON.stringify(
  //       data,
  //       null,
  //       2
  //     );
  //     document.getElementById("recordsPanel").classList.remove("hidden");
  //   })
  //   .catch((err) => alert("Error fetching records."));
}

// async function viewRecords() {
//   e.preventDefault();

//   const patientAddress = document.getElementById("patientAddress").value;
//   const timestamp = Date.now();
//   const message = JSON.stringify({ patientAddress, timestamp });

//   const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
//   const sender = accounts[0];

//   if (sender.toLowerCase() !== patientAddress.toLowerCase()) {
//     return alert("Connected account does not match patient address.");
//   }

//   const signature = await window.ethereum.request({
//     method: "personal_sign",
//     params: [message, sender],
//   });

//   // Send signature to server
//   await fetch("/api/records/authorize", {
//     method: "POST",
//     headers: {
//       "Content-Type": "application/json",
//     },
//     body: JSON.stringify({
//       patientAddress,
//       timestamp,
//       signature,
//     }),
//   });

//   alert("Authorization signed and saved.");
// }

// async function viewPatientRecords() {
//   const patientAddress = document.getElementById("patientID").value.trim();
//   if (!patientAddress) return alert("Please enter a patient address");

//   try {
//     const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
//     const senderAddress = accounts[0];
//     const token = "fake-auth-token";

//     const response = await fetch(`/api/records/ipfs/${patientAddress}`, {
//       method: "GET",
//       headers: {
//         Authorization: token,
//         "X-User-Address": senderAddress
//       }
//     });

//     const result = await response.json();
//     const display = document.getElementById("recordsDisplay");
//     display.innerHTML = "";

//     if (!response.ok) {
//       return alert("Error: " + result.error);
//     }

//     if (result.ipfs_hashes.length === 0) {
//       display.textContent = "No records found for this patient.";
//       return;
//     }

//     result.ipfs_hashes.forEach(hash => {
//       const link = `https://ipfs.io/ipfs/${hash}`;
//       const div = document.createElement("div");
//       div.innerHTML = `<a href="${link}" target="_blank">${link}</a>`;
//       display.appendChild(div);
//     });
//   } catch (err) {
//     console.error(err);
//     alert("Failed to fetch records.");
//   }
// }


document.getElementById("recordForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const formData = new FormData(this);

  // Step 1: Upload the file
  const uploadRes = await fetch("/api/upload_to_ipfs", {
    method: "POST",
    body: formData,
  });

  const { ipfsHash } = await uploadRes.json();
  if (!ipfsHash) return alert("Failed to upload file to IPFS");

  // Step 2: Construct record metadata
  const data = {
    patientAddress: formData.get("patientAddress"),
    condition: formData.get("condition"),
    diagnosis: formData.get("diagnosis"),
    treatment: formData.get("treatment"),
    ipfsHash: ipfsHash
    // timestamp: Date.now()
  };

  // Step 3: Upload metadata to IPFS
  const metadataRes = await fetch("/api/save_record_to_ipfs", {
    method: "POST",
    headers: {
      Authorization: "fake-auth-token",
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  });

  const metadata = await metadataRes.json();
  if (!metadata.ipfsHash) return alert("Failed to upload metadata");

  // Step 4: Sign the metadata JSON
  const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
  const senderAddress = accounts[0];

  const msg = JSON.stringify(data);

  const signature = await window.ethereum.request({
    method: "personal_sign",
    params: [msg, senderAddress],
  });

  // Step 5: Send to your /api/records/signed route
  const res = await fetch("/api/records/signed", {
    method: "POST",
    headers: {
      Authorization: "fake-auth-token",
      "Content-Type": "application/json",
      "X-User-Address": senderAddress
    },
    body: JSON.stringify({
      data,
      signature
    })
  });

  const result = await res.json();
  if (res.ok) {
    alert("Record saved successfully (off-chain)\n" + ipfsHash);
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
