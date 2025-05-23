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

async function viewRecords() {
  const recordsPanel = document.getElementById("recordsPanel");

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
}

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

  // Step 3: Sign the metadata JSON
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
