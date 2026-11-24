# Mina Lourdes: prototipo de control de pesaje y leyes

Prototipo web (Flask + SQLite) para la materia Ingeniería de Software (ITH, S5A). Cubre el flujo de la planta: el basculista registra el peso de cada camión y emite su ticket, el laboratorista registra la ley del mineral, y el supervisor consulta tickets, solicita y aprueba correcciones, cierra tickets y audita la bitácora. La báscula es simulada.

## Inicio rápido

| | Linux / macOS | Windows |
|---|---|---|
| Arrancar | `./run.sh` | doble clic en `run.bat` |
| Abrir | http://127.0.0.1:5000 | http://127.0.0.1:5000 |

### Usuarios y contraseñas

| Usuario | Contraseña | Rol | Qué puede hacer |
|---|---|---|---|
| `basculista` | `1234` | Basculista | Leer el peso de la báscula (o capturarlo a mano si está desconectada), guardar pesajes, generar e imprimir sus tickets y consultarlos. |
| `laboratorista` | `1234` | Laboratorista | Ver el historial de últimos tickets, consultar tickets y registrar la ley (análisis) de los tickets pendientes. |
| `supervisor` | `1234` | Supervisor | Consultar todos los tickets, solicitar correcciones, aprobarlas o rechazarlas, cerrar tickets y revisar la bitácora. |

Son usuarios de demostración: se crean automáticamente la primera vez que arranca la app y se vuelven a crear al reiniciar los datos.

## Requisitos

- **Python 3.11 o superior** (probado con Python 3.14).
- Conexión a internet **solo la primera vez**, para descargar Flask y Flask-SQLAlchemy.
- Un navegador web (Chrome, Firefox, Edge…).

No hace falta instalar ninguna base de datos: SQLite viene incluido en Python y los datos se guardan en un solo archivo (`instance/mina_lourdes.db`).

## Ejecutar en Linux (o macOS)

1. Instale Python si no lo tiene:
   - Ubuntu / Debian: `sudo apt install python3 python3-venv`
   - Fedora: `sudo dnf install python3`
   - Arch / Omarchy: `sudo pacman -S python`
   - macOS: `brew install python` o el instalador de <https://www.python.org/downloads/>
2. Descargue el proyecto:
   ```bash
   git clone https://github.com/jmloz/mina-lourdes.git
   cd mina-lourdes
   ```
3. Arranque la app:
   ```bash
   ./run.sh
   ```
   Si aparece «Permiso denegado», ejecute antes `chmod +x run.sh` (o use `bash run.sh`).
4. Abra **http://127.0.0.1:5000** en el navegador.
5. Para detener el servidor pulse **Ctrl + C** en la terminal.

## Ejecutar en Windows

1. Instale Python desde <https://www.python.org/downloads/>. En la primera pantalla del instalador **marque la casilla «Add python.exe to PATH»**.
2. Descargue el proyecto: en GitHub pulse **Code → Download ZIP** y descomprímalo, o con Git:
   ```bat
   git clone https://github.com/jmloz/mina-lourdes.git
   cd mina-lourdes
   ```
3. Haga **doble clic en `run.bat`** (o ejecútelo desde CMD / PowerShell con `.\run.bat`).
   Se abrirá una ventana negra: **no la cierre**, es el servidor.
4. Abra **http://127.0.0.1:5000** en el navegador.
5. Para detener el servidor pulse **Ctrl + C** en esa ventana (o ciérrela).

## Qué hacen los scripts

`run.sh` y `run.bat` hacen lo mismo:

1. Crean el entorno virtual `.venv` si no existe (o lo reparan si quedó incompleto).
2. Instalan las dependencias de `requirements.txt` dentro de `.venv`.
3. Ejecutan `run.py`, que crea la base de datos con datos de demostración la primera vez y levanta el servidor en `127.0.0.1:5000`.

Si prefiere hacerlo a mano:

| Paso | Linux / macOS | Windows |
|---|---|---|
| Crear entorno | `python3 -m venv .venv` | `py -3 -m venv .venv` |
| Instalar dependencias | `.venv/bin/python -m pip install -r requirements.txt` | `.venv\Scripts\python -m pip install -r requirements.txt` |
| Arrancar | `.venv/bin/python run.py` | `.venv\Scripts\python run.py` |

## Problemas comunes

- **«no se encontró python3» / «no se encontro Python»:** Python no está instalado o no está en el PATH. En Windows reinstálelo marcando «Add python.exe to PATH».
- **Windows abre la Microsoft Store al ejecutar `python`:** desactive los alias en *Configuración → Aplicaciones → Alias de ejecución de aplicaciones* (`python.exe` y `python3.exe`) e instale Python desde python.org.
- **«Address already in use» / puerto 5000 ocupado:** ya hay otro servidor corriendo (quizá una ventana anterior de Mina Lourdes). Ciérrelo y vuelva a ejecutar el script.
- **Algo quedó mal instalado:** borre la carpeta `.venv` y vuelva a ejecutar el script.
- **Quiero empezar con datos limpios:** vea *Reiniciar los datos* más abajo.

## Reiniciar los datos

Para volver al estado demo original, detenga el servidor y ejecute:

| Linux / macOS | Windows |
|---|---|
| `.venv/bin/python seed.py` | `.venv\Scripts\python seed.py` |

Esto borra y recrea la base de datos con los datos de demostración.

## Pruebas

| Linux / macOS | Windows |
|---|---|
| `.venv/bin/python -m pytest -q` | `.venv\Scripts\python -m pytest -q` |

## Guion de demostración (≈ 5 min)

Entre con cada usuario en el orden indicado. Los casos de uso (CU) se recorren en orden de número dentro de cada rol.

**1. Basculista** (`basculista` / `1234`)

1. **CU-01 Captura de peso:** en *Captura de pesaje*, pulse **Leer peso** (la báscula simulada devuelve un peso) y luego **Guardar pesaje**. El pesaje queda registrado.
2. **CU-02 Lectura automática:** pulse **Alternar conexión de báscula (demo)** para **desconectar la báscula** e intente leer o guardar: el sistema muestra el error y no guarda nada. Con la báscula desconectada, capture el peso a mano (p. ej. `18500,25`), pulse **Guardar pesaje manual** y genere el ticket (aparece «Lectura: Manual»). Vuelva a conectarla.
3. **CU-03 Emitir ticket:** en *Generación de ticket* elija el pesaje sin ticket, pulse **Generar ticket**, y el sistema abre la vista de **impresión** del ticket. El ticket queda en estado *Pendiente de análisis*.

**2. Laboratorista** (`laboratorista` / `1234`)

4. **CU-09 Historial:** en *Historial de últimos tickets* revise los tickets recientes y su estado.
5. **CU-08 Registro de análisis:** en un ticket pendiente pulse **Registrar análisis**, capture la ley (p. ej. `2.350`) y pulse **Guardar análisis**. El ticket pasa a *Análisis registrado*.

**3. Supervisor** (`supervisor` / `1234`)

6. **CU-04 Consulta de tickets:** en *Consulta de tickets* filtre por estado o número y abra el detalle de un ticket.
7. **CU-05 Solicitar corrección:** en el detalle de un ticket con análisis, pulse **Solicitar corrección**, elija el campo (p. ej. resultado de ley), capture el nuevo valor y el motivo, y pulse **Enviar solicitud**.
8. **CU-06 Aprobar / rechazar:** en *Correcciones y aprobaciones* apruebe una solicitud (el ticket se actualiza) y rechace otra (el ticket vuelve a su estado anterior).
9. **Cerrar ticket:** en un ticket con análisis registrado o actualizado, pulse **Cerrar ticket**. El ticket queda cerrado y no admite más cambios.
10. **CU-07 Bitácora:** en *Bitácora* filtre por fechas, usuario o acción y pulse **Buscar**; observe los registros de cada operación realizada en la demo.

## Clases UML → archivo

| Clase UML | Modelo (`app/models.py`) | Servicio (`app/servicios/`) | Rutas (`app/rutas/`) |
|---|---|---|---|
| Pesaje | `Pesaje` | `pesajes.py` | `basculista.py` |
| Ticket | `Ticket` | `tickets.py` | `tickets.py` |
| Analisis | `Analisis` | `analisis.py` | `laboratorio.py` |
| CorreccionTicket | `CorreccionTicket` | `correcciones.py` | `supervisor.py` |
| Bitacora | `Bitacora` | `bitacora.py` | `supervisor.py` (ruta `/bitacora`) |
| Bascula | `Bascula` | `bascula.py` | `basculista.py` (ruta `/conexion`) |
| Basculista / Laboratorista / Supervisor | `Usuario` (campo `rol`) | No hay servicio dedicado; el login y los roles viven en `app/auth.py` | `principal.py` (login y menú) |

Estados y transiciones de ticket: `app/estados.py`. Validación de entradas: `app/servicios/validacion.py`.
