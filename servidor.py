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

# Soporte de CORS para que el cliente web (local o GitHub Pages) se comunique sin bloqueos
@app.after_request
def habilitar_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Usuario, X-Contrasena, X-Password"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

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

# Manejo de peticiones OPTIONS para CORS pre-flight
@app.route("/registro", methods=["OPTIONS"])
@app.route("/login", methods=["OPTIONS"])
@app.route("/api/tareas", methods=["OPTIONS"])
@app.route("/api/tareas/<int:tarea_id>", methods=["OPTIONS"])
def preflight_cors(*args, **kwargs):
    return "", 204

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
# 3.3 GESTIÓN DE TAREAS: GET /tareas (HTML DE BIENVENIDA + CLIENTE WEB INTERACTIVO)
# ------------------------------------------------------------------------------
PLANTILLA_BIENVENIDA = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Gestión de Tareas - Cliente Web & API</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0a0f1d;
            --bg-card: #131b2e;
            --bg-card-hover: #18223b;
            --border: #23304d;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --secondary: #10b981;
            --danger: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --code-bg: #0b1120;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            padding: 30px 15px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container { max-width: 900px; width: 100%; }
        
        .header {
            text-align: center;
            margin-bottom: 25px;
        }
        .badge {
            background: rgba(59, 130, 246, 0.15);
            border: 1px solid rgba(59, 130, 246, 0.4);
            color: #60a5fa;
            font-size: 0.85rem;
            font-weight: 600;
            padding: 5px 14px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 12px;
        }
        h1 { font-size: 2.2rem; font-weight: 800; margin-bottom: 6px; }
        .sub { color: var(--text-muted); font-size: 1rem; }

        .welcome-card {
            background: rgba(16, 185, 129, 0.1);
            border-left: 4px solid var(--secondary);
            padding: 18px 22px;
            border-radius: 8px;
            margin-bottom: 25px;
        }
        .welcome-card h2 { color: #34d399; font-size: 1.25rem; margin-bottom: 4px; }
        .welcome-card p { color: #cbd5e1; font-size: 0.95rem; }

        .grid-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        .info-box {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 15px;
        }
        .info-box span { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }
        .info-box p { font-size: 1.1rem; font-weight: 700; margin-top: 4px; }

        /* Panels */
        .panel {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 25px;
        }
        .panel h3 { font-size: 1.2rem; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
        
        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr auto;
            gap: 12px;
            align-items: end;
        }
        @media (max-width: 650px) {
            .form-grid { grid-template-columns: 1fr; }
        }
        .form-group { display: flex; flex-direction: column; gap: 6px; }
        label { font-size: 0.85rem; color: var(--text-muted); font-weight: 500; }
        input {
            background: var(--bg-dark);
            border: 1px solid var(--border);
            color: #fff;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }
        input:focus { border-color: var(--primary); }
        button {
            background: var(--primary);
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: background 0.2s;
            height: 42px;
        }
        button:hover { background: var(--primary-hover); }
        button.btn-secondary { background: #334155; }
        button.btn-secondary:hover { background: #475569; }
        button.btn-success { background: #059669; }
        button.btn-success:hover { background: #10b981; }
        button.btn-danger { background: #dc2626; padding: 6px 12px; height: auto; font-size: 0.8rem; }
        button.btn-danger:hover { background: #ef4444; }

        .auth-status {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* Task Cards */
        .task-list { display: flex; flex-direction: column; gap: 10px; margin-top: 15px; }
        .task-item {
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 15px;
        }
        .task-info h4 { font-size: 1rem; color: #fff; margin-bottom: 3px; }
        .task-info p { font-size: 0.85rem; color: var(--text-muted); }
        .task-status-badge {
            font-size: 0.75rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .st-pendiente { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
        .st-completada { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
        .task-actions { display: flex; gap: 8px; align-items: center; }

        /* Log console */
        .log-box {
            background: var(--code-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px;
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
            color: #38bdf8;
            max-height: 160px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        footer { margin-top: 30px; text-align: center; color: var(--text-muted); font-size: 0.85rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="badge">Programación sobre Redes - 3.° D</span>
            <h1>Sistema de Gestión de Tareas</h1>
            <p class="sub">PFO 2 | Cliente Web Interactivo & API REST Flask con SQLite</p>
        </div>

        <div class="welcome-card">
            <h2>👋 ¡Bienvenido/a al Sistema de Gestión de Tareas!</h2>
            <p>Has accedido al endpoint <strong>GET /tareas</strong>. Desde este panel web puedes interactuar en vivo con la API REST y la base de datos SQLite.</p>
        </div>

        <div class="grid-info">
            <div class="info-box">
                <span>Alumno</span>
                <p>Rodrigo Berger</p>
            </div>
            <div class="info-box">
                <span>Base de Datos</span>
                <p>SQLite (Persistente)</p>
            </div>
            <div class="info-box">
                <span>Seguridad</span>
                <p>Hash scrypt / PBKDF2</p>
            </div>
            <div class="info-box">
                <span>Estado API</span>
                <p style="color: #34d399;">● Online (200 OK)</p>
            </div>
        </div>

        <!-- Barra de Estado de Sesión -->
        <div class="auth-status">
            <div>
                <span style="color: var(--text-muted); font-size: 0.85rem;">Usuario activo:</span>
                <strong id="user-display" style="color: #60a5fa; margin-left: 6px;">[No autenticado]</strong>
            </div>
            <div id="logout-container" style="display: none;">
                <button onclick="cerrarSesion()" class="btn-secondary" style="height: 32px; padding: 4px 12px; font-size: 0.8rem;">Cerrar Sesión</button>
            </div>
        </div>

        <!-- Panel 1: Registro & Login -->
        <div class="panel" id="auth-panel">
            <h3>🔐 Autenticación de Usuario</h3>
            <div class="form-grid">
                <div class="form-group">
                    <label>Usuario</label>
                    <input type="text" id="auth-user" placeholder="Ej: nombre" value="nombre">
                </div>
                <div class="form-group">
                    <label>Contraseña</label>
                    <input type="password" id="auth-pass" placeholder="Ej: 1234" value="1234">
                </div>
                <div style="display: flex; gap: 8px;">
                    <button onclick="ejecutarLogin()">Iniciar Sesión</button>
                    <button onclick="ejecutarRegistro()" class="btn-secondary">Registrarse</button>
                </div>
            </div>
        </div>

        <!-- Panel 2: Gestión de Tareas (Desbloqueado tras login) -->
        <div class="panel" id="tasks-panel">
            <h3>📋 Gestión de Tareas (CRUD en SQLite)</h3>
            
            <div id="tasks-locked-msg" style="color: var(--text-muted); font-size: 0.95rem;">
                Inicia sesión en el formulario superior para crear y consultar tus tareas en tiempo real.
            </div>

            <div id="tasks-content" style="display: none;">
                <!-- Crear Tarea -->
                <div class="form-grid" style="margin-bottom: 20px;">
                    <div class="form-group">
                        <label>Título de la Tarea</label>
                        <input type="text" id="task-title" placeholder="Ej: Estudiar para el examen de Redes">
                    </div>
                    <div class="form-group">
                        <label>Descripción (Opcional)</label>
                        <input type="text" id="task-desc" placeholder="Ej: Repasar sockets, HTTP y REST">
                    </div>
                    <button onclick="crearTarea()" class="btn-success">+ Crear Tarea</button>
                </div>

                <!-- Lista de Tareas -->
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="font-size: 0.95rem; color: #cbd5e1;">Tus Tareas Registradas:</h4>
                    <button onclick="cargarTareas()" class="btn-secondary" style="height: 30px; padding: 4px 10px; font-size: 0.8rem;">↻ Refrescar</button>
                </div>
                <div id="task-list-container" class="task-list">
                    <!-- Se rellena con JS -->
                </div>
            </div>
        </div>

        <!-- Registro de Eventos HTTP (Consola) -->
        <div class="panel">
            <h3>📡 Registro de Peticiones HTTP en Vivo</h3>
            <div id="http-log" class="log-box">[SISTEMA] Cliente web listo. Esperando peticiones...</div>
        </div>

        <footer>
            <p>PFO 2: Sistema de Gestión de Tareas | Programación sobre Redes &copy; 2026 - Rodrigo Berger</p>
        </footer>
    </div>

    <script>
        let currentUser = null;
        let currentPass = null;

        function logHttp(mensaje) {
            const box = document.getElementById("http-log");
            const time = new Date().toLocaleTimeString();
            box.textContent = `[${time}] ${mensaje}\n` + box.textContent;
        }

        async function ejecutarRegistro() {
            const user = document.getElementById("auth-user").value.trim();
            const pass = document.getElementById("auth-pass").value.trim();

            if (!user || !pass) {
                alert("Por favor ingresa usuario y contraseña.");
                return;
            }

            try {
                logHttp(`POST /registro -> Enviando {"usuario": "${user}", "contraseña": "****"}...`);
                const res = await fetch("/registro", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ usuario: user, "contraseña": pass })
                });
                const data = await res.json();
                
                if (res.status === 201) {
                    logHttp(`[ÉXITO 201] ${data.mensaje} | ID: ${data.usuario.id} | Clave hasheada en SQLite.`);
                    alert(`¡Usuario '${user}' registrado con éxito! Ahora puedes iniciar sesión.`);
                } else {
                    logHttp(`[ERROR ${res.status}] ${data.mensaje}`);
                    alert(`Error (${res.status}): ${data.mensaje}`);
                }
            } catch (err) {
                logHttp(`[ERROR RED] No se pudo conectar con el servidor: ${err}`);
            }
        }

        async function ejecutarLogin() {
            const user = document.getElementById("auth-user").value.trim();
            const pass = document.getElementById("auth-pass").value.trim();

            if (!user || !pass) {
                alert("Por favor ingresa usuario y contraseña.");
                return;
            }

            try {
                logHttp(`POST /login -> Verificando credenciales de '${user}'...`);
                const res = await fetch("/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ usuario: user, "contraseña": pass })
                });
                const data = await res.json();

                if (res.status === 200) {
                    currentUser = user;
                    currentPass = pass;
                    logHttp(`[ÉXITO 200] ${data.mensaje} | Acceso a tareas concedido.`);

                    // Actualizar interfaz
                    document.getElementById("user-display").textContent = currentUser;
                    document.getElementById("logout-container").style.display = "block";
                    document.getElementById("tasks-locked-msg").style.display = "none";
                    document.getElementById("tasks-content").style.display = "block";

                    // Cargar tareas del usuario
                    cargarTareas();
                } else {
                    logHttp(`[ERROR ${res.status}] ${data.mensaje}`);
                    alert(`Error de autenticación: ${data.mensaje}`);
                }
            } catch (err) {
                logHttp(`[ERROR RED] No se pudo conectar con el servidor: ${err}`);
            }
        }

        function cerrarSesion() {
            currentUser = null;
            currentPass = null;
            document.getElementById("user-display").textContent = "[No autenticado]";
            document.getElementById("logout-container").style.display = "none";
            document.getElementById("tasks-locked-msg").style.display = "block";
            document.getElementById("tasks-content").style.display = "none";
            logHttp("[INFO] Sesión cerrada.");
        }

        async function cargarTareas() {
            if (!currentUser) return;
            try {
                logHttp(`GET /api/tareas -> Consultando tareas de '${currentUser}'...`);
                const res = await fetch("/api/tareas", {
                    method: "GET",
                    headers: {
                        "X-Usuario": currentUser,
                        "X-Contrasena": currentPass
                    }
                });
                const data = await res.json();
                
                const container = document.getElementById("task-list-container");
                container.innerHTML = "";

                if (!data.tareas || data.tareas.length === 0) {
                    container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem; padding: 10px 0;">No tienes tareas registradas aún. ¡Crea una arriba!</p>`;
                    return;
                }

                data.tareas.forEach(t => {
                    const isDone = t.estado === "completada";
                    const badgeClass = isDone ? "st-completada" : "st-pendiente";
                    const item = document.createElement("div");
                    item.className = "task-item";
                    item.innerHTML = `
                        <div class="task-info">
                            <h4>${t.titulo}</h4>
                            <p>${t.descripcion || "Sin descripción adicional"} • Creada: ${t.fecha_creacion}</p>
                        </div>
                        <div class="task-actions">
                            <span class="task-status-badge ${badgeClass}">${t.estado}</span>
                            ${!isDone ? `<button onclick="completarTarea(${t.id})" class="btn-success" style="padding: 5px 10px; height: auto; font-size: 0.8rem;">✓ Completar</button>` : ""}
                            <button onclick="eliminarTarea(${t.id})" class="btn-danger">✕</button>
                        </div>
                    `;
                    container.appendChild(item);
                });
                logHttp(`[ÉXITO 200] Se cargaron ${data.total_tareas} tareas.`);
            } catch (err) {
                logHttp(`[ERROR] Falló carga de tareas: ${err}`);
            }
        }

        async function crearTarea() {
            if (!currentUser) return;
            const title = document.getElementById("task-title").value.trim();
            const desc = document.getElementById("task-desc").value.trim();

            if (!title) {
                alert("El título de la tarea es obligatorio.");
                return;
            }

            try {
                logHttp(`POST /api/tareas -> Creando tarea '${title}'...`);
                const res = await fetch("/api/tareas", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Usuario": currentUser,
                        "X-Contrasena": currentPass
                    },
                    body: JSON.stringify({ titulo: title, descripcion: desc })
                });
                const data = await res.json();
                if (res.status === 201) {
                    logHttp(`[ÉXITO 201] Tarea #${data.tarea.id} creada exitosamente en SQLite.`);
                    document.getElementById("task-title").value = "";
                    document.getElementById("task-desc").value = "";
                    cargarTareas();
                } else {
                    logHttp(`[ERROR ${res.status}] ${data.mensaje}`);
                }
            } catch (err) {
                logHttp(`[ERROR] ${err}`);
            }
        }

        async function completarTarea(id) {
            try {
                logHttp(`PUT /api/tareas/${id} -> Marcando tarea como completada...`);
                const res = await fetch(`/api/tareas/${id}`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Usuario": currentUser,
                        "X-Contrasena": currentPass
                    },
                    body: JSON.stringify({ estado: "completada" })
                });
                const data = await res.json();
                if (res.status === 200) {
                    logHttp(`[ÉXITO 200] Tarea #${id} actualizada a 'completada'.`);
                    cargarTareas();
                }
            } catch (err) {
                logHttp(`[ERROR] ${err}`);
            }
        }

        async function eliminarTarea(id) {
            if (!confirm(`¿Deseas eliminar la tarea #${id}?`)) return;
            try {
                logHttp(`DELETE /api/tareas/${id} -> Eliminando tarea...`);
                const res = await fetch(`/api/tareas/${id}`, {
                    method: "DELETE",
                    headers: {
                        "X-Usuario": currentUser,
                        "X-Contrasena": currentPass
                    }
                });
                const data = await res.json();
                if (res.status === 200) {
                    logHttp(`[ÉXITO 200] Tarea #${id} eliminada de SQLite.`);
                    cargarTareas();
                }
            } catch (err) {
                logHttp(`[ERROR] ${err}`);
            }
        }
    </script>
</body>
</html>
"""

@app.route("/tareas", methods=["GET"])
def ver_tareas_bienvenida():
    """
    Endpoint: GET /tareas
    Consigna:
    - "GET /tareas: Muestre un html de bienvenida"
    Retorna la aplicación cliente web interactiva que se comunica directamente
    con la API REST y SQLite.
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
    print(f"  • GET  http://{HOST}:{PORT}/tareas (Cliente Web & Bienvenida)")
    print("=" * 65)
    app.run(host=HOST, port=PORT, debug=False)

if __name__ == "__main__":
    iniciar_servidor()
