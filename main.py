import sqlite3
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

# Beschreibung
description="""Eine FastAPI zum Verwalten einer SQLite Bücherdatenbank. 

Die API dient als Beispiel für Einsteiger.
Datenbank wird periodisch zurückgesetzt.
Informationen über Bücher können abgerufen, eingetragen,
geändert oder gelöscht werden.

Datenstruktur eines Buchs: 
```json
{
    "isbn": "978-3518380239",
    "author": "Thomas Bernhard",
    "title": "Holzfällen. Eine Erregung",
    "pages": 336,
    "book_id": 2
}
```

Made by Nils
"""

# pydantic Datenmodell ohne ID (zum posten)
class Book(BaseModel):
    isbn: str = '123-4567890123'
    author: str = 'Max Mustermann'
    title: str = 'Ein Buch'
    pages: int | None = 700


# mit ID (zum Abfragen)
class BookGet(Book):
    book_id: int = 100


class Message(BaseModel):
    message: str = 'success'


class MessagePost(Message):
    new_id: int
    new_data: Book


class MessageDelete(Message):
    deleted_id: int


# App erstellen
app = FastAPI(
    title="Super Bücher API",
    description=description,
    version="0.1",
)


# Funktion zum SQL-Verbindung generieren
def get_con():
    return sqlite3.connect("buecher.sqlite")


# ENDPUNKTE
@app.get("/")
def read_root() -> Message:
    """User Begrüßung."""
    return Message(message="Hello User!")


@app.get("/books")
def read_books(con: sqlite3.Connection = Depends(get_con)) -> list[BookGet]:
    """Alle Bücher zurückgeben."""
    cursor = con.cursor()  # Cursor erstellen

    # Daten abfragen und in Pydantic-Instanzen umwandeln
    # (damit json mit Schlüsselnamen zurückgegeben werden kann)
    try:
        books = cursor.execute("SELECT * FROM buch").fetchall()
        books = [
            BookGet(
                book_id=book[0],
                isbn=book[1],
                author=book[2],
                title=book[3],
                pages=book[4],
            )
            for book in books
        ]
        return books
    except sqlite3.Error as e:
        raise HTTPException(500, f"SQL Fehler: {e}")
    finally:
        # Verbindung schließen
        cursor.close()
        con.close()


@app.get("/books/{id}")
def read_book(id: int, con: sqlite3.Connection = Depends(get_con)) -> BookGet:
    """Bestimmtes Buch zurückgeben"""
    cursor = con.cursor()

    try:
        book = cursor.execute(
            """
                SELECT * FROM buch
                WHERE book_id = ?
            """,
            [id],
        ).fetchall()

        if book:
            # Falls Buch gefunden, in Pydantic-Instanz umwandeln
            book = BookGet(
                book_id=book[0],
                isbn=book[1],
                author=book[2],
                title=book[3],
                pages=book[4]
            )
            return book
        else:
            raise HTTPException(404, f"Book with id {id} not found.")
    except sqlite3.Error as e:
        raise HTTPException(500, f"SQL Fehler: {e}")
    finally:
        # Verbindung schließen
        cursor.close()
        con.close()


@app.post("/books/{id}", status_code=201)
def post_book(book: Book,
              con: sqlite3.Connection = Depends(get_con)) -> MessagePost:
    """Buch hinzufügen"""
    cursor = con.cursor()

    try:
        cursor.execute(
            """
                INSERT INTO buch (book_id, isbn, author, title, pages)
                    VALUES (?, ?, ?, ?, ?)
            """,
            (id, book.isbn, book.author, book.title, book.pages),
        )
        con.commit()
        result = MessagePost(message="Book created successfully.",
                             new_id=id,
                             new_data=book)
        return result
    except sqlite3.Error as e: 
        con.rollback() 
        # JSON-Fehlermeldung zurückgeben
        # (wird von FastAPI geregelt, man muss den Fehler nur ausrufen)
        # Lässt sich mit exception_handler auch global automatisieren
        raise HTTPException(status_code=400, detail=f"SQL Error: {e}")
    finally:
        # Egal ob es geklappt hat, die Verbindung am Ende wieder schließen
        cursor.close()
        con.close()


@app.put("/books/{id}")
def update_book(id: int, book: Book, con: sqlite3.Connection = Depends(get_con)):
    """Buch updaten."""
    cursor = con.cursor()

    try:
        cursor.execute(
            """
                UPDATE buch
                SET isbn = ?,
                    author = ? ,
                    title = ?,
                    pages = ?
                WHERE book_id = ?
            """,
            (book.isbn, book.author, book.title, book.pages, id),
        )
        con.commit()
        result = {
            "message": "changed successfully.",
            "changed book id": id,
            "new_entry": book,
        }
    except sqlite3.Error as e:
        con.rollback()
        raise HTTPException(status_code=500, detail=f"SQL Error: {e}")
    finally:
        cursor.close()
        con.close()

    return result


@app.delete("/books/{id}")
def delete_book(id: int, con: sqlite3.Connection = Depends(get_con)):
    """Buch löschen"""
    cursor = con.cursor()
    try:
        cursor.execute("DELETE FROM buch WHERE book_id = ?", [id])
        con.commit()
        result = MessageDelete(
            message="Book deleted successfully.",
            deleted_id=id
        )
    except sqlite3.Error as e:
        con.rollback()
        raise HTTPException(status_code=500, detail=f"SQL Error: {e}")
    finally:
        cursor.close()
        con.close()

    return result


if __name__ == "__main__":
    # Uvicorn wird nur importiert, wenn das Skript direkt ausgeführt wird.
    import uvicorn
    uvicorn.run("main:app", reload=True, port=8000)
