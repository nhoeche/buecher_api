import sqlite3
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel


# pydantic Datenmodell ohne ID (zum posten)
class Book(BaseModel):
    isbn: str
    author: str
    title: str
    pages: int | None

# mit ID (zum Abfragen)
class BookGet(Book):
    book_id: int


# App erstellen
app = FastAPI(title="Super Bücher API",
              description="Made by Datacraft",
              version="0.1")


# Funktion zum SQL-Verbindung generieren
def get_con():
    return sqlite3.connect("buecher.sqlite")



# ENDPUNKTE
@app.get("/")
def read_root():
    """User Begrüßung."""
    return {"message": "Hello User!"}


@app.get("/books")
def read_books(con: sqlite3.Connection = Depends(get_con)):
    """Alle Bücher zurückgeben."""
    cursor = con.cursor()  # Cursor erstellen

    # Daten abfragen und in Dictionary umwandeln (damit wir json mit Schlüsselnamen zurückgeben)
    books = cursor.execute("SELECT * FROM buch").fetchall()
    books = [BookGet(book_id=book[0], isbn=book[1], author=book[2], title=book[3], pages=book[4]) for book in books]

    # Verbindung schließen
    cursor.close()
    con.close()
    return books


@app.get("/books/{id}")
def read_book(id: int, con: sqlite3.Connection = Depends(get_con)):
    """Bestimmtes Buch zurückgeben"""
    cursor = con.cursor()

    book = cursor.execute("""
            SELECT * FROM buch
            WHERE book_id = ?
        """,
        [id]).fetchall()
    book = BookGet(book_id=book[0], isbn=book[1], author=book[2], title=book[3], pages=book[4])

    cursor.close()
    con.close()
    return book


@app.post("/books/{id}", status_code=201)
def post_book(book: Book, con: sqlite3.Connection = Depends(get_con)):
    """Buch hinzufügen"""
    cursor = con.cursor()

    # Ab hier mit Error handling (könnte oben ergänzt werden)
    try:  # Versuche einzutragen...
        cursor.execute("""
                INSERT INTO buch (book_id, isbn, author, title, pages)
                    VALUES (?, ?, ?, ?, ?)
            """,
            (id, book.isbn, book.author, book.title, book.pages)
        )
        con.commit()
        result = {"added": book}
    except sqlite3.Error as e:  # Wenn SQL-Fehler, dann...
        con.rollback()  # Aktion rükgängig machen
        # JSON-Fehlermeldung zurpckgeben (wird von FastAPI geregelt, man muss den Fehler nur ausrufen)
        raise HTTPException(status_code=400, detail=f"SQL Error: {e}")
    finally:
        # Egal ob es geklappt hat, die Verbindung am ende wieder schließen
        cursor.close()
        con.close()
    
    return result
    

@app.put("/books/{id}")
def update_book(id: int, book: Book, con: sqlite3.Connection = Depends(get_con)):
    """Buch updaten."""
    cursor = con.cursor()

    try:
        cursor.execute("""
            UPDATE buch
            SET isbn = ?,
                author = ? ,
                title = ?,
                pages = ?
            WHERE book_id = ?
        """,
        (book.isbn, book.author, book.title, book.pages, id)).fetchall()
        con.commit()
        result = {"changed": id, "new": book}
    except sqlite3.Error as e:
        con.rollback()
        raise HTTPException(status_code=400, detail=f"SQL Error: {e}")
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
        result = {"deleted": id}
    except sqlite3.Error as e:
        con.rollback()
        raise HTTPException(status_code=400, detail=f"SQL Error: {e}")
    finally:
        cursor.close()
        con.close()

    return result


# Falls das Skript direkt ausgeführt wird, soll uvicorn importiert werden und der Webserver gestartet werden.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True, port=8000)