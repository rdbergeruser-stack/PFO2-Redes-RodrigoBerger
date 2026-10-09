import sys

try:
    import requests
except ImportError:
    print("[ERROR] Requiere instalar la librería requests: pip install requests")
    sys.exit(1)

# ==============================================================================
# CLIENTE DE CONSOLA
# ==============================================================================
# Institución: IFTS N.° 29
# Materia: Programación sobre redes - 3.° D
# Alumno: Rodrigo Berger
# Proyecto: PFO 2 - Cliente de Consola para API REST
BASE_URL = "http://localhost:5000"

class ClienteConsola:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.usuario_actual = None
        self.contrasena_actual = None
        self.session = requests.Session()

    def get_auth_headers(self):
        """Retorna las cabeceras de autenticación si hay sesión activa."""
        if self.usuario_actual and self.contrasena_actual:
            return {
                "X-Usuario": self.usuario_actual,
                "X-Contrasena": self.contrasena_actual
            }
        return {}

    def registrar_usuario(self):
        """Envía solicitud POST /registro para crear un usuario."""
        print("\n" + "-" * 50)
        print(" [1] REGISTRO DE NUEVO USUARIO")
        print("-" * 50)
        usuario = input("Nombre de usuario: ").strip()
        contrasena = input("Contraseña: ").strip()

        if not usuario or not contrasena:
            print("[AVISO] Debe ingresar usuario y contraseña.")
            return

        payload = {"usuario": usuario, "contraseña": contrasena}
        try:
            r = self.session.post(f"{self.base_url}/registro", json=payload, timeout=5)
            data = r.json()

            if r.status_code == 201:
                u = data.get("usuario", {})
                print(f"\n[ÉXITO 201] {data.get('mensaje')}")
                print(f" -> ID: #{u.get('id')} | Usuario: {u.get('usuario')}")
                print(" -> Contraseña almacenada de forma segura mediante hash criptográfico en SQLite.")
            else:
                print(f"\n[ERROR {r.status_code}] {data.get('mensaje')}")

        except requests.exceptions.ConnectionError:
            print(f"\n[ERROR CONEXIÓN] No se pudo conectar a {self.base_url}. Asegúrese de que 'servidor.py' esté en ejecución.")

    def iniciar_sesion(self):
        """Envía solicitud POST /login para autenticarse."""
        print("\n" + "-" * 50)
        print(" [2] INICIO DE SESIÓN")
        print("-" * 50)
        usuario = input("Nombre de usuario: ").strip()
        contrasena = input("Contraseña: ").strip()

        if not usuario or not contrasena:
            print("[AVISO] Debe ingresar usuario y contraseña.")
            return

        payload = {"usuario": usuario, "contraseña": contrasena}
        try:
            r = self.session.post(f"{self.base_url}/login", json=payload, timeout=5)
            data = r.json()

            if r.status_code == 200:
                self.usuario_actual = usuario
                self.contrasena_actual = contrasena
                print(f"\n[ÉXITO 200] {data.get('mensaje')}")
                print(f" -> Sesión iniciada para el usuario: '{self.usuario_actual}'")
            else:
                print(f"\n[ERROR {r.status_code}] {data.get('mensaje')}")

        except requests.exceptions.ConnectionError:
            print(f"\n[ERROR CONEXIÓN] No se pudo conectar a {self.base_url}.")

    def listar_usuarios(self):
        """
        Envía solicitud GET /usuarios.
        Este endpoint requiere sesión activa (envía headers de autenticación).
        """
        print("\n" + "-" * 50)
        print(" [3] LISTADO DE USUARIOS (GET /usuarios)")
        print("-" * 50)

        if not self.usuario_actual:
            print("[BLOQUEADO] El listado de usuarios requiere sesión iniciada.")
            print("Por favor, inicie sesión primero utilizando la Opción 2.")
            return

        try:
            r = self.session.get(
                f"{self.base_url}/usuarios",
                headers=self.get_auth_headers(),
                timeout=5
            )
            data = r.json()

            if r.status_code == 200:
                usuarios = data.get("usuarios", [])
                print(f"\n[ÉXITO 200] Total de usuarios registrados: {data.get('total_usuarios')}\n")
                print(f"{'ID':<6} | {'USUARIO':<20} | {'FECHA DE REGISTRO'}")
                print("-" * 50)
                for u in usuarios:
                    print(f"#{u['id']:<5} | {u['usuario']:<20} | {u['fecha_registro']}")
                print("-" * 50)
                print("Nota: Por motivos de seguridad, las contraseñas/hashes nunca se exponen en la API.")
            else:
                print(f"\n[ERROR {r.status_code}] {data.get('mensaje')}")

        except requests.exceptions.ConnectionError:
            print(f"\n[ERROR CONEXIÓN] No se pudo conectar a {self.base_url}.")

    def cerrar_sesion(self):
        """Limpia la sesión en el cliente."""
        if not self.usuario_actual:
            print("\n[INFO] No hay ninguna sesión activa actualmente.")
            return
        print(f"\n[INFO] Sesión cerrada para '{self.usuario_actual}'.")
        self.usuario_actual = None
        self.contrasena_actual = None

def main():
    cliente = ClienteConsola()

    print("=" * 60)
    print("   CLIENTE DE CONSOLA - SISTEMA DE GESTIÓN DE USUARIOS")
    print("   IFTS N.° 29 | Prog. sobre redes - 3.° D | Rodrigo Berger")
    print("=" * 60)

    while True:
        sesion_txt = f"[{cliente.usuario_actual}]" if cliente.usuario_actual else "[No autenticado]"
        print("\n" + "=" * 45)
        print(f" MENÚ PRINCIPAL  {sesion_txt}")
        print("=" * 45)
        print(" 1. Registrar usuario       (POST /registro)")
        print(" 2. Iniciar sesión          (POST /login)")
        print(" 3. Listar usuarios         (GET /usuarios) [Requiere login]")
        print(" 4. Cerrar sesión")
        print(" 5. Salir")
        print("=" * 45)

        op = input("Seleccione una opción (1-5): ").strip()
        if op == "1":
            cliente.registrar_usuario()
        elif op == "2":
            cliente.iniciar_sesion()
        elif op == "3":
            cliente.listar_usuarios()
        elif op == "4":
            cliente.cerrar_sesion()
        elif op in ["5", "salir", "exit"]:
            print("\n[INFO] Saliendo del programa. ¡Hasta luego!")
            break
        else:
            print("[AVISO] Opción no válida. Ingrese un número del 1 al 5.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrumpido por el usuario.")
        sys.exit(0)
