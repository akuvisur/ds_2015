from argparse import _ActionsContainer
import sqlite3 as sql
import time

DATABASE_FILE = "ds2015.db"
CHUNK_SIZE = 200000

def init():
    cur, conn = getCursor()
    cur.execute('''
       CREATE TABLE IF NOT EXISTS hashes
       (
       id INTEGER PRIMARY KEY ASC,
       hash TEXT,
       created_time REAL,
       started_time REAL,
       solved_time REAL,
       solved INTEGER DEFAULT 0,
       solution TEXT,
       solvable INTEGER DEFAULT 1
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
    cur.execute("SELECT * FROM hashes WHERE solved = 0 AND solvable = 1")
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
    ##print "getprogress"
    hash_id = 0
    cur, conn = getCursor()
    sql = "SELECT hash_working FROM clients WHERE id = '" + str(client_id) + "'"
    cur.execute(sql)
    found = False
    for row in cur:
        hash_id = row[0]
        if not hash_id:
            return None, None, None
        found = True
    if not found:
        return None, None, None

    sql = "SELECT hash FROM hashes WHERE id = " + str(hash_id)
    cur.execute(sql)
    for row in cur:
        target = str(row[0])
    nextChunk(hash_id)
    sql = "SELECT character, row FROM progress WHERE hash_id = '" + str(hash_id) + "'"
    cur.execute(sql)
    if not row:
        return None, None, None
    for row in cur:
        updateClient(hash_id, row[0], row[1])
        print "target = " + str(target)
        print "character = " + str(row[0])
        print "row = " + str(row[1])
        return target, row[0], row[1]

def getNextHash():
    cur, conn = getCursor()
    cur.execute("SELECT id, hash FROM hashes WHERE solved = 0 AND solvable = 1 ORDER BY created_time LIMIT 1")
    found = False
    for row in cur:
        print row[0]
        hash_id = row[0]
        target = row[1]
        found = True
        ## taanne paasee
    if not found:
        return None, None, None
    nextChunk(hash_id)
    sql = "SELECT * FROM progress WHERE hash_id = '" + str(hash_id) + "'"
    cur.close()
    cur, conn = getCursor()
    cur.execute(sql)
    for row in cur:
        print "searching for " + str(target) + " " + str(row[1]) + " " + str(row[2])
        updateClient(hash_id, row[1], row[2])
        return target, row[1], row[2]

# update client progress
def updateClient(hash_id, character, row):
    cur, conn = getCursor()
    cur.execute("UPDATE progress SET character = '" + str(character) + "', row = '" + str(row)+ "' WHERE hash_id = '" + str(hash_id) + "'")
    conn.commit()

# set client to work on hash x
def setClientWorking(target, client_id):
    cur, conn = getCursor()
    cur.execute("SELECT id FROM hashes WHERE hash = '" + str(target) + "'")
    for row in cur:
        hash_id = row[0]
    cur.execute("UPDATE clients SET hash_working = '" + str(hash_id) + "' WHERE id = '" + str(client_id) + "'")
    conn.commit()

def nextChunk(hash_id):
    ##print "nextchunk"
    cur, conn = getCursor()
    cur.execute("SELECT row FROM progress WHERE hash_id = '" + str(hash_id) + "'")
    found = False
    for row in cur:
        curRow = row[0]
        found = True
        ##print "found"
    if not found:
        return 0
    cur.execute("UPDATE progress SET row = " + str(curRow + CHUNK_SIZE))
    conn.commit()
    cur.close()


def nextCharacter(target_hash):
    ##print "Nextcharacter"
    cur, conn = getCursor()
    cur.execute("SELECT id FROM hashes WHERE hash = '" + target_hash + "'")
    for row in cur:
        hash_id = row[0]
    cur.execute("SELECT character FROM progress WHERE hash_id = '" + str(hash_id) + "'")
    for row in cur:
        curChar = row[0]
    ## if not end of alphabets
    if ord(curChar) < 122:
        new_char = chr(ord(curChar) + 1)
    else:
        couldNotSolve(hash_id)
        return 0
    cur.execute("UPDATE progress SET character = '" + str(new_char) + "', row = 0 WHERE hash_id = '" + str(hash_id) + "'")
    conn.commit()

def solve(target, solution):
    cur, conn = getCursor()
    cur.execute("UPDATE hashes SET solved = 1, solution = '" + str(solution) + "' WHERE hash = '" + target + "'")
    conn.commit()

def couldNotSolve(hash_id):
    cur, conn = getCursor()
    cur.execute("UPDATE hashes SET solvable = 0 WHERE id = '" + str(hash_id) + "'")
    conn.commit()

def post_hash(hash):
    cur, conn = getCursor()
    sql = "INSERT INTO hashes (hash, created_time) VALUES ('" + str(hash) + "'," + str(time.time()) + ")"
    cur.execute(sql)
    conn.commit()
    lastid = cur.lastrowid
    cur.execute("INSERT INTO progress VALUES (" + str(lastid) + ",'a', 1)")
    conn.commit()
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
    cur.execute("DELETE FROM clients WHERE id = '" + str(client_id) + "'")
    conn.commit()
    conn.close()
    print "Disconnected " + str(client_id)
    return "Deleted"

def ping(client_id):
    cur, conn = getCursor()
    now = time.time()
    cur.execute("UPDATE clients SET last_ping = " + str(now) + " WHERE id = '" + str(client_id) + "'")
    conn.commit()
    return str(now)

def getPing(client_id):
    cur, conn = getCursor()
    cur.execute("SELECT last_ping FROM clients WHERE id = '" + str(client_id) + "'")
    for row in cur:
        return str(row[0])

# remove nonresponding clients
def killThemDead():
    cur, conn = getCursor()
    now = time.time()
    cur.execute("SELECT id, last_ping FROM clients")
    for row in cur:
        # if client not responed for 60 seconds
        if (now - row[1]) > 90:
            cur.execute("DELETE FROM clients WHERE id ='" + str(row[0]) + "'")
            conn.commit()


def getCursor():
    c = sql.connect(DATABASE_FILE)
    c.cursor().execute("PRAGMA foreign_keys = ON")
    return c.cursor(), c