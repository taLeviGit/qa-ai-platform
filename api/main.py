import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Response, status

from api import auth
from api.database import get_connection, init_db
from api.pricing import calculate_price
from api.schemas import (
    Customer,
    CustomerCreate,
    CustomerUpdate,
    LoginRequest,
    Policy,
    PolicyCreate,
    Quote,
    QuoteCreate,
    TokenResponse,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Insurance Quotes API", version="1.0.0", lifespan=lifespan)

# ============== Helpers ===================

def get_customer_or_404(conn: sqlite3.Connection, customer_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return row

def get_quote_or_404(conn: sqlite3.Connection, quote_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quote not found")
    return row

def get_policy_or_404(conn: sqlite3.Connection, policy_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM policies WHERE id = ?", (policy_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")
    return row


# ============== 1.Health ===================

@app.get("/health")
def health():
    return {"status": "ok"}

# ============== 2.Authorization ===================

@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    token = auth.login(body.username, body.password)
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return TokenResponse(access_token=token)

# ============== 3-7.Customers ===================

@app.post("/customers", response_model=Customer, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerCreate, user: dict = Depends(auth.get_current_user)):
    with get_connection() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO customers (name, email, age) VALUES (?, ?, ?)",
                (body.name, body.email, body.age),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
        return Customer(id=cur.lastrowid, **body.model_dump())

@app.get("/customers", response_model=list[Customer])
def list_customers(user: dict = Depends(auth.get_current_user)):
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM customers ORDER BY id").fetchall()
        return [Customer(**dict(row)) for row in rows]


@app.get("/customers/{customer_id}", response_model=Customer)
def get_customer(customer_id: int, user: dict = Depends(auth.get_current_user)):
    with get_connection() as conn:
        return Customer(**dict(get_customer_or_404(conn, customer_id)))


@app.patch("/customers/{customer_id}", response_model=Customer)
def update_customer(
    customer_id: int, body: CustomerUpdate, user: dict = Depends(auth.get_current_user)
):
    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    with get_connection() as conn:
        get_customer_or_404(conn, customer_id)
        if updates:
            set_clause = ", ".join(f"{field} = ?" for field in updates)
            try:
                conn.execute(
                    f"UPDATE customers SET {set_clause} WHERE id = ?",
                    (*updates.values(), customer_id),
                )
            except sqlite3.IntegrityError:
                raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")
        return Customer(**dict(get_customer_or_404(conn, customer_id)))


@app.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, user: dict = Depends(auth.require_admin)):
    with get_connection() as conn:
        get_customer_or_404(conn, customer_id)
        conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ============== 8-10. Quotes ===================

@app.post("/quotes", response_model=Quote, status_code=status.HTTP_201_CREATED)
def create_quote(body: QuoteCreate, user: dict = Depends(auth.get_current_user)):
    with get_connection() as conn:
        customer = get_customer_or_404(conn, body.customer_id)
        price = calculate_price(customer["age"], body.car_value)
        created_at = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO quotes (customer_id, car_value, price, created_at) VALUES (?, ?, ?, ?)",
            (body.customer_id, body.car_value, price, created_at),
        )
        return Quote(
            id=cur.lastrowid,
            customer_id=body.customer_id,
            car_value=body.car_value,
            price=price,
            created_at=created_at,
        )


@app.get("/quotes/{quote_id}", response_model=Quote)
def get_quote(quote_id: int, user: dict = Depends(auth.get_current_user)):
    with get_connection() as conn:
        return Quote(**dict(get_quote_or_404(conn, quote_id)))


@app.get("/customers/{customer_id}/quotes", response_model=list[Quote])
def list_customer_quotes(customer_id: int, user: dict = Depends(auth.get_current_user)):
    with get_connection() as conn:
        get_customer_or_404(conn, customer_id)
        rows = conn.execute(
            "SELECT * FROM quotes WHERE customer_id = ? ORDER BY id", (customer_id,)
        ).fetchall()
        return [Quote(**dict(row)) for row in rows]


# ============== 11-13. Policies ===================

@app.post("/policies", response_model=Policy, status_code=status.HTTP_201_CREATED)
def create_policy(body: PolicyCreate, user: dict = Depends(auth.get_current_user)):
    with get_connection() as conn:
        get_quote_or_404(conn, body.quote_id)
        try:
            cur = conn.execute("INSERT INTO policies (quote_id) VALUES (?)", (body.quote_id,))
        except sqlite3.IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, "A policy already exists for this quote")
        return Policy(id=cur.lastrowid, quote_id=body.quote_id, status="active")


@app.get("/policies/{policy_id}", response_model=Policy)
def get_policy(policy_id: int, user: dict = Depends(auth.get_current_user)):
    with get_connection() as conn:
        return Policy(**dict(get_policy_or_404(conn, policy_id)))


@app.post("/policies/{policy_id}/cancel", response_model=Policy)
def cancel_policy(policy_id: int, user: dict = Depends(auth.require_admin)):
    with get_connection() as conn:
        policy = get_policy_or_404(conn, policy_id)
        if policy["status"] == "cancelled":
            raise HTTPException(status.HTTP_409_CONFLICT, "Policy is already cancelled")
        conn.execute("UPDATE policies SET status = 'cancelled' WHERE id = ?", (policy_id,))
        return Policy(id=policy_id, quote_id=policy["quote_id"], status="cancelled")