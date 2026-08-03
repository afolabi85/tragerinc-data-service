from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import pandas as pd

# =========================
# FILE PATHS
# =========================

CUSTOMER_FILE = "tragerinc_customer_info.csv"
ENERGY_FILE = "tragerinc_energy_usage.csv"
TICKET_FILE = "tragerinc_support_tickets.csv"

# =========================
# LOAD CSV DATA
# =========================

customer_df = pd.read_csv(CUSTOMER_FILE, parse_dates=["Date_Joined"])
energy_df = pd.read_csv(ENERGY_FILE, parse_dates=["Date"])
ticket_df = pd.read_csv(TICKET_FILE, parse_dates=["Date_Opened", "Date_Closed"])

# =========================
# INITIALIZE FASTAPI APP
# =========================

app = FastAPI(
    title="TragerInc Data Service",
    version="1.0.0"
)

# =========================
# PYDANTIC MODELS
# =========================

class Customer(BaseModel):
    customer_id: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    address: str
    account_status: str
    date_joined: datetime


class CustomerCreate(BaseModel):
    customer_id: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    address: str
    account_status: str


class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    account_status: Optional[str] = None
    date_joined: Optional[datetime] = None


class EnergyUsage(BaseModel):
    customer_id: str
    date: datetime
    usage_kwh: float
    peak_demand_kwh: Optional[float] = None
    total_charge: float
    energy_type: Optional[str] = None


class CustomerTicket(BaseModel):
    ticket_id: str
    customer_id: str
    issue_type: str
    ticket_status: str
    date_opened: datetime
    date_closed: Optional[datetime] = None
    resolution_method: Optional[str] = None


class Customer360Summary(BaseModel):
    lifetime_kwh: float
    lifetime_spend: float
    total_support_tickets: int


class Customer360Response(BaseModel):
    profile: Customer
    energy_last_30_days: List[EnergyUsage]
    support_tickets: List[CustomerTicket]
    summary: Customer360Summary


# =========================
# GET CUSTOMER
# =========================

@app.get("/customers/{customer_id}", response_model=Customer)
def get_customer(customer_id: str):

    customer = customer_df[customer_df["Customer_ID"] == customer_id]

    if customer.empty:
        raise HTTPException(status_code=404, detail="Customer not found")

    row = customer.iloc[0]

    return Customer(
        customer_id=row["Customer_ID"],
        first_name=row["First_Name"],
        last_name=row["Last_Name"],
        email=row["Email"],
        phone_number=row["Phone_Number"],
        address=row["Address"],
        account_status=row["Account_Status"],
        date_joined=row["Date_Joined"]
    )


# =========================
# GET ENERGY USAGE
# =========================

@app.get("/energy-usage/{customer_id}", response_model=List[EnergyUsage])
def get_energy_usage(customer_id: str):

    customer_energy = energy_df[energy_df["Customer_ID"] == customer_id]

    if customer_energy.empty:
        raise HTTPException(status_code=404, detail=f"No energy usage found for '{customer_id}'.")

    cutoff = energy_df["Date"].max() - timedelta(days=30)
    recent_energy_data = customer_energy[customer_energy["Date"] >= cutoff].copy()

    # Ensure optional columns exist
    if "Peak_Demand_kWh" not in recent_energy_data.columns:
        recent_energy_data["Peak_Demand_kWh"] = None

    recent_energy_data["Peak_Demand_kWh"] = (
        recent_energy_data["Peak_Demand_kWh"]
        .where(recent_energy_data["Peak_Demand_kWh"].notna(), None)
    )

    if "Energy_Type" not in recent_energy_data.columns:
        recent_energy_data["Energy_Type"] = None

    recent_energy_data["Energy_Type"] = (
        recent_energy_data["Energy_Type"]
        .where(recent_energy_data["Energy_Type"].notna(), None)
    )

    return [
        EnergyUsage(
            customer_id=row["Customer_ID"],
            date=row["Date"],
            usage_kwh=row["Usage_kWh"],            # FIXED
            peak_demand_kwh=row["Peak_Demand_kWh"], # FIXED
            total_charge=row["Total_Charge"],
            energy_type=row["Energy_Type"]
        )
        for _, row in recent_energy_data.iterrows()
    ]


# =========================
# GET SUPPORT TICKETS
# =========================

@app.get("/support-tickets/{customer_id}", response_model=List[CustomerTicket])
def get_support_tickets(customer_id: str):

    support_ticket = ticket_df[ticket_df["Customer_ID"] == customer_id].copy()

    if support_ticket.empty:
        raise HTTPException(status_code=404, detail="No tickets found")

    if "Resolution_Method" not in support_ticket.columns:
        support_ticket["Resolution_Method"] = None

    support_ticket["Date_Closed"] = support_ticket["Date_Closed"].where(
        support_ticket["Date_Closed"].notna(), None
    )

    support_ticket["Resolution_Method"] = support_ticket["Resolution_Method"].where(
        support_ticket["Resolution_Method"].notna(), None
    )

    return [
        CustomerTicket(
            ticket_id=row["Ticket_ID"],
            customer_id=row["Customer_ID"],
            issue_type=row["Issue_Type"],
            ticket_status=row["Ticket_Status"],
            date_opened=row["Date_Opened"],
            date_closed=row["Date_Closed"],
            resolution_method=row["Resolution_Method"]
        )
        for _, row in support_ticket.iterrows()
    ]


# =========================
# CUSTOMER 360
# =========================

@app.get("/customer-360/{customer_id}", response_model=Customer360Response)
def customer_360(customer_id: str):

    cust = customer_df[customer_df["Customer_ID"] == customer_id]

    if cust.empty:
        raise HTTPException(status_code=404, detail="Customer not found")

    row = cust.iloc[0]

    energy_all = energy_df[energy_df["Customer_ID"] == customer_id]
    tickets_all = ticket_df[ticket_df["Customer_ID"] == customer_id]

    cutoff = datetime.now() - timedelta(days=30)
    energy_30 = energy_all[energy_all["Date"] >= cutoff].copy()

    if "Peak_Demand_kWh" not in energy_all.columns:
        energy_all["Peak_Demand_kWh"] = None
        energy_30["Peak_Demand_kWh"] = None

    if "Energy_Type" not in energy_all.columns:
        energy_all["Energy_Type"] = None
        energy_30["Energy_Type"] = None

    if "Resolution_Method" not in tickets_all.columns:
        tickets_all["Resolution_Method"] = None

    summary = Customer360Summary(
        lifetime_kwh=float(energy_all["Usage_kWh"].sum()),   # FIXED
        lifetime_spend=float(energy_all["Total_Charge"].sum()),
        total_support_tickets=len(tickets_all)
    )

    return Customer360Response(
        profile=Customer(
            customer_id=row["Customer_ID"],
            first_name=row["First_Name"],
            last_name=row["Last_Name"],
            email=row["Email"],
            phone_number=row["Phone_Number"],
            address=row["Address"],
            account_status=row["Account_Status"],
            date_joined=row["Date_Joined"]
        ),
        energy_last_30_days=[
            EnergyUsage(
                customer_id=r["Customer_ID"],
                date=r["Date"],
                usage_kwh=r["Usage_kWh"],             # FIXED
                peak_demand_kwh=r["Peak_Demand_kWh"], # FIXED
                total_charge=r["Total_Charge"],
                energy_type=r["Energy_Type"]
            )
            for _, r in energy_30.iterrows()
        ],
        support_tickets=[
            CustomerTicket(
                ticket_id=r["Ticket_ID"],
                customer_id=r["Customer_ID"],
                issue_type=r["Issue_Type"],
                ticket_status=r["Ticket_Status"],
                date_opened=r["Date_Opened"],
                date_closed=r["Date_Closed"],
                resolution_method=r["Resolution_Method"]
            )
            for _, r in tickets_all.iterrows()
        ],
        summary=summary
    )


# =========================
# CREATE CUSTOMER
# =========================

@app.post("/customers")
def create_customer(customer: CustomerCreate):

    global customer_df

    if (customer_df["Customer_ID"] == customer.customer_id).any():
        raise HTTPException(status_code=400, detail="Customer already exists")

    new_row = pd.DataFrame([{
        "Customer_ID": customer.customer_id,
        "First_Name": customer.first_name,
        "Last_Name": customer.last_name,
        "Email": customer.email,
        "Phone_Number": customer.phone_number,
        "Address": customer.address,
        "Account_Status": customer.account_status,
        "Date_Joined": datetime.now()
    }])

    customer_df = pd.concat([customer_df, new_row], ignore_index=True)
    customer_df.to_csv(CUSTOMER_FILE, index=False)

    return {"message": "created", "customer_id": customer.customer_id}


# =========================
# UPDATE CUSTOMER
# =========================

@app.put("/customers/{customer_id}")
def update_customer(customer_id: str, update: CustomerUpdate):

    global customer_df

    idx = customer_df.index[customer_df["Customer_ID"] == customer_id]

    if len(idx) == 0:
        raise HTTPException(status_code=404, detail="Customer not found")

    i = idx[0]

    mapping = {
        "first_name": "First_Name",
        "last_name": "Last_Name",
        "email": "Email",
        "phone_number": "Phone_Number",
        "address": "Address",
        "account_status": "Account_Status",
        "date_joined": "Date_Joined"
    }

    for field, value in update.dict(exclude_unset=True).items():
        col = mapping.get(field)
        if col:
            customer_df.at[i, col] = value

    customer_df.to_csv(CUSTOMER_FILE, index=False)

    return {"message": "updated"}


# =========================
# DELETE CUSTOMER
# =========================

@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: str):

    global customer_df

    before = len(customer_df)
    customer_df = customer_df[customer_df["Customer_ID"] != customer_id]

    if len(customer_df) == before:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer_df.to_csv(CUSTOMER_FILE, index=False)

    return {"message": "deleted"}
