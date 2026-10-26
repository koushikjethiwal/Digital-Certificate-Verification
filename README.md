# 🎓 CertChain | Digital Certificate Verification Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)

**CertChain** is a professional-grade academic prototype designed to eliminate credential forgery. By combining a relational database with a custom blockchain implementation, CertChain ensures that digital certificates are immutable, transparent, and instantly verifiable.

---

## 🌟 Key Features

- **🚀 Analytics Dashboard:** A real-time hub monitoring total issuances, chain height, and global system integrity.
- **⛓️ Visual Blockchain Explorer:** A graphical representation of the cryptographically linked ledger.
- **🛡️ Integrity Engine:** Uses SHA-256 hashing to detect any modification in certificate records.
- **🧪 Tampering Simulation Lab:** A controlled environment to demonstrate how blockchain detects database attacks.
- **📱 Responsive Design:** A premium SaaS-inspired UI that works across all device sizes.

## 🛠 Technology Stack

- **Backend:** Python 3.x, Flask
- **Storage:** SQLite (Relational Data), JSON (Blockchain Ledger)
- **Cryptography:** SHA-256 (hashlib)
- **Frontend:** Jinja2, CSS3 (Modern Grid/Flex), HTML5

---

## 🚀 Getting Started (MacBook Air M1)

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/certchain.git
cd certchain

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Execution
```bash
python3 app.py
```
Visit **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 📖 Demonstration Workflow

1. **Issuance:** Navigate to `Issue` $\rightarrow$ Enter Student Details $\rightarrow$ Generate Certificate.
2. **Verification:** Copy the `Certificate ID` $\rightarrow$ Navigate to `Verify` $\rightarrow$ Confirm Authenticity.
3. **Inspection:** Visit the `Blockchain Explorer` to see the linked hash chain.
4. **The Attack:** Use the `Tampering Lab` to modify a record $\rightarrow$ Re-verify to see the integrity failure.

## 📐 System Architecture

**The Trust Loop:**
`Input Data` $\rightarrow$ `SHA-256 Hash` $\rightarrow$ `SQLite Record` + `Blockchain Block` $\rightarrow$ `Verification Check`

---

## ⚠️ Academic Disclaimer
This project is a **Proof of Concept (PoC)**. It uses a local blockchain stored on a single server for educational demonstration. A production-grade system would utilize a decentralized consensus network (e.g., Ethereum, Hyperledger) to ensure true immutability.

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
