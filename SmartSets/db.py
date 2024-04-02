import sqlite3

con = sqlite3.connect("studySets.db")
cursor = con.cursor()
con.execute("PRAGMA foreign_keys = 1")
print("connected to db")


def init(reset):
    if reset==True: #empty the tables on init if true
        cursor.execute("""DROP TABLE IF EXISTS cards """)
        cursor.execute("""DROP TABLE IF EXISTS sets """)
        con.commit()
        print("tables dropped")

    #create tables
    cmd1 = """CREATE TABLE IF NOT EXISTS
        sets (
            set_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            setName TEXT UNIQUE,
            numCards INTEGER,
            avgMastery REAL DEFAULT 0
        )"""
    cursor.execute(cmd1)

    cmd2 = """CREATE TABLE IF NOT EXISTS
        cards (
            set_id INTEGER, 
            card_id INTEGER,
            mastery REAL DEFAULT 0, 
            term TEXT, 
            definition TEXT, 
            attempts INTEGER DEFAULT 0,
            FOREIGN KEY(set_id) REFERENCES sets(set_id)
        )"""
    cursor.execute(cmd2)
    print("Database Tables Initialised")


def addSet(name, terms, definitions): #add a new set to the sets table and add the corresponding cards to the cards table
    #sets table
    addRecordToSets = """INSERT INTO sets (setName, numCards) 
        VALUES (?,?)"""
    setRec = (name, len(terms))
    cursor.execute(addRecordToSets,setRec)
    con.commit()
    foreignKey = (cursor.lastrowid)
    print("added set")

    #cards table
    addRecordToCards = """INSERT INTO cards (set_id, card_id, term, definition) 
        VALUES (?,?,?,?)"""
    cardIndexes = list(range(0,len(terms)))
    for i,j,k in zip(cardIndexes,terms,definitions):
        cardRec = (foreignKey, i, j, k) 
        cursor.execute(addRecordToCards, cardRec)
    con.commit()
    print("added cards")


def getNumSets():
    cursor.execute("SELECT count(*) FROM sets")
    result = cursor.fetchone()
    numSets = result[0]
    return numSets
    

def getSetNames():
    cursor.execute("SELECT setName FROM sets")
    setObjs = cursor.fetchall()
    setNames = []
    for tuple in setObjs: #just getting rid of the db tuple formatiing
        setNames.append(tuple[0])
    return setNames


def getCards(setName):
    cursor.execute("SELECT set_id FROM sets WHERE setName=?", (setName,)) #not sure why but i get errors if i don't put a comma after these values
    row = cursor.fetchone()
    desiredID = row[0]
    cursor.execute("SELECT * FROM cards where set_id=?", (desiredID,))
    cards = cursor.fetchall()
    return cards

def getMastery(set_id,card_id):
    cursor.execute("SELECT mastery FROM cards WHERE set_id=? AND card_id=?",(set_id,card_id))
    result = cursor.fetchone()
    return result[0]

def updateMastery(set_id,card_id,masteryScore):
    cursor.execute("UPDATE cards SET mastery=?, attempts=attempts+1 WHERE set_id=? AND card_id=?",(masteryScore,set_id,card_id))
    con.commit()

def updateAvgMastery(set_id, avgMastery):
    cursor.execute("UPDATE sets SET avgMastery=? WHERE set_id=?", (avgMastery, set_id))
    con.commit()

def getSetDisplay():
    cursor.execute("SELECT set_id, setName, numCards, avgMastery FROM sets")
    sets = cursor.fetchall()
    return sets

def getAttemptsSum(set_id):
    cursor.execute("SELECT attempts FROM cards WHERE set_id=?", (set_id,))
    attempts = cursor.fetchall()
    sumAttempts = 0
    for attempt in attempts:
        sumAttempts += attempt[0]
    return sumAttempts

