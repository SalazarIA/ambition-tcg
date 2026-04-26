# Ambitionz

Ambitionz é um protótipo beta de TCG online com combate elemental, coleção, deck builder, boosters, arena 1v1 e preparação para Android, iOS e Steam/Desktop.

## Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-SocketIO
- PostgreSQL em produção
- SQLite local
- HTML/CSS/JavaScript
- PWA
- Capacitor para Android/iOS
- Futuro wrapper desktop para Steam

## Rodar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py