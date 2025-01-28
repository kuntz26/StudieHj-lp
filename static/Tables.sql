CREATE TABLE IF NOT EXISTS people (
    id              INTEGER NOT NULL,
    username        TEXT NOT NULL,
    grade           TEXT NOT NULL,
    filename        TEXT,
    PRIMARY KEY(id AUTOINCREMENT)
);

CREATE TABLE IF NOT EXISTS login (
    personid    INTEGER NOT NULL,
    email       TEXT NOT NULL,
    password    TEXT NOT NULL,
    FOREIGN KEY(personid) REFERENCES people(id)
);

CREATE TABLE IF NOT EXISTS privateMessages (
    id          INTEGER NOT NULL,
    senderid    INTEGER NOT NULL,
    recipientid INTEGER NOT NULL,
    message     TEXT NOT NULL,
    date        DATE NOT NULL,
    PRIMARY KEY(id AUTOINCREMENT),
    FOREIGN KEY(senderid) REFERENCES people(id),
    FOREIGN KEY(recipientid) REFERENCES people(id)
);

CREATE TABLE IF NOT EXISTS publicMessages (
    id          INTEGER NOT NULL,
    senderid    INTEGER NOT NULL,
    header      TEXT NOT NULL,
    message     TEXT NOT NULL,
    categoryid  INTEGER NOT NULL,
    date        DATE NOT NULL,
    picturename TEXT,
    PRIMARY KEY(id AUTOINCREMENT),
    FOREIGN KEY(senderid) REFERENCES people(id),
    FOREIGN KEY(categoryid) REFERENCES category(id)
);

CREATE TABLE IF NOT EXISTS comments (
    id          INTEGER NOT NULL,
    date        DATE NOT NULL,
    messageid   INEGER NOT NULL,
    comment     TEXT NOT NULL,
    senderid    INTEGER NOT NULL,
    PRIMARY KEY(id AUTOINCREMENT),
    FOREIGN KEY(senderid) REFERENCES people(id),
    FOREIGN KEY(messageid) REFERENCES publicMessages(id)
);

CREATE TABLE IF NOT EXISTS category (
    id          INTEGER NOT NULL,
    name        TEXT NOT NULL,
    PRIMARY KEY(id AUTOINCREMENT)
);