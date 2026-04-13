schema = """
DATABASE: Chinook (SQLite)

TABLES:

albums(
    AlbumId INTEGER PRIMARY KEY,
    Title TEXT,
    ArtistId INTEGER
)

artists(
    ArtistId INTEGER PRIMARY KEY,
    Name TEXT
)

customers(
    CustomerId INTEGER PRIMARY KEY,
    FirstName TEXT,
    LastName TEXT,
    Company TEXT,
    Address TEXT,
    City TEXT,
    State TEXT,
    Country TEXT,
    PostalCode TEXT,
    Phone TEXT,
    Fax TEXT,
    Email TEXT,
    SupportRepId INTEGER
)

employees(
    EmployeeId INTEGER PRIMARY KEY,
    LastName TEXT,
    FirstName TEXT,
    Title TEXT,
    ReportsTo INTEGER,
    BirthDate TEXT,
    HireDate TEXT,
    Address TEXT,
    City TEXT,
    State TEXT,
    Country TEXT,
    PostalCode TEXT,
    Phone TEXT,
    Fax TEXT,
    Email TEXT
)

genres(
    GenreId INTEGER PRIMARY KEY,
    Name TEXT
)

invoices(
    InvoiceId INTEGER PRIMARY KEY,
    CustomerId INTEGER,
    InvoiceDate TEXT,
    BillingAddress TEXT,
    BillingCity TEXT,
    BillingState TEXT,
    BillingCountry TEXT,
    BillingPostalCode TEXT,
    Total REAL
)

invoice_items(
    InvoiceLineId INTEGER PRIMARY KEY,
    InvoiceId INTEGER,
    TrackId INTEGER,
    UnitPrice REAL,
    Quantity INTEGER
)

media_types(
    MediaTypeId INTEGER PRIMARY KEY,
    Name TEXT
)

playlists(
    PlaylistId INTEGER PRIMARY KEY,
    Name TEXT
)

playlist_track(
    PlaylistId INTEGER,
    TrackId INTEGER
)

tracks(
    TrackId INTEGER PRIMARY KEY,
    Name TEXT,
    AlbumId INTEGER,
    MediaTypeId INTEGER,
    GenreId INTEGER,
    Composer TEXT,
    Milliseconds INTEGER,
    Bytes INTEGER,
    UnitPrice REAL
)
"""