"""
Holy Places CMS - Main Application
A comprehensive spiritual knowledge hub with modular CMS architecture.
"""

import os
import json
import uuid
import hashlib
import sqlite3
import functools
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, jsonify, send_from_directory, abort, g
)

# ─── Configuration ───────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'holyplaces-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'holyplaces.db')

ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
ALLOWED_AUDIO_EXT = {'mp3', 'wav', 'ogg', 'aac'}
ALLOWED_VIDEO_EXT = {'mp4', 'webm', 'mov'}

# ─── Database ────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript('''
    -- Users table with role-based access
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'editor',
        permissions TEXT DEFAULT '{}',
        is_active INTEGER DEFAULT 1,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    );

    -- Dynamic modules system
    CREATE TABLE IF NOT EXISTS modules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT,
        icon TEXT DEFAULT '📁',
        sort_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        fields_schema TEXT DEFAULT '[]',
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    );

    -- Holy places (main content)
    CREATE TABLE IF NOT EXISTS places (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        short_description TEXT,
        full_content TEXT,
        state TEXT,
        city TEXT,
        country TEXT DEFAULT 'India',
        latitude REAL,
        longitude REAL,
        featured_image TEXT,
        status TEXT DEFAULT 'draft',
        is_featured INTEGER DEFAULT 0,
        view_count INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    );

    -- Module entries (content for each module)
    CREATE TABLE IF NOT EXISTS module_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module_id INTEGER NOT NULL,
        place_id INTEGER,
        title TEXT NOT NULL,
        slug TEXT NOT NULL,
        content TEXT,
        custom_fields TEXT DEFAULT '{}',
        featured_image TEXT,
        status TEXT DEFAULT 'draft',
        sort_order INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE,
        FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE SET NULL,
        FOREIGN KEY (created_by) REFERENCES users(id)
    );

    -- Media library
    CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        mime_type TEXT,
        file_size INTEGER,
        folder TEXT DEFAULT 'general',
        alt_text TEXT,
        caption TEXT,
        uploaded_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (uploaded_by) REFERENCES users(id)
    );

    -- Place-media relationships
    CREATE TABLE IF NOT EXISTS place_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id INTEGER NOT NULL,
        media_id INTEGER NOT NULL,
        media_role TEXT DEFAULT 'gallery',
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
        FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE
    );

    -- Entry-media relationships
    CREATE TABLE IF NOT EXISTS entry_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER NOT NULL,
        media_id INTEGER NOT NULL,
        media_role TEXT DEFAULT 'gallery',
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (entry_id) REFERENCES module_entries(id) ON DELETE CASCADE,
        FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE
    );

    -- Place categories/tags
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT,
        color TEXT DEFAULT '#C76B8F'
    );

    CREATE TABLE IF NOT EXISTS place_tags (
        place_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        PRIMARY KEY (place_id, tag_id),
        FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
    );

    -- Nearby places relationships
    CREATE TABLE IF NOT EXISTS nearby_places (
        place_id INTEGER NOT NULL,
        nearby_place_id INTEGER NOT NULL,
        distance_km REAL,
        PRIMARY KEY (place_id, nearby_place_id),
        FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
        FOREIGN KEY (nearby_place_id) REFERENCES places(id) ON DELETE CASCADE
    );

    -- Admin permission definitions (set by super admin)
    CREATE TABLE IF NOT EXISTS permission_definitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        permission_key TEXT UNIQUE NOT NULL,
        label TEXT NOT NULL,
        description TEXT,
        category TEXT DEFAULT 'general'
    );

    -- Audit log
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity_type TEXT,
        entity_id INTEGER,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    ''')
    db.commit()

def seed_db():
    """Seed database with initial data."""
    db = get_db()
    
    # Check if already seeded
    user = db.execute("SELECT id FROM users LIMIT 1").fetchone()
    if user:
        return
    
    # Create super admin
    admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    db.execute("""
        INSERT INTO users (username, email, password_hash, display_name, role, permissions)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ('admin', 'admin@holyplaces.com', admin_hash, 'Super Admin', 'super_admin',
          json.dumps({"all": True})))
    
    # Create editor user
    editor_hash = hashlib.sha256('editor123'.encode()).hexdigest()
    db.execute("""
        INSERT INTO users (username, email, password_hash, display_name, role, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ('editor', 'editor@holyplaces.com', editor_hash, 'Content Editor', 'editor', 1))
    
    # Create default modules
    default_modules = [
        ('Holy Places', 'holy-places', 'Sacred destinations and temples', '🛕', 1),
        ('Temples', 'temples', 'Detailed temple profiles', '🏛️', 2),
        ('Sacred Stories', 'sacred-stories', 'Mythological tales and legends', '📖', 3),
        ('Festivals', 'festivals', 'Celebrations and religious events', '🎪', 4),
        ('Pilgrimage Guides', 'pilgrimage-guides', 'Routes and travel guides', '🚶', 5),
        ('Events', 'events', 'Upcoming spiritual events', '📅', 6),
        ('Bhajans & Kirtans', 'bhajans-kirtans', 'Devotional music and audio', '🎵', 7),
        ('Spiritual Articles', 'spiritual-articles', 'In-depth spiritual writings', '📝', 8),
    ]
    for name, slug, desc, icon, order in default_modules:
        db.execute("""
            INSERT INTO modules (name, slug, description, icon, sort_order, is_active, created_by)
            VALUES (?, ?, ?, ?, ?, 1, 1)
        """, (name, slug, desc, icon, order))
    
    # Create default tags
    tags = [
        ('Char Dham', 'char-dham', '#C76B8F'),
        ('Jyotirlinga', 'jyotirlinga', '#E89B4F'),
        ('Heritage', 'heritage', '#8BAB8A'),
        ('Pilgrimage', 'pilgrimage', '#6B8AB5'),
        ('UNESCO', 'unesco', '#B58A6B'),
        ('Sikh Heritage', 'sikh-heritage', '#C4A44E'),
        ('Buddhist', 'buddhist', '#8A6BB5'),
        ('Jain Sacred', 'jain-sacred', '#6BB58A'),
    ]
    for name, slug, color in tags:
        db.execute("INSERT INTO tags (name, slug, color) VALUES (?, ?, ?)", (name, slug, color))
    
    # Create sample holy places
    places = [
        ('Kedarnath Temple', 'kedarnath-temple', 'One of the twelve Jyotirlingas of Lord Shiva, nestled in the Himalayas at 11,755 feet.',
         '<h2>The Sacred Abode of Lord Shiva</h2><p>Kedarnath Temple is one of the holiest Hindu temples dedicated to Lord Shiva. Located in the Garhwal Himalayan range near the Mandakini river, it is one of the four sites in India\'s Chota Char Dham pilgrimage.</p><h3>History & Legend</h3><p>The temple is believed to have been built by the Pandavas and later revived by Adi Shankaracharya in the 8th century CE. According to legend, the Pandavas sought Lord Shiva here to seek forgiveness for their sins during the Kurukshetra war. Lord Shiva, trying to avoid them, took the form of a bull and dove into the ground. His hump remained at Kedarnath, while other body parts appeared at four other locations, now known as the Panch Kedar.</p><h3>Architecture</h3><p>Built of large, heavy, evenly cut grey stone slabs, the temple presents an impressive sight with the backdrop of towering snow-clad peaks. The temple structure showcases the typical North Indian style of architecture with a conical shikhara.</p>',
         'Uttarakhand', 'Rudraprayag', 'India', 30.7352, 79.0669, 'published', 1),
        ('Somnath Temple', 'somnath-temple', 'The first among the twelve Jyotirlinga shrines of Lord Shiva, rebuilt through the ages.',
         '<h2>The Eternal Shrine</h2><p>Somnath Temple, located at the shore of the Arabian Sea in Veraval, Gujarat, is believed to be the first among the twelve Jyotirlinga shrines of Lord Shiva. It is an important pilgrimage and tourist spot of India.</p><h3>Legends</h3><p>According to tradition, the Somnath temple was first built by the Moon God (Soma) himself in gold, then rebuilt by Ravana in silver, then by Krishna in wood, and finally by Bhimdeva in stone.</p>',
         'Gujarat', 'Veraval', 'India', 20.8880, 70.4012, 'published', 1),
        ('Meenakshi Amman Temple', 'meenakshi-amman-temple', 'A historic Hindu temple with stunning Dravidian architecture and 14 magnificent gopurams.',
         '<h2>Marvel of Dravidian Architecture</h2><p>The Meenakshi Amman Temple is a historic Hindu temple located on the southern bank of the Vaigai River in the temple city of Madurai, Tamil Nadu. It is dedicated to Meenakshi, a form of Parvati, and her consort, Sundareshwar, a form of Shiva.</p><h3>The 14 Gopurams</h3><p>The temple complex spans 14 acres and has 14 gateway towers (gopurams), the tallest of which is the southern tower, reaching approximately 170 feet. Each gopuram is a riot of colors, covered with thousands of stucco figures of deities, mythical animals, and monsters.</p>',
         'Tamil Nadu', 'Madurai', 'India', 9.9195, 78.1193, 'published', 1),
        ('Varanasi Ghats', 'varanasi-ghats', 'The oldest living city where the Ganges washes away lifetimes of karma.',
         '<h2>City of Light</h2><p>Varanasi, also known as Kashi or Banaras, is one of the oldest continuously inhabited cities in the world. Situated on the banks of the holy Ganges, it is the spiritual capital of India.</p><h3>The Sacred Ghats</h3><p>There are around 88 ghats in Varanasi, most of which are used for bathing and Hindu puja ceremonies, while two are used exclusively as cremation grounds. The most famous ghats include Dashashwamedh Ghat, Manikarnika Ghat, Assi Ghat, and Tulsi Ghat.</p>',
         'Uttar Pradesh', 'Varanasi', 'India', 25.3176, 83.0078, 'published', 1),
        ('Golden Temple', 'golden-temple', 'The holiest Gurdwara of Sikhism, a symbol of equality and spiritual devotion.',
         '<h2>Harmandir Sahib</h2><p>The Golden Temple, also known as Sri Harmandir Sahib or Darbar Sahib, is a Gurdwara located in the city of Amritsar, Punjab. It is the preeminent spiritual site of Sikhism and one of the most visited religious sites in the world.</p><h3>Architecture & Design</h3><p>The temple sits on a 67-foot square of marble and is a two-story marble structure with a dome of pure gold. The upper floors and dome are decorated with around 750 kg of pure gold.</p>',
         'Punjab', 'Amritsar', 'India', 31.6200, 74.8765, 'published', 1),
        ('Tirupati Balaji', 'tirupati-balaji', 'The richest and most visited temple in the world, dedicated to Lord Venkateswara.',
         '<h2>Abode of Lord Venkateswara</h2><p>The Tirumala Venkateswara Temple is a famous Hindu temple dedicated to Lord Venkateswara, a form of Vishnu. Located in the hill town of Tirumala at Tirupati in Chittoor district of Andhra Pradesh, it is the most visited place of worship in the world.</p>',
         'Andhra Pradesh', 'Tirupati', 'India', 13.6833, 79.3472, 'published', 0),
    ]
    
    for title, slug, short, full, state, city, country, lat, lng, status, featured in places:
        db.execute("""
            INSERT INTO places (title, slug, short_description, full_content, state, city, country,
                              latitude, longitude, status, is_featured, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (title, slug, short, full, state, city, country, lat, lng, status, featured))
    
    # Add tags to places
    tag_assignments = [(1,1),(1,2),(2,2),(3,3),(4,4),(5,6)]
    for pid, tid in tag_assignments:
        db.execute("INSERT INTO place_tags (place_id, tag_id) VALUES (?, ?)", (pid, tid))
    
    # Nearby places
    db.execute("INSERT INTO nearby_places VALUES (1, 4, 530)")
    db.execute("INSERT INTO nearby_places VALUES (4, 1, 530)")
    db.execute("INSERT INTO nearby_places VALUES (2, 3, 1400)")
    
    # Sample module entries
    entries = [
        (3, 1, 'The Legend of Kedarnath', 'legend-of-kedarnath',
         '<p>When the Pandavas sought Lord Shiva after the Kurukshetra war to seek his blessings for redemption, Shiva eluded them repeatedly. He transformed into a bull and hid among the cattle at Kedarnath.</p><p>Bhima recognized him and tried to catch the bull, but Shiva dove into the ground. His hump remained at Kedarnath, forming the unique lingam shape worshipped there today.</p>'),
        (3, 4, 'Why Ganga Descended to Earth', 'ganga-descent',
         '<p>King Bhagiratha performed intense penance for thousands of years to bring the River Ganga down from heaven to earth to liberate the souls of his ancestors.</p><p>Lord Shiva caught Ganga in his matted locks to break her fall, releasing her gently to flow across India as the holiest of rivers.</p>'),
        (4, None, 'Maha Shivaratri', 'maha-shivaratri',
         '<p>The Great Night of Shiva is celebrated annually in honour of Lord Shiva. It marks the night when Shiva performed the cosmic dance of creation, preservation, and destruction.</p>'),
        (4, None, 'Kumbh Mela', 'kumbh-mela',
         '<p>The largest religious gathering in the world, Kumbh Mela is held every 12 years at four riverbank pilgrimage sites. Millions gather to bathe in the sacred rivers.</p>'),
        (7, None, 'Om Namah Shivaya Collection', 'om-namah-shivaya',
         '<p>A collection of devotional renditions of the sacred mantra Om Namah Shivaya, recorded at various temples across India.</p>'),
        (8, None, 'The Significance of Temple Architecture', 'temple-architecture-significance',
         '<p>Hindu temple architecture is not merely about aesthetics — every element carries deep spiritual symbolism. From the gopuram representing the cosmic mountain to the garbhagriha symbolizing the cave of the heart.</p>'),
    ]
    for mod_id, place_id, title, slug, content in entries:
        db.execute("""
            INSERT INTO module_entries (module_id, place_id, title, slug, content, status, created_by)
            VALUES (?, ?, ?, ?, ?, 'published', 1)
        """, (mod_id, place_id, title, slug, content))
    
    # Permission definitions
    perms = [
        ('manage_places', 'Manage Holy Places', 'Create, edit, delete holy places', 'content'),
        ('manage_modules', 'Manage Modules', 'Create and configure content modules', 'system'),
        ('manage_entries', 'Manage Module Entries', 'Create and edit module entries', 'content'),
        ('manage_media', 'Manage Media', 'Upload and manage media files', 'media'),
        ('publish_content', 'Publish Content', 'Publish or unpublish content', 'content'),
        ('manage_users', 'Manage Users', 'Create and manage user accounts', 'system'),
        ('manage_tags', 'Manage Tags', 'Create and manage categories/tags', 'content'),
        ('view_analytics', 'View Analytics', 'Access site analytics dashboard', 'system'),
        ('manage_settings', 'Manage Settings', 'Change site-wide settings', 'system'),
    ]
    for key, label, desc, cat in perms:
        db.execute("INSERT INTO permission_definitions (permission_key, label, description, category) VALUES (?,?,?,?)",
                   (key, label, desc, cat))
    
    db.commit()

# ─── Helpers ─────────────────────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def slugify(text):
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def get_current_user():
    if 'user_id' not in session:
        return None
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (session['user_id'],)).fetchone()

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access the admin panel.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user or user['role'] not in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('admin_dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def has_permission(user, perm_key):
    if user['role'] == 'super_admin':
        return True
    perms = json.loads(user['permissions'] or '{}')
    return perms.get(perm_key, False) or perms.get('all', False)

def allowed_file(filename, allowed_ext):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_ext

def log_action(user_id, action, entity_type=None, entity_id=None, details=None):
    db = get_db()
    db.execute("INSERT INTO audit_log (user_id, action, entity_type, entity_id, details) VALUES (?,?,?,?,?)",
               (user_id, action, entity_type, entity_id, details))
    db.commit()

# ─── Context Processors ─────────────────────────────────────────
@app.context_processor
def inject_globals():
    db = get_db()
    modules = db.execute("SELECT * FROM modules WHERE is_active = 1 ORDER BY sort_order").fetchall()
    return {
        'current_user': get_current_user(),
        'active_modules': modules,
        'current_year': datetime.now().year,
        'has_permission': has_permission,
    }

# ═══════════════════════════════════════════════════════════════
# FRONTEND ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def home():
    db = get_db()
    featured = db.execute("""
        SELECT p.*, GROUP_CONCAT(t.name) as tag_names, GROUP_CONCAT(t.color) as tag_colors
        FROM places p
        LEFT JOIN place_tags pt ON p.id = pt.place_id
        LEFT JOIN tags t ON pt.tag_id = t.id
        WHERE p.status = 'published' AND p.is_featured = 1
        GROUP BY p.id ORDER BY p.updated_at DESC LIMIT 6
    """).fetchall()
    
    recent = db.execute("SELECT * FROM places WHERE status='published' ORDER BY created_at DESC LIMIT 8").fetchall()
    modules = db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall()
    
    stories = db.execute("""
        SELECT me.*, m.name as module_name, m.icon as module_icon
        FROM module_entries me JOIN modules m ON me.module_id = m.id
        WHERE me.status = 'published' AND m.slug = 'sacred-stories'
        ORDER BY me.created_at DESC LIMIT 4
    """).fetchall()
    
    bhajans = db.execute("""
        SELECT me.* FROM module_entries me JOIN modules m ON me.module_id = m.id
        WHERE me.status = 'published' AND m.slug = 'bhajans-kirtans'
        ORDER BY me.created_at DESC LIMIT 4
    """).fetchall()
    
    stats = {
        'places': db.execute("SELECT COUNT(*) FROM places WHERE status='published'").fetchone()[0],
        'entries': db.execute("SELECT COUNT(*) FROM module_entries WHERE status='published'").fetchone()[0],
        'modules': db.execute("SELECT COUNT(*) FROM modules WHERE is_active=1").fetchone()[0],
    }
    
    return render_template('frontend/home.html',
                         featured=featured, recent=recent, modules=modules,
                         stories=stories, bhajans=bhajans, stats=stats)

@app.route('/place/<slug>')
def place_detail(slug):
    db = get_db()
    place = db.execute("SELECT * FROM places WHERE slug=? AND status='published'", (slug,)).fetchone()
    if not place:
        abort(404)
    
    # Increment view count
    db.execute("UPDATE places SET view_count = view_count + 1 WHERE id = ?", (place['id'],))
    db.commit()
    
    # Get tags
    tags = db.execute("""
        SELECT t.* FROM tags t JOIN place_tags pt ON t.id = pt.tag_id WHERE pt.place_id = ?
    """, (place['id'],)).fetchall()
    
    # Get media
    media_items = db.execute("""
        SELECT m.*, pm.media_role FROM media m
        JOIN place_media pm ON m.id = pm.media_id
        WHERE pm.place_id = ? ORDER BY pm.sort_order
    """, (place['id'],)).fetchall()
    
    # Get nearby places
    nearby = db.execute("""
        SELECT p.*, np.distance_km FROM places p
        JOIN nearby_places np ON p.id = np.nearby_place_id
        WHERE np.place_id = ? AND p.status = 'published'
    """, (place['id'],)).fetchall()
    
    # Get related module entries
    related_entries = db.execute("""
        SELECT me.*, m.name as module_name, m.icon as module_icon, m.slug as module_slug
        FROM module_entries me JOIN modules m ON me.module_id = m.id
        WHERE me.place_id = ? AND me.status = 'published'
        ORDER BY m.sort_order, me.sort_order
    """, (place['id'],)).fetchall()
    
    # Get related places (same tags)
    related = db.execute("""
        SELECT DISTINCT p.* FROM places p
        JOIN place_tags pt ON p.id = pt.place_id
        WHERE pt.tag_id IN (SELECT tag_id FROM place_tags WHERE place_id = ?)
        AND p.id != ? AND p.status = 'published' LIMIT 3
    """, (place['id'], place['id'])).fetchall()
    
    return render_template('frontend/place.html',
                         place=place, tags=tags, media=media_items,
                         nearby=nearby, related_entries=related_entries, related=related)

@app.route('/explore')
def explore():
    db = get_db()
    page = request.args.get('page', 1, type=int)
    per_page = 12
    tag = request.args.get('tag', '')
    state = request.args.get('state', '')
    q = request.args.get('q', '')
    
    query = "SELECT p.*, GROUP_CONCAT(t.name) as tag_names FROM places p LEFT JOIN place_tags pt ON p.id = pt.place_id LEFT JOIN tags t ON pt.tag_id = t.id WHERE p.status = 'published'"
    params = []
    
    if q:
        query += " AND (p.title LIKE ? OR p.short_description LIKE ? OR p.city LIKE ? OR p.state LIKE ?)"
        params.extend([f'%{q}%'] * 4)
    if tag:
        query += " AND t.slug = ?"
        params.append(tag)
    if state:
        query += " AND p.state = ?"
        params.append(state)
    
    query += " GROUP BY p.id ORDER BY p.is_featured DESC, p.updated_at DESC"
    
    total = len(db.execute(query, params).fetchall())
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])
    
    places = db.execute(query, params).fetchall()
    tags = db.execute("SELECT * FROM tags ORDER BY name").fetchall()
    states = db.execute("SELECT DISTINCT state FROM places WHERE status='published' AND state IS NOT NULL ORDER BY state").fetchall()
    
    return render_template('frontend/explore.html',
                         places=places, tags=tags, states=states,
                         current_tag=tag, current_state=state, query=q,
                         page=page, total=total, per_page=per_page)

@app.route('/module/<slug>')
def module_page(slug):
    db = get_db()
    module = db.execute("SELECT * FROM modules WHERE slug=? AND is_active=1", (slug,)).fetchone()
    if not module:
        abort(404)
    
    entries = db.execute("""
        SELECT me.*, p.title as place_title, p.slug as place_slug
        FROM module_entries me
        LEFT JOIN places p ON me.place_id = p.id
        WHERE me.module_id = ? AND me.status = 'published'
        ORDER BY me.sort_order, me.created_at DESC
    """, (module['id'],)).fetchall()
    
    return render_template('frontend/module.html', module=module, entries=entries)

@app.route('/module/<mod_slug>/<entry_slug>')
def entry_detail(mod_slug, entry_slug):
    db = get_db()
    module = db.execute("SELECT * FROM modules WHERE slug=?", (mod_slug,)).fetchone()
    if not module:
        abort(404)
    entry = db.execute("""
        SELECT me.*, p.title as place_title, p.slug as place_slug
        FROM module_entries me
        LEFT JOIN places p ON me.place_id = p.id
        WHERE me.module_id = ? AND me.slug = ? AND me.status = 'published'
    """, (module['id'], entry_slug)).fetchone()
    if not entry:
        abort(404)
    
    media_items = db.execute("""
        SELECT m.* FROM media m
        JOIN entry_media em ON m.id = em.media_id
        WHERE em.entry_id = ? ORDER BY em.sort_order
    """, (entry['id'],)).fetchall()
    
    return render_template('frontend/entry.html', module=module, entry=entry, media=media_items)

@app.route('/search')
def search():
    q = request.args.get('q', '')
    if not q:
        return redirect(url_for('explore'))
    return redirect(url_for('explore', q=q))

# ═══════════════════════════════════════════════════════════════
# ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        db = get_db()
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user = db.execute("SELECT * FROM users WHERE username=? AND is_active=1",
                         (username,)).fetchone()
        if user and user['password_hash'] == hash_password(password):
            session['user_id'] = user['id']
            db.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now(), user['id']))
            db.commit()
            log_action(user['id'], 'login')
            flash('Welcome back, ' + user['display_name'] + '!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    db = get_db()
    stats = {
        'places': db.execute("SELECT COUNT(*) FROM places").fetchone()[0],
        'published': db.execute("SELECT COUNT(*) FROM places WHERE status='published'").fetchone()[0],
        'entries': db.execute("SELECT COUNT(*) FROM module_entries").fetchone()[0],
        'media': db.execute("SELECT COUNT(*) FROM media").fetchone()[0],
        'users': db.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0],
        'modules': db.execute("SELECT COUNT(*) FROM modules WHERE is_active=1").fetchone()[0],
    }
    recent_places = db.execute("SELECT * FROM places ORDER BY updated_at DESC LIMIT 5").fetchall()
    recent_log = db.execute("""
        SELECT al.*, u.display_name FROM audit_log al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC LIMIT 10
    """).fetchall()
    modules = db.execute("SELECT m.*, (SELECT COUNT(*) FROM module_entries me WHERE me.module_id=m.id) as entry_count FROM modules m ORDER BY m.sort_order").fetchall()
    
    return render_template('admin/dashboard.html', stats=stats, recent_places=recent_places,
                         recent_log=recent_log, modules=modules)

# ─── Places CRUD ─────────────────────────────────────────────
@app.route('/admin/places')
@login_required
def admin_places():
    db = get_db()
    status = request.args.get('status', '')
    q = request.args.get('q', '')
    query = "SELECT * FROM places WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    if q:
        query += " AND (title LIKE ? OR city LIKE ? OR state LIKE ?)"
        params.extend([f'%{q}%']*3)
    query += " ORDER BY updated_at DESC"
    places = db.execute(query, params).fetchall()
    return render_template('admin/places.html', places=places, current_status=status, query=q)

@app.route('/admin/places/new', methods=['GET', 'POST'])
@login_required
def admin_place_new():
    db = get_db()
    if request.method == 'POST':
        title = request.form['title']
        slug = slugify(title)
        # Ensure unique slug
        existing = db.execute("SELECT id FROM places WHERE slug=?", (slug,)).fetchone()
        if existing:
            slug = slug + '-' + str(uuid.uuid4())[:6]
        
        db.execute("""
            INSERT INTO places (title, slug, short_description, full_content, state, city, country,
                              latitude, longitude, featured_image, status, is_featured, created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            title, slug, request.form.get('short_description', ''),
            request.form.get('full_content', ''),
            request.form.get('state', ''), request.form.get('city', ''),
            request.form.get('country', 'India'),
            request.form.get('latitude', type=float),
            request.form.get('longitude', type=float),
            request.form.get('featured_image', ''),
            request.form.get('status', 'draft'),
            1 if request.form.get('is_featured') else 0,
            session['user_id']
        ))
        db.commit()
        place_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        # Handle tags
        tag_ids = request.form.getlist('tags')
        for tid in tag_ids:
            db.execute("INSERT OR IGNORE INTO place_tags (place_id, tag_id) VALUES (?,?)", (place_id, tid))
        db.commit()
        
        log_action(session['user_id'], 'create_place', 'place', place_id, title)
        flash(f'Place "{title}" created successfully!', 'success')
        return redirect(url_for('admin_places'))
    
    tags = db.execute("SELECT * FROM tags ORDER BY name").fetchall()
    return render_template('admin/place_form.html', place=None, tags=tags, editing=False)

@app.route('/admin/places/<int:place_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_place_edit(place_id):
    db = get_db()
    place = db.execute("SELECT * FROM places WHERE id=?", (place_id,)).fetchone()
    if not place:
        abort(404)
    
    if request.method == 'POST':
        db.execute("""
            UPDATE places SET title=?, short_description=?, full_content=?, state=?, city=?, country=?,
                            latitude=?, longitude=?, featured_image=?, status=?, is_featured=?,
                            updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (
            request.form['title'], request.form.get('short_description', ''),
            request.form.get('full_content', ''),
            request.form.get('state', ''), request.form.get('city', ''),
            request.form.get('country', 'India'),
            request.form.get('latitude', type=float),
            request.form.get('longitude', type=float),
            request.form.get('featured_image', ''),
            request.form.get('status', 'draft'),
            1 if request.form.get('is_featured') else 0,
            place_id
        ))
        
        # Update tags
        db.execute("DELETE FROM place_tags WHERE place_id=?", (place_id,))
        for tid in request.form.getlist('tags'):
            db.execute("INSERT OR IGNORE INTO place_tags (place_id, tag_id) VALUES (?,?)", (place_id, tid))
        db.commit()
        
        log_action(session['user_id'], 'update_place', 'place', place_id, request.form['title'])
        flash('Place updated successfully!', 'success')
        return redirect(url_for('admin_places'))
    
    tags = db.execute("SELECT * FROM tags ORDER BY name").fetchall()
    place_tags = [r['tag_id'] for r in db.execute("SELECT tag_id FROM place_tags WHERE place_id=?", (place_id,)).fetchall()]
    return render_template('admin/place_form.html', place=place, tags=tags, place_tags=place_tags, editing=True)

@app.route('/admin/places/<int:place_id>/delete', methods=['POST'])
@login_required
def admin_place_delete(place_id):
    db = get_db()
    place = db.execute("SELECT title FROM places WHERE id=?", (place_id,)).fetchone()
    db.execute("DELETE FROM places WHERE id=?", (place_id,))
    db.commit()
    log_action(session['user_id'], 'delete_place', 'place', place_id, place['title'] if place else '')
    flash('Place deleted.', 'info')
    return redirect(url_for('admin_places'))

# ─── Module Builder ──────────────────────────────────────────
@app.route('/admin/modules')
@login_required
def admin_modules():
    db = get_db()
    modules = db.execute("""
        SELECT m.*, (SELECT COUNT(*) FROM module_entries WHERE module_id=m.id) as entry_count,
               u.display_name as creator_name
        FROM modules m LEFT JOIN users u ON m.created_by = u.id
        ORDER BY m.sort_order
    """).fetchall()
    return render_template('admin/modules.html', modules=modules)

@app.route('/admin/modules/new', methods=['GET', 'POST'])
@login_required
def admin_module_new():
    if request.method == 'POST':
        db = get_db()
        name = request.form['name']
        slug = slugify(name)
        existing = db.execute("SELECT id FROM modules WHERE slug=?", (slug,)).fetchone()
        if existing:
            slug = slug + '-' + str(uuid.uuid4())[:4]
        
        db.execute("""
            INSERT INTO modules (name, slug, description, icon, sort_order, fields_schema, created_by)
            VALUES (?,?,?,?,?,?,?)
        """, (
            name, slug, request.form.get('description', ''),
            request.form.get('icon', '📁'),
            request.form.get('sort_order', 0, type=int),
            request.form.get('fields_schema', '[]'),
            session['user_id']
        ))
        db.commit()
        log_action(session['user_id'], 'create_module', 'module', None, name)
        flash(f'Module "{name}" created!', 'success')
        return redirect(url_for('admin_modules'))
    return render_template('admin/module_form.html', module=None, editing=False)

@app.route('/admin/modules/<int:mod_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_module_edit(mod_id):
    db = get_db()
    module = db.execute("SELECT * FROM modules WHERE id=?", (mod_id,)).fetchone()
    if not module:
        abort(404)
    if request.method == 'POST':
        db.execute("""
            UPDATE modules SET name=?, description=?, icon=?, sort_order=?, fields_schema=?,
                             is_active=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
        """, (
            request.form['name'], request.form.get('description', ''),
            request.form.get('icon', '📁'),
            request.form.get('sort_order', 0, type=int),
            request.form.get('fields_schema', '[]'),
            1 if request.form.get('is_active') else 0,
            mod_id
        ))
        db.commit()
        flash('Module updated!', 'success')
        return redirect(url_for('admin_modules'))
    return render_template('admin/module_form.html', module=module, editing=True)

@app.route('/admin/modules/<int:mod_id>/delete', methods=['POST'])
@login_required
def admin_module_delete(mod_id):
    db = get_db()
    db.execute("DELETE FROM modules WHERE id=?", (mod_id,))
    db.commit()
    flash('Module deleted.', 'info')
    return redirect(url_for('admin_modules'))

# ─── Module Entries CRUD ─────────────────────────────────────
@app.route('/admin/entries')
@app.route('/admin/entries/<int:mod_id>')
@login_required
def admin_entries(mod_id=None):
    db = get_db()
    modules = db.execute("SELECT * FROM modules ORDER BY sort_order").fetchall()
    query = """
        SELECT me.*, m.name as module_name, m.icon as module_icon,
               p.title as place_title
        FROM module_entries me
        JOIN modules m ON me.module_id = m.id
        LEFT JOIN places p ON me.place_id = p.id
    """
    params = []
    if mod_id:
        query += " WHERE me.module_id = ?"
        params.append(mod_id)
    query += " ORDER BY me.updated_at DESC"
    entries = db.execute(query, params).fetchall()
    return render_template('admin/entries.html', entries=entries, modules=modules, current_mod=mod_id)

@app.route('/admin/entries/new', methods=['GET', 'POST'])
@login_required
def admin_entry_new():
    db = get_db()
    if request.method == 'POST':
        title = request.form['title']
        slug = slugify(title)
        existing = db.execute("SELECT id FROM module_entries WHERE slug=? AND module_id=?",
                             (slug, request.form['module_id'])).fetchone()
        if existing:
            slug = slug + '-' + str(uuid.uuid4())[:4]
        
        place_id = request.form.get('place_id', type=int) or None
        db.execute("""
            INSERT INTO module_entries (module_id, place_id, title, slug, content, custom_fields,
                                      featured_image, status, sort_order, created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            request.form['module_id'], place_id, title, slug,
            request.form.get('content', ''),
            request.form.get('custom_fields', '{}'),
            request.form.get('featured_image', ''),
            request.form.get('status', 'draft'),
            request.form.get('sort_order', 0, type=int),
            session['user_id']
        ))
        db.commit()
        flash(f'Entry "{title}" created!', 'success')
        return redirect(url_for('admin_entries'))
    
    modules = db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall()
    places = db.execute("SELECT id, title FROM places ORDER BY title").fetchall()
    return render_template('admin/entry_form.html', entry=None, modules=modules, places=places, editing=False)

@app.route('/admin/entries/<int:entry_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_entry_edit(entry_id):
    db = get_db()
    entry = db.execute("SELECT * FROM module_entries WHERE id=?", (entry_id,)).fetchone()
    if not entry:
        abort(404)
    if request.method == 'POST':
        place_id = request.form.get('place_id', type=int) or None
        db.execute("""
            UPDATE module_entries SET module_id=?, place_id=?, title=?, content=?,
                   custom_fields=?, featured_image=?, status=?, sort_order=?,
                   updated_at=CURRENT_TIMESTAMP WHERE id=?
        """, (
            request.form['module_id'], place_id, request.form['title'],
            request.form.get('content', ''),
            request.form.get('custom_fields', '{}'),
            request.form.get('featured_image', ''),
            request.form.get('status', 'draft'),
            request.form.get('sort_order', 0, type=int),
            entry_id
        ))
        db.commit()
        flash('Entry updated!', 'success')
        return redirect(url_for('admin_entries'))
    
    modules = db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall()
    places = db.execute("SELECT id, title FROM places ORDER BY title").fetchall()
    return render_template('admin/entry_form.html', entry=entry, modules=modules, places=places, editing=True)

@app.route('/admin/entries/<int:entry_id>/delete', methods=['POST'])
@login_required
def admin_entry_delete(entry_id):
    db = get_db()
    db.execute("DELETE FROM module_entries WHERE id=?", (entry_id,))
    db.commit()
    flash('Entry deleted.', 'info')
    return redirect(url_for('admin_entries'))

# ─── Media Library ───────────────────────────────────────────
@app.route('/admin/media')
@login_required
def admin_media():
    db = get_db()
    folder = request.args.get('folder', '')
    file_type = request.args.get('type', '')
    query = "SELECT * FROM media WHERE 1=1"
    params = []
    if folder:
        query += " AND folder=?"
        params.append(folder)
    if file_type:
        query += " AND file_type=?"
        params.append(file_type)
    query += " ORDER BY created_at DESC"
    media_items = db.execute(query, params).fetchall()
    folders = db.execute("SELECT DISTINCT folder FROM media ORDER BY folder").fetchall()
    return render_template('admin/media.html', media=media_items, folders=folders,
                         current_folder=folder, current_type=file_type)

@app.route('/admin/media/upload', methods=['POST'])
@login_required
def admin_media_upload():
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('admin_media'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin_media'))
    
    # Determine file type
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext in ALLOWED_IMAGE_EXT:
        file_type = 'image'
        subfolder = 'images'
    elif ext in ALLOWED_AUDIO_EXT:
        file_type = 'audio'
        subfolder = 'audio'
    elif ext in ALLOWED_VIDEO_EXT:
        file_type = 'video'
        subfolder = 'video'
    else:
        flash('File type not allowed.', 'error')
        return redirect(url_for('admin_media'))
    
    filename = secure_filename(f"{uuid.uuid4().hex[:12]}_{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    
    db = get_db()
    folder = request.form.get('folder', 'general')
    db.execute("""
        INSERT INTO media (filename, original_name, file_type, mime_type, file_size, folder,
                          alt_text, caption, uploaded_by)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        f"{subfolder}/{filename}", file.filename, file_type, file.content_type,
        os.path.getsize(filepath), folder,
        request.form.get('alt_text', ''), request.form.get('caption', ''),
        session['user_id']
    ))
    db.commit()
    flash(f'File "{file.filename}" uploaded!', 'success')
    
    if request.headers.get('Accept') == 'application/json':
        media_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        return jsonify({'id': media_id, 'filename': f"{subfolder}/{filename}", 'type': file_type})
    
    return redirect(url_for('admin_media'))

@app.route('/admin/media/<int:media_id>/delete', methods=['POST'])
@login_required
def admin_media_delete(media_id):
    db = get_db()
    m = db.execute("SELECT * FROM media WHERE id=?", (media_id,)).fetchone()
    if m:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], m['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)
        db.execute("DELETE FROM media WHERE id=?", (media_id,))
        db.commit()
    flash('Media deleted.', 'info')
    return redirect(url_for('admin_media'))

# ─── User Management ────────────────────────────────────────
@app.route('/admin/users')
@login_required
@role_required('super_admin')
def admin_users():
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/new', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def admin_user_new():
    db = get_db()
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        existing = db.execute("SELECT id FROM users WHERE username=? OR email=?", (username, email)).fetchone()
        if existing:
            flash('Username or email already exists.', 'error')
        else:
            perms = {}
            for key in request.form.getlist('permissions'):
                perms[key] = True
            
            db.execute("""
                INSERT INTO users (username, email, password_hash, display_name, role, permissions, created_by)
                VALUES (?,?,?,?,?,?,?)
            """, (
                username, email, hash_password(password),
                request.form.get('display_name', username),
                request.form.get('role', 'editor'),
                json.dumps(perms),
                session['user_id']
            ))
            db.commit()
            flash(f'User "{username}" created!', 'success')
            return redirect(url_for('admin_users'))
    
    perm_defs = db.execute("SELECT * FROM permission_definitions ORDER BY category, label").fetchall()
    return render_template('admin/user_form.html', user=None, perm_defs=perm_defs, editing=False)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def admin_user_edit(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        abort(404)
    
    if request.method == 'POST':
        perms = {}
        for key in request.form.getlist('permissions'):
            perms[key] = True
        
        updates = {
            'email': request.form['email'],
            'display_name': request.form.get('display_name', user['username']),
            'role': request.form.get('role', 'editor'),
            'permissions': json.dumps(perms),
            'is_active': 1 if request.form.get('is_active') else 0,
        }
        
        if request.form.get('password'):
            updates['password_hash'] = hash_password(request.form['password'])
        
        set_clause = ', '.join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [user_id]
        db.execute(f"UPDATE users SET {set_clause} WHERE id=?", values)
        db.commit()
        flash('User updated!', 'success')
        return redirect(url_for('admin_users'))
    
    perm_defs = db.execute("SELECT * FROM permission_definitions ORDER BY category, label").fetchall()
    user_perms = json.loads(user['permissions'] or '{}')
    return render_template('admin/user_form.html', user=user, perm_defs=perm_defs,
                         user_perms=user_perms, editing=True)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('super_admin')
def admin_user_delete(user_id):
    if user_id == session['user_id']:
        flash('Cannot delete your own account.', 'error')
        return redirect(url_for('admin_users'))
    db = get_db()
    db.execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
    db.commit()
    flash('User deactivated.', 'info')
    return redirect(url_for('admin_users'))

# ─── Tags Management ────────────────────────────────────────
@app.route('/admin/tags', methods=['GET', 'POST'])
@login_required
def admin_tags():
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        slug = slugify(name)
        color = request.form.get('color', '#C76B8F')
        desc = request.form.get('description', '')
        try:
            db.execute("INSERT INTO tags (name, slug, description, color) VALUES (?,?,?,?)",
                      (name, slug, desc, color))
            db.commit()
            flash(f'Tag "{name}" created!', 'success')
        except sqlite3.IntegrityError:
            flash('Tag already exists.', 'error')
        return redirect(url_for('admin_tags'))
    
    tags = db.execute("""
        SELECT t.*, COUNT(pt.place_id) as place_count
        FROM tags t LEFT JOIN place_tags pt ON t.id = pt.tag_id
        GROUP BY t.id ORDER BY t.name
    """).fetchall()
    return render_template('admin/tags.html', tags=tags)

@app.route('/admin/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def admin_tag_delete(tag_id):
    db = get_db()
    db.execute("DELETE FROM tags WHERE id=?", (tag_id,))
    db.commit()
    flash('Tag deleted.', 'info')
    return redirect(url_for('admin_tags'))

# ═══════════════════════════════════════════════════════════════
# REST API (for future mobile apps)
# ═══════════════════════════════════════════════════════════════

@app.route('/api/v1/places')
def api_places():
    db = get_db()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    q = request.args.get('q', '')
    tag = request.args.get('tag', '')
    state = request.args.get('state', '')
    
    query = "SELECT * FROM places WHERE status='published'"
    params = []
    if q:
        query += " AND (title LIKE ? OR short_description LIKE ?)"
        params.extend([f'%{q}%']*2)
    if state:
        query += " AND state=?"
        params.append(state)
    
    total = len(db.execute(query, params).fetchall())
    query += " ORDER BY is_featured DESC, updated_at DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page-1)*per_page])
    places = db.execute(query, params).fetchall()
    
    return jsonify({
        'data': [dict(p) for p in places],
        'meta': {'page': page, 'per_page': per_page, 'total': total}
    })

@app.route('/api/v1/places/<slug>')
def api_place_detail(slug):
    db = get_db()
    place = db.execute("SELECT * FROM places WHERE slug=? AND status='published'", (slug,)).fetchone()
    if not place:
        return jsonify({'error': 'Not found'}), 404
    
    tags = db.execute("SELECT t.* FROM tags t JOIN place_tags pt ON t.id=pt.tag_id WHERE pt.place_id=?",
                     (place['id'],)).fetchall()
    nearby = db.execute("""
        SELECT p.title, p.slug, p.short_description, np.distance_km
        FROM places p JOIN nearby_places np ON p.id=np.nearby_place_id
        WHERE np.place_id=? AND p.status='published'
    """, (place['id'],)).fetchall()
    entries = db.execute("""
        SELECT me.*, m.name as module_name FROM module_entries me
        JOIN modules m ON me.module_id=m.id
        WHERE me.place_id=? AND me.status='published'
    """, (place['id'],)).fetchall()
    
    result = dict(place)
    result['tags'] = [dict(t) for t in tags]
    result['nearby_places'] = [dict(n) for n in nearby]
    result['module_entries'] = [dict(e) for e in entries]
    return jsonify(result)

@app.route('/api/v1/modules')
def api_modules():
    db = get_db()
    modules = db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall()
    return jsonify([dict(m) for m in modules])

@app.route('/api/v1/modules/<slug>/entries')
def api_module_entries(slug):
    db = get_db()
    module = db.execute("SELECT * FROM modules WHERE slug=? AND is_active=1", (slug,)).fetchone()
    if not module:
        return jsonify({'error': 'Not found'}), 404
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    entries = db.execute("""
        SELECT me.*, p.title as place_title, p.slug as place_slug
        FROM module_entries me LEFT JOIN places p ON me.place_id=p.id
        WHERE me.module_id=? AND me.status='published'
        ORDER BY me.sort_order, me.created_at DESC LIMIT ? OFFSET ?
    """, (module['id'], per_page, (page-1)*per_page)).fetchall()
    
    return jsonify({
        'module': dict(module),
        'entries': [dict(e) for e in entries]
    })

@app.route('/api/v1/search')
def api_search():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'results': []})
    db = get_db()
    places = db.execute("SELECT id,title,slug,short_description,state,city FROM places WHERE status='published' AND (title LIKE ? OR short_description LIKE ?) LIMIT 10",
                       (f'%{q}%', f'%{q}%')).fetchall()
    entries = db.execute("""
        SELECT me.id, me.title, me.slug, m.slug as module_slug, m.name as module_name
        FROM module_entries me JOIN modules m ON me.module_id=m.id
        WHERE me.status='published' AND me.title LIKE ? LIMIT 10
    """, (f'%{q}%',)).fetchall()
    return jsonify({
        'places': [dict(p) for p in places],
        'entries': [dict(e) for e in entries]
    })

# ─── Error Handlers ──────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('frontend/404.html'), 404

# ─── App Startup ─────────────────────────────────────────────
with app.app_context():
    init_db()
    seed_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
