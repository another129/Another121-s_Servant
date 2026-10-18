# Another121's Servant

**Asistente personal de Telegram desarrollado en Python para la automatización de tareas y la integración con servicios externos.**

## Descripción

Another121's Servant es un proyecto personal de desarrollo de software enfocado en la automatización de procesos mediante un bot de Telegram.

El proyecto utiliza Python, la API de Telegram y la integración con Google Tasks para gestionar tareas desde una interfaz de mensajería.

Fue desarrollado en un entorno Linux, utilizando CachyOS (basado en Arch Linux), con el objetivo de explorar la programación de bots, las APIs, la ejecución de procesos y la automatización.

## Tecnologías utilizadas

| Tecnología | Aplicación |
|---|---|
| Python | Desarrollo de la lógica del bot |
| Telegram Bot API | Comunicación mediante Telegram |
| BotFather | Creación y configuración del bot |
| Google Tasks API | Integración con tareas |
| Google OAuth 2.0 | Autorización para acceder a Google Tasks |
| Linux / CachyOS | Entorno de desarrollo |
| Bash | Administración y ejecución desde terminal |
| Git y GitHub | Control de versiones |

## Características

- Integración de un bot de Telegram con servicios externos.
- Comunicación y recepción de mensajes mediante Telegram.
- Integración con Google Tasks para consultar y administrar tareas.
- Autenticación mediante OAuth 2.0 para servicios de Google.
- Gestión de credenciales mediante archivos locales y variables de entorno.
- Desarrollo y ejecución desde un entorno Linux.

## Arquitectura general

```text
                 USUARIO
                    |
                    v
                TELEGRAM
                    |
                    v
             TELEGRAM BOT API
                    |
                    v
             APLICACIÓN PYTHON
                    |
          +---------+---------+
          |                   |
          v                   v
    LÓGICA DEL BOT       GOOGLE TASKS API
          |                   |
          v                   v
    AUTOMATIZACIÓN       GESTIÓN DE TAREAS
```

## Estructura del proyecto

```text
Another121Servant/
|
|-- bot.py
|-- another121servant_tasks_bot.py
|-- .gitignore
```

**bot.py:** archivo principal de implementación del bot.

**another121servant_tasks_bot.py:** implementación de funcionalidades relacionadas con la integración de tareas.

**.gitignore:** exclusión de archivos temporales y datos locales que no deben publicarse.

## Instalación y configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/another129/Another121-s_Servant.git
cd Another121-s_Servant
```

### 2. Preparar el entorno Python

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Instalar las dependencias

Las dependencias deben instalarse de acuerdo con las importaciones y versiones utilizadas en el código.

Se recomienda mantener un archivo `requirements.txt` para facilitar la instalación reproducible.

### 4. Configurar Telegram

Crear un bot mediante [BotFather](https://t.me/BotFather) y obtener el token de acceso.

Configurar el token como variable de entorno:

```bash
export TG_TOKEN="TU_TOKEN_DE_TELEGRAM"
```

No publicar el token ni almacenarlo directamente en el repositorio.

### 5. Configurar Google Tasks

La integración con Google Tasks requiere configurar credenciales OAuth 2.0 mediante Google Cloud.

Los archivos de credenciales y tokens de acceso deben mantenerse fuera del control de versiones.

### 6. Ejecutar el bot

```bash
python bot.py
```

La ejecución requiere haber instalado las dependencias y configurado previamente los servicios necesarios.

## Fundamento técnico

El proyecto permite aplicar conceptos de ingeniería de software:

- Programación en Python.
- Programación asíncrona.
- Integración de APIs.
- Autenticación y autorización.
- Automatización de procesos.
- Manejo de errores y ejecución de servicios.
- Administración de sistemas Linux.

## Seguridad

Este repositorio no debe incluir:

- Tokens de Telegram.
- Contraseñas o claves privadas.
- Credenciales OAuth de Google.
- Tokens de acceso o actualización.
- Archivos con información personal.
- Configuraciones que permitan acceso remoto no autorizado.

Se recomienda aplicar controles de autorización antes de permitir que un bot ejecute operaciones sobre el sistema anfitrión.

## Posibles mejoras

- Incorporar pruebas automatizadas.
- Añadir registro estructurado de eventos.
- Mejorar el manejo de errores.
- Documentar las dependencias en `requirements.txt`.
- Implementar controles de acceso por usuario.
- Preparar el proyecto para despliegue como servicio Linux.
- Ampliar las integraciones con herramientas externas.

## Autor

**another129**

Estudiante de Ingeniería Mecatrónica — Universidad del Valle de Guatemala (UVG).

Intereses: programación, automatización, matemáticas aplicadas, inteligencia artificial e integración de sistemas.

## Repositorio

[Another121's Servant en GitHub](https://github.com/another129/Another121-s_Servant)
