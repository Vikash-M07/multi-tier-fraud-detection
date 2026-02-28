from flask import Flask, render_template, request, redirect, jsonify, session
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "fraud_secret_key"

DATABASE = "fraud.db"


# -------------------------
# DATABASE CONNECTION
# -------------------------
def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------
# INITIALIZE DATABASE
# -------------------------
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier TEXT NOT NULL,
        amount REAL NOT NULL,
        risk INTEGER NOT NULL
    )
    """)

    # Add date column if missing
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN date TEXT")
    except:
        pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier TEXT NOT NULL,
        risk INTEGER NOT NULL,
        message TEXT NOT NULL,
        date TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


init_db()


# -------------------------
# SMART FRAUD CALCULATION
# -------------------------
def calculate_risk(supplier, amount):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT amount, risk FROM transactions WHERE supplier=?",
        (supplier,)
    )
    history = cursor.fetchall()
    conn.close()

    risk = 0

    # Amount weight
    if amount > 10000:
        risk += 40
    elif amount > 5000:
        risk += 25
    else:
        risk += 10

    # Historical deviation
    if history:
        avg_amount = sum(row["amount"] for row in history) / len(history)
        if amount > avg_amount * 2:
            risk += 20

    # Previous fraud history
    previous_fraud = len([row for row in history if row["risk"] > 70])
    risk += previous_fraud * 5

    # Random simulation factor
    risk += random.randint(0, 10)

    return min(risk, 100)


# -------------------------
# LOGIN
# -------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == "admin" and password == "admin123":
            session["user"] = username
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid Credentials")

    return render_template("login.html")


# -------------------------
# DASHBOARD
# -------------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html")


# -------------------------
# ANALYZE TRANSACTION
# -------------------------
@app.route("/analyze", methods=["POST"])
def analyze():

    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        supplier = request.form.get("supplier", "").strip()
        amount = request.form.get("amount", "").strip()

        if supplier == "" or amount == "":
            return jsonify({
                "status": "error",
                "message": "Supplier and amount required"
            }), 400

        amount = float(amount)

        risk = calculate_risk(supplier, amount)

        conn = get_db()
        cursor = conn.cursor()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO transactions (supplier, amount, risk, date)
            VALUES (?, ?, ?, ?)
        """, (supplier, amount, risk, now))

        # Create alert if risk high
        if risk >= 80:
            cursor.execute("""
                INSERT INTO alerts (supplier, risk, message, date)
                VALUES (?, ?, ?, ?)
            """, (
                supplier,
                risk,
                f"⚠ High Risk Transaction Detected for {supplier}",
                now
            ))

        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "risk": risk
        })

    except Exception as e:
        print("SERVER ERROR:", e)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# -------------------------
# GET TRANSACTION DATA
# -------------------------
@app.route("/get_data")
def get_data():

    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT supplier, risk, amount FROM transactions")
    rows = cursor.fetchall()
    conn.close()

    suppliers = [row["supplier"] for row in rows]
    risks = [row["risk"] for row in rows]
    amounts = [row["amount"] for row in rows]

    total = len(rows)
    high_risk = len([r for r in risks if r >= 80])
    avg_risk = sum(risks) / total if total > 0 else 0

    return jsonify({
        "suppliers": suppliers,
        "risks": risks,
        "amounts": amounts,
        "total": total,
        "high_risk": high_risk,
        "avg_risk": round(avg_risk, 2)
    })


# -------------------------
# GET ALERTS
# -------------------------
@app.route("/get_alerts")
def get_alerts():

    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT supplier, risk, message, date
        FROM alerts
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    alerts = [{
        "supplier": row["supplier"],
        "risk": row["risk"],
        "message": row["message"],
        "date": row["date"]
    } for row in rows]

    return jsonify(alerts)

from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import TableStyle
import os


@app.route("/export_pdf")
def export_pdf():

    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT supplier, amount, risk, date FROM transactions")
    rows = cursor.fetchall()
    conn.close()

    file_path = "fraud_report.pdf"
    doc = SimpleDocTemplate(file_path)

    elements = []

    data = [["Supplier", "Amount", "Risk", "Date"]]

    for row in rows:
        data.append([
            row["supplier"],
            str(row["amount"]),
            str(row["risk"]),
            row["date"]
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("GRID", (0,0), (-1,-1), 1, colors.black)
    ]))

    elements.append(table)
    doc.build(elements)

    return send_file(file_path, as_attachment=True)
# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------------------------
# RUN APP
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)