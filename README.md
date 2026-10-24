# 🔌 PLC Academy - PLC_APP

Una aplicación web interactiva para aprender programación de PLC Industrial (Ladder Logic) desde cualquier dispositivo, especialmente optimizada para practicar desde el celular.

## 🚀 Características Principales
- **Simulador Ladder Interactivo:** Arma rungs con contactos NA/NC y bobinas. Observa el flujo de energía en tiempo real.
- **Autenticación Segura:** Sistema de registro e inicio de sesión gestionado por Supabase Auth.
- **Persistencia en la Nube:** Guarda y carga tus proyectos (rungs y estados) directamente en la base de datos.
- **Seguridad Basada en Roles (RBAC):** Implementación de políticas RLS (Row Level Security) y JWT Claims para separar a los usuarios en roles de `admin` y `student`. Los administradores pueden ver todos los proyectos; los estudiantes solo los suyos.
- **Diseño Mobile-First:** Interfaz adaptada con pestañas y controles táctiles grandes.

## 🛠️ Stack Tecnológico
- **Frontend/Backend:** [Streamlit](https://streamlit.io/) (Python)
- **Base de Datos y Auth:** [Supabase](https://supabase.com/) (PostgreSQL + RLS)
- **Lenguaje:** Python 3.9+

## 🗄️ Esquema de Base de Datos (Supabase)
El proyecto utiliza las siguientes tablas en Supabase:
- `profiles`: Almacena información del usuario (XP, nivel).
- `projects`: Almacena los programas Ladder en formato JSON.
- `user_roles`: Gestiona los permisos (`admin` o `student`).

## ⚙️ Cómo ejecutar localmente
1. Clona este repositorio:
   ```bash
   git clone https://github.com/TU-USUARIO/plc-academy.git
