<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licencia MIT (ver archivo LICENSE) -->

<div align="center">
  <img src="docs/assets/omega-fire.png" alt="Omega-Fire" width="256">
</div>

# 󰦝 OMEGA-FIRE

**Puesto unificado de gestión de la seguridad de red**

> Desarrollado por **kraynux** para **Omega-server** 
[https://kraynux.snake-mackarel.ts.net](https://kraynux.snake-mackarel.ts.net)

Página oficial: [OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; Vista previa: [Screenshots](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

🇫🇷 [Français](README.md) · 🇬🇧 [English](README.en.md) · 🇪🇸 **Español** · 🇷🇺 [Русский](README.ru.md) · 🇨🇳 [中文](README.zh.md)

---

**Omega-Fire** es una aplicación TUI (Terminal User Interface) en Python construida con [Textual](https://github.com/Textualize/textual). Ofrece desde un terminal una interfaz única para administrar los cortafuegos de Linux, Fail2Ban, las direcciones baneadas, las reglas de red, los registros (logs) y las estadísticas del sistema.

La interfaz Textual es el modo de funcionamiento por defecto y navega mediante menús, formularios validados (todos los campos requeridos se verifican antes de continuar) y pantallas dedicadas, con temas, ayuda contextual y atajos de teclado compartidos con el resto de la suite OMEGA (omega-check, omega-deep, omega-stress...). La antigua interfaz [Rich](https://github.com/Textualize/rich), secuencial y controlada mediante la introducción de números, sigue disponible vía `--legacy-cli` (ver [Lanzamiento](#lanzamiento)).

El proyecto está diseñado según los principios de la **Clean Architecture**, con una separación clara entre el dominio de negocio, la orquestación, la infraestructura y la interfaz de usuario.

## Índice

- [Presentación](#presentación)
- [Funcionalidades](#funcionalidades)
- [Arquitectura](#arquitectura)
- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Configuración](#configuración)
- [Backends y compatibilidad](#backends-y-compatibilidad)
- [Persistencia, logs y exportaciones](#persistencia-logs-y-exportaciones)
- [Seguridad](#seguridad)
- [Pruebas y calidad](#pruebas-y-calidad)
- [Estado del proyecto](#estado-del-proyecto)
- [Desinstalación](#desinstalación)
- [Licencia](#licencia)

---

## Presentación

Omega-Fire actúa como un **puesto de pilotaje local** para la seguridad de red. Detecta automáticamente los componentes presentes en la máquina y adapta los menús a las capacidades realmente disponibles.

### Objetivos

- Reunir nftables, iptables, ip6tables y Fail2Ban en una interfaz coherente.
- Facilitar la observación y la acción sobre las conexiones, los baneos y los eventos del sistema.
- Centralizar las exportaciones, las copias de seguridad, las auditorías y el historial de operaciones.
- Mantener una arquitectura testeable y extensible.
- Funcionar en modo degradado cuando falte un componente opcional.

### Qué hace Omega-Fire

- Detecta los backends, servicios, núcleo y herramientas disponibles.
- Administra nftables, iptables e ip6tables cuando estos componentes están presentes.
- Gestiona las IP baneadas, individualmente o en lotes, con importación, exportación, sincronización y flush.
- Crea, lista y elimina reglas avanzadas.
- Aplica políticas predefinidas con copia de seguridad automática previa.
- Administra los jails de Fail2Ban y sus baneos.
- Analiza los logs en vivo o en forma de estadísticas.
- Ofrece supervisión en forma de monitoreo.
- Utiliza conntrack para mostrar las conexiones activas cuando está disponible.
- Genera exportaciones en JSON, TXT y HTML.
- Guarda y restaura el estado completo en archivos `.tar.gz`.
- Registra las operaciones en un log de aplicación y una auditoría JSON estructurada.
- Supervisa los servicios y aplicaciones detectados: systemd, runit, OpenRC, Docker, servidores, VNC, etc.

### Qué no hace el proyecto

- No sustituye a nftables, iptables ni Fail2Ban.
- No constituye un cortafuegos autónomo independiente del sistema.
- No proporciona autenticación multiusuario.
- No expone ninguna API de red en funcionamiento normal.
- No es un panel (dashboard) web.
- No protege directamente una máquina remota desde otra máquina.
- No instala por defecto ningún archivo fuera de su propia carpeta.
- No garantiza la disponibilidad de todos los backends en todas las distribuciones.

---

## Funcionalidades

### 1. Capacidades y diagnósticos

- Visualización del registro de capacidades detectadas.
- Consulta detallada de una capacidad por identificador.
- Nuevo escaneo manual del sistema tras instalar un componente.
- Consulta de diagnósticos recientes.
- Consulta y búsqueda en el log de aplicación.
- Exportación del estado y los diagnósticos en JSON, TXT o HTML.

### 2. Gestión unificada de IP

La lista negra unificada permite trabajar con nftables e iptables desde una misma pantalla.

- Baneo de una IP o de una lista de IPs.
- Desbaneo individual o por lotes.
- Introducción directa o importación desde un archivo.
- Lista por backend o vista unificada.
- Sincronización entre los backends NFTables/IPTables.
- Exportación y reimportación de las listas.
- Limpieza completa de uno o varios backends.
- Compatibilidad con IPv4 e IPv6.
- Gestión de los archivos de lista de bloqueo (`var/blocklist/`) y de sus favoritos (pins) directamente desde la pantalla dedicada.

### 3. Gestión de reglas y políticas

- Asistente paso a paso para crear una regla avanzada.
- Lista de las reglas del sistema y de las reglas creadas por Omega-Fire.
- Eliminación de una regla por selección.
- Limpieza automática de las reglas inactivas en la base de referencia.
- Aplicación de políticas predefinidas.
- Copia de seguridad automática antes de aplicar una política.
- Personalización, guardado y restauración de una política.
- Identificación de la política activa en el menú de estado y en el dashboard.
- Señalización de los perfiles modificados en la forma `Perfil + CUSTOM`.

### 4. Gestión de Fail2Ban

- Estado detallado de los jails y sus parámetros.
- Número de IPs baneadas e información de límite de tasa (rate-limit).
- Búsqueda de una IP en los jails.
- Baneo y desbaneo individuales o múltiples.
- Transferencia de IPs entre jails, backends y archivos.
- Creación guiada de un jail personalizado.
- Plantillas de jails predefinidas.
- Eliminación de un jail.
- Vaciado de un jail o purga general.
- Exportación en JSON, TXT o HTML.
- Verificación y auditoría de configuración.
- Control del servicio: estado, inicio, parada, reinicio, activación y desactivación al arranque.

### 5. Logs y mantenimiento

- Live Tail con panel de control de Omega-Fire.
- Visualización multiarchivo con favoritos (fuentes preferidas, persistidas entre dos lanzamientos).
- Integración de `lnav`: selección de uno o varios archivos (números o rutas manuales, separados por comas), fusión automática en una sola vista cronológica, encapsulado en un header/footer de Omega-Fire (ver [Navegación](#navegación)).
- Análisis de las IPs más frecuentes con Top N.
- Limpieza específica de una IP en archivos LOG o TXT.
- Rotación y copias de seguridad inmediatas o automatizadas.
- Restauración de una copia de seguridad.
- Purga según antigüedad, cuota, tipo o selección manual.
- Limpieza avanzada por carpeta o entorno.
- Estadísticas sobre 24 horas, 7 días o 30 días.
- Análisis de los eventos, movimientos, cuotas e IPs presentes en los jails.

### 6. Exportaciones e informes

Formatos disponibles:

- **JSON**: datos estructurados y reutilizables.
- **TXT**: formato bruto o adaptado a la inyección.
- **HTML**: informe legible y visual.

Informes disponibles:

- Lista negra completa.
- Conjunto de reglas (ruleset) estructurado.
- Reglas seleccionadas por origen: sistema, Omega-Fire o activas.
- Informe de auditoría completo.
- Estadísticas de Fail2Ban.
- Estado y diagnósticos del sistema.
- Informes estadísticos sobre 7 o 30 días.

Temas HTML:

- `omega-base` — azul noche y cian, tema por defecto.
- `omega-burn` — brasa rojo-anaranjado.
- `omega-neon` — cyberpunk cian y magenta.
- `light-basic` — claro y sobrio.
- `light-alt` — papel crema y verde bosque.

### 7. Sistema y persistencia

- Copia de seguridad del estado completo: reglas, baneos nftables, baneos iptables y Fail2Ban.
- Creación de archivos `.tar.gz` con marca de tiempo.
- Lista y restauración de instantáneas (snapshots).
- Historial de acciones.
- Filtrado y purga del historial.
- Recarga de configuración y nuevo escaneo sin reiniciar.

### 8. Monitoreo y estadísticas

- Panel de control en tiempo real con actualización periódica (cada 2 segundos), sin bloquear la interfaz durante la recopilación.
- Visualización de la política activa.
- Conexiones activas vía conntrack.
- Tráfico, eventos, estadísticas y logs de servidor.
- Informes consolidados sobre 7 y 30 días.
- Exportación HTML de las instantáneas e informes.

### 9. Ajustes

- Elección del tema activo entre los diez temas `omega-*` compartidos con el resto de la suite (ver [Temas y terminales](#temas-y-terminales)), persistido entre dos lanzamientos.
- Sobrescritura manual del perfil de renderizado (automático, completo, estándar, reducido o mono únicamente), aplicada en el próximo lanzamiento.
- Accesible desde el menú principal (`9. AJUSTES`) o directamente mediante la tecla `s`.

---

## Arquitectura

```text
src/omega_fire/
├── app/              Bootstrap y contenedor de inyección de dependencias
├── core/             Capacidades, enumeraciones y excepciones
├── domain/           Lógica de negocio pura: reglas, IPs, jails, logs
├── application/      Orquestación: commands y queries
├── infrastructure/   Backends, almacenamiento, exportaciones, logs y sondas del sistema
├── ports/            Contratos Protocol/ABC
├── interfaces/       interfaces/tui/ (Textual, por defecto) + interfaces/cli/ (Rich, --legacy-cli)
├── plugins/          Extensiones integradas: nftables, iptables, Fail2Ban, conntrack
└── shared/           Parsing, red, formateo y utilidades transversales
```

### Principios de diseño

- `domain/` no contiene E/S ni dependencia hacia la infraestructura.
- `application/` orquesta los casos de uso a través del dominio y los puertos — las pantallas Textual y las acciones de la interfaz Rich llaman a los mismos commands/queries, la lógica de negocio no depende de ninguna de las dos interfaces.
- `infrastructure/` es la única capa autorizada a llamar a `nft`, `iptables`, `fail2ban-client` y demás herramientas externas (subprocess, pty, archivos).
- `interfaces/` no debe llamar directamente a `subprocess`.
- `ports/` define los contratos esperados por los adaptadores.
- `core/` proporciona el registro de capacidades utilizado por las distintas capas.
- Los plugins permiten añadir o hacer evolucionar los backends sin modificar el dominio de negocio.
- La interfaz Textual (`interfaces/tui/`) se apoya en [`omega-lib`](https://github.com/) (dependencia compartida por toda la suite OMEGA: tema de 9 tokens, detección de terminal, contratos de puerto comunes), no publicada en PyPI — vendorizada en el archivo distribuible (`vendor/omega-lib/`, ver [Instalación](#instalación)).
- Toda llamada potencialmente lenta (backend de firewall, `fail2ban-client`, disco) desencadenada desde una pantalla Textual se ejecuta en segundo plano (hilo), nunca en el hilo principal de la interfaz — un dashboard o un formulario permanece reactivo durante la operación en lugar de congelar toda la aplicación.

### Estructura de los datos

Omega-Fire utiliza SQLite a través de la biblioteca estándar `sqlite3`, sin ORM externo. Los principales conjuntos de datos conciernen a los baneos, reglas, eventos de auditoría e instantáneas.

Las migraciones están versionadas y se aplican automáticamente al arrancar.

---

## Requisitos previos

### Sistema

- Linux, con prioridad para Arch Linux y distribuciones compatibles.
- Python 3.10 o superior.
- Privilegios root disponibles vía `sudo`.
- Un gestor de servicios: systemd, runit u OpenRC.
- Al menos un backend de firewall: nftables o iptables.
- Un terminal de al menos 80x24 (ver [Temas y terminales](#temas-y-terminales) para el detalle de los perfiles de renderizado según el tamaño disponible).

### Dependencias de Python

Las dependencias de producción están definidas en `requirements.txt`:

- `textual` — interfaz TUI por defecto.
- `omega-lib` — tema, detección de terminal y contratos compartidos con la suite OMEGA (no publicada en PyPI, ver [Arquitectura](#arquitectura) e [Instalación](#instalación)).
- `rich` — renderizado de la interfaz `--legacy-cli` y de algunos informes.
- `psutil` — información del sistema (CPU, memoria, red, procesos) para el dashboard y los diagnósticos.
- `jinja2` — generación de las exportaciones HTML.
- `python-dotenv` — variables de entorno.
- `pyte` — emulador de terminal virtual, para la encapsulación de `lnav` (menús 5.9/8.6).

Las herramientas de calidad (`pytest`, `black`, `flake8`, `mypy`) están listadas como comentario en `requirements.txt`: descoméntelas o instálelas por separado si contribuye al proyecto (ver [Pruebas y calidad](#pruebas-y-calidad)).

### Herramientas opcionales recomendadas

La aplicación funciona en modo degradado si estas herramientas están ausentes:

- `fail2ban` — baneo automatizado.
- `conntrack` o `conntrack-tools` — conexiones activas y estadísticas de red.
- `lnav` — análisis avanzado y multiarchivo de los logs.

En Arch Linux y derivados:

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## Instalación

El archivo oficial se proporciona en formato `.tar.gz`. Verifique su integridad antes de instalar:

```bash
sha256sum omega-fire.tar.gz
```

### Método 1 — script de instalación

```bash
[ -d omega-fire ] && echo "ℹ️ Ya extraído aquí, paso omitido." || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire ya existe, movimiento omitido." || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

Lanzamiento:

```bash
./omega-fire.sh
```

Si se instaló el alias, abra una nueva terminal y use:

```bash
fire
```

### Método 2 — instalación completa resiliente

Este comando puede relanzarse: ignora los pasos ya realizados.

```bash
([ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire ya existe, extracción omitida." || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv ya existe, paso omitido." || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ Grupo omega-fire ya presente." || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER ya es miembro del grupo omega-fire." || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire instalado. Ejecute ./omega-fire.sh."
```

### Método 3 — instalación detallada

```bash
# 1. Extraer
[ -d omega-fire ] && echo "ℹ️ Ya extraído aquí, paso omitido." || tar -xzf omega-fire.tar.gz

# 2. Mover al home
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire ya existe, movimiento omitido." || mv omega-fire ~/

# 3. Entrar en el proyecto
cd ~/omega-fire/

# 4. Crear el entorno virtual
[ -d .venv ] && echo "ℹ️ .venv ya existe, creación omitida." || python3 -m venv .venv

# 5. Instalar las dependencias (omega-lib vendorizada, si está presente, antes de requirements.txt)
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. Hacer ejecutable el lanzador
chmod +x omega-fire.sh

# 7. Preparar var/ para root y el usuario actual
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. Lanzar
./omega-fire.sh
```

`vendor/omega-lib/` solo está presente en el archivo oficial (`build-release.sh` lo integra automáticamente, ya que omega-lib no está publicada en PyPI); en un clon de desarrollo, instálela por separado desde su propio repositorio (`pip install -e ruta/a/omega-lib`).

El grupo dedicado y el bit `setgid` permiten a root y al usuario compartir los archivos generados en `var/` sin abrir los permisos a todo el sistema. Puede ser necesaria una nueva sesión o `newgrp omega-fire` para beneficiarse inmediatamente de la pertenencia al grupo.

### Alias de Bash o Zsh

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

Recargue después el shell:

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Iconos y símbolos Nerd Fonts

Si los iconos no están disponibles, instale los símbolos Nerd Fonts:

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## Uso

### Lanzamiento

```bash
cd ~/omega-fire
./omega-fire.sh

# o simplemente, si se creó el alias:
fire
```

El lanzador:

1. Verifica los privilegios root y relanza vía `sudo` si es necesario.
2. Detecta `.venv`, `venv` o el Python del sistema.
3. Configura `PYTHONPATH` hacia `src/`.
4. Lanza `python -m omega_fire` — la interfaz **Textual**, por defecto.

Para lanzar la antigua interfaz Rich (introducción secuencial de números) en su lugar:

```bash
./omega-fire.sh --legacy-cli
```

### Recorrido general

1. Pantalla de inicio (splash), luego aviso si el terminal es demasiado pequeño.
2. Detección de las capacidades del sistema (pantalla dedicada, no bloqueante).
3. Menú principal: 8 secciones temáticas (1-8) más los ajustes (9).
4. Selección de una sección, luego de una acción — cada acción abre un formulario cuyos campos requeridos se validan antes de continuar.
5. Confirmación explícita antes de cualquier operación sensible o destructiva (flush, purga, restauración...).
6. Ejecución en segundo plano para las operaciones lentas (la interfaz permanece utilizable durante la espera), luego retorno al menú con un resumen del resultado.

### Navegación

- Flechas arriba/abajo: mover el cursor en una lista o un menú.
- Tab / Mayús+Tab: navegar entre los campos de un formulario.
- Intro: seleccionar o validar.
- Clic en una fila de una tabla: seleccionarla y pre-rellenar los campos correspondientes (fuente a marcar como favorita, jail objetivo, etc.).
- `Esc`: volver a la pantalla anterior (pide confirmación de salida desde el inicio).
- `a`: ayuda contextual — detalla la acción en curso, o la totalidad de las acciones de la sección actual si ninguna pantalla de acción está aún abierta.
- `t`: pasar al tema siguiente, sin confirmación.
- `r`: redetectar el tamaño y la familia del terminal.
- `s`: abrir los ajustes (tema, perfil de renderizado).
- `q` / `Ctrl+Q`: salir, con confirmación.

#### Particularidades de la pantalla lnav (5.9 / 8.6)

`lnav` está encapsulado en un pseudo-terminal con un header/footer de Omega-Fire persistentes alrededor de su propia vista, para evitar cualquier colisión entre sus atajos nativos y los de Omega-Fire:

- Flechas ↑↓: navegar en los logs (atajo nativo de `lnav`, transmitido tal cual).
- Flechas ←→: desplazarse horizontalmente en las líneas largas (atajo nativo de `lnav`).
- `g` / `G`: ir al principio / al final (atajo nativo de `lnav`).
- `Ctrl+C`: marcar la línea actual y copiarla al portapapeles del sistema (sustituye al comando nativo de copia de `lnav`, que puede bloquearse en algunos sistemas).
- `t` minúscula: tema siguiente, propio de esta vista (la `T` mayúscula sigue siendo el atajo nativo de `lnav` para mostrar el tiempo transcurrido entre líneas).
- `Ctrl+Q`: volver a Omega-Fire (cierra `lnav` limpiamente, sin salir de la aplicación).

---

## Temas y terminales

Diez temas `omega-*` se comparten con el resto de la suite OMEGA:

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- Cambie entre temas con `t`, o elija uno directamente desde los ajustes (`s`).
- El tema elegido se persiste y se recupera en el próximo lanzamiento.
- Omega-Fire adapta automáticamente la complejidad visual (bordes, splash, densidad de información) al terminal detectado mediante un **perfil de renderizado**: Completo, Estándar, Reducido o Mono (solo ASCII). El perfil puede sobrescribirse manualmente desde los ajustes.

| Tamaño mínimo | Perfil | Terminales típicos |
|---|---|---|
| 120×32 o más | Completo | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 o más | Estándar | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 o más | Reducido | urxvt, xterm, SSH moderno |
| por debajo de 80×24 | Mono (solo ASCII) | Linux TTY, SSH antiguo |

Por debajo de 80×24, se rechaza el lanzamiento (tamaño mínimo requerido); redimensione el terminal y relance, o use `r` tras redimensionar si la visualización no se ha actualizado automáticamente.

---

## Configuración

La configuración específica puede ajustarse en:

```text
omega-fire/config/omega-fire.conf
```

Puede definir en particular:

- rutas de los registros (logs);
- servidores y fuentes de monitoreo;
- backends disponibles o rutas personalizadas;
- entornos a analizar;
- parámetros adaptados a una instalación particular.

La configuración se relee al reiniciar o durante un nuevo escaneo manual (menú 1.3 o 7.4).

### Rutas internas y rutas del sistema

Por defecto, Omega-Fire trabaja en su propia carpeta:

```text
var/exports/       # carpeta interna del proyecto
/var/exports/      # ruta absoluta del sistema
```

La `/` inicial es, por tanto, significativa. Las importaciones y exportaciones hacia el sistema deben ser solicitadas explícitamente por el usuario.

---

## Backends y compatibilidad

Omega-Fire detecta los componentes y activa únicamente las funcionalidades utilizables.

| Componente | Rol | Estado |
|---|---|---|
| nftables | Cortafuegos IPv4/IPv6 moderno | Recomendado |
| iptables | Cortafuegos IPv4 | Compatible |
| ip6tables | Cortafuegos IPv6 con iptables | Compatible si está disponible |
| Fail2Ban | Jails y baneos automatizados | Opcional |
| conntrack | Conexiones activas | Opcional |
| lnav | Análisis avanzado de logs | Opcional |
| systemd, runit, OpenRC | Gestión de servicios | Detección automática |
| Docker, VNC, servidores | Aplicaciones y servicios detectados | Según instalación |

### IPv4 e IPv6

Ambas familias de direcciones son compatibles con los backends que las soportan:

- nftables: IPv4 e IPv6 en dual stack;
- iptables/ip6tables: según los binarios disponibles;
- Fail2Ban: según la configuración del jail y del sistema.

Los formatos IPv6 largos, comprimidos, locales, mixtos, con ceros y en notación CIDR son procesados por los componentes correspondientes.

---

## Persistencia, logs y exportaciones

### Persistencia

- SQLite a través de `sqlite3`.
- Tablas relativas a los baneos, reglas, auditorías e instantáneas.
- Migraciones versionadas aplicadas automáticamente.
- Archivos de estado completo en formato `.tar.gz`.
- Favoritos (fuentes de logs preferidas) e historial reciente persistidos en JSON (`var/runtime/`), sobreviven a un reinicio.

### Registros (logs)

- Log de texto de la aplicación: `var/logs/app.log`.
- Log de auditoría JSON estructurado con, en particular, `event_type`, `actor`, `action`, `result` y `details`.

### Exportaciones

Las exportaciones están disponibles en JSON, TXT y HTML, con varios temas CSS para los informes HTML.

---

## Seguridad

Omega-Fire actúa sobre componentes críticos del sistema y debe utilizarse con prudencia.

- El lanzamiento requiere privilegios root vía `sudo`.
- El flush, la purga general y la aplicación de una política pueden ser destructivos.
- Una política predefinida desencadena una copia de seguridad automática antes de la modificación.
- Realice una copia de seguridad manual antes de cada cambio importante.
- Verifique el estado real del cortafuegos, de los jails y de las conexiones después de cada operación.
- Pruebe primero en una máquina o un objetivo desechable.
- Utilice las redes de documentación RFC 5737 para las pruebas IPv4: `192.0.2.0/24`, `198.51.100.0/24` y `203.0.113.0/24`.
- Verifique las exportaciones e instantáneas antes de restaurarlas en una máquina de producción.
- No conceda permisos más amplios de lo necesario a la carpeta `var/`.

---

## Pruebas y calidad

El proyecto cuenta con una suite histórica de 152 pruebas unitarias, escrita antes de la migración a Textual: cubre el dominio de negocio, la orquestación (`application/`), la infraestructura y la interfaz Rich (`interfaces/cli/`), pero **aún no cubre `interfaces/tui/`** (la interfaz Textual por defecto). Este archivo no contiene la carpeta `tests/`: recupérela desde su repositorio de desarrollo si necesita ejecutarla.

```bash
source .venv/bin/activate
python -m unittest discover tests/unit -v
```

Como la arquitectura en capas separa estrictamente el dominio de negocio de la presentación (`domain/`, `application/`, `ports/` en `Protocol`, ver [Arquitectura](#arquitectura)), esta suite sigue siendo válida sin cambios pese a la migración: solo la interfaz Textual, más reciente, aún no tiene su propia cobertura dedicada.

Si contribuye al proyecto, instale las herramientas de calidad declaradas (como comentario) en `requirements.txt`:

```bash
pip install pytest pytest-cov black flake8 mypy
```

Herramientas disponibles una vez instaladas:

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## Estado del proyecto

### Puntos operativos

- TUI Textual unificada para los principales mecanismos de seguridad de red, formularios validados, temas y ayuda contextual compartidos con la suite OMEGA.
- Interfaz Rich histórica conservada como respaldo (`--legacy-cli`).
- Detección automática de las capacidades.
- Gestión de los backends disponibles.
- Soporte IPv4/IPv6 según las herramientas presentes.
- Registro (logging) de aplicación y auditoría.
- Copia de seguridad y restauración.
- Exportaciones JSON, TXT y HTML.
- Dashboard y estadísticas, actualizados en segundo plano sin bloquear la interfaz.
- Arquitectura en capas documentada.

### Limitaciones conocidas

- La suite de pruebas (152) aún no cubre la interfaz Textual (`interfaces/tui/`), escrita después de ella (ver [Pruebas y calidad](#pruebas-y-calidad)).
- El mecanismo `ExecutionPlan`/`PipelineStep` se mantiene parcialmente conservado en el proyecto.
- La disponibilidad exacta de las funcionalidades depende de los binarios, servicios, permisos y configuraciones de la máquina anfitriona.
- La interfaz Rich histórica (`--legacy-cli`) ya no es el eje de desarrollo activo; se conserva mientras se termina de consolidar totalmente la interfaz Textual en condiciones reales.

---

## Desinstalación

Si los datos permanecen en la carpeta del proyecto:

```bash
sudo rm -rf ~/omega-fire
```

Elimine manualmente los archivos exportados a otros lugares, los eventuales alias `fire` añadidos en `~/.bashrc` o `~/.zshrc`, así como el grupo dedicado si ya no se utiliza:

```bash
sudo groupdel omega-fire
```

Ejecute este último comando únicamente si ningún otro archivo o servicio depende de ese grupo.

---

## Licencia

Omega-Fire se distribuye bajo licencia **MIT**. Consulte el archivo [`LICENSE`](LICENSE) para el texto completo.

---

> **Omega-Fire — Observar, pilotar, auditar, asegurar.**
>
> Una interfaz TUI unificada para nftables, iptables, ip6tables, Fail2Ban, los logs y el monitoreo de red.
