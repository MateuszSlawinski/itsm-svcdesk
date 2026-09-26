# ai-generated: 90% - implemented from the Lab 1 API contract and reviewed against published vectors
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dora_metrics import MetricInputError, compute_metrics

app = FastAPI()
DB = os.environ.get("SVCDESK_DB", "/data/svcdesk.db")
TZ = ZoneInfo("Europe/Warsaw")
MATRIX = [[None, "P1", "P2", "P3"], [None, "P2", "P3", "P4"], [None, "P3", "P4", "P4"]]
TARGETS = {"P1": (15, 240), "P2": (60, 480), "P3": (240, 1440), "P4": (480, 4320)}


def conn():
    os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS tickets (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
      reporter TEXT NOT NULL, impact INTEGER NOT NULL, urgency INTEGER NOT NULL,
      priority TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL,
      acknowledged_at TEXT, resolved_at TEXT, closed_at TEXT, related_to TEXT)""")
    c.commit()
    return c


def instant(value):
    if not isinstance(value, str) or not value:
        raise ValueError("invalid timestamp")
    s = value[:-1] + "+00:00" if value.endswith("Z") else value
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError("timestamp must include offset")
    return dt.astimezone(timezone.utc)


def fmt(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def now_for(request):
    header = request.headers.get("x-test-clock")
    enabled = os.environ.get("SVCDESK_TEST_CLOCK", "").lower() in ("1", "true", "yes")
    if header and enabled:
        try:
            return instant(header)
        except Exception:
            raise HTTPException400("invalid test clock")
    return datetime.now(timezone.utc)


class HTTPException400(Exception):
    def __init__(self, message):
        self.message = message


def error(status, code, message):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def business_due(start, minutes):
    local = start.astimezone(TZ)
    remaining = float(minutes)
    while True:
        if local.weekday() >= 5:
            local = datetime.combine((local + timedelta(days=1)).date(), time(8), TZ)
            continue
        opening = datetime.combine(local.date(), time(8), TZ)
        closing = datetime.combine(local.date(), time(16), TZ)
        if local < opening:
            local = opening
        elif local >= closing:
            local = datetime.combine((local + timedelta(days=1)).date(), time(8), TZ)
            continue
        available = (closing - local).total_seconds() / 60
        if remaining <= available:
            return local + timedelta(minutes=remaining)
        remaining -= available
        local = datetime.combine((local + timedelta(days=1)).date(), time(8), TZ)


def due_times(created, priority):
    ack, resolve = TARGETS[priority]
    if priority == "P1" and os.environ.get("SVCDESK_SLA_CLOCK", "wallclock") == "wallclock":
        return created + timedelta(minutes=ack), created + timedelta(minutes=resolve)
    return business_due(created, ack).astimezone(timezone.utc), business_due(created, resolve).astimezone(timezone.utc)


def is_business(dt):
    local = dt.astimezone(TZ)
    return local.weekday() < 5 and time(8) <= local.timetz().replace(tzinfo=None) < time(16)


def ticket_json(row):
    created = instant(row["created_at"])
    ack, resolve = due_times(created, row["priority"])
    return {
        "id": row["id"], "title": row["title"], "description": row["description"],
        "reporter": json.loads(row["reporter"]), "impact": row["impact"], "urgency": row["urgency"],
        "priority": row["priority"], "state": row["state"], "created_at": row["created_at"],
        "acknowledged_at": row["acknowledged_at"], "resolved_at": row["resolved_at"],
        "closed_at": row["closed_at"], "related_to": row["related_to"],
        "sla": {"ack_due_at": fmt(ack), "resolve_due_at": fmt(resolve)}
    }


def get_row(tid):
    c = conn()
    row = c.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
    c.close()
    return row


@app.exception_handler(HTTPException400)
async def bad_clock(request, exc):
    return error(400, "validation", exc.message)


@app.exception_handler(Exception)
async def unexpected(request, exc):
    if isinstance(exc, ValueError):
        return error(400, "validation", str(exc))
    return error(500, "internal_error", "internal server error")


@app.get("/health")
def health():
    return {"status": "ok", "service": "svcdesk"}


@app.post("/dora/metrics")
async def dora_metrics(request: Request):
    try:
        body = await request.json()
    except ValueError:
        return error(400, "validation", "request body must contain valid JSON")
    try:
        return compute_metrics(body)
    except MetricInputError as exc:
        return error(422, "validation", str(exc))


@app.get("/dora/ticket-events")
def ticket_events():
    c = conn()
    rows = c.execute("SELECT * FROM tickets").fetchall()
    c.close()
    events = []
    for row in rows:
        phases = (
            ("created_at", "created", "new"),
            ("acknowledged_at", "acknowledged", "acknowledged"),
            ("resolved_at", "resolved", "resolved"),
            ("closed_at", "closed", "closed"),
        )
        for timestamp_field, phase, state in phases:
            timestamp = row[timestamp_field]
            if timestamp is not None:
                events.append({
                    "ticket_id": row["id"],
                    "at": timestamp,
                    "phase": phase,
                    "priority": row["priority"],
                    "state": state,
                })
    events.sort(key=lambda event: (instant(event["at"]), event["ticket_id"]))
    return events


@app.post("/tickets")
async def create_ticket(request: Request):
    try:
        body = await request.json()
    except Exception:
        return error(400, "validation", "JSON body required")
    if not isinstance(body, dict):
        return error(400, "validation", "object body required")
    title = body.get("title")
    description = body.get("description", "")
    reporter = body.get("reporter")
    impact, urgency = body.get("impact"), body.get("urgency")
    if not isinstance(title, str) or not 1 <= len(title) <= 200:
        return error(422, "validation", "title is required and must be 1..200 characters")
    if not isinstance(description, str) or len(description) > 4000:
        return error(422, "validation", "description must be at most 4000 characters")
    if not isinstance(reporter, dict) or not isinstance(reporter.get("name"), str) or not 1 <= len(reporter["name"]) <= 100:
        return error(422, "validation", "reporter.name is required")
    if "email" in reporter and reporter["email"] is not None and not isinstance(reporter["email"], str):
        return error(422, "validation", "reporter.email must be a string or null")
    if not isinstance(impact, int) or isinstance(impact, bool) or impact not in (1, 2, 3):
        return error(422, "validation", "impact must be 1, 2 or 3")
    if not isinstance(urgency, int) or isinstance(urgency, bool) or urgency not in (1, 2, 3):
        return error(422, "validation", "urgency must be 1, 2 or 3")
    if "related_to" in body and body["related_to"] is not None and not isinstance(body["related_to"], str):
        return error(422, "validation", "related_to must be a string or null")
    try:
        created = now_for(request)
    except HTTPException400 as e:
        raise e
    vip = reporter.get("vip", False)
    if not isinstance(vip, bool):
        return error(422, "validation", "reporter.vip must be boolean")
    priority = MATRIX[impact - 1][urgency]
    if vip and priority in ("P3", "P4"):
        priority = "P2"
    rep = {"name": reporter["name"], "email": reporter.get("email"), "vip": vip}
    tid = str(uuid.uuid4())
    c = conn()
    c.execute("INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (tid, title, description, json.dumps(rep), impact, urgency, priority, "new", fmt(created), None, None, None, body.get("related_to")))
    c.commit()
    row = c.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
    c.close()
    return JSONResponse(status_code=201, content=ticket_json(row))


@app.get("/tickets")
def list_tickets(state: str = None, priority: str = None):
    c = conn()
    q, args = "SELECT * FROM tickets", []
    clauses = []
    if state is not None:
        clauses.append("state=?"); args.append(state)
    if priority is not None:
        clauses.append("priority=?"); args.append(priority)
    if clauses: q += " WHERE " + " AND ".join(clauses)
    rows = c.execute(q, args).fetchall(); c.close()
    return [ticket_json(r) for r in rows]


@app.get("/tickets/{tid}")
def get_ticket(tid: str):
    row = get_row(tid)
    return ticket_json(row) if row else error(404, "not_found", "ticket not found")


@app.get("/tickets/{tid}/sla")
def sla(tid: str, request: Request):
    row = get_row(tid)
    if not row: return error(404, "not_found", "ticket not found")
    created = instant(row["created_at"]); ack, resolve = due_times(created, row["priority"])
    try: now = now_for(request)
    except HTTPException400 as e: raise e
    ack_b = (instant(row["acknowledged_at"]) > ack if row["acknowledged_at"] else now > ack)
    resolved_active = row["resolved_at"] is not None and row["state"] in ("resolved", "closed")
    res_b = (instant(row["resolved_at"]) > resolve if resolved_active else now > resolve)
    business_clock = not (row["priority"] == "P1" and os.environ.get("SVCDESK_SLA_CLOCK", "wallclock") == "wallclock")
    paused = row["state"] not in ("resolved", "closed") and business_clock and not is_business(now)
    return {"priority": row["priority"], "ack_due_at": fmt(ack), "resolve_due_at": fmt(resolve),
            "ack_breached": ack_b, "resolve_breached": res_b, "paused": paused}


@app.post("/tickets/{tid}/{action}")
def transition(tid: str, action: str, request: Request):
    row = get_row(tid)
    if not row: return error(404, "not_found", "ticket not found")
    try: now = now_for(request)
    except HTTPException400 as e: raise e
    state = row["state"]; new_state = None; updates = {}
    if action == "ack" and state == "new":
        new_state, updates = "acknowledged", {"acknowledged_at": fmt(now)}
    elif action == "start" and state == "acknowledged": new_state = "in_progress"
    elif action == "resolve" and state == "in_progress":
        new_state, updates = "resolved", {"resolved_at": fmt(now)}
    elif action == "close" and state == "resolved":
        new_state, updates = "closed", {"closed_at": fmt(now)}
    elif action == "reopen" and state in ("resolved", "closed"):
        if state == "closed": return error(409, "ticket_closed", "closed tickets are immutable")
        if now > instant(row["resolved_at"]) + timedelta(days=7):
            return error(409, "reopen_window_expired", "reopen window expired")
        new_state, updates = "in_progress", {"resolved_at": None, "closed_at": None}
    else:
        return error(409, "invalid_transition", "invalid state transition")
    c = conn()
    fields = ["state=?"]; values = [new_state]
    for k, v in updates.items(): fields.append(k + "=?"); values.append(v)
    values.append(tid)
    c.execute("UPDATE tickets SET " + ", ".join(fields) + " WHERE id=?", values); c.commit()
    out = c.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone(); c.close()
    return ticket_json(out)
