<div align="center">

# 🗡️ Ashen Emporium

[![Heroku Deployment](https://img.shields.io/badge/Heroku-Live%20App-79589F?style=for-the-badge&logo=heroku&logoColor=white)](https://ashen-emporium-ecommerce-533460192970.herokuapp.com/)
![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2-darkgreen?style=for-the-badge&logo=django&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-purple?style=for-the-badge&logo=bootstrap&logoColor=white)
![Stripe](https://img.shields.io/badge/Stripe-Payments-635BFF?style=for-the-badge&logo=stripe&logoColor=white)

![Platform](https://img.shields.io/badge/Platform-Web_App-black?style=for-the-badge)
![Database](https://img.shields.io/badge/Database-SQLite-lightgrey?style=for-the-badge&logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Portfolio_Project-success?style=for-the-badge)
![Coverage](https://img.shields.io/codecov/c/github/TGOSS1984/ashen-emporium?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

![Tests](https://github.com/TGOSS1984/ashen-emporium/actions/workflows/tests.yml/badge.svg)




</div>

**A Souls-inspired e-commerce platform built with Django**

Ashen Emporium is a full-stack Django application that combines automated content ingestion, rich lore presentation, and real-world e-commerce functionality into a cohesive, extensible retail platform inspired by Souls-like RPGs.

This project emphasises **scalable architecture, automation over manual admin work, and production-ready patterns**, making it suitable as both a portfolio piece and a foundation for future expansion.

---

## 📑 Table of Contents

- [Live Demo](#-live-demo)
- [Project Overview](#-project-overview)
- [Core Features](#-core-features)
  - [E-commerce](#-e-commerce)
  - [Armour Sets](#-armour-sets-advanced-domain-logic)
  - [Lore System](#-lore-system)
  - [Automation & Data Pipelines](#-automation--data-pipelines)
  - [Frontend & UX](#-frontend--ux)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure-simplified)
- [Local Setup](#-local-setup)
- [Asset & Lore Workflows](#-asset--lore-workflows)
- [Testing & Safety](#-testing--safety)
- [Deployment Notes](#-deployment-notes)
- [Licensing & Assets](#-licensing--assets)
- [Author](#-author)
- [Next Possible Enhancements](#-next-possible-enhancements)

---

## 🔥 Live Demo

> Deployment prepared (Heroku-ready).  
> Production upload of media assets intentionally deferred (see Licensing section).

---

## 📜 Project Overview

The goal of Ashen Emporium is to model how a large, content-heavy catalogue (weapons, armour, spells, sets) can be:

- ingested automatically from external asset libraries  
- enriched with lore and metadata  
- presented through a modern, mobile-friendly UI  
- sold using realistic checkout and stock-control logic  

The project deliberately mirrors challenges found in real retail systems:
- bundles and sets
- partial availability
- shared components
- automated classification
- safe bulk operations

---

## ✨ Core Features

### 🛒 E-commerce

- Product catalogue with search, filtering, and pagination
- Session-based shopping cart with quantity management
- Stripe Checkout integration (test mode)
- Stock-aware purchasing and validation
- Cart badge counts via context processors

---

### 🛡️ Armour Sets (Advanced Domain Logic)

Armour pieces are automatically grouped into **Armour Sets** (e.g. *Alberich’s Set*) using filename and name analysis.

Each set provides:
- a dedicated set detail page
- hero image selection
- image gallery switching
- per-piece availability status
- bundle pricing with automatic discount
- ability to:
  - add the full set
  - or add **only missing pieces** already not owned

Shared components (e.g. gauntlets used by multiple variants) are handled via rule-based distribution without manual intervention.

---

### 📚 Lore System

Lore text is imported from structured text files and automatically matched to products using fuzzy name matching.

Features:
- short lore snippets shown on catalogue cards
- full lore displayed on product detail pages
- configurable confidence thresholds
- dry-run mode with CSV reporting
- protection against duplicate overwrites

This allows large volumes of narrative content to be safely attached to products without manual admin editing.

---

### 🧠 Automation & Data Pipelines

The platform prioritises **repeatable automation** over one-off scripts.

Implemented management commands include:
- bulk asset ingestion
- catalogue building from assets
- armour set construction
- lore importing with confidence scoring
- subtype auto-tagging (e.g. cloth / leather / plate)
- safe synchronisation between product groups and sets

All commands support dry-run or reporting modes where appropriate.

---

### 🎨 Frontend & UX

- Bootstrap 5 responsive layout
- Mobile-first navigation with off-canvas menus
- Font Awesome icons for cart and account actions
- Persistent search with filter state retention
- Dark, Souls-inspired visual theme

The UI balances atmosphere with usability, particularly on smaller screens.

---

## 🧱 Technology Stack

| Layer | Technology |
|-----|-----------|
| Backend | Django 4.2 |
| Database | SQLite (dev), PostgreSQL-ready |
| Frontend | Bootstrap 5, HTML, CSS |
| Payments | Stripe Checkout |
| Media | Local storage (Cloudinary-ready) |
| Auth | Django Auth |
| Deployment | Heroku (prepared) |

---

## 🗂️ Project Structure (Simplified)

ashen-emporium/
├── accounts/ # Authentication & user flows
├── catalog/ # Products, armour sets, lore, filters
│ └── management/commands/
│ ├── import_assets.py
│ ├── import_lore.py
│ ├── build_armour_sets.py
│ └── auto_tag_subtypes.py
├── cart/ # Basket logic
├── orders/ # Order records
├── payments/ # Stripe integration
├── templates/
├── static/
├── media/
└── README.md


---

## 🛠️ Local Setup

### 1️⃣ Clone & Install

```bash
git clone https://github.com/yourusername/ashen-emporium.git
cd ashen-emporium
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

```

2️⃣ Environment Variables
Create a .env file:

```bash
SECRET_KEY=your-secret-key
DEBUG=True
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

```

3️⃣ Migrate & Run

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

```

📦 Asset & Lore Workflows
Import Assets

```bash
python manage.py import_assets \
  --source ashen-assets \
  --publish \
  --stock 5 \
  --price 1299

```

Import Lore (Safe Preview)

```bash
python manage.py import_lore --dry-run --threshold 0.93
```

Apply lore updates:
```bash
python manage.py import_lore --threshold 0.93
```

Build Armour Sets
```bash
python manage.py build_armour_sets --dry-run
python manage.py build_armour_sets
```
---

## 🧪 Testing & Safety

Manual functional testing of:

- cart flows

- bundle pricing

- stock enforcement

- Bulk operations protected via:

- dry-run modes

- CSV audit reports

- Idempotent commands allow safe re-execution

---

## 🚀 Deployment Notes
Heroku configuration prepared

- Whitenoise enabled for static assets

- Cloudinary support optional and switchable

- Production asset upload intentionally deferred

---

## ⚠️ Licensing & Assets
This project is educational and portfolio-focused.

- No copyrighted game assets are distributed

- Visuals are placeholders or user-owned

- All logic, architecture, and automation are original

---

## 👤 Author

Tom Goss
Full-Stack Developer (Django · Data · Analytics)

This project reflects a focus on realistic system design, automation, and maintainable Django architecture rather than surface-level demos.