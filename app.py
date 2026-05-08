from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "clave_secreta_123"

# ---- USUARIO Y CONTRASEÑA ----
USUARIO = "admin"
CONTRASENA = "admin123"

# ---- DECORADOR LOGIN ----

def login_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorador

# ---- RUTAS DE LOGIN ----

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario = request.form["usuario"]
        contrasena = request.form["contrasena"]
        if usuario == USUARIO and contrasena == CONTRASENA:
            session["usuario"] = usuario
            return redirect(url_for("index"))
        else:
            error = "Usuario o contraseña incorrectos"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))

# ---- BASE DE DATOS ----

def get_db():
    con = sqlite3.connect("facturas.db")
    con.row_factory = sqlite3.Row
    return con

def crear_tablas():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            cantidad INTEGER,
            precio_unitario REAL,
            subtotal REAL,
            iva REAL,
            descuento REAL,
            total REAL,
            fecha TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            ruc TEXT UNIQUE,
            telefono TEXT,
            email TEXT,
            direccion TEXT,
            fecha TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            descripcion TEXT,
            precio_compra REAL,
            precio_venta REAL,
            stock INTEGER,
            stock_minimo INTEGER,
            fecha TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cuentas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            concepto TEXT,
            monto REAL,
            fecha_emision TEXT,
            fecha_vencimiento TEXT,
            estado TEXT
        )
    """)
    con.commit()
    con.close()

# ---- RUTAS ----

@app.route("/")
@login_requerido
def index():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*), SUM(total) FROM facturas")
    facturas = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM clientes")
    clientes = cur.fetchone()
    cur.execute("SELECT COUNT(*), SUM(monto) FROM cuentas WHERE estado = 'PENDIENTE'")
    pendientes = cur.fetchone()
    cur.execute("SELECT * FROM facturas ORDER BY id DESC LIMIT 5")
    ultimas_facturas = cur.fetchall()
    con.close()
    return render_template("index.html",
        total_facturas=facturas[0] or 0,
        monto_total=facturas[1] or 0,
        total_clientes=clientes[0] or 0,
        cuentas_pendientes=pendientes[0] or 0,
        monto_pendiente=pendientes[1] or 0,
        ultimas_facturas=ultimas_facturas
    )

@app.route("/facturacion")
@login_requerido
def facturacion():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM facturas ORDER BY id DESC")
    facturas = cur.fetchall()
    con.close()
    return render_template("facturacion.html", facturas=facturas)

@app.route("/facturacion/nueva", methods=["POST"])
@login_requerido
def nueva_factura():
    producto = request.form["producto"]
    cantidad = int(request.form["cantidad"])
    precio = float(request.form["precio"])
    iva_pct = float(request.form["iva"]) / 100
    subtotal = cantidad * precio
    iva = subtotal * iva_pct
    total = subtotal + iva
    descuento = 0
    if total > 10000000:
        descuento = total * 0.05
        total = total - descuento
    fecha = datetime.now().strftime("%d/%m/%Y")
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO facturas (producto, cantidad, precio_unitario, subtotal, iva, descuento, total, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (producto, cantidad, precio, subtotal, iva, descuento, total, fecha))
    con.commit()
    con.close()
    return redirect(url_for("facturacion"))

@app.route("/facturacion/eliminar/<int:id>")
@login_requerido
def eliminar_factura(id):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM facturas WHERE id = ?", (id,))
    con.commit()
    con.close()
    return redirect(url_for("facturacion"))

@app.route("/clientes")
@login_requerido
def clientes():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM clientes ORDER BY id DESC")
    clientes = cur.fetchall()
    con.close()
    return render_template("clientes.html", clientes=clientes)

@app.route("/clientes/nuevo", methods=["POST"])
@login_requerido
def nuevo_cliente():
    nombre = request.form["nombre"]
    ruc = request.form["ruc"]
    telefono = request.form["telefono"]
    email = request.form["email"]
    direccion = request.form["direccion"]
    fecha = datetime.now().strftime("%d/%m/%Y")
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute("""
            INSERT INTO clientes (nombre, ruc, telefono, email, direccion, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nombre, ruc, telefono, email, direccion, fecha))
        con.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        con.close()
    return redirect(url_for("clientes"))

@app.route("/clientes/eliminar/<int:id>")
@login_requerido
def eliminar_cliente(id):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM clientes WHERE id = ?", (id,))
    con.commit()
    con.close()
    return redirect(url_for("clientes"))

@app.route("/stock")
@login_requerido
def stock():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM productos ORDER BY id DESC")
    productos = cur.fetchall()
    con.close()
    return render_template("stock.html", productos=productos)

@app.route("/stock/nuevo", methods=["POST"])
@login_requerido
def nuevo_producto():
    nombre = request.form["nombre"]
    descripcion = request.form["descripcion"]
    precio_compra = float(request.form["precio_compra"])
    precio_venta = float(request.form["precio_venta"])
    stock = int(request.form["stock"])
    stock_minimo = int(request.form["stock_minimo"])
    fecha = datetime.now().strftime("%d/%m/%Y")
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute("""
            INSERT INTO productos (nombre, descripcion, precio_compra, precio_venta, stock, stock_minimo, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nombre, descripcion, precio_compra, precio_venta, stock, stock_minimo, fecha))
        con.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        con.close()
    return redirect(url_for("stock"))

@app.route("/cuentas")
@login_requerido
def cuentas():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM cuentas ORDER BY estado, fecha_vencimiento")
    cuentas = cur.fetchall()
    con.close()
    return render_template("cuentas.html", cuentas=cuentas)

@app.route("/cuentas/nueva", methods=["POST"])
@login_requerido
def nueva_cuenta():
    cliente = request.form["cliente"]
    concepto = request.form["concepto"]
    monto = float(request.form["monto"])
    vencimiento = request.form["vencimiento"]
    fecha = datetime.now().strftime("%d/%m/%Y")
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO cuentas (cliente, concepto, monto, fecha_emision, fecha_vencimiento, estado)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (cliente, concepto, monto, fecha, vencimiento, "PENDIENTE"))
    con.commit()
    con.close()
    return redirect(url_for("cuentas"))

@app.route("/cuentas/pagar/<int:id>")
@login_requerido
def pagar_cuenta(id):
    con = get_db()
    cur = con.cursor()
    cur.execute("UPDATE cuentas SET estado = 'PAGADO' WHERE id = ?", (id,))
    con.commit()
    con.close()
    return redirect(url_for("cuentas"))

@app.route("/cuentas/eliminar/<int:id>")
@login_requerido
def eliminar_cuenta(id):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM cuentas WHERE id = ?", (id,))
    con.commit()
    con.close()
    return redirect(url_for("cuentas"))

if __name__ == "__main__":
    crear_tablas()
    app.run(debug=True)
    git add .
git commit -m "agregar login"
git push
