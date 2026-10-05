import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# CONFIGURACIÓN GENERAL DEL SERVIDOR
# ==============================================================================
# Materia: Programación sobre redes - 3.° D
# Alumno: Rodrigo Berger
# Proyecto: PFO 2 - Sistema de Gestión de Tareas con API y Base de Datos
HOST = "localhost"
PORT = 5000
DB_NAME = "tareas_db.sqlite"

app = Flask(__name__)
app.config["SECRET_KEY"] = "pfo2_redes_berger_rodrigo_2026"

# ==============================================================================
# 1. FUNCIÓN: INICIALIZAR BASE DE DATOS SQLITE
# ==============================================================================
def inicializar_db():
    """
    Crea la base de datos SQLite y las tablas 'usuarios' y 'tareas' si no existen.
    Garantiza la persistencia relacional requerida por la consigna.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Tabla de usuarios: contraseña hasheada (¡nunca en texto plano!)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                contrasena_hash TEXT NOT NULL,
                fecha_registro TEXT NOT NULL
            )
        ''')

        # Tabla de tareas: vinculadas a cada usuario registrado
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tareas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                descripcion TEXT,
                estado TEXT DEFAULT 'pendiente',
                fecha_creacion TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        conn.close()
        print("[DB] Base de datos e inicialización de tablas completada con éxito.")
    except sqlite3.Error as e:
        print(f"[ERROR DB] Error al inicializar la base de datos: {e}")
        raise SystemExit(1)

def get_db():
    """Retorna una conexión a SQLite configurada con Row factory."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ==============================================================================
# 2. HELPER DE AUTENTICACIÓN
# ==============================================================================
def autenticar_usuario(req):
    """
    Valida credenciales recibidas mediante:
    - Cabeceras HTTP ('X-Usuario' y 'X-Contrasena' o HTTP Basic Auth)
    - O parámetros JSON / Query string
    Retorna: (usuario_row, dict_error, status_code)
    """
    usuario = None
    contrasena = None

    # 1. HTTP Basic Auth
    auth = req.authorization
    if auth and auth.username and auth.password:
        usuario = auth.username.strip()
        contrasena = auth.password
    else:
        # 2. Headers personalizados
        header_user = req.headers.get("X-Usuario")
        header_pass = req.headers.get("X-Contrasena") or req.headers.get("X-Password")
        if header_user and header_pass:
            usuario = header_user.strip()
            contrasena = header_pass
        elif req.is_json:
            # 3. Cuerpo JSON
            data = req.get_json(silent=True) or {}
            usuario = data.get("usuario")
            contrasena = data.get("contraseña") or data.get("contrasena")

    if not usuario or not contrasena:
        return None, {"status": "error", "mensaje": "Credenciales no provistas (usuario y contraseña requeridos)."}, 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,))
    user = cursor.fetchone()
    conn.close()

    if not user or not check_password_hash(user["contrasena_hash"], contrasena):
        return None, {"status": "error", "mensaje": "Usuario o contraseña incorrectos."}, 401

    return user, None, 200

# ==============================================================================
# 3. ENDPOINTS DE LA API REST
# ==============================================================================

# ------------------------------------------------------------------------------
# 3.1 REGISTRO DE USUARIOS: POST /registro
# ------------------------------------------------------------------------------
@app.route("/registro", methods=["POST"])
def registrar_usuario():
    """
    Endpoint: POST /registro
    Consigna:
    - Recibe {"usuario": "nombre", "contraseña": "1234"}.
    - Almacenar usuarios en SQLite con contraseñas hasheadas (¡nunca en texto plano!).
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "status": "error",
            "mensaje": "Cuerpo de solicitud inválido. Debe enviar un JSON con 'usuario' y 'contraseña'."
        }), 400

    usuario = data.get("usuario")
    contrasena = data.get("contraseña") or data.get("contrasena")

    if not usuario or not str(usuario).strip():
        return jsonify({"status": "error", "mensaje": "El campo 'usuario' es obligatorio."}), 400

    if not contrasena or not str(contrasena).strip():
        return jsonify({"status": "error", "mensaje": "El campo 'contraseña' es obligatorio."}), 400

    usuario = str(usuario).strip()
    contrasena = str(contrasena).strip()

    # Hasheo criptográfico con salt aleatorio (PBKDF2/scrypt de Werkzeug)
    contrasena_hasheada = generate_password_hash(contrasena)
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (usuario, contrasena_hash, fecha_registro) VALUES (?, ?, ?)",
            (usuario, contrasena_hasheada, fecha_actual)
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
        conn.close()

        print(f"[REGISTRO] Usuario creado: '{usuario}' (ID: {nuevo_id}) | Clave protegida con hash.")
        return jsonify({
            "status": "success",
            "mensaje": "Usuario registrado exitosamente.",
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
            "mensaje": f"El nombre de usuario '{usuario}' ya se encuentra registrado."
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
    Endpoint: POST /login
    Consigna:
    - Verifica credenciales y permite acceso a las tareas.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "status": "error",
            "mensaje": "Cuerpo de solicitud inválido. Debe enviar un JSON con 'usuario' y 'contraseña'."
        }), 400

    usuario = data.get("usuario")
    contrasena = data.get("contraseña") or data.get("contrasena")

    if not usuario or not contrasena:
        return jsonify({"status": "error", "mensaje": "Debe ingresar 'usuario' y 'contraseña'."}), 400

    usuario = str(usuario).strip()
    contrasena = str(contrasena).strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,))
    user = cursor.fetchone()
    conn.close()

    if not user or not check_password_hash(user["contrasena_hash"], contrasena):
        print(f"[LOGIN FALLIDO] Credenciales incorrectas para: '{usuario}'")
        return jsonify({
            "status": "error",
            "mensaje": "Credenciales inválidas. Usuario o contraseña incorrectos."
        }), 401

    print(f"[LOGIN EXITOSO] Acceso concedido al usuario: '{usuario}' (ID: {user['id']})")
    return jsonify({
        "status": "success",
        "mensaje": f"Bienvenido/a {usuario}, inicio de sesión exitoso.",
        "usuario": {
            "id": user["id"],
            "usuario": user["usuario"]
        },
        "acceso_tareas": True,
        "instruccion": "Acceso a tareas concedido. Puede consultar GET /tareas para ver el mensaje de bienvenida."
    }), 200

# ------------------------------------------------------------------------------
# 3.3 GESTIÓN DE TAREAS: GET /tareas (HTML DE BIENVENIDA)
# ------------------------------------------------------------------------------
PLANTILLA_BIENVENIDA = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bienvenida - Sistema de Gestión de Tareas</title>
    <style>
        :root {
            --bg: #0f172a;
            --card: #1e293b;
            --primary: #2563eb;
            --text: #f8fafc;
            --muted: #94a3b8;
            --accent: #10b981;
            --border: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, sans-serif; }
        body {
            background-color: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            max-width: 750px;
            width: 100%;
            padding: 35px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.4);
        }
        .badge {
            background: rgba(37, 99, 235, 0.2);
            color: #60a5fa;
            border: 1px solid rgba(37, 99, 235, 0.4);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 12px;
        }
        h1 { font-size: 2rem; margin-bottom: 8px; }
        .sub { color: var(--muted); margin-bottom: 24px; }
        .welcome {
            background: rgba(16, 185, 129, 0.1);
            border-left: 4px solid var(--accent);
            padding: 18px;
            border-radius: 6px;
            margin-bottom: 25px;
        }
        .welcome h2 { color: #34d399; font-size: 1.25rem; margin-bottom: 6px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        .box {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border);
            padding: 15px;
            border-radius: 8px;
        }
        .box span { font-size: 0.8rem; color: var(--muted); text-transform: uppercase; }
        .box p { font-size: 1.05rem; font-weight: bold; margin-top: 4px; }
        .endpoints {
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid var(--border);
            padding: 18px;
            border-radius: 8px;
            font-size: 0.9rem;
        }
        .endpoints h3 { margin-bottom: 10px; font-size: 1rem; color: #cbd5e1; }
        .endpoint-row { padding: 6px 0; border-bottom: 1px dashed var(--border); display: flex; gap: 10px; }
        .endpoint-row:last-child { border-bottom: none; }
        .method { font-weight: bold; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; }
        .post { background: #166534; color: #bbf7d0; }
        .get { background: #1e40af; color: #bfdbfe; }
        footer { margin-top: 25px; text-align: center; color: var(--muted); font-size: 0.85rem; }
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">Programación sobre Redes - 3.° D</span>
        <h1>Sistema de Gestión de Tareas</h1>
        <p class="sub">PFO 2 | API REST Flask con Base de Datos SQLite</p>

        <div class="welcome">
            <h2>👋 ¡Bienvenido/a al Sistema de Gestión de Tareas!</h2>
            <p>La API REST y la Base de Datos SQLite se encuentran operativas. Has accedido exitosamente al endpoint <strong>GET /tareas</strong>.</p>
        </div>

        <div class="grid">
            <div class="box">
                <span>Alumno</span>
                <p>Rodrigo Berger</p>
            </div>
            <div class="box">
                <span>Base de Datos</span>
                <p>SQLite (tareas_db.sqlite)</p>
            </div>
            <div class="box">
                <span>Seguridad</span>
                <p>Hash scrypt / PBKDF2</p>
            </div>
            <div class="box">
                <span>Estado API</span>
                <p style="color: #34d399;">● Online (200 OK)</p>
            </div>
        </div>

        <div class="endpoints">
            <h3>Endpoints Disponibles:</h3>
            <div class="endpoint-row"><span class="method post">POST</span> <code>/registro</code>: Alta de usuario con clave hasheada.</div>
            <div class="endpoint-row"><span class="method post">POST</span> <code>/login</code>: Validación de credenciales y acceso a tareas.</div>
            <div class="endpoint-row"><span class="method get">GET</span> <code>/tareas</code>: HTML de bienvenida.</div>
            <div class="endpoint-row"><span class="method get">GET</span> <code>/api/tareas</code>: Listado de tareas (JSON).</div>
            <div class="endpoint-row"><span class="method post">POST</span> <code>/api/tareas</code>: Creación de nueva tarea (JSON).</div>
        </div>

        <footer>
            <p>Desarrollado para Programación sobre Redes &copy; 2026 - Rodrigo Berger</p>
        </footer>
    </div>
</body>
</html>
"""

@app.route("/tareas", methods=["GET"])
def ver_tareas_bienvenida():
    """
    Endpoint: GET /tareas
    Consigna:
    - "GET /tareas: Muestre un html de bienvenida"
    """
    if request.headers.get("Accept") == "application/json" or request.args.get("format") == "json":
        return jsonify({
            "status": "success",
            "mensaje": "¡Bienvenido/a al Sistema de Gestión de Tareas!",
            "alumno": "Rodrigo Berger",
            "base_datos": "SQLite (tareas_db.sqlite)"
        }), 200

    return render_template_string(PLANTILLA_BIENVENIDA), 200

# ------------------------------------------------------------------------------
# 3.4 GESTIÓN DE TAREAS: ENDPOINTS REST COMPLEMENTARIOS
# ------------------------------------------------------------------------------
@app.route("/api/tareas", methods=["GET"])
def api_listar_tareas():
    """Endpoint: GET /api/tareas - Lista tareas del usuario autenticado."""
    user, err, status = autenticar_usuario(request)
    if err:
        return jsonify(err), status

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, titulo, descripcion, estado, fecha_creacion FROM tareas WHERE usuario_id = ? ORDER BY id DESC",
        (user["id"],)
    )
    filas = cursor.fetchall()
    conn.close()

    tareas = [dict(f) for f in filas]
    return jsonify({
        "status": "success",
        "usuario": user["usuario"],
        "total_tareas": len(tareas),
        "tareas": tareas
    }), 200

@app.route("/api/tareas", methods=["POST"])
def api_crear_tarea():
    """Endpoint: POST /api/tareas - Crea una nueva tarea para el usuario autenticado."""
    user, err, status = autenticar_usuario(request)
    if err:
        return jsonify(err), status

    data = request.get_json(silent=True) or {}
    titulo = data.get("titulo")
    descripcion = data.get("descripcion", "")

    if not titulo or not str(titulo).strip():
        return jsonify({"status": "error", "mensaje": "El campo 'titulo' es obligatorio."}), 400

    titulo = str(titulo).strip()
    descripcion = str(descripcion).strip()
    fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tareas (usuario_id, titulo, descripcion, estado, fecha_creacion) VALUES (?, ?, ?, 'pendiente', ?)",
        (user["id"], titulo, descripcion, fecha_creacion)
    )
    conn.commit()
    tarea_id = cursor.lastrowid
    conn.close()

    print(f"[TAREA CREADA] ID: {tarea_id} | Título: '{titulo}' | Usuario: '{user['usuario']}'")
    return jsonify({
        "status": "success",
        "mensaje": "Tarea creada exitosamente.",
        "tarea": {
            "id": tarea_id,
            "titulo": titulo,
            "descripcion": descripcion,
            "estado": "pendiente",
            "fecha_creacion": fecha_creacion
        }
    }), 201

@app.route("/api/tareas/<int:tarea_id>", methods=["PUT"])
def api_actualizar_tarea(tarea_id):
    """Endpoint: PUT /api/tareas/<id> - Actualiza estado de una tarea."""
    user, err, status = autenticar_usuario(request)
    if err:
        return jsonify(err), status

    data = request.get_json(silent=True) or {}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tareas WHERE id = ? AND usuario_id = ?", (tarea_id, user["id"]))
    tarea = cursor.fetchone()

    if not tarea:
        conn.close()
        return jsonify({"status": "error", "mensaje": "Tarea no encontrada o no pertenece al usuario."}), 404

    nuevo_estado = data.get("estado", "completada")
    cursor.execute("UPDATE tareas SET estado = ? WHERE id = ?", (nuevo_estado, tarea_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "mensaje": f"Tarea {tarea_id} actualizada a estado: {nuevo_estado}"}), 200

@app.route("/api/tareas/<int:tarea_id>", methods=["DELETE"])
def api_eliminar_tarea(tarea_id):
    """Endpoint: DELETE /api/tareas/<id> - Elimina una tarea."""
    user, err, status = autenticar_usuario(request)
    if err:
        return jsonify(err), status

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tareas WHERE id = ? AND usuario_id = ?", (tarea_id, user["id"]))
    tarea = cursor.fetchone()

    if not tarea:
        conn.close()
        return jsonify({"status": "error", "mensaje": "Tarea no encontrada o no pertenece al usuario."}), 404

    cursor.execute("DELETE FROM tareas WHERE id = ?", (tarea_id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "mensaje": f"Tarea {tarea_id} eliminada correctamente."}), 200

# ==============================================================================
# 4. INICIALIZACIÓN Y ARRANQUE DEL SERVIDOR
# ==============================================================================
def iniciar_servidor():
    print("=" * 65)
    print("   SERVIDOR API REST FLASK - SISTEMA DE GESTIÓN DE TAREAS")
    print("   Materia: Programación sobre redes - 3.° D | Alumno: Rodrigo Berger")
    print("=" * 65)
    inicializar_db()
    print(f"[SERVIDOR] Escuchando en http://{HOST}:{PORT}...")
    print(f"  • POST http://{HOST}:{PORT}/registro")
    print(f"  • POST http://{HOST}:{PORT}/login")
    print(f"  • GET  http://{HOST}:{PORT}/tareas (HTML de Bienvenida)")
    print("=" * 65)
    app.run(host=HOST, port=PORT, debug=False)

if __name__ == "__main__":
    iniciar_servidor()
