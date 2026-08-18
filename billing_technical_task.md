# Billing App — Technical Specification
*Product: Credit Scoring SaaS*

## 1. Architecture & Tech Stack
- **Backend:** Django.
- **Frontend:** Django Templates with **Shadcn UI** component library.
- **Pricing Model:** Volume-based tier pricing (as the number of requests rises, the price per request lowers).
- **Scope:** Customer-facing panel only.

---

## 2. URL Routing & Views Architecture

### `/` — Usage Dashboard (Main Overview)
* **What it does:** Displays real-time consumption metrics, visual charts, and dynamic cost calculations based on tiered pricing.
* **What is on the page:**
  * **Metric Cards & Charts:** 
    * *Today* (Requests count, total price, hourly chart).
    * *Yesterday* (Requests count, total price, comparison).
    * *This Week* (Requests count, total price, daily chart).
    * *This Month* (Requests count, accumulated price, daily trend chart).
  * **Current Tier Widget:** Visual progress bar showing current volume bracket and next tier threshold.

### `/history/` — History of Usage
* **What it does:** Provides a granular log of all API calls and credit scoring requests for auditing and debugging.
* **What is on the page:**
  * **Filters Bar:** Date range picker, status selector (Success, Client Error, Server Error), and endpoint filter.
  * **Data Table:** Request ID, Timestamp, Endpoint, Response Time, Status Code, and Calculated Cost.
  * **Aggregations:** Breakdown tables grouped by day and hour.
  * **Export Actions:** Buttons to download logs as `.csv` or `.json`.

### `/pricing/` — Tier-Based Pricing Matrix
* **What it does:** Transparently shows the customer how volume discounts apply to their scoring requests.
* **What is on the page:**
  * **Pricing Tiers Table:** Clear breakdown of volume brackets.
  * **Current Position Indicator:** Highlights the tier the customer is currently in based on month-to-date usage.

### `/invoices/` — Monthly Invoices & Billing
* **What it does:** Lists generated monthly summaries of charges.
* **What is on the page:**
  * **Invoices Table:** Invoice Number, Billing Period (Month/Year), Total Requests, Total Amount Due, and Status (Generated / Reviewed).
  * **Actions:** "Download PDF" button for each invoice.
  * **Historical Statement:** Breakdown of previous months' final costs.
