# main.py
import os
import hashlib
import secrets
import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import SQLModel, Field, create_engine, Session, select
from passlib.context import CryptContext
from jose import jwt
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# ---------------------
# Config
# ---------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./db.sqlite")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret")
JWT_ALGO = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "60"))

PAYHERE_MERCHANT_ID = os.getenv("PAYHERE_MERCHANT_ID", "")
PAYHERE_MERCHANT_SECRET = os.getenv("PAYHERE_MERCHANT_SECRET", "")
PAYHERE_MODE = os.getenv("PAYHERE_MODE", "sandbox")  # 'sandbox' or 'live'
# BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
BASE_URL = os.getenv("BASE_URL","https://736788489893.ngrok-free.app")

PAYHERE_CHECKOUT_URL = (
    "https://sandbox.payhere.lk/pay/checkout"
    if PAYHERE_MODE == "sandbox"
    else "https://www.payhere.lk/pay/checkout"
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
engine = create_engine(DATABASE_URL, echo=False)

app = FastAPI(title="Auth + API Key + PayHere (Demo)")

origins = [
    "http://localhost:4200",  # your Angular frontend
    # add more allowed origins if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or use ["*"] to allow all origins (not recommended for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------
# DB models
# ---------------------
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str

class Plan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float
    currency: str = "LKR"
    recurrence: str = "1 Month"
    duration: str = "Forever"
    monthly_quota: int = 10000  # sample quota for API requests per month

class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: str = Field(index=True, unique=True)
    customer_email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    plan_id: Optional[int] = None
    status: str = Field(default="pending")  # pending, active, cancelled
    payhere_subscription_id: Optional[str] = None
    api_key_id: Optional[int] = None
    api_key_plain: Optional[str] = None  # NOTE: plain kept temporarily to show to user (demo only)

class APIKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key_hash: str  # store hash(plain_key)
    owner_email: Optional[str] = None
    active: bool = True
    quota_remaining: int = 0
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# ---------------------
# Pydantic Schemas
# ---------------------
class RegisterIn(BaseModel):
    email: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ---------------------
# Utilities
# ---------------------
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGO)
    return encoded

def generate_api_key_plain() -> str:
    return secrets.token_urlsafe(32)

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def payhere_amount_format(amount: float) -> str:
    # PayHere expects e.g. "1000.00"
    return f"{amount:.2f}"

def payhere_hash(merchant_id: str, order_id: str, amount: float, currency: str, merchant_secret: str) -> str:
    # As PayHere docs: hash = UPPER(md5(merchant_id + order_id + amount_formatted + currency + UPPER(md5(merchant_secret))))
    hashed_secret = hashlib.md5(merchant_secret.encode("utf-8")).hexdigest().upper()
    amount_formatted = payhere_amount_format(amount)
    raw = f"{merchant_id}{order_id}{amount_formatted}{currency}{hashed_secret}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()

def verify_payhere_md5sig(merchant_id, order_id, payhere_amount, payhere_currency, status_code, md5sig, merchant_secret) -> bool:
    raw = f"{merchant_id}{order_id}{payhere_amount}{payhere_currency}{status_code}{hashlib.md5(merchant_secret.encode('utf-8')).hexdigest().upper()}"
    local = hashlib.md5(raw.encode("utf-8")).hexdigest().upper()
    return local == (md5sig or "").upper()

# ---------------------
# Auth dependencies (JWT)
# ---------------------
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ---------------------
# API Key auth dependency (for third-party consumers)
# ---------------------
from fastapi import Header

async def require_api_key(x_api_key: Optional[str] = Header(None), session: Session = Depends(get_session)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    key_hash = sha256_hex(x_api_key)
    api = session.exec(select(APIKey).where(APIKey.key_hash == key_hash, APIKey.active == True)).first()
    if not api:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    # Enforce simple quota (decrement)
    if api.quota_remaining <= 0:
        raise HTTPException(status_code=429, detail="Quota exhausted")
    api.quota_remaining -= 1
    session.add(api)
    session.commit()
    return api

# ---------------------
# Startup: create DB + seed a plan
# ---------------------
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    with Session(engine) as s:
        plan = s.exec(select(Plan).where(Plan.name == "Starter")).first()
        if not plan:
            p = Plan(name="Starter", price=1000.0, currency="LKR", recurrence="1 Month", duration="Forever", monthly_quota=10000)
            s.add(p)
            s.commit()

# ---------------------
# Register / Login
# ---------------------
@app.post("/register")
def register(payload: RegisterIn, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.email == payload.email)).first():
        raise HTTPException(400, "Email already registered")
    u = User(email=payload.email, hashed_password=hash_password(payload.password))
    session.add(u)
    session.commit()
    return {"msg": "registered"}

@app.post("/token", response_model=TokenOut)
def login_for_token(form_data: Request, session: Session = Depends(get_session)):
    # Accept JSON body or form-data (simple demo)
    body = {}
    try:
        body = form_data.json()
    except Exception:
        # fallback: use form data
        pass
    # For simplicity in this demo: accept JSON with email/password
    import json
    data = json.loads(form_data._body.decode()) if hasattr(form_data, "_body") else body
    # But to keep it simple: we will parse JSON from the raw body.
    # (In production use OAuth2PasswordRequestForm)
    raise HTTPException(400, "Use /login with JSON {'email','password'}")

@app.post("/login", response_model=TokenOut)
def login(payload: RegisterIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.email})
    return {"access_token": token}

# ---------------------
# Create subscription (redirects user to PayHere)
# ---------------------
@app.post("/subscribe", response_class=HTMLResponse)
def subscribe(first_name: str = Form(...),
              last_name: str = Form(...),
              email: str = Form(...),
              plan_id: int = Form(...),
              phone: str = Form(""),
              address: str = Form(""),
              city: str = Form(""),
              session: Session = Depends(get_session)):
    plan = session.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    order_id = secrets.token_hex(12)  # unique order id
    amount = plan.price
    currency = plan.currency
    recurrence = plan.recurrence
    duration = plan.duration

    # Save a pending subscription
    sub = Subscription(order_id=order_id, customer_email=email, first_name=first_name, last_name=last_name, plan_id=plan.id, status="pending")
    session.add(sub)
    session.commit()

    # Generate server-side hash for redirect form
    hash_val = payhere_hash(PAYHERE_MERCHANT_ID, order_id, amount, currency, PAYHERE_MERCHANT_SECRET)

    # Build auto-submit HTML form to redirect customer to PayHere
    notify_url = f"{BASE_URL}/webhooks/payhere"
    return_url = f"{BASE_URL}/subscribe/return?order_id={order_id}"
    cancel_url = f"{BASE_URL}/subscribe/cancel?order_id={order_id}"

    html = f"""
    <html><body>
      <p>Redirecting to PayHere...</p>
      <form id="payhere_form" method="post" action="{PAYHERE_CHECKOUT_URL}">
        <input type="hidden" name="merchant_id" value="{PAYHERE_MERCHANT_ID}" />
        <input type="hidden" name="return_url" value="{return_url}" />
        <input type="hidden" name="cancel_url" value="{cancel_url}" />
        <input type="hidden" name="notify_url" value="{notify_url}" />

        <input type="hidden" name="order_id" value="{order_id}" />
        <input type="hidden" name="items" value="{plan.name} subscription" />
        <input type="hidden" name="currency" value="{currency}" />
        <input type="hidden" name="amount" value="{payhere_amount_format(amount)}" />
        <input type="hidden" name="recurrence" value="{recurrence}" />
        <input type="hidden" name="duration" value="{duration}" />
        <input type="hidden" name="first_name" value="{first_name}" />
        <input type="hidden" name="last_name" value="{last_name}" />
        <input type="hidden" name="email" value="{email}" />
        <input type="hidden" name="phone" value="{phone}" />
        <input type="hidden" name="address" value="{address}" />
        <input type="hidden" name="city" value="{city}" />
        <input type="hidden" name="country" value="Sri Lanka" />
        <input type="hidden" name="hash" value="{hash_val}" />
      </form>
      <script>document.getElementById('payhere_form').submit();</script>
    </body></html>
    """
    return HTMLResponse(content=html)

# ---------------------
# PayHere webhook (notify_url)
# ---------------------
@app.post("/webhooks/payhere")
async def payhere_notify(request: Request, session: Session = Depends(get_session)):
    # PayHere sends application/x-www-form-urlencoded
    form = await request.form()
    data = {k: form.get(k) for k in form.keys()}

    # Required items to verify
    merchant_id = data.get("merchant_id")
    order_id = data.get("order_id")
    payhere_amount = data.get("payhere_amount")
    payhere_currency = data.get("payhere_currency")
    status_code = data.get("status_code")
    md5sig = data.get("md5sig")
    subscription_id = data.get("subscription_id") or None

    # Verify signature
    if not verify_payhere_md5sig(merchant_id, order_id, payhere_amount, payhere_currency, status_code, md5sig, PAYHERE_MERCHANT_SECRET):
        return JSONResponse({"ok": False, "reason": "invalid_md5"}, status_code=400)

    # Find subscription by order_id
    sub = session.exec(select(Subscription).where(Subscription.order_id == order_id)).first()
    if not sub:
        return JSONResponse({"ok": False, "reason": "subscription_not_found"}, status_code=404)

    # status_code 2 => success
    if str(status_code) == "2":
        sub.status = "active"
        sub.payhere_subscription_id = subscription_id or data.get("subscription_id") or None

        # Create API key for the subscriber (one time when subscription becomes active)
        # Generate plain key and hash it for storage
        plain_key = generate_api_key_plain()
        key_hash = sha256_hex(plain_key)
        plan = session.get(Plan, sub.plan_id)
        quota = plan.monthly_quota if plan else 1000
        api = APIKey(key_hash=key_hash, owner_email=sub.customer_email, active=True, quota_remaining=quota)
        session.add(api)
        session.commit()
        # store relation
        sub.api_key_id = api.id
        sub.api_key_plain = plain_key  # TEMP: store plain for user to view once (demo)
        session.add(sub)
        session.commit()
        # In production: email the key instead of storing plain; delete plain after showing once.

    elif str(status_code) in ("-2", "-1", "-3"):
        sub.status = "failed_or_cancelled"
        session.add(sub)
        session.commit()

    return JSONResponse({"ok": True})

# ---------------------
# Return URL page (customer returns to this page after payment)
# ---------------------
@app.get("/subscribe/return", response_class=HTMLResponse)
def subscribe_return(order_id: str, session: Session = Depends(get_session)):
    sub = session.exec(select(Subscription).where(Subscription.order_id == order_id)).first()
    if not sub:
        return HTMLResponse("<h3>Order not found</h3>", status_code=404)
    if sub.status != "active":
        return HTMLResponse(f"<h3>Payment status: {sub.status}</h3><p>Please wait for the webhook</p>")

    # Show API key to the user one time
    api_key_plain = sub.api_key_plain or "key_not_available"
    # For security, clear the plain key after showing (demo)
    sub.api_key_plain = None
    session.add(sub)
    session.commit()

    html = f"""
    <html><body>
      <h2>Subscription Active</h2>
      <p>Your API key (store it securely):</p>
      <pre>{api_key_plain}</pre>
      <p>Use it as header <code>x-api-key: &lt;API_KEY&gt;</code> for API requests.</p>
    </body></html>
    """
    return HTMLResponse(html)

# ---------------------
# Example external API endpoint protected by API key
# ---------------------
@app.get("/v1/data")
def public_data(api: APIKey = Depends(require_api_key)):
    return {"msg": "Hello, API client", "quota_left": api.quota_remaining}

# ---------------------
# Utility endpoints for admin/demo
# ---------------------
@app.get("/plans")
def list_plans(session: Session = Depends(get_session)):
    plans = session.exec(select(Plan)).all()
    return plans

@app.get("/subscriptions")
def list_subs(session: Session = Depends(get_session)):
    return session.exec(select(Subscription)).all()
