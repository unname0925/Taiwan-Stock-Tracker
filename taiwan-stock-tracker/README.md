# Taiwan Stock Tracker

一個用於追蹤台灣證券交易所（TWSE）股票的區域網路 Web 應用程式。
使用 Python / Flask + yfinance 開發。

---

## Features

| Feature | Detail |
|---|---|
| **儀表板** | 顯示您追蹤的每檔股票前一個交易日的最高價、最低價和收盤價 |
| **高低點指示條** | 以視覺化長條圖顯示收盤價在當日波動範圍內的位置 |
| **歷史資料表** | 分別提供最高價、最低價、收盤價的獨立可捲動表格 |
| **自動抓取資料** | 於平日台灣時間 18:00 從 Yahoo Finance 獲取資料 |
| **手動更新資料** | 儀表板上提供「重新抓取資料」按鈕 |
| **管理股票** | 透過網頁UI介面新增/移除股票 |

---

## 環境需求
**Python 3.9+**

---

### 1. 安裝流程

```bash
cd taiwan-stock-tracker
pip install -r requirements.txt
```


### 2. 啟動伺服器

```bash
python app.py
```

應用程式將在 http://0.0.0.0:5000 啟動——可從您區域網路內的任何裝置連線。

- 從本機連線: http://localhost:5000
- 從同一個 Wi-Fi 網路下的其他裝置連線: http://<您機器的IP地址>:5000
- 透過外網 IP + 路由轉發即可訪問。

---

## 設定您的股票

### 透過網頁介面（建議）

前往上方導覽列的 管理股票。
輸入股票代號（例如 2330）與公司名稱

### 透過設定檔
編輯 `data/config.json` :
```json
{
  "stocks": [
    {"symbol": "2330.TW", "name": "台積電"},
    {"symbol": "2317.TW", "name": "鴻海"},
    {"symbol": "2454.TW", "name": "聯發科"}
  ]
}
```
編輯此檔案後請重新啟動伺服器

---


## 資料儲存

所有資料皆以 JSON 格式儲存於本機的 `data/` 資料夾中：

| File | Contents |
|---|---|
| `data/config.json` | Your stock list |
| `data/stocks.json` | Historical High / Low / Close keyed by symbol → date |

---

## 自動抓取排程

排程器會於 每週一至週五的台灣時間 18:00 (UTC+8) 執行。
