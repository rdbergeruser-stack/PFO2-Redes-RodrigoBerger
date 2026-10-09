import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# CONFIGURACIÓN DEL SERVIDOR
# ==============================================================================
# Institución: IFTS N.° 29
# Materia: Programación sobre redes - 3.° D
# Alumno: Rodrigo Berger
# Proyecto: PFO 2 - Sistema de Usuarios con API REST y SQLite
HOST = "localhost"
PORT = 5000
DB_NAME = "usuarios.db"

app = Flask(__name__)

# Habilitar CORS para permitir peticiones desde index.html (local o GitHub Pages)
@app.after_request
def habilitar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Usuario, X-Contrasena, X-Password"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/registro", methods=["OPTIONS"])
@app.route("/login", methods=["OPTIONS"])
@app.route("/usuarios", methods=["OPTIONS"])
def cors_preflight():
    return "", 204

# ==============================================================================
# 1. BASE DE DATOS SQLITE
# ==============================================================================
def get_db():
    """Retorna una conexión a SQLite con soporte de acceso por nombre de columna."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db():
    """Crea la tabla 'usuarios' e inserta un usuario de prueba si está vacía."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            contrasena_hash TEXT NOT NULL,
            fecha_registro TEXT NOT NULL
        )
    """)
    conn.commit()

    # Usuarios de prueba iniciales para facilitar pruebas inmediatas
    cursor.execute("SELECT COUNT(*) as total FROM usuarios")
    if cursor.fetchone()["total"] == 0:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for u in ["Rodrigo", "Berger"]:
            cursor.execute(
                "INSERT INTO usuarios (usuario, contrasena_hash, fecha_registro) VALUES (?, ?, ?)",
                (u, generate_password_hash("1234"), fecha)
            )
        conn.commit()
        print("[DB] Creados usuarios de prueba iniciales: 'Rodrigo' y 'Berger' (clave: '1234')")

    conn.close()
    print(f"[DB] Base de datos '{DB_NAME}' inicializada correctamente.")

# ==============================================================================
# 2. HELPER DE AUTENTICACIÓN
# ==============================================================================
def autenticar_usuario(req):
    """
    Verifica credenciales mediante cabeceras HTTP ('X-Usuario' y 'X-Contrasena' o Basic Auth).
    Retorna: (usuario_row, dict_error, status_code)
    """
    usuario = None
    contrasena = None

    # Opción A: HTTP Basic Auth
    auth = req.authorization
    if auth and auth.username and auth.password:
        usuario = auth.username.strip()
        contrasena = auth.password
    else:
        # Opción B: Headers personalizados
        header_user = req.headers.get("X-Usuario")
        header_pass = req.headers.get("X-Contrasena") or req.headers.get("X-Password")
        if header_user and header_pass:
            usuario = header_user.strip()
            contrasena = header_pass

    if not usuario or not contrasena:
        return None, {
            "status": "error",
            "mensaje": "Acceso no autorizado. Debe iniciar sesión primero."
        }, 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,))
    user = cursor.fetchone()
    conn.close()

    if not user or not check_password_hash(user["contrasena_hash"], contrasena):
        return None, {
            "status": "error",
            "mensaje": "Credenciales inválidas. Sesión no autorizada."
        }, 401

    return user, None, 200

# ==============================================================================
# 3. ENDPOINTS DE LA API REST
# ==============================================================================

@app.route("/", methods=["GET"])
def index():
    """Sirve la página web index.html si se accede desde el navegador."""
    if os.path.exists("index.html"):
        return send_file("index.html")
    return jsonify({
        "status": "success",
        "mensaje": "API de Gestión de Usuarios en funcionamiento.",
        "endpoints": ["POST /registro", "POST /login", "GET /usuarios"]
    }), 200

# ------------------------------------------------------------------------------
# 3.1 REGISTRO DE USUARIOS: POST /registro
# ------------------------------------------------------------------------------
@app.route("/registro", methods=["POST"])
def registrar_usuario():
    """
    Crea un usuario nuevo almacenando su contraseña con hash seguro.
    Body JSON: {"usuario": "...", "contraseña": "..."}
    """
    data = request.get_json(silent=True) or {}
    usuario = data.get("usuario")
    contrasena = data.get("contraseña") or data.get("contrasena")

    if not usuario or not str(usuario).strip():
        return jsonify({"status": "error", "mensaje": "El campo 'usuario' es obligatorio."}), 400

    if not contrasena or not str(contrasena).strip():
        return jsonify({"status": "error", "mensaje": "El campo 'contraseña' es obligatorio."}), 400

    usuario = str(usuario).strip()
    contrasena = str(contrasena).strip()

    # Generación de hash criptográfico seguro con salt
    hash_clave = generate_password_hash(contrasena)
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (usuario, contrasena_hash, fecha_registro) VALUES (?, ?, ?)",
            (usuario, hash_clave, fecha_actual)
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
        conn.close()

        print(f"[REGISTRO] Usuario registrado: '{usuario}' (ID: {nuevo_id}) con hash criptográfico.")
        return jsonify({
            "status": "success",
            "mensaje": f"Usuario '{usuario}' registrado exitosamente.",
            "usuario": {
                "id": nuevo_id,
                "usuario": usuario,
                "fecha_registro": fecha_actual
            }
        }), 201

    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({
            "status": "error",
            "mensaje": f"El nombre de usuario '{usuario}' ya está registrado."
        }), 409
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "mensaje": f"Error interno: {str(e)}"}), 500

# ------------------------------------------------------------------------------
# 3.2 INICIO DE SESIÓN: POST /login
# ------------------------------------------------------------------------------
@app.route("/login", methods=["POST"])
def iniciar_sesion():
    """
    Verifica las credenciales del usuario comparando contra el hash en SQLite.
    Body JSON: {"usuario": "...", "contraseña": "..."}
    """
    data = request.get_json(silent=True) or {}
    usuario = data.get("usuario")
    contrasena = data.get("contraseña") or data.get("contrasena")

    if not usuario or not contrasena:
        return jsonify({"status": "error", "mensaje": "Debe enviar 'usuario' y 'contraseña'."}), 400

    usuario = str(usuario).strip()
    contrasena = str(contrasena).strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,))
    user = cursor.fetchone()
    conn.close()

    if not user or not check_password_hash(user["contrasena_hash"], contrasena):
        print(f"[LOGIN FALLIDO] Intento erróneo para usuario: '{usuario}'")
        return jsonify({
            "status": "error",
            "mensaje": "Credenciales inválidas. Usuario o contraseña incorrectos."
        }), 401

    print(f"[LOGIN EXITOSO] Sesión iniciada: '{usuario}' (ID: {user['id']})")
    return jsonify({
        "status": "success",
        "mensaje": f"Inicio de sesión exitoso. ¡Bienvenido/a {usuario}!",
        "usuario": {
            "id": user["id"],
            "usuario": user["usuario"],
            "fecha_registro": user["fecha_registro"]
        }
    }), 200

# ------------------------------------------------------------------------------
# 3.3 LISTADO DE USUARIOS: GET /usuarios (RETIENE SESIÓN INICIADA)
# ------------------------------------------------------------------------------
@app.route("/usuarios", methods=["GET"])
def listar_usuarios():
    """
    Retorna el listado de usuarios registrados.
    Requiere que el usuario esté autenticado.
    No expone las contraseñas ni los hashes por seguridad.
    """
    usuario_autenticado, err, status_code = autenticar_usuario(request)
    if err:
        return jsonify(err), status_code

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, usuario, fecha_registro FROM usuarios ORDER BY id ASC")
    filas = cursor.fetchall()
    conn.close()

    lista = [dict(fila) for fila in filas]
    print(f"[LISTADO] '{usuario_autenticado['usuario']}' consultó la lista ({len(lista)} usuarios).")

    return jsonify({
        "status": "success",
        "solicitado_por": usuario_autenticado["usuario"],
        "total_usuarios": len(lista),
        "usuarios": lista
    }), 200

# ==============================================================================
# 4. EJECUCIÓN
# ==============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("   SERVIDOR API REST - SISTEMA DE GESTIÓN DE USUARIOS")
    print("   IFTS N.° 29 | Prog. sobre redes - 3.° D | Rodrigo Berger")
    print("=" * 60)
    inicializar_db()
    print(f"[SERVIDOR] Corriendo en http://{HOST}:{PORT}")
    print(f"  • POST http://{HOST}:{PORT}/registro")
    print(f"  • POST http://{HOST}:{PORT}/login")
    print(f"  • GET  http://{HOST}:{PORT}/usuarios (Protegido)")
    print("=" * 60)
    app.run(host=HOST, port=PORT, debug=False)
