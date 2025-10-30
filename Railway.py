import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import random
from datetime import datetime
import traceback
import sys

# ---------- DATABASE SETUP ----------
try:
    conn = sqlite3.connect("railway.db")
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
except Exception:
    print("Failed to open DB:")
    traceback.print_exc()
    sys.exit(1)

# Users Table
cur.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)""")

# Trains Table
cur.execute("""CREATE TABLE IF NOT EXISTS trains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    source TEXT,
    destination TEXT,
    time TEXT,
    seats INTEGER
)""")

# Bookings Table
cur.execute("""CREATE TABLE IF NOT EXISTS bookings (
    pnr TEXT PRIMARY KEY,
    username TEXT,
    train_id INTEGER,
    date TEXT,
    status TEXT,
    FOREIGN KEY(train_id) REFERENCES trains(id)
)""")

# Add sample trains if DB empty
cur.execute("SELECT COUNT(*) FROM trains")
if cur.fetchone()[0] == 0:
    trains = [
        ("Shatabdi Express", "Kolkata", "Delhi", "06:00 AM", 50),
        ("Rajdhani Express", "Mumbai", "Delhi", "09:00 AM", 60),
        ("Duronto Express", "Kolkata", "Bangalore", "07:30 PM", 55),
        ("Intercity Express", "Chennai", "Hyderabad", "03:00 PM", 40),
        ("Garib Rath", "Patna", "Delhi", "11:45 PM", 70),
    ]
    cur.executemany("INSERT INTO trains (name, source, destination, time, seats) VALUES (?, ?, ?, ?, ?)", trains)
    conn.commit()

# ---------- FUNCTIONS ----------
def safe_execute(query, params=()):
    try:
        cur.execute(query, params)
        return cur
    except Exception:
        traceback.print_exc()
        messagebox.showerror("Database Error", "An error occurred. Check terminal for details.")
        return None

def login_user():
    user = username_entry.get().strip()
    pw = password_entry.get().strip()

    if not user or not pw:
        messagebox.showerror("Error", "Enter both username and password!")
        return

    try:
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pw))
        if cur.fetchone():
            messagebox.showinfo("Success", f"Welcome, {user}!")
            login_frame.pack_forget()
            dashboard(user)
        else:
            messagebox.showerror("Error", "Invalid credentials!")
    except Exception:
        traceback.print_exc()
        messagebox.showerror("Error", "Login failed. See terminal for details.")

def register_user():
    user = username_entry.get().strip()
    pw = password_entry.get().strip()

    if not user or not pw:
        messagebox.showerror("Error", "Enter both username and password!")
        return

    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user, pw))
        conn.commit()
        messagebox.showinfo("Success", "Account created successfully! Login now.")
        username_entry.delete(0, tk.END)
        password_entry.delete(0, tk.END)
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Username already exists!")
    except Exception:
        traceback.print_exc()
        messagebox.showerror("Error", "Registration failed. See terminal for details.")

# ---------- DASHBOARD ----------
def dashboard(user):
    dash = tk.Frame(root, bg="white")
    dash.pack(fill="both", expand=True)

    tk.Label(dash, text=f"Welcome, {user}", font=("Arial", 16, "bold"), bg="white").pack(pady=10)

    def view_trains():
        try:
            cur.execute("SELECT id, name, source, destination, time, seats FROM trains")
            trains = cur.fetchall()
        except Exception:
            traceback.print_exc()
            messagebox.showerror("Error", "Failed to load trains.")
            return

        train_window = tk.Toplevel(root)
        train_window.title("Available Trains")
        train_window.geometry("700x300")

        cols = ("Train ID", "Name", "Source", "Destination", "Time", "Seats")
        tree = ttk.Treeview(train_window, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=110, anchor="center")
        for t in trains:
            tree.insert("", "end", values=t)
        tree.pack(fill="both", expand=True)

    def book_ticket():
        def confirm_booking():
            train_id_raw = train_id_entry.get().strip()
            if not train_id_raw:
                messagebox.showerror("Error", "Enter a Train ID")
                return
            try:
                train_id = int(train_id_raw)
            except ValueError:
                messagebox.showerror("Error", "Train ID must be a number")
                return

            try:
                cur.execute("SELECT seats FROM trains WHERE id=?", (train_id,))
                result = cur.fetchone()
            except Exception:
                traceback.print_exc()
                messagebox.showerror("Error", "DB error while checking seats.")
                return

            if not result:
                messagebox.showerror("Error", "Invalid Train ID")
                return
            seats = result[0]
            if seats <= 0:
                messagebox.showerror("Error", "No seats available!")
                return

            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Generate unique PNR
            for _ in range(10):
                pnr = "PNR" + str(random.randint(10000, 99999))
                try:
                    cur.execute("INSERT INTO bookings (pnr, username, train_id, date, status) VALUES (?, ?, ?, ?, ?)",
                                (pnr, user, train_id, date, "Confirmed"))
                    cur.execute("UPDATE trains SET seats=seats-1 WHERE id=?", (train_id,))
                    conn.commit()
                    messagebox.showinfo("Booked", f"Ticket Booked!\nYour PNR: {pnr}")
                    book_win.destroy()
                    return
                except sqlite3.IntegrityError:
                    # PNR collision, try again
                    continue
                except Exception:
                    traceback.print_exc()
                    messagebox.showerror("Error", "Booking failed. See terminal for details.")
                    return

            messagebox.showerror("Error", "Could not generate unique PNR. Try again.")

        book_win = tk.Toplevel(root)
        book_win.title("Book Ticket")
        book_win.geometry("350x200")

        tk.Label(book_win, text="Enter Train ID:", font=("Arial", 12)).pack(pady=10)
        train_id_entry = tk.Entry(book_win)
        train_id_entry.pack(pady=5)
        tk.Button(book_win, text="Confirm Booking", command=confirm_booking).pack(pady=10)

    def check_pnr():
        def search_pnr():
            pnr = pnr_entry.get().strip()
            if not pnr:
                messagebox.showerror("Error", "Enter a PNR")
                return
            try:
                cur.execute("""SELECT b.pnr, t.name, t.source, t.destination, b.date, b.status 
                            FROM bookings b JOIN trains t ON b.train_id=t.id WHERE b.pnr=? AND b.username=?""",
                            (pnr, user))
                result = cur.fetchone()
            except Exception:
                traceback.print_exc()
                messagebox.showerror("Error", "DB error while searching PNR.")
                return

            if result:
                messagebox.showinfo("PNR Details", f"PNR: {result[0]}\nTrain: {result[1]}\nFrom: {result[2]}\nTo: {result[3]}\nDate: {result[4]}\nStatus: {result[5]}")
            else:
                messagebox.showerror("Error", "PNR not found or not yours!")

        pnr_win = tk.Toplevel(root)
        pnr_win.title("Check PNR Status")
        pnr_win.geometry("350x200")
        tk.Label(pnr_win, text="Enter PNR:", font=("Arial", 12)).pack(pady=10)
        pnr_entry = tk.Entry(pnr_win)
        pnr_entry.pack(pady=5)
        tk.Button(pnr_win, text="Search", command=search_pnr).pack(pady=10)

    def cancel_ticket():
        def confirm_cancel():
            pnr = cancel_entry.get().strip()
            if not pnr:
                messagebox.showerror("Error", "Enter a PNR")
                return
            try:
                cur.execute("SELECT train_id FROM bookings WHERE pnr=? AND username=? AND status='Confirmed'", (pnr, user))
                result = cur.fetchone()
            except Exception:
                traceback.print_exc()
                messagebox.showerror("Error", "DB error while checking booking.")
                return

            if not result:
                messagebox.showerror("Error", "PNR not found or already canceled!")
                return
            train_id = result[0]
            try:
                cur.execute("UPDATE bookings SET status='Cancelled' WHERE pnr=?", (pnr,))
                cur.execute("UPDATE trains SET seats=seats+1 WHERE id=?", (train_id,))
                conn.commit()
                messagebox.showinfo("Cancelled", "Ticket Cancelled Successfully!")
                cancel_win.destroy()
            except Exception:
                traceback.print_exc()
                messagebox.showerror("Error", "Cancellation failed. See terminal for details.")

        cancel_win = tk.Toplevel(root)
        cancel_win.title("Cancel Ticket")
        cancel_win.geometry("350x200")
        tk.Label(cancel_win, text="Enter PNR:", font=("Arial", 12)).pack(pady=10)
        cancel_entry = tk.Entry(cancel_win)
        cancel_entry.pack(pady=5)
        tk.Button(cancel_win, text="Confirm Cancel", command=confirm_cancel).pack(pady=10)

    def logout():
        dash.destroy()
        login_page()

    ttk.Button(dash, text="🚄 View Trains", command=view_trains).pack(pady=10)
    ttk.Button(dash, text="🎟️ Book Ticket", command=book_ticket).pack(pady=10)
    ttk.Button(dash, text="🔍 Check PNR Status", command=check_pnr).pack(pady=10)
    ttk.Button(dash, text="❌ Cancel Ticket", command=cancel_ticket).pack(pady=10)
    ttk.Button(dash, text="🚪 Logout", command=logout).pack(pady=10)


# ---------- LOGIN PAGE ----------
def login_page():
    global username_entry, password_entry, login_frame
    login_frame = tk.Frame(root, bg="white")
    login_frame.pack(fill="both", expand=True)

    tk.Label(login_frame, text="Railway Reservation System", font=("Arial", 18, "bold"), bg="white", fg="darkblue").pack(pady=20)
    tk.Label(login_frame, text="Username:", bg="white").pack()
    username_entry = tk.Entry(login_frame)
    username_entry.pack(pady=5)

    tk.Label(login_frame, text="Password:", bg="white").pack()
    password_entry = tk.Entry(login_frame, show="*")
    password_entry.pack(pady=5)

    ttk.Button(login_frame, text="Login", command=login_user).pack(pady=10)
    ttk.Button(login_frame, text="Register", command=register_user).pack(pady=5)


# ---------- MAIN ----------
def on_closing():
    try:
        conn.close()
    except Exception:
        pass
    root.destroy()

root = tk.Tk()
root.title("Railway Reservation System")
root.geometry("420x460")
root.configure(bg="white")
root.protocol("WM_DELETE_WINDOW", on_closing)

login_page()
try:
    root.mainloop()
except Exception:
    print("Unhandled exception in GUI:")
    traceback.print_exc()
    on_closing()