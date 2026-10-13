
import os
import sqlite3
import hashlib
import secrets
import hmac

BAZA = os.environ.get(
    "VZTM_WHITELIST_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "whitelist.db")
)


def polacz():
    db = sqlite3.connect(BAZA)
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE COLLATE NOCASE,
            haslo_hash TEXT NOT NULL,
            aktywne INTEGER NOT NULL DEFAULT 1,
            utworzono TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()
    return db


def hash_hasla(haslo, sol=None):
    sol = sol or secrets.token_hex(16)
    wynik = hashlib.pbkdf2_hmac(
        "sha256", haslo.encode("utf-8"), bytes.fromhex(sol), 300_000
    ).hex()
    return f"{sol}${wynik}"


def sprawdz_haslo(haslo, zapis):
    try:
        sol, oczekiwany = zapis.split("$", 1)
        aktualny = hash_hasla(haslo, sol).split("$", 1)[1]
        return hmac.compare_digest(aktualny, oczekiwany)
    except (ValueError, TypeError):
        return False


def utworz_konto(login, haslo):
    login = login.strip()
    if len(login) < 3 or len(login) > 40:
        raise ValueError("Login musi mieć od 3 do 40 znaków.")
    if len(haslo) < 12:
        raise ValueError("Hasło musi mieć co najmniej 12 znaków.")

    db = polacz()
    try:
        db.execute(
            "INSERT INTO whitelist (login, haslo_hash) VALUES (?, ?)",
            (login, hash_hasla(haslo)),
        )
        db.commit()
    finally:
        db.close()


def lista_kont():
    db = polacz()
    try:
        return db.execute(
            "SELECT id, login, aktywne, utworzono FROM whitelist ORDER BY id"
        ).fetchall()
    finally:
        db.close()


def ustaw_aktywne(login, aktywne):
    db = polacz()
    try:
        wynik = db.execute(
            "UPDATE whitelist SET aktywne=? WHERE login=?",
            (1 if aktywne else 0, login.strip()),
        )
        db.commit()
        return wynik.rowcount > 0
    finally:
        db.close()


def usun_konto(login):
    db = polacz()
    try:
        wynik = db.execute(
            "DELETE FROM whitelist WHERE login=?", (login.strip(),)
        )
        db.commit()
        return wynik.rowcount > 0
    finally:
        db.close()


def uwierzytelnij(login, haslo):
    db = polacz()
    try:
        konto = db.execute(
            "SELECT haslo_hash, aktywne FROM whitelist WHERE login=?",
            (login.strip(),),
        ).fetchone()
        if not konto or not konto["aktywne"]:
            return False
        return sprawdz_haslo(haslo, konto["haslo_hash"])
    finally:
        db.close()


if __name__ == "__main__":
    print("Moduł whitelisty VZTM — zarządzanie kontami")
    print("Ten plik udostępnia funkcje do użycia w panelu administratora.")
    print("Nie tworzy automatycznie konta administratora.")
