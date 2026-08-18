import csv
import requests
from decimal import Decimal
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from django.shortcuts import render
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponse, JsonResponse
from .models import Invoice, Profile, Company, Pocket
from .translations import TRANSLATIONS


# Safe conversion helper for URL parameters
def safe_int(value, default):
    """Safely converts string parameters to integers without raising ValueError."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_translated_context(request):
    lang = request.COOKIES.get('lang', 'ru')
    if lang not in TRANSLATIONS:
        lang = 'ru'
    return TRANSLATIONS[lang]


def get_api_url(request):
    """
    Safely extracts dynamic API URL and credentials from the user's Profile -> Company.
    Returns (None, None, None) if user, profile, or company configuration is missing.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None, None, None

    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None)

    if not company or not company.api_url:
        return None, None, None

    return company.api_url, company.api_username, company.api_password


# Dynamic Pocket Pricing Calculation using Decimal for exact financial precision
def calculate_pocket_details(company, request_count):
    """Calculates pocket limit, over-limit counts, progress percentage, and total cost using Decimal."""
    pocket = getattr(company, 'pocket', None) if company else None
    if not pocket:
        return {
            "pocket_name": "N/A",
            "requests_count": 0,
            "price": Decimal("0.00"),
            "price_per_request_over_limit": Decimal("0.00"),
            "over_limit_count": 0,
            "total_amount": Decimal("0.00"),
            "progress_pct": 0,
            "remaining": 0,
        }

    over_limit_count = max(0, request_count - pocket.requests_count)

    # Convert prices to Decimal to prevent floating point inaccuracy
    price = Decimal(str(pocket.price))
    price_per_request_over_limit = Decimal(str(pocket.price_per_request_over_limit))

    over_limit_cost = Decimal(over_limit_count) * price_per_request_over_limit
    total_amount = price + over_limit_cost
    remaining = max(0, pocket.requests_count - request_count)
    progress_pct = min(int((request_count / pocket.requests_count) * 100), 100) if pocket.requests_count > 0 else 100

    return {
        "pocket_name": pocket.name,
        "requests_count": pocket.requests_count,
        "price": price,
        "price_per_request_over_limit": price_per_request_over_limit,
        "over_limit_count": over_limit_count,
        "total_amount": total_amount,
        "progress_pct": progress_pct,
        "remaining": remaining,
    }


def fetch_api_predictions(request, start_date=None, end_date=None, page=1, items_per_page=100):
    """Helper function to request a single page of predictions from the company's upstream API."""
    today_formatted = datetime.now().strftime("%d.%m.%Y")
    params = {
        "start_date": start_date or today_formatted,
        "end_date": end_date or today_formatted,
        "page": page,
        "items_per_page": items_per_page,
    }

    dynamic_api_url, api_username, api_password = get_api_url(request)
    if not dynamic_api_url:
        return {
            "code": 400,
            "data": [],
            "meta": {"itemsPerPage": items_per_page, "totalItems": 0, "currentPage": 1, "lastPage": 1},
        }

    try:
        response = requests.get(dynamic_api_url, auth=(api_username, api_password), params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        print(f"API Error ({dynamic_api_url}): {e}")

    return {
        "code": 500,
        "data": [],
        "meta": {"itemsPerPage": items_per_page, "totalItems": 0, "currentPage": 1, "lastPage": 1},
    }


def fetch_all_api_predictions(request, start_date=None, end_date=None, items_per_page=200):
    """Helper function to automatically iterate through all pages and aggregate full datasets."""
    page = 1
    all_data = []
    last_meta = {"itemsPerPage": items_per_page, "totalItems": 0, "currentPage": 1, "lastPage": 1}

    while True:
        api_response = fetch_api_predictions(
            request, start_date=start_date, end_date=end_date, page=page, items_per_page=items_per_page
        )
        data = api_response.get("data", [])
        last_meta = api_response.get("meta", last_meta)

        if not data:
            break

        all_data.extend(data)

        last_page = last_meta.get("lastPage", page)
        if page >= last_page:
            break

        page += 1

    return {"data": all_data, "meta": last_meta}


def build_daily_series(request, start_date_obj, end_date_obj, num_days):
    """Fetches raw prediction data for a date range and buckets it by calendar day."""
    start_str = start_date_obj.strftime("%d.%m.%Y")
    end_str = end_date_obj.strftime("%d.%m.%Y")

    daily_counts = defaultdict(int)
    daily_approved = defaultdict(int)

    all_predictions = fetch_all_api_predictions(request, start_date=start_str, end_date=end_str)
    data = all_predictions.get("data", [])

    for item in data:
        date_raw = item.get("prediction_date", "")
        if not date_raw:
            continue
        try:
            dt = datetime.strptime(date_raw, "%d.%m.%Y %H:%M:%S")
        except ValueError:
            continue
        key = dt.strftime("%Y-%m-%d")
        daily_counts[key] += 1
        if item.get("prediction") == "Approved":
            daily_approved[key] += 1

    labels, counts, approval_rates = [], [], []
    for i in range(num_days):
        day = start_date_obj + timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        labels.append(day.strftime("%d.%m"))  # e.g., 15.08
        day_count = daily_counts.get(key, 0)
        counts.append(day_count)
        day_approved = daily_approved.get(key, 0)
        approval_rates.append(round((day_approved / day_count * 100), 1) if day_count else 0.0)

    return {"labels": labels, "counts": counts, "approval_rates": approval_rates}


# Views
@login_not_required
class CustomLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()

        # Check if user has profile
        if not hasattr(user, "profile"):
            form.add_error(
                None,
                "This account does not have an associated profile. Please contact support.",
            )
            return self.form_invalid(form)

        return super().form_valid(form)


def dashboard_view(request):
    """
    `/` — Usage Dashboard
    Computes real-time consumption metrics and hourly chart breakdowns.
    """
    now = datetime.now()
    today_str = now.strftime("%d.%m.%Y")
    yesterday_str = (now - timedelta(days=1)).strftime("%d.%m.%Y")
    week_start_str = (now - timedelta(days=7)).strftime("%d.%m.%Y")
    month_start_str = now.replace(day=1).strftime("%d.%m.%Y")

    user_company = getattr(getattr(request.user, "profile", None), "company", None)

    # Fetch live API totals
    yesterday_data = fetch_api_predictions(request, yesterday_str, yesterday_str, page=1, items_per_page=1)
    week_data = fetch_api_predictions(request, week_start_str, today_str, page=1, items_per_page=1)
    month_data = fetch_api_predictions(request, month_start_str, today_str, page=1, items_per_page=1)

    today_all = fetch_all_api_predictions(request, today_str, today_str)
    data_list = today_all.get("data", [])
    today_count = today_all.get("meta", {}).get("totalItems", len(data_list))

    yesterday_count = yesterday_data.get("meta", {}).get("totalItems", 0)
    week_count = week_data.get("meta", {}).get("totalItems", 0)
    month_count = month_data.get("meta", {}).get("totalItems", 0)

    # Compute Pocket details with exact Decimal precision
    pocket_info = calculate_pocket_details(user_company, month_count)

    approved_count = sum(1 for item in data_list if item.get("prediction") == "Approved")
    approval_rate = round((approved_count / len(data_list) * 100), 1) if data_list else 0.0

    hours = [0] * 24
    branch_counter = Counter()

    for item in data_list:
        branch_counter[item.get("branch", "unknown")] += 1
        date_raw = item.get("prediction_date", "")
        if date_raw:
            try:
                dt = datetime.strptime(date_raw, "%d.%m.%Y %H:%M:%S")
                hours[dt.hour] += 1
            except ValueError:
                pass

    thirty_days_start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    series_30d = build_daily_series(request, thirty_days_start, now, 30)

    context = {
        "today_requests": today_count,
        "yesterday_requests": yesterday_count,
        "week_requests": week_count,
        "month_requests": month_count,
        "month_cost": f"{pocket_info['total_amount']:,.2f}",

        # Pocket details
        "pocket_info": pocket_info,

        # Performance Analytics
        "approval_rate": approval_rate,
        "branch_breakdown": dict(branch_counter),
        "hourly_chart_data": hours,

        "usage_30d_labels": series_30d["labels"],
        "usage_30d_data": series_30d["counts"],
        "approval_7d_labels": series_30d["labels"][-7:],
        "approval_7d_data": series_30d["approval_rates"][-7:],

        "t": get_translated_context(request)
    }
    return render(request, "main.html", context)


def history_view(request):
    """
    `/history/` — Audit logs loaded with UI pagination support.
    """
    # Safe Integer extraction for GET parameters
    page = safe_int(request.GET.get("page"), 1)
    items_per_page = safe_int(request.GET.get("items_per_page"), 10)

    start_date = request.GET.get("start_date", datetime.now().strftime("%d.%m.%Y"))
    end_date = request.GET.get("end_date", datetime.now().strftime("%d.%m.%Y"))

    api_response = fetch_api_predictions(
        request,
        start_date=start_date,
        end_date=end_date,
        page=page,
        items_per_page=items_per_page
    )

    raw_logs = api_response.get("data", [])
    meta = api_response.get("meta", {})
    total_items = meta.get("totalItems", 0)

    logs = []
    for item in raw_logs:
        logs.append({
            "prediction_date": item.get("prediction_date"),
            "pinfl": item.get("pinfl"),
            "prediction": item.get("prediction"),
            "good_prob": item.get("good_prob"),
            "bad_prob": item.get("bad_prob"),
            "branch": item.get("branch")
        })

    context = {
        "logs": logs,
        "meta": meta,
        "start_date": start_date,
        "end_date": end_date,
        "total_items": total_items,
        "t": get_translated_context(request)
    }
    return render(request, "history.html", context)


def pricing_view(request):
    """
    `/pricing/` — Displays available Pockets from DB and user's current company pocket.
    """
    user_company = getattr(getattr(request.user, "profile", None), "company", None)
    pockets = Pocket.objects.all().order_by("price")

    today_str = datetime.now().strftime("%d.%m.%Y")
    month_start_str = datetime.now().replace(day=1).strftime("%d.%m.%Y")

    month_data = fetch_api_predictions(request, month_start_str, today_str, page=1, items_per_page=1)
    month_count = month_data.get("meta", {}).get("totalItems", 0)

    pocket_info = calculate_pocket_details(user_company, month_count)

    context = {
        "pockets": pockets,
        "current_pocket": user_company.pocket if user_company else None,
        "pocket_info": pocket_info,
        "month_count": month_count,
        "t": get_translated_context(request)
    }
    return render(request, "pricing.html", context)


def invoices_view(request):
    """
    `/invoices/` — Displays database invoices for user's company and calculates unbilled MTD balance.
    """
    user_company = getattr(getattr(request.user, "profile", None), "company", None)

    if user_company:
        invoices = Invoice.objects.filter(company=user_company).order_by("-invoice_month")
    else:
        invoices = Invoice.objects.all().order_by("-invoice_month")

    today_str = datetime.now().strftime("%d.%m.%Y")
    month_start_str = datetime.now().replace(day=1).strftime("%d.%m.%Y")

    month_data = fetch_api_predictions(request, month_start_str, today_str, page=1, items_per_page=1)
    month_count = month_data.get("meta", {}).get("totalItems", 0)

    pocket_info = calculate_pocket_details(user_company, month_count)

    context = {
        "invoices": invoices,
        "current_balance": f"${pocket_info['total_amount']:,.2f}",
        "t": get_translated_context(request)
    }
    return render(request, "invoices.html", context)


def export_logs_csv(request):
    """Export all predictions to CSV across all pages."""
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    api_response = fetch_all_api_predictions(request, start_date=start_date, end_date=end_date)
    data = api_response.get("data", [])

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="predictions_history.csv"'

    writer = csv.writer(response)
    writer.writerow(["Hash UID", "Date", "PINFL", "Branch", "Prediction", "Good Prob (%)", "Bad Prob (%)"])
    for row in data:
        writer.writerow([
            row.get("hash_uid"), row.get("prediction_date"), row.get("pinfl"),
            row.get("branch"), row.get("prediction"), row.get("good_prob"), row.get("bad_prob")
        ])
    return response


def export_logs_json(request):
    """Export all predictions to JSON across all pages."""
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    api_response = fetch_all_api_predictions(request, start_date=start_date, end_date=end_date)
    return JsonResponse(api_response)


def generate_invoice(request):
    """
    `/invoices/generate/` — Computes monthly consumption based on active Pocket and saves Invoice.
    """
    now = datetime.now()
    user_company = getattr(getattr(request.user, "profile", None), "company", None)

    # Safe Integer extraction with boundary fallbacks
    month = safe_int(request.GET.get("month"), now.month)
    year = safe_int(request.GET.get("year"), now.year)

    if not (1 <= month <= 12):
        month = now.month
    if year < 2000 or year > 2100:
        year = now.year

    start_date_obj = datetime(year, month, 1)
    next_month_first_day = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    end_date_obj = next_month_first_day - timedelta(days=1)

    api_data = fetch_api_predictions(
        request,
        start_date=start_date_obj.strftime("%d.%m.%Y"),
        end_date=end_date_obj.strftime("%d.%m.%Y"),
        page=1,
        items_per_page=1
    )
    total_requests = api_data.get("meta", {}).get("totalItems", 0)

    pocket_info = calculate_pocket_details(user_company, total_requests)
    total_amount = pocket_info["total_amount"]

    invoice_number = f"INV-{str(user_company).upper()}-{month:02d}-{year}"
    period_str = start_date_obj.strftime("%m-%Y")            # e.g. 08-2026
    issue_date_str = now.strftime("%d.%m.%Y")                 # e.g. 15.08.2026

    invoice_obj = None

    if user_company:
        invoice_obj, _ = Invoice.objects.update_or_create(
            company=user_company,
            invoice_month=start_date_obj.date(),
            defaults={
                "name": invoice_number,
                "total_requests": total_requests,
                "total_amount": total_amount,
                "status": Invoice.StatusChoices.GENERATED,
                "description": f"API Billing for {period_str} ({total_requests:,} calls under Pocket: {pocket_info['pocket_name']})",
            }
        )

    if request.GET.get("format") == "json":
        return JsonResponse({
            "invoice_number": invoice_number,
            "company": user_company.name if user_company else "N/A",
            "period": period_str,
            "total_requests": total_requests,
            "pocket": pocket_info["pocket_name"],
            "total_amount": float(total_amount),
            "status": "Generated",
            "issue_date": issue_date_str,
        })

    context = {
        "invoice_number": invoice_number,
        "company": user_company,
        "period": period_str,
        "issue_date": issue_date_str,
        "total_requests": total_requests,
        "pocket_info": pocket_info,
        "total_amount": f"{total_amount:,.2f}",
        "invoice_obj": invoice_obj,
        "t": get_translated_context(request)
    }
    return render(request, "invoice_detail.html", context)
