import requests
from decouple import config
from huggingface_hub import InferenceClient
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Chat Service",
    version="1.0.0",
    description="Handles AI chat responses using customer data"
)

@app.get("/")
def home():
    return {"message": "Chat service running"}

HF_API_KEY = config("HF_API_KEY")
FASTAPI_BASE_URL = config("FASTAPI_BASE_URL")

client = InferenceClient(api_key=HF_API_KEY)
TIMEOUT = 5


def get_customer_info(customer_id: str):
    url = f"{FASTAPI_BASE_URL}/customers/{customer_id}"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data
            print(f"[WARN] Empty customer info for {customer_id}")
            return {}
        if resp.status_code == 404:
            print(f"[WARN] Customer {customer_id} not found (404)")
            return {}
        print(f"[WARN] Non-200 response for customer {customer_id}: {resp.status_code}")
        return {}
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Customer info fetch failed for {customer_id}: {e}")
        return {}


def get_energy_usage(customer_id: str):
    url = f"{FASTAPI_BASE_URL}/energy-usage/{customer_id}"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                return data
            print(f"[WARN] Empty energy usage for {customer_id}")
            return []
        print(f"[WARN] Non-200 response for energy usage {customer_id}: {resp.status_code}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Energy usage fetch failed for {customer_id}: {e}")
        return []


def get_support_tickets(customer_id: str):
    url = f"{FASTAPI_BASE_URL}/support-tickets/{customer_id}"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                return data
            print(f"[WARN] Empty support tickets for {customer_id}")
            return []
        print(f"[WARN] Non-200 response for support tickets {customer_id}: {resp.status_code}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Support ticket fetch failed for {customer_id}: {e}")
        return []


def generate_chatbot_response(user_input: str, customer_id: str) -> str:
    customer = get_customer_info(customer_id)
    energy = get_energy_usage(customer_id)
    tickets = get_support_tickets(customer_id)

    latest_energy = energy[-1] if energy else None
    latest_ticket = tickets[-1] if tickets else {}

    customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
    if not customer_name:
        customer_name = "Unknown Customer"

    usage_kwh = latest_energy.get("usage_kwh") if latest_energy else "N/A"
    peak_kw = latest_energy.get("peak_demand_kwh", "N/A")
    total_charge = latest_energy.get("total_charge", "N/A")

    context = f"""
Customer Information
--------------------
Name: {customer_name}
Email: {customer.get('email', 'N/A')}
Account Status: {customer.get('account_status', 'N/A')}

Latest Energy Usage
--------------------
Usage (kWh): {usage_kwh}
Peak Demand (kW): {peak_kw}
Charge: {total_charge}

Latest Support Ticket
----------------------
Ticket ID: {latest_ticket.get('ticket_id', 'N/A')}
Status: {latest_ticket.get('ticket_status', 'N/A')}
Issue: {latest_ticket.get('issue_type', 'N/A')}

Customer Question
-----------------
{user_input}
"""

    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-R1",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an energy company support assistant. "
                    "Always respond in one short sentence. "
                    "Format every answer like: 'Your charge is £X based on Y kWh used.' "
                    "Use only the provided context. If information is missing, say so explicitly."
                ),
            },
            {
                "role": "user",
                "content": context,
            },
        ],
        max_tokens=500,
        temperature=0.7,
    )

    return response.choices[0].message.content


class ChatRequest(BaseModel):
    customer_id: str
    message: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    reply = generate_chatbot_response(
        user_input=request.message,
        customer_id=request.customer_id
    )
    return ChatResponse(response=reply)
