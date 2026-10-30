import sqlite3
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.models import Customer, Order, Ticket
from app.config import settings

router = APIRouter(prefix='/enterprise', tags=['Synthetic enterprise API'])


def connect():
    db = Path(settings().enterprise_db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def seed():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS customers(id TEXT PRIMARY KEY, name TEXT, tier TEXT);
        CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY, customer_id TEXT, status TEXT, expected_delivery TEXT);
        CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY, customer_id TEXT, priority TEXT, status TEXT, summary TEXT);
        INSERT OR IGNORE INTO customers VALUES ('CUST-001','Example North','standard'),('CUST-002','Example West','enterprise');
        INSERT OR IGNORE INTO orders VALUES ('ORD-1003','CUST-002','in transit','2026-11-03'),('ORD-1004','CUST-001','processing','2026-11-06');
        INSERT OR IGNORE INTO tickets VALUES ('TKT-1001','CUST-002','P1','open','Production service unavailable'),('TKT-1002','CUST-002','P2','open','Intermittent report delays'),('TKT-1003','CUST-001','P3','closed','Account access question');
        ''')


def one(table, identifier):
    # Table identifiers are selected only by the fixed route implementations below.
    with connect() as c:
        row = c.execute(f'SELECT * FROM {table} WHERE id=?', (identifier,)).fetchone()
    if row is None:
        raise HTTPException(404, 'Synthetic record not found')
    return dict(row)


@router.get('/customers/{customer_id}', response_model=Customer)
def customer(customer_id: str):
    return one('customers', customer_id)


@router.get('/orders/{order_id}', response_model=Order)
def order(order_id: str):
    return one('orders', order_id)


@router.get('/tickets/{ticket_id}', response_model=Ticket)
def ticket(ticket_id: str):
    return one('tickets', ticket_id)


@router.get('/customers/{customer_id}/tickets', response_model=list[Ticket])
def tickets(customer_id: str, status: str | None = None):
    one('customers', customer_id)
    if status not in (None, 'open', 'closed'):
        raise HTTPException(422, 'status must be open or closed')
    with connect() as c:
        rows = c.execute('SELECT * FROM tickets WHERE customer_id=? AND (? IS NULL OR status=?)',
                         (customer_id, status, status)).fetchall()
    return [dict(r) for r in rows]
