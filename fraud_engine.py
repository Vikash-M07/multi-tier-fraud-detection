import hashlib
import networkx as nx
import random

G = nx.DiGraph()

known_invoices = set()

def generate_fingerprint(invoice_no, amount, supplier):
    raw = f"{invoice_no}{amount}{supplier}"
    return hashlib.sha256(raw.encode()).hexdigest()

def detect_fraud(data):

    invoice_no = data["invoice_no"]
    amount = float(data["amount"])
    supplier = data["supplier"]
    buyer = data["buyer"]
    lender = data["lender"]

    fingerprint = generate_fingerprint(invoice_no, amount, supplier)

    risk_score = 0

    # Rule 1: Duplicate invoice
    if fingerprint in known_invoices:
        risk_score += 70
    else:
        known_invoices.add(fingerprint)

    # Rule 2: High amount
    if amount > 100000:
        risk_score += 20

    # Rule 3: Network suspicious activity
    G.add_edge(supplier, buyer)
    if G.degree(supplier) > 3:
        risk_score += 20

    # Rule 4: Random anomaly simulation
    risk_score += random.randint(0, 20)

    if risk_score > 100:
        risk_score = 100

    status = "FRAUD" if risk_score > 60 else "SAFE"

    return {
        "fingerprint": fingerprint,
        "risk_score": risk_score,
        "status": status
    }