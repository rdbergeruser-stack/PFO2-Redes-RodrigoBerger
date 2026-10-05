import sys
import webbrowser

try:
    import requests
except ImportError:
    print("[ERROR] Requiere instalar la librería requests: pip install requests")
    sys.exit(1)

# ==============================================================================
# CONFIGURACIÓN DEL CLIENTE
# ==============================================================================
# Materia: Programación sobre redes - 3.° D
# Alumno: Rodrigo Berger
# Proyecto: PFO 2 - Cliente de Consola para API REST
BASE_URL = "http://localhost:5000"

class ClienteAPI:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.usuario_actual = None
        self.contrasena_actual = None
        self.session = requests.Session()

    def get_headers(self):
        """Retorna credenciales del usuario autenticado."""
        if self.usuario_actual and self.contrasena_actual:
            return {
                "X-Usuario": self.usuario_actual,
                "X-Contrasena": self.contrasena_actual
            }
        return {}

    def registrar(self):
        """Permite registrar un usuario (POST /registro)."""
        print("\n" + "-" * 45)
        print(" [1] REGISTRO DE USUARIO")
        print("-" * 45)
        usuario = input("Nombre de usuario (ej: nombre): ").strip()
        contrasena = input("Contraseña (ej: 1234): ").strip()

        if not usuario or not contrasena:
            print("[AVISO] Debe completar ambos campos.")
            return

        payload = {"usuario": usuario, "contraseña": contrasena}
        try:
            r = self.session.post(f"{self.base_url}/registro", json=payload, timeout=5)
            data = r.json()
            if r.status_code == 201:
                print(f"\n[ÉXITO {r.status_code}] {data.get('mensaje')}")
                print(f" -> Usuario: {data['usuario']['usuario']} (ID: {data['usuario']['id']})")
                print(" -> Contraseña almacenada de forma segura con hash en SQLite.")
            else:
                print(f"\n[ERROR {r.status_code}] {data.get('mensaje')}")
        except requests.exceptions.ConnectionError:
            print(f"\n[ERROR CONEXIÓN] No se pudo conectar a {self.base_url}. Inicie 'python servidor.py'.")

    def login(self):
        """Permite iniciar sesión (POST /login)."""
        print("\n" + "-" * 45)
        print(" [2] INICIO DE SESIÓN")
        print("-" * 45)
        usuario = input("Nombre de usuario: ").strip()
        contrasena = input("Contraseña: ").strip()

        if not usuario or not contrasena:
            print("[AVISO] Debe completar ambos campos.")
            return

        payload = {"usuario": usuario, "contraseña": contrasena}
        try:
            r = self.session.post(f"{self.base_url}/login", json=payload, timeout=5)
            data = r.json()
            if r.status_code == 200:
                self.usuario_actual = usuario
                self.contrasena_actual = contrasena
                print(f"\n[ÉXITO {r.status_code}] {data.get('mensaje')}")
                print(f" -> Sesión iniciada como: '{self.usuario_actual}'")
            else:
                print(f"\n[ERROR {r.status_code}] {data.get('mensaje')}")
        except requests.exceptions.ConnectionError:
            print(f"\n[ERROR CONEXIÓN] No se pudo conectar a {self.base_url}. Inicie 'python servidor.py'.")

    def ver_bienvenida(self):
        """Consulta el endpoint GET /tareas requerido por la consigna."""
        print("\n" + "-" * 45)
        print(" [3] CONSULTAR GET /tareas")
        print("-" * 45)
        url = f"{self.base_url}/tareas"
        try:
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                print(f"[ÉXITO {r.status_code}] Endpoint GET /tareas respondió correctamente.")
                print(f" -> Content-Type: {r.headers.get('Content-Type')}")
                print(f" -> Tamaño HTML: {len(r.text)} bytes.")
                abrir = input("\n¿Desea abrir la página en su navegador web? (s/n): ").strip().lower()
                if abrir in ["s", "si", "sí", "y"]:
                    webbrowser.open(url)
            else:
                print(f"[ERROR {r.status_code}] No se pudo acceder a {url}.")
        except requests.exceptions.ConnectionError:
            print(f"\n[ERROR CONEXIÓN] No se pudo conectar a {self.base_url}.")

    def listar_tareas(self):
        """Consulta GET /api/tareas."""
        if not self.usuario_actual:
            print("\n[AVISO] Inicie sesión primero (Opción 2).")
            return

        print("\n" + "-" * 45)
        print(f" [4] MIS TAREAS ({self.usuario_actual})")
        print("-" * 45)
        try:
            r = self.session.get(f"{self.base_url}/api/tareas", headers=self.get_headers(), timeout=5)
            data = r.json()
            tareas = data.get("tareas", [])
            if not tareas:
                print("No hay tareas registradas. Cree una con la Opción 5.")
            else:
                print(f"Total: {len(tareas)} tareas\n")
                for t in tareas:
                    estado = "✓ [COMPLETADA]" if t["estado"] == "completada" else "○ [PENDIENTE]"
                    print(f"ID #{t['id']} | {estado} | {t['titulo']}")
                    if t.get("descripcion"):
                        print(f"   Detalle: {t['descripcion']}")
                    print("-" * 35)
        except requests.exceptions.ConnectionError:
            print(f"\n[ERROR CONEXIÓN] No se pudo conectar a {self.base_url}.")

    def crear_tarea(self):
        """Crea una tarea con POST /api/tareas."""
        if not self.usuario_actual:
            print("\n[AVISO] Inicie sesión primero (Opción 2).")
            return

        print("\n" + "-" * 45)
        print(" [5] CREAR NUEVA TAREA")
        print("-" * 45)
        titulo = input("Título de la tarea: ").strip()
        if not titulo:
            print("[AVISO] El título es obligatorio.")
            return
        descripcion = input("Descripción (opcional): ").strip()

        payload = {"titulo": titulo, "descripcion": descripcion}
        try:
            r = self.session.post(f"{self.base_url}/api/tareas", json=payload, headers=self.get_headers(), timeout=5)
            data = r.json()
            if r.status_code == 201:
                t = data.get("tarea", {})
                print(f"\n[ÉXITO {r.status_code}] {data.get('mensaje')}")
                print(f" -> ID: #{t.get('id')} | Título: {t.get('titulo')}")
            else:
                print(f"\n[ERROR {r.status_code}] {data.get('mensaje')}")
        except requests.exceptions.ConnectionError:
            print(f"\n[ERROR CONEXIÓN] No se pudo conectar a {self.base_url}.")

    def completar_tarea(self):
        """Actualiza una tarea con PUT /api/tareas/<id>."""
        if not self.usuario_actual:
            print("\n[AVISO] Inicie sesión primero (Opción 2).")
            return

        print("\n" + "-" * 45)
        print(" [6] COMPLETAR TAREA")
        print("-" * 45)
        tarea_id = input("ID de la tarea: ").strip()
        if not tarea_id.isdigit():
            print("[AVISO] Ingrese un ID numérico válido.")
            return

        try:
            r = self.session.put(f"{self.base_url}/api/tareas/{tarea_id}", json={"estado": "completada"}, headers=self.get_headers(), timeout=5)
            data = r.json()
            if r.status_code == 200:
                print(f"\n[ÉXITO {r.status_code}] {data.get('mensaje')}")
            else:
                print(f"\n[ERROR {r.status_code}] {data.get('mensaje')}")
        except requests.exceptions.ConnectionError:
            print(f"\n[ERROR CONEXIÓN] No se pudo conectar a {self.base_url}.")

    def cerrar_sesion(self):
        if not self.usuario_actual:
            print("\n[INFO] No hay sesión activa.")
            return
        print(f"\n[INFO] Sesión de '{self.usuario_actual}' cerrada.")
        self.usuario_actual = None
        self.contrasena_actual = None

def main():
    cliente = ClienteAPI()
    print("=" * 60)
    print("   CLIENTE DE CONSOLA - SISTEMA DE GESTIÓN DE TAREAS")
    print("   Materia: Programación sobre redes - 3.° D | Alumno: Rodrigo Berger")
    print("=" * 60)

    while True:
        sesion = f"[{cliente.usuario_actual}]" if cliente.usuario_actual else "[No autenticado]"
        print("\n" + "=" * 45)
        print(f" MENÚ PRINCIPAL  {sesion}")
        print("=" * 45)
        print("1. Registrar usuario            (POST /registro)")
        print("2. Iniciar sesión               (POST /login)")
        print("3. Ver bienvenida de tareas     (GET /tareas)")
        print("4. Listar mis tareas            (GET /api/tareas)")
        print("5. Crear nueva tarea            (POST /api/tareas)")
        print("6. Marcar tarea completada      (PUT /api/tareas/<id>)")
        print("7. Cerrar sesión")
        print("8. Salir")
        print("=" * 45)

        op = input("Seleccione una opción (1-8): ").strip()
        if op == "1":
            cliente.registrar()
        elif op == "2":
            cliente.login()
        elif op == "3":
            cliente.ver_bienvenida()
        elif op == "4":
            cliente.listar_tareas()
        elif op == "5":
            cliente.crear_tarea()
        elif op == "6":
            cliente.completar_tarea()
        elif op == "7":
            cliente.cerrar_sesion()
        elif op in ["8", "salir", "exit"]:
            print("\n[INFO] Cliente finalizado. ¡Hasta luego!")
            break
        else:
            print("[AVISO] Opción inválida.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Programa interrumpido por el usuario.")
        sys.exit(0)
