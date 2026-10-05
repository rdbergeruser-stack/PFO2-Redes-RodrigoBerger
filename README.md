# PFO 2: Sistema de Gestión de Tareas con API REST y Base de Datos

**Materia:** Programación sobre redes - 3.° D  
**Alumno:** Rodrigo Berger  
**Tecnologías:** Python 3, Flask (API REST), SQLite3, Criptografía y Hashing (`werkzeug.security` - PBKDF2/scrypt), Cliente HTTP (`requests`).

---

## 📌 1. Descripción del Proyecto

Este trabajo práctico implementa una arquitectura **Cliente-Servidor** basada en una **API REST** desarrollada con **Flask** y respaldada por persistencia en una base de datos relacional **SQLite** (`tareas_db.sqlite`).

El sistema ofrece autenticación de usuarios con almacenamiento protegido mediante **hashing criptográfico unidireccional y salting** (sin texto plano), control de acceso y gestión de tareas, junto con un cliente interactivo en consola y una vista web de bienvenida.

### Componentes:
- **`servidor.py`**: API REST en Flask que gestiona los endpoints de registro, login, bienvenida y tareas, persistiendo los datos en SQLite.
- **`cliente.py`**: Cliente de consola con menú interactivo para comunicarse con la API de forma intuitiva.
- **`index.html`**: Página web estática para alojar la presentación del proyecto en **GitHub Pages**.
- **`tareas_db.sqlite`**: Base de datos relacional con tablas `usuarios` y `tareas`.

---

## 🗄️ 2. Estructura de la Base de Datos (SQLite)

La persistencia se realiza en `tareas_db.sqlite`:

### Tabla: `usuarios`
| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Identificador único del usuario |
| `usuario` | `TEXT` | `UNIQUE NOT NULL` | Nombre de usuario |
| `contrasena_hash` | `TEXT` | `NOT NULL` | Hash seguro generado con salt (scrypt/PBKDF2) |
| `fecha_registro` | `TEXT` | `NOT NULL` | Fecha y hora del registro |

### Tabla: `tareas`
| Campo | Tipo | Restricciones | Descripción |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Identificador único de la tarea |
| `usuario_id` | `INTEGER` | `NOT NULL, FOREIGN KEY` | Vinculación con el usuario creador |
| `titulo` | `TEXT` | `NOT NULL` | Título de la tarea |
| `descripcion` | `TEXT` | - | Detalle complementario |
| `estado` | `TEXT` | `DEFAULT 'pendiente'` | Estado (`pendiente` o `completada`) |
| `fecha_creacion` | `TEXT` | `NOT NULL` | Fecha y hora de alta |

---

## 🌐 3. Especificación de Endpoints

### 1. Registro de Usuarios: `POST /registro`
Da de alta un usuario y almacena la contraseña hasheada en SQLite.
- **Body (JSON):**
  ```json
  {
    "usuario": "nombre",
    "contraseña": "1234"
  }
  ```
- **Respuestas:**
  - `201 Created`: Usuario registrado con éxito.
  - `400 Bad Request`: Datos incompletos.
  - `409 Conflict`: El nombre de usuario ya existe.

### 2. Inicio de Sesión: `POST /login`
Comprueba credenciales contra el hash en base de datos y habilita el acceso.
- **Body (JSON):**
  ```json
  {
    "usuario": "nombre",
    "contraseña": "1234"
  }
  ```
- **Respuestas:**
  - `200 OK`: Inicio de sesión exitoso.
  - `401 Unauthorized`: Usuario o contraseña incorrectos.

### 3. Pantalla de Bienvenida: `GET /tareas`
Requerimiento de consigna: *"GET /tareas: Muestre un html de bienvenida"*.
- **Respuesta (`200 OK`):** Retorna la página HTML estilizada de bienvenida con el estado del sistema.

### 4. Listado y Gestión de Tareas (API REST)
- `GET /api/tareas`: Retorna el listado de tareas del usuario autenticado en JSON.
- `POST /api/tareas`: Crea una nueva tarea (`{"titulo": "...", "descripcion": "..."}`).
- `PUT /api/tareas/<id>`: Actualiza estado de la tarea (ej: `{"estado": "completada"}`).
- `DELETE /api/tareas/<id>`: Elimina una tarea.

---

## 🧠 4. Respuestas Conceptuales

### 1. ¿Por qué hashear contraseñas?

Almacenar contraseñas en texto plano representa un fallo crítico de seguridad. Los motivos técnicos esenciales para utilizar funciones hash son:

1. **Protección ante Fugas de Datos (Data Breaches):**  
   Si la base de datos es extraída indebidamente por un atacante o se filtra una copia de seguridad, el atacante solo obtiene cadenas de hashes ininteligibles, impidiendo el acceso a las contraseñas reales de los usuarios.

2. **Propiedad Unidireccional (One-Way):**  
   A diferencia del cifrado simétrico/asimétrico (que es reversible mediante claves), una función hash criptográfica es **matemáticamente irreversible**. Es directo calcular `Hash = H(contraseña)`, pero es computacionalmente inviable deducir la contraseña original a partir del hash (`H⁻¹(Hash)`). Para autenticar, el servidor calcula el hash del texto ingresado en el login y lo compara con el almacenado, sin necesidad de conocer la clave en texto plano.

3. **Defensa contra Tablas de Arcoíris (Rainbow Tables) mediante Salting:**  
   Algoritmos modernos (como scrypt o PBKDF2 empleados por `werkzeug.security`) generan automáticamente un **Salt** (secuencia aleatoria única por usuario) que se combina con la contraseña antes de procesarla. Esto asegura que dos usuarios con la misma clave (ej: `"1234"`) tengan hashes totalmente distintos, inutilizando ataques basados en diccionarios precalculados.

4. **Resistencia a Fuerza Bruta:**  
   Los algoritmos específicos para contraseñas aplican deliberadamente costos computacionales y de memoria para ralentizar ataques automatizados de prueba y error masivos.

---

### 2. Ventajas de usar SQLite en este proyecto

Para el contexto y alcance de este proyecto, SQLite aporta ventajas clave:

1. **Arquitectura sin Servidor (Serverless):**  
   A diferencia de motores como MySQL o PostgreSQL, SQLite no requiere un servicio o proceso demonio corriendo en segundo plano ni apertura de puertos de red. La biblioteca interactúa directamente con el archivo en disco.

2. **Cero Configuración (Zero-Configuration):**  
   No requiere credenciales de red, administración de permisos ni cadenas complejas de conexión. Viene integrado de forma nativa en la biblioteca estándar de Python (`import sqlite3`).

3. **Portabilidad y Simplicidad de Entrega:**  
   Toda la base de datos se almacena en un único archivo autocontenido (`tareas_db.sqlite`). Esto facilita su entrega, respaldo y ejecución en cualquier equipo sin instalar infraestructura adicional.

4. **Garantía ACID:**  
   Cumple estrictamente con las propiedades de Atomicidad, Consistencia, Aislamiento y Durabilidad (**ACID**), protegiendo la integridad de los datos ante apagados abruptos o errores.

5. **Eficiencia y Bajo Consumo de Recursos:**  
   Tiene un consumo despreciable de memoria y CPU, haciéndolo ideal para desarrollos locales, pruebas y arquitecturas ligeras con Flask.

---

## 🚀 5. Guía de Ejecución

### Requisitos
Instalar dependencias necesarias:
```bash
pip install flask requests
```

### Paso 1: Iniciar el Servidor API
En una terminal:
```bash
python servidor.py
```

### Paso 2: Iniciar el Cliente de Consola
En otra terminal distinta:
```bash
python cliente.py
```
Sigue el menú interactivo para registrar un usuario, iniciar sesión, ver la bienvenida y gestionar tareas.

### 👤 Usuarios y Credenciales de Prueba

Para probar el inicio de sesión y acceso a tareas de inmediato, la base de datos SQLite ya cuenta con los siguientes usuarios registrados:

| Usuario | Contraseña |
|---|---|
| `Rodrigo` | `1234` |
| `Berger` | `1234` |

*(También es posible registrar cualquier otro usuario nuevo desde la Opción 1 del cliente de consola o desde el cliente web).*

---

## 📸 6. Capturas de Pantalla de Pruebas Exitosas

### 1. Inicialización del Servidor y Cliente
Puesta en marcha del servidor API Flask escuchando en `http://localhost:5000` con la base de datos SQLite inicializada, junto al menú interactivo de `cliente.py`.
![01 - Servidor y Cliente Iniciados](Capturas/01.jpg)

### 2. Formulario de Registro de Usuario
Selección de la Opción 1 en el cliente de consola e ingreso de los datos requeridos (`usuario: Berger`, `contraseña: 1234`).
![02 - Formulario de Registro](Capturas/02.jpg)

### 3. Registro Exitoso (`POST /registro` 201 Created)
Confirmación del alta del usuario en el cliente y verificación en el log del servidor indicando que la contraseña fue almacenada con hash seguro en SQLite.
![03 - Registro Exitoso con Hash](Capturas/03.jpg)

### 4. Inicio de Sesión (`POST /login` 200 OK)
Verificación de credenciales contra el hash en base de datos SQLite y habilitación de la sesión para el acceso a las tareas.
![04 - Login Exitoso](Capturas/04.jpg)

### 5. Consulta de Bienvenida (`GET /tareas` 200 OK)
Petición al endpoint `GET /tareas` desde el cliente, obteniendo la respuesta HTTP 200 con el contenido HTML de bienvenida.
![05 - Endpoint GET /tareas](Capturas/05.jpg)

### 6. Gestión Completa de Tareas y Cliente Web Interactivo
Flujo integral de creación (`POST /api/tareas`), consulta (`GET /api/tareas`) y actualización a completada (`PUT /api/tareas/1`), visualizando las respuestas en la consola del cliente, los logs del servidor y el cliente web interactivo.
![06 - Gestión Completa de Tareas](Capturas/06.jpg)

---

## 🌐 7. Enlaces del Proyecto

- **Repositorio en GitHub:**  
  [https://github.com/rdbergeruser-stack/PFO2-Redes-RodrigoBerger](https://github.com/rdbergeruser-stack/PFO2-Redes-RodrigoBerger)

- **Sitio publicado en GitHub Pages:**  
  [https://rdbergeruser-stack.github.io/PFO2-Redes-RodrigoBerger/](https://rdbergeruser-stack.github.io/PFO2-Redes-RodrigoBerger/)
