# 📄 README — AI Event Output Guide（Frontend Integration）
## Overview

後端的 AI 功能目前透過 WebSocket 主動推送結果給前端，用於顯示：
* Inventory Analysis
* Menu Suggestions
* Restock Plan
* Procurement Plan

前端不需要等候 REST API，只要處理 WebSocket 事件即可。
---

## 🔌 WebSocket Event Format

後端透過 ```/ws?room_id=<id>``` 推送事件。

每一個 AI 事件都會長這樣：
```json
{
  "type": "ai_event",
  "event": "inventory_analysis",   // or menu_suggestions, restock_plan, procurement_plan
  "room_id": 1,
  "narrative": "A friendly natural language summary.",
  "payload": { ... }               // AI 模組產出的 JSON
}
```

前端只需要根據 ```event``` 來決定使用哪個 UI component。

## 📦 Supported AI Events & Payload Schema

以下是後端已固定的 Output Format（安全可依賴）。

---
### 1️⃣ ```event = "inventory_analysis"```

WS example:
```json
{
  "type": "ai_event",
  "event": "inventory_analysis",
  "room_id": 1,
  "narrative": "Your stock levels need some attention.",
  "payload": {
    "narrative": "Your inventory has some items running low.",
    "low_stock": [
      {
        "product_name": "Tomatoes",
        "stock": 5,
        "safety_stock": 10,
        "status": "critical",
        "recommended_restock_qty": 6,
        "recommended_grocery_items": [
          { "title": "Roma Tomatoes Pack", "price": 3.99, "rating": 4.5 }
        ]
      }
    ],
    "healthy": [
      {
        "product_name": "Olive Oil",
        "stock": 12,
        "safety_stock": 5
      }
    ]
  }
}
```

### 2️⃣ ```event = "menu_suggestions"```
```json
{
  "type": "ai_event",
  "event": "menu_suggestions",
  "room_id": 1,
  "narrative": "Here are dishes you can prepare today!",
  "payload": {
    "narrative": "Based on your ingredients, here are suggested dishes.",
    "dishes": [
      {
        "name": "Tomato Pasta",
        "ingrdients_used": ["Tomatoes", "Cheese"],
        "missing_ingredients": ["Basil"],
        "recommended_grocery_items": [
          { "title": "Fresh Basil Bunch", "price": 2.99, "rating": 4.7 }
        ]
      }
    ]
  }
}
```

### 3️⃣ ```event = "restock_plan"```
```json
{
  "type": "ai_event",
  "event": "restock_plan",
  "room_id": 1,
  "narrative": "Here is your weekly restock plan.",
  "payload": {
    "goal": "",
    "summary": "3 items need restocking.",
    "narrative": "You are running low on tomatoes and milk.",
    "items": [
      {
        "name": "Tomatoes",
        "quantity": 8,
        "notes": "Stock below safety level.",
        "price_estimate": 3.99,
        "supplier": "Amazon Fresh"
      }
    ]
  }
}
```

### 4️⃣ ```event = "procurement_plan"```
```json
{
  "type": "ai_event",
  "event": "procurement_plan",
  "room_id": 1,
  "narrative": "Here is your procurement shopping plan.",
  "payload": {
    "goal": "Dinner party prep",
    "summary": "3 ingredients needed.",
    "narrative": "You need to buy a few ingredients for the dinner party.",
    "items": [
      {
        "name": "Chicken Breast",
        "quantity": "2 lbs",
        "notes": "Main protein for the dish."
      }
    ]
  }
}
```

## 🎨 Frontend Responsibilities

前端要做的只有三件事：

### ✔ 1. WebSocket Listener
```dart
socket.onMessage.listen((data) {
  final json = jsonDecode(data);

  if (json["type"] == "ai_event") {
    final eventType = json["event"];
    final narrative = json["narrative"];
    final payload = json["payload"];

    // TODO: switch UI component based on eventType
  }
});
```

## ✔ 2. 根據 event 呈現不同 UI

* ```inventory_analysis``` → 條列 low_stock & healthy
* ```menu_suggestions``` → 菜單卡片
* ```restock_plan``` → 補貨列表 + 價格
* procurement_plan → 代辦採購表
  
---

## ✔ 3. Render narrative（一定有）

每個 AI 事件都有一段：
```
narrative: "<friendly explanation>"
```

前端可以直接在 UI 顯示成：
💡 AI Summary: …


## 📌 Notes

* 所有 AI 模組都保證輸出固定 JSON shape。
* 前端不需要解析 LLM 原始文字。