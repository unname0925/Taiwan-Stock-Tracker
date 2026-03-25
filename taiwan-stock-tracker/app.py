from flask import Flask, render_template, jsonify, request
import json
import os
from datetime import datetime, timedelta
import yfinance as yf
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

app = Flask(__name__)

DATA_FILE   = "data/stocks.json"
CONFIG_FILE = "data/config.json"
ORDERS_FILE = "data/orders.json"
TAIWAN_TZ   = pytz.timezone("Asia/Taipei")

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_config():
    default = {
        "stocks": [
            {"symbol": "2330.TW", "name": "台積電"},
            {"symbol": "2317.TW", "name": "鴻海"},
            {"symbol": "2454.TW", "name": "聯發科"},
            {"symbol": "2881.TW", "name": "富邦金"},
            {"symbol": "2882.TW", "name": "國泰金"},
        ]
    }
    return load_json(CONFIG_FILE, default)

def load_data():
    default = {"high": {}, "low": {}, "close": {}}
    return load_json(DATA_FILE, default)

def save_data(data):
    save_json(DATA_FILE, data)

def load_orders():
    return load_json(ORDERS_FILE, [])

def save_orders(orders):
    save_json(ORDERS_FILE, orders)

def tw_today():
    return datetime.now(TAIWAN_TZ).strftime("%Y-%m-%d")

def prev_trading_day():
    """Return most recent weekday date string (Taiwan time)."""
    dt = datetime.now(TAIWAN_TZ)
    
    while dt.weekday() >= 5:   
        dt -= timedelta(days=1)
    return dt.strftime("%Y-%m-%d")


def fetch_stock_data():
    """Fetch previous trading day OHLC for all configured stocks."""
    config = load_config()
    data = load_data()
    date_key = prev_trading_day()

    print(f"[{datetime.now(TAIWAN_TZ)}] Fetching data for {date_key} …")

    for stock in config["stocks"]:
        symbol = stock["symbol"]
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                print(f"  ✗ No data for {symbol}")
                continue

            row = hist.iloc[-1]
            actual_date = hist.index[-1].strftime("%Y-%m-%d")

            for table in ("high", "low", "close"):
                if symbol not in data[table]:
                    data[symbol] = {}          
                    data[table][symbol] = {}

            data["high"][symbol][actual_date]  = round(float(row["High"]),  2)
            data["low"][symbol][actual_date]   = round(float(row["Low"]),   2)
            data["close"][symbol][actual_date] = round(float(row["Close"]), 2)
            print(f"  ✓ {symbol}: H={data['high'][symbol][actual_date]}  "
                  f"L={data['low'][symbol][actual_date]}  "
                  f"C={data['close'][symbol][actual_date]}")
        except Exception as e:
            print(f"  ✗ {symbol}: {e}")

    save_data(data)
    print("Done.\n")
    return date_key

@app.route("/")
def index():
    config = load_config()
    data   = load_data()
    
    all_dates = set()
    for sym_data in data["close"].values():
        all_dates.update(sym_data.keys())
    date_key = max(all_dates) if all_dates else prev_trading_day()

    dashboard = []
    for stock in config["stocks"]:
        sym = stock["symbol"]
        dashboard.append({
            "symbol": sym,
            "name":   stock["name"],
            "high":   data["high"].get(sym,  {}).get(date_key),
            "low":    data["low"].get(sym,   {}).get(date_key),
            "close":  data["close"].get(sym, {}).get(date_key),
        })

    return render_template("index.html",
                           dashboard=dashboard,
                           date=date_key,
                           today=tw_today())

@app.route("/tables")
def tables():
    config = load_config()
    data   = load_data()
    stocks = config["stocks"]

    all_dates = set()
    for table in ("high", "low", "close"):
        for sym_data in data[table].values():
            all_dates.update(sym_data.keys())
    dates = sorted(all_dates, reverse=True)[:60]   

    def build_table(table_key):
        rows = []
        for stock in stocks:
            sym = stock["symbol"]
            row = {"symbol": sym, "name": stock["name"], "prices": []}
            for d in dates:
                row["prices"].append(data[table_key].get(sym, {}).get(d))
            rows.append(row)
        return rows

    return render_template("tables.html",
                           dates=dates,
                           high_rows=build_table("high"),
                           low_rows=build_table("low"),
                           close_rows=build_table("close"))

@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    date = fetch_stock_data()
    return jsonify({"status": "ok", "date": date})

@app.route("/api/stocks", methods=["GET"])
def api_stocks():
    return jsonify(load_config()["stocks"])

@app.route("/api/stocks", methods=["POST"])
def api_add_stock():
    body = request.json
    config = load_config()
    symbol = body.get("symbol", "").upper().strip()
    name   = body.get("name", "").strip()
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    if not symbol.endswith(".TW"):
        symbol += ".TW"

    if any(s["symbol"] == symbol for s in config["stocks"]):
        return jsonify({"error": "already exists"}), 409
    config["stocks"].append({"symbol": symbol, "name": name or symbol})
    save_json(CONFIG_FILE, config)
    return jsonify({"status": "added", "symbol": symbol})

@app.route("/api/stocks/<path:symbol>", methods=["DELETE"])
def api_delete_stock(symbol):
    config = load_config()
    before = len(config["stocks"])
    config["stocks"] = [s for s in config["stocks"] if s["symbol"] != symbol]
    if len(config["stocks"]) == before:
        return jsonify({"error": "not found"}), 404
    save_json(CONFIG_FILE, config)
    return jsonify({"status": "deleted"})

@app.route("/manage")
def manage():
    config = load_config()
    return render_template("manage.html", stocks=config["stocks"])

@app.route("/orders")
def orders():
    orders_list = load_orders()
    config = load_config()
    data   = load_data()
    date_key = prev_trading_day()


    tracked = {s["symbol"]: s["name"] for s in config["stocks"]}
    for o in orders_list:
        sym = o["symbol"]
        o["current_price"] = data["close"].get(sym, {}).get(date_key)
        o["tracked_name"]  = tracked.get(sym)

    return render_template("orders.html",
                           orders=orders_list,
                           tracked_stocks=config["stocks"],
                           date=date_key)

@app.route("/api/orders", methods=["GET"])
def api_get_orders():
    return jsonify(load_orders())

@app.route("/api/orders", methods=["POST"])
def api_add_order():
    body = request.json
    symbol = body.get("symbol", "").upper().strip()
    name   = body.get("name",   "").strip()
    try:
        target_price = round(float(body.get("target_price", 0)), 2)
        lots         = int(body.get("lots", 1))
    except (ValueError, TypeError):
        return jsonify({"error": "invalid number"}), 400

    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    if not symbol.endswith(".TW") and not symbol.endswith(".TWO"):
        symbol += ".TW"
    if target_price <= 0:
        return jsonify({"error": "target price must be > 0"}), 400
    if lots <= 0:
        return jsonify({"error": "lots must be > 0"}), 400

    import uuid
    order = {
        "id":           str(uuid.uuid4())[:8],
        "symbol":       symbol,
        "name":         name or symbol,
        "target_price": target_price,
        "lots":         lots,
        "shares":       lots * 1000,
        "total":        round(target_price * lots * 1000, 2),
        "status":       "pending",  
        "note":         body.get("note", "").strip(),
        "created_at":   datetime.now(TAIWAN_TZ).strftime("%Y-%m-%d %H:%M"),
    }
    orders_list = load_orders()
    orders_list.append(order)
    save_orders(orders_list)
    return jsonify({"status": "added", "order": order})

@app.route("/api/orders/<order_id>", methods=["PATCH"])
def api_update_order(order_id):
    body = request.json
    orders_list = load_orders()
    for o in orders_list:
        if o["id"] == order_id:
            if "status" in body:
                o["status"] = body["status"]
            if "target_price" in body:
                o["target_price"] = round(float(body["target_price"]), 2)
                o["total"] = round(o["target_price"] * o["shares"], 2)
            if "lots" in body:
                o["lots"]   = int(body["lots"])
                o["shares"] = o["lots"] * 1000
                o["total"]  = round(o["target_price"] * o["shares"], 2)
            if "note" in body:
                o["note"] = body["note"].strip()
            save_orders(orders_list)
            return jsonify({"status": "updated", "order": o})
    return jsonify({"error": "not found"}), 404

@app.route("/api/orders/<order_id>", methods=["DELETE"])
def api_delete_order(order_id):
    orders_list = load_orders()
    before = len(orders_list)
    orders_list = [o for o in orders_list if o["id"] != order_id]
    if len(orders_list) == before:
        return jsonify({"error": "not found"}), 404
    save_orders(orders_list)
    return jsonify({"status": "deleted"})



def start_scheduler():
    scheduler = BackgroundScheduler(timezone=TAIWAN_TZ)
    scheduler.add_job(fetch_stock_data, "cron",
                      day_of_week="mon-fri", hour=18, minute=0)
    scheduler.start()
    print("Scheduler started — auto-fetch at 18:00 Taiwan time on weekdays.")


if __name__ == "__main__":
    # Fetch on startup if today's data is missing
    data = load_data()
    config = load_config()
    date_key = prev_trading_day()
    missing = any(
        data["close"].get(s["symbol"], {}).get(date_key) is None
        for s in config["stocks"]
    )
    if missing:
        print("Missing data detected — fetching now …")
        fetch_stock_data()

    start_scheduler()
    app.run(host="0.0.0.0", port=5000, debug=False)
    