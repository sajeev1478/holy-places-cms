# 🪷 Holy Places CMS

A comprehensive spiritual knowledge hub for India's holy places with a beautiful **Lotus Bloom** themed frontend and full-featured admin panel.

---

## ✨ Features

### Frontend (Lotus Bloom Theme)
- **Responsive** homepage with hero, featured places, stories, audio player, newsletter
- **Explore page** with search, tag filters, state filters, pagination
- **Place detail** pages with rich content, gallery, audio, video, map, nearby places, related content
- **Module pages** for Sacred Stories, Festivals, Bhajans, Pilgrimage Guides, etc.
- **Entry detail** pages with rich content and media
- **PWA-ready** with manifest.json for future mobile app conversion
- **SEO-friendly** URLs and meta tags

### Admin Panel
- **Dashboard** with stats, recent activity, module overview
- **Holy Places CRUD** — create, edit, delete with rich text editor (Quill.js)
- **Dynamic Module Builder** — create unlimited content modules (Stories, Festivals, Bhajans, etc.)
- **Module Entries** — create content entries linked to places or standalone
- **Media Library** — upload images, audio, video with folder organization
- **Tags & Categories** — color-coded tags for filtering places
- **User Management** — Super Admin, Content Admin, Editor roles
- **Granular Permissions** — 9 permission types configurable per user
- **Audit Log** — tracks all admin actions

### REST API (for Mobile Apps)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/places` | GET | List places (paginated, filterable) |
| `/api/v1/places/<slug>` | GET | Place detail with tags, nearby, entries |
| `/api/v1/modules` | GET | List active modules |
| `/api/v1/modules/<slug>/entries` | GET | Module entries (paginated) |
| `/api/v1/search?q=...` | GET | Search places and entries |

---

## 🚀 Quick Start

### Requirements
- Python 3.10+
- Flask 3.x
- Pillow (for image handling)

### Installation
```bash
# Install dependencies
pip install flask pillow

# Run the server
python app.py
```

### Access
| URL | Description |
|-----|-------------|
| `http://localhost:5000` | Frontend website |
| `http://localhost:5000/admin` | Admin panel |
| `http://localhost:5000/api/v1/places` | REST API |

### Demo Credentials
| Role | Username | Password |
|------|----------|----------|
| Super Admin | `admin` | `admin123` |
| Editor | `editor` | `editor123` |

---

## 📁 Project Structure
```
holy-places/
├── app.py                      # Main Flask application (routes, API, auth)
├── holyplaces.db               # SQLite database (auto-created)
├── static/
│   ├── manifest.json           # PWA manifest
│   └── uploads/                # User-uploaded media
│       ├── images/
│       ├── audio/
│       └── video/
└── templates/
    ├── frontend/
    │   ├── base.html           # Lotus Bloom theme base (header, footer, CSS)
    │   ├── home.html           # Homepage
    │   ├── explore.html        # Search & browse places
    │   ├── place.html          # Individual place detail
    │   ├── module.html         # Module content listing
    │   ├── entry.html          # Individual entry detail
    │   └── 404.html            # Error page
    └── admin/
        ├── base.html           # Admin layout (sidebar, topbar, CSS)
        ├── login.html          # Admin login
        ├── dashboard.html      # Dashboard with stats
        ├── places.html         # Places list
        ├── place_form.html     # Place create/edit form
        ├── modules.html        # Module builder
        ├── module_form.html    # Module create/edit form
        ├── entries.html        # Module entries list
        ├── entry_form.html     # Entry create/edit form
        ├── media.html          # Media library
        ├── users.html          # User management
        ├── user_form.html      # User create/edit form
        └── tags.html           # Tags management
```

---

## 🗄️ Database Schema
- **users** — Authentication, roles, permissions
- **modules** — Dynamic content modules with custom field schemas
- **places** — Holy places with location, rich content, coordinates
- **module_entries** — Content entries linked to modules and places
- **media** — Centralized media library (images, audio, video)
- **tags** — Color-coded categorization system
- **place_tags** — Many-to-many place-tag relationships
- **place_media / entry_media** — Media attachments
- **nearby_places** — Place proximity relationships
- **audit_log** — Admin action tracking

---

## 🎨 Theme: Lotus Bloom
- **Colors:** Rose (#E8A0BF), Cream (#FDF8F3), Sage (#8BAB8A), Saffron (#E89B4F)
- **Fonts:** Playfair Display (headings), Lora (body), DM Sans (UI)
- **Style:** Soft organic design with rounded cards, floating blobs, warm pastels

---

## 📱 Mobile App Conversion
The project is PWA-ready and includes a full REST API layer. To convert to native apps:
1. Use the REST API endpoints with React Native, Flutter, or Capacitor
2. The PWA manifest allows "Add to Home Screen" on Android/iOS
3. All content is API-driven for easy mobile consumption

---

## 🔒 Security Notes
⚠️ For production deployment:
- Change `SECRET_KEY` in app.py
- Replace SHA-256 password hashing with bcrypt
- Add CSRF protection (Flask-WTF)
- Add rate limiting
- Use PostgreSQL/MySQL instead of SQLite
- Enable HTTPS
- Add input sanitization for rich content
