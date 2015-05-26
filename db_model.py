from argparse import _ActionsContainer
import sqlite3 as sql
import time

DATABASE_FILE = "ds2015.db"

def init():
    cur, conn = getCursor()
    cur.execute('''
       CREATE TABLE IF NOT EXISTS hashes
       (
       id INTEGER PRIMARY KEY ASC,
       hash TEXT,
       started_time REAL,
       solved_time REAL,
       solved INTEGER DEFAULT 0,
       solution TEXT
       )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS progress
        (
        hash_id INTEGER REFERENCES hashes(id) ON DELETE CASCADE,
        character TEXT,
        row REAL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS clients
        (
        id TEXT UNIQUE,
        hash_working INTEGER,
        join_time REAL,
        last_ping REAL
        )
    ''')

def getClients():
    result = []
    cur, conn = getCursor()
    cur.execute('''
        SELECT * FROM clients
    ''')
    for row in cur:
        result.append(row)

    return result

def getUnsolvedHashes():
    result = []
    cur, conn = getCursor()
    cur.execute("SELECT * FROM hashes WHERE solved = 0")
    for row in cur:
        result.append(row)
    return result

def getSolvedHashes():
    result = []
    cur, conn = getCursor()
    cur.execute("SELECT * FROM hashes WHERE solved = 1")
    for row in cur:
        result.append(row)
    return result


def getProgress(client_id):
    hash_id = 0
    cur, conn = getCursor()
    sql = "SELECT hash_working FROM clients WHERE client_id = " + client_id
    cur.execute(sql)
    if not row:
        return None, None
    for row in cur:
        hash_id =  row[0]
    sql = "SELECT character, row FROM progress WHERE hash_id = " + hash_id
    cur.execute(sql)
    if not row:
        return None, None
    for row in cur:
        return row[0], row[1]

def nextCharacter(hash_id):
    cur, conn = getCursor()
    cur.execute("SELECT character FROM progress WHERE hash_id = " + hash_id)
    for row in cur:
        curChar = row[0]
    ## if not end of alphabets
    if ord(curChar) < 123:
        new_char = char(ord(curChar) + 1)
    cur.execute("UPDATE progress SET character = " + new_char + ", row = 0 WHERE hash_id = " + hash_id)
    conn.commit()


def post_hash(hash):
    cur, conn = getCursor()
    sql = "INSERT INTO hashes (hash, started_time) VALUES ('" + str(hash) + "'," + str(time.time()) + ")"
    cur.execute(sql)
    conn.commit()
    lastid = cur.lastrowid
    cur.execute("SELECT * FROM hashes WHERE id = " + str(lastid))
    for row in cur:
        return row

def connectClient(client_id):
    cur, conn = getCursor()

    print "connecting " + client_id
    try:
        cur.execute("INSERT INTO clients (id, join_time, last_ping) VALUES ('"+str(client_id)+"', "+str(time.time())+"," +str(time.time())+")")
        conn.commit()

    except Exception:
        return "FAILURE, not unique"
    sql = "SELECT last_ping FROM clients WHERE id = '" + str(client_id) + "'"
    cur.execute(sql)

    for row in cur:
        conn.close()
        return "OK"

    conn.close()
    return "FAILURE"

def disconnect(client_id):
    cur, conn = getCursor()
    cur.execute("DELETE FROM clients WHERE client_id = '" + str(client_id) + "'")
    conn.commit()
    conn.close()
    return "Deleted"

def ping(client_id):
    cur, conn = getCursor()
    now = time.time()
    cur.execute("UPDATE clients SET last_ping = " + now + " WHERE client_id = '" + str(client_id) + "'")
    conn.commit()
    return str(now)

def getPing(client_id):
    cur, conn = getCursor()
    cur.execute("SELECT last_ping FROM clients WHERE client_id = '" + str(client_id) + "'")
    for row in cur:
        return str(row[0])

def getCursor():
    c = sql.connect(DATABASE_FILE)
    c.cursor().execute("PRAGMA foreign_keys = ON")
    return c.cursor(), c