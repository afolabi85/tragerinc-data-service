#STEP1 IMPORT LIBRARIES

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
from datetime import datetime, timedelta
import uvicorn


#STEP2 FILE PATH CONSTANTS

CUSTOMER_FILE = r"C:\Users\User\Desktop\AMDARI\MLops\tragerinc_customer_info.csv"

ENERGY_FILE = r"C:\Users\User\Desktop\AMDARI\MLops\tragerinc_energy_usage.csv"

TICKET_FILE = r"C:\Users\User\Desktop\AMDARI\MLops\tragerinc_support_tickets.csv"


#STEP3 LOAD CSV FILES

customer_info_df = pd.read_csv(
    CUSTOMER_FILE,
    parse_dates=["Date_Joined"]
)

energy_usage_df = pd.read_csv(
    ENERGY_FILE,
    parse_dates=["Date"]
)

customer_tickets_df = pd.read_csv(
    TICKET_FILE,
    parse_dates=["Date_Opened", "Date_Closed"]
)


#STEP4 INITIALISE FASTAPI

app = FastAPI(
    title="Trager Inc FastAPI",
    version="1.0.0",
    description="customer info, energy usage, and customer tickets API"
)


#STEP5 ROOT ENDPOINT

@app.get(
    "/",
    tags=["Health Check"]
)
def home():

    return {
        "message": "Trager Inc API is running successfully"
    }


#STEP6 BUILDING PYDANTIC MODELS

class Customer(BaseModel):

    customer_id: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    address: str
    date_joined: datetime
    
    account_status: str


class EnergyUsage(BaseModel):

    customer_id: str
    date: datetime
    usage_kwh: float
    peak_demand_kwh: Optional[float] = None
    total_charge: float
    energy_type: str


class CustomerTicket(BaseModel):

    ticket_id: str
    customer_id: str
    issue_type: str
    ticket_status: str
    date_opened: datetime
    date_closed: Optional[datetime] = None
    resolution_method: Optional[str] = None


#STEP7 BUILDING API GET ENDPOINTS

@app.get(
    "/customers/{customer_id}",
    response_model=Customer,
    tags=["Customers"]
)
def get_customer_info(customer_id: str):

    customer_row = customer_info_df[
        customer_info_df["Customer_ID"] == customer_id
    ]

    if customer_row.empty:
        raise HTTPException(
            status_code=404,
            detail="customer not found"
        )

    customer = customer_row.iloc[0]

    return {
        "customer_id": customer["Customer_ID"],
        "first_name": customer["First_Name"],
        "last_name": customer["Last_Name"],
        "email": customer["Email"],
        "phone_number": customer["Phone_Number"],
        "address": customer["Address"],
        "date_joined": customer["Date_Joined"],
        "account_status": customer["Account_Status"]
    }


@app.get(
    "/energy-usage/{customer_id}",
    response_model=List[EnergyUsage],
    tags=["Energy Usage"]
)
def get_energy_usage(customer_id: str):

    customer_energy = energy_usage_df[
        energy_usage_df["Customer_ID"] == customer_id
    ].copy()

    if customer_energy.empty:
        raise HTTPException(
            status_code=404,
            detail="customer not found"
        )

    last_30_days = datetime.now() - timedelta(days=30)

    recent_customer_energy = customer_energy[
        customer_energy["Date"] >= last_30_days
    ].copy()

    recent_customer_energy.loc[:, "Peak_Demand_kWh"] = (
        recent_customer_energy["Peak_Demand_kWh"]
        .where(
            pd.notna(recent_customer_energy["Peak_Demand_kWh"]),
            None
        )
    )

    return [
        EnergyUsage(
            customer_id=row["Customer_ID"],
            date=row["Date"],
            usage_kwh=row["Usage_KWh"],
            peak_demand_kwh=row["Peak_Demand_KWh"],
            total_charge=row["Total_Charge"],
            energy_type=row["Energy_Type"]
        )
        for _, row in recent_customer_energy.iterrows()
    ]


@app.get(
    "/support-tickets/{customer_id}",
    response_model=List[CustomerTicket],
    tags=["Support Tickets"]
)
def get_support_tickets(customer_id: str):

    customer_ticket = customer_tickets_df[
        customer_tickets_df["Customer_ID"] == customer_id
    ].copy()

    if customer_ticket.empty:
        raise HTTPException(
            status_code=404,
            detail="customer not found"
        )

    customer_ticket.loc[:, "Date_Closed"] = (
        customer_ticket["Date_Closed"]
        .where(
            pd.notna(customer_ticket["Date_Closed"]),
            None
        )
    )

    customer_ticket.loc[:, "Resolution_Method"] = (
        customer_ticket["Resolution_Method"]
        .where(
            pd.notna(customer_ticket["Resolution_Method"]),
            None
        )
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
        for _, row in customer_ticket.iterrows()
    ]


#STEP8 CUSTOMER360 ENDPOINT

@app.get(
    "/customer360/{customer_id}",
    tags=["Customer360"]
)
def get_customer360(customer_id: str):

    customer_row = customer_info_df[
        customer_info_df["Customer_ID"] == customer_id
    ]

    if customer_row.empty:
        raise HTTPException(
            status_code=404,
            detail="customer not found"
        )

    customer = customer_row.iloc[0]

    #ENERGY USAGE

    customer_energy = energy_usage_df[
        energy_usage_df["Customer_ID"] == customer_id
    ].copy()

    last_30_days = datetime.now() - timedelta(days=30)

    recent_energy = customer_energy[
        customer_energy["Date"] >= last_30_days
    ].copy()

    recent_energy.loc[:, "Peak_Demand_KWh"] = (
        recent_energy["Peak_Demand_KWh"]
        .where(
            pd.notna(recent_energy["Peak_Demand_KWh"]),
            None
        )
    )

    energy_list = [
        {
            "customer_id": row["Customer_ID"],
            "date": row["Date"],
            "usage_kwh": row["Usage_KWh"],
            "peak_demand_kwh": row["Peak_Demand_KWh"],
            "total_charge": row["Total_Charge"],
            "energy_type": row["Energy_Type"]
        }
        for _, row in recent_energy.iterrows()
    ]

    #SUPPORT TICKETS

    tickets = customer_tickets_df[
        customer_tickets_df["Customer_ID"] == customer_id
    ].copy()

    tickets.loc[:, "Date_Closed"] = (
        tickets["Date_Closed"]
        .where(
            pd.notna(tickets["Date_Closed"]),
            None
        )
    )

    tickets.loc[:, "Resolution_Method"] = (
        tickets["Resolution_Method"]
        .where(
            pd.notna(tickets["Resolution_Method"]),
            None
        )
    )

    ticket_list = [
        {
            "ticket_id": row["Ticket_ID"],
            "customer_id": row["Customer_ID"],
            "issue_type": row["Issue_Type"],
            "ticket_status": row["Ticket_Status"],
            "date_opened": row["Date_Opened"],
            "date_closed": row["Date_Closed"],
            "resolution_method": row["Resolution_Method"]
        }
        for _, row in tickets.iterrows()
    ]

    #METRICS

    metrics = {
        "total_kwh_30_days": float(
            recent_energy["Usage_KWh"].sum()
        ),

        "avg_daily_kwh": (
            float(recent_energy["Usage_KWh"].mean())
            if not recent_energy.empty else 0
        ),

        "open_ticket_count": int(
            (tickets["Ticket_Status"] == "Open").sum()
        ),

        "lifetime_ticket_count": int(
            len(tickets)
        )
    }

    return {

        "customer": {
            "customer_id": customer["Customer_ID"],
            "first_name": customer["First_Name"],
            "last_name": customer["Last_Name"],
            "email": customer["Email"],
            "phone_number": customer["Phone_Number"],
            "address": customer["Address"],
            "date_joined": customer["Date_Joined"],
            "account_status": customer["Account_Status"]
        },

        "energy_usage_last_30_days": energy_list,

        "support_tickets": ticket_list,

        "metrics": metrics
    }


#STEP9 API POST ENDPOINTS

@app.post(
    "/customers",
    response_model=Customer,
    status_code=201,
    tags=["Customers"]
)
def create_customer(new_customer: Customer):

    global customer_info_df

    #CHECK CUSTOMER ID

    existing_customer = customer_info_df[
        customer_info_df["Customer_ID"] == new_customer.customer_id
    ]

    if not existing_customer.empty:
        raise HTTPException(
            status_code=400,
            detail="customer already exists"
        )

    #CHECK EMAIL

    existing_email = customer_info_df[
        customer_info_df["Email"] == new_customer.email
    ]

    if not existing_email.empty:
        raise HTTPException(
            status_code=400,
            detail="email already exists"
        )

    #CREATE NEW ROW

    new_row = {
        "Customer_ID": new_customer.customer_id,
        "First_Name": new_customer.first_name,
        "Last_Name": new_customer.last_name,
        "Email": new_customer.email,
        "Phone_Number": new_customer.phone_number,
        "Address": new_customer.address,
        "Date_Joined": new_customer.date_joined,
        "Account_Status": new_customer.account_status
    }

    #APPEND DATAFRAME

    customer_info_df = pd.concat(
        [customer_info_df, pd.DataFrame([new_row])],
        ignore_index=True
    )

    #SAVE CSV

    customer_info_df.to_csv(
        CUSTOMER_FILE,
        index=False
    )

    return new_customer


@app.post(
    "/energy-usage",
    response_model=EnergyUsage,
    status_code=201,
    tags=["Energy Usage"]
)
def create_energy_usage(new_energy_usage: EnergyUsage):

    global energy_usage_df

    #CHECK CUSTOMER EXISTS

    customer_exists = customer_info_df[
        customer_info_df["Customer_ID"] == new_energy_usage.customer_id
    ]

    if customer_exists.empty:
        raise HTTPException(
            status_code=404,
            detail="customer not found"
        )

    #CREATE NEW ROW

    new_row = {
        "Customer_ID": new_energy_usage.customer_id,
        "Date": new_energy_usage.date,
        "Usage_KWh": new_energy_usage.usage_kwh,
        "Peak_Demand_KWh": new_energy_usage.peak_demand_kwh,
        "Total_Charge": new_energy_usage.total_charge,
        "Energy_Type": new_energy_usage.energy_type
    }

    #APPEND DATAFRAME

    energy_usage_df = pd.concat(
        [energy_usage_df, pd.DataFrame([new_row])],
        ignore_index=True
    )

    #SAVE CSV

    energy_usage_df.to_csv(
        ENERGY_FILE,
        index=False
    )

    return new_energy_usage


@app.post(
    "/support-tickets",
    response_model=CustomerTicket,
    status_code=201,
    tags=["Support Tickets"]
)
def create_support_ticket(new_ticket: CustomerTicket):

    global customer_tickets_df

    #CHECK CUSTOMER EXISTS

    customer_exists = customer_info_df[
        customer_info_df["Customer_ID"] == new_ticket.customer_id
    ]

    if customer_exists.empty:
        raise HTTPException(
            status_code=404,
            detail="customer not found"
        )

    #CHECK TICKET EXISTS

    existing_ticket = customer_tickets_df[
        customer_tickets_df["Ticket_ID"] == new_ticket.ticket_id
    ]

    if not existing_ticket.empty:
        raise HTTPException(
            status_code=400,
            detail="ticket already exists"
        )

    #CREATE NEW ROW

    new_row = {
        "Ticket_ID": new_ticket.ticket_id,
        "Customer_ID": new_ticket.customer_id,
        "Issue_Type": new_ticket.issue_type,
        "Ticket_Status": new_ticket.ticket_status,
        "Date_Opened": new_ticket.date_opened,
        "Date_Closed": new_ticket.date_closed,
        "Resolution_Method": new_ticket.resolution_method
    }

    #APPEND DATAFRAME

    customer_tickets_df = pd.concat(
        [customer_tickets_df, pd.DataFrame([new_row])],
        ignore_index=True
    )

    #SAVE CSV

    customer_tickets_df.to_csv(
        TICKET_FILE,
        index=False
    )

    return new_ticket


#STEP10 API PUT ENDPOINT

@app.put(
    "/customers/{customer_id}",
    response_model=Customer,
    tags=["Customers"]
)
def update_customer(
    customer_id: str,
    updated_customer: Customer
):

    global customer_info_df

    #CHECK CUSTOMER EXISTS

    customer_index = customer_info_df[
        customer_info_df["Customer_ID"] == customer_id
    ].index

    if len(customer_index) == 0:
        raise HTTPException(
            status_code=404,
            detail="customer not found"
        )

    #CHECK CUSTOMER ID MATCH

    if updated_customer.customer_id != customer_id:
        raise HTTPException(
            status_code=400,
            detail="customer_id mismatch"
        )

    #UPDATE RECORD

    customer_info_df.loc[
        customer_index,
        "First_Name"
    ] = updated_customer.first_name

    customer_info_df.loc[
        customer_index,
        "Last_Name"
    ] = updated_customer.last_name

    customer_info_df.loc[
        customer_index,
        "Email"
    ] = updated_customer.email

    customer_info_df.loc[
        customer_index,
        "Phone_Number"
    ] = updated_customer.phone_number

    customer_info_df.loc[
        customer_index,
        "Address"
    ] = updated_customer.address

    customer_info_df.loc[
        customer_index,
        "Date_Joined"
    ] = updated_customer.date_joined

    customer_info_df.loc[
        customer_index,
        "Account_Status"
    ] = updated_customer.account_status

    #SAVE CSV

    customer_info_df.to_csv(
        CUSTOMER_FILE,
        index=False
    )

    updated_row = customer_info_df.loc[
        customer_index
    ].iloc[0]

    return {
        "customer_id": updated_row["Customer_ID"],
        "first_name": updated_row["First_Name"],
        "last_name": updated_row["Last_Name"],
        "email": updated_row["Email"],
        "phone_number": updated_row["Phone_Number"],
        "address": updated_row["Address"],
        "date_joined": updated_row["Date_Joined"],
        "account_status": updated_row["Account_Status"]
    }


#STEP11 API DELETE ENDPOINT

@app.delete(
    "/customers/{customer_id}",
    tags=["Customers"]
)
def delete_customer(customer_id: str):

    global customer_info_df
    global energy_usage_df
    global customer_tickets_df

    #CHECK CUSTOMER EXISTS

    customer_exists = customer_info_df[
        customer_info_df["Customer_ID"] == customer_id
    ]

    if customer_exists.empty:
        raise HTTPException(
            status_code=404,
            detail="customer not found"
        )

    #SOFT DELETE CUSTOMER

    customer_index = customer_info_df[
        customer_info_df["Customer_ID"] == customer_id
    ].index

    customer_info_df.loc[
        customer_index,
        "Account_Status"
    ] = "Deleted"

    #SAVE CSV

    customer_info_df.to_csv(
        CUSTOMER_FILE,
        index=False
    )

    return {
        "message": f"customer {customer_id} soft deleted successfully"
    }


#STEP12 RUN APPLICATION

if __name__ == "__main__":

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )