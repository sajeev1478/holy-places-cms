"""
Holy Dham CMS - Main Application (v3)
4-Tier Hierarchy: Holy Dham > Key Places > Key Spots > Sub-Spots
With Category Framework for Tier 3 & Tier 4
"""

import os, json, uuid, hashlib, sqlite3, functools, re, random
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (Flask, render_template, request, redirect, url_for, flash,
    session, jsonify, abort, g)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'holyplaces-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'holyplaces.db')

ALLOWED_IMAGE_EXT = {'png','jpg','jpeg','gif','webp','svg'}
ALLOWED_AUDIO_EXT = {'mp3','wav','ogg','aac'}
ALLOWED_VIDEO_EXT = {'mp4','webm','mov'}

# ─── Predefined Icon Library (50+ icons for field selection) ───
FIELD_ICONS = [
    ('🕐','Clock / Hours'),('⏰','Alarm / Timing'),('🕰️','Mantle Clock'),
    ('📅','Calendar / Date'),('🌤️','Weather / Season'),('☀️','Sun / Summer'),('❄️','Winter'),
    ('🚗','Car / Drive'),('✈️','Flight'),('🚌','Bus'),('🚂','Train'),('🛺','Auto / Rickshaw'),('🗺️','Map / Route'),('🧭','Compass'),
    ('🏨','Hotel / Stay'),('🛏️','Bed / Room'),('🏠','House'),('🏕️','Camp'),
    ('📜','History / Scroll'),('🏛️','Heritage'),('📚','Books'),('📖','Open Book'),
    ('👔','Formal Dress'),('👗','Dress'),('🥻','Saree'),('👞','Shoes'),
    ('🎵','Music / Audio'),('🔊','Speaker'),('🎙️','Microphone'),('🎶','Musical Notes'),
    ('🎬','Video / Film'),('📹','Camera'),('🎥','Movie Camera'),
    ('🖼️','Gallery / Frame'),('📷','Photo'),('🎞️','Film Strip'),('📸','Camera Flash'),
    ('🔗','Link / URL'),('🌐','Web / Globe'),
    ('💰','Cost / Fee'),('🎫','Ticket'),('💳','Card / Payment'),('🆓','Free'),
    ('📍','Location / Pin'),('📌','Pinned'),('🗺️','Map'),
    ('📋','Clipboard / Info'),('ℹ️','Information'),('📄','Document'),('📝','Notes / Write'),
    ('🙏','Prayer / Worship'),('🪔','Diya / Lamp'),('🕉️','Om / Sacred'),('📿','Mala / Beads'),
    ('🛕','Temple'),('⛩️','Shrine / Torii'),('🔔','Bell'),('🌺','Flower / Offering'),
    ('🧘','Meditation'),('💐','Bouquet'),('🌸','Cherry Blossom'),('🪷','Lotus'),
    ('☎️','Phone'),('📞','Telephone'),('✉️','Email'),('📮','Mail'),
    ('⚠️','Warning / Note'),('✅','Checkmark'),('❌','Cross / Closed'),('🔒','Locked / Private'),
    ('🌊','Water / River'),('⛰️','Mountain'),('🌳','Tree / Forest'),('🌙','Moon / Night'),
    ('🍲','Food'),('☕','Tea / Coffee'),('🥤','Drink'),('🍽️','Dining'),
    ('♿','Accessibility'),('🚻','Restroom'),('🅿️','Parking'),('🚰','Drinking Water'),
]

# Default icons for built-in & custom fields
FIELD_DEFAULT_ICONS = {
    'title':'📝','city':'🏙️','state':'🗺️','country':'🌍',
    'short_description':'📋','full_content':'📖','featured_image':'🖼️',
    'latitude':'📍','longitude':'📍','tags':'🏷️','status':'📊','is_featured':'⭐',
    'audio_narration':'🎵','video_tour':'🎬','gallery_images':'🖼️',
    'opening_hours':'🕐','best_time_to_visit':'🌤️','how_to_reach':'🚗',
    'accommodation':'🏨','history':'📜','dress_code':'🥻',
    'external_audio_url':'🔗','external_video_url':'🔗',
    'entry_fee':'💰','phone':'☎️','email':'✉️','website':'🌐',
}

BUILTIN_FIELDS = [
    {'key':'title','label':'Title','type':'text','required':True},
    {'key':'city','label':'City','type':'text'},
    {'key':'state','label':'State','type':'text'},
    {'key':'country','label':'Country','type':'text'},
    {'key':'short_description','label':'Short Description','type':'textarea'},
    {'key':'full_content','label':'Full Content','type':'richtext'},
    {'key':'featured_image','label':'Featured Image','type':'image'},
    {'key':'latitude','label':'Latitude','type':'number'},
    {'key':'longitude','label':'Longitude','type':'number'},
    {'key':'tags','label':'Tags','type':'tags'},
    {'key':'status','label':'Status','type':'select'},
    {'key':'is_featured','label':'Featured on Homepage','type':'checkbox'},
]

# ─── Tier-3 Key Spot Categories ───
SPOT_CATEGORIES = [
    ('temple','Temple (Mandir)','Consecrated place of deity worship','🛕','#E74C3C'),
    ('kund','Kund / Sarovar','Sacred water body for rituals and purification','💧','#3498DB'),
    ('ghat','Ghat','Steps leading to water for rituals','🪜','#1ABC9C'),
    ('leela_sthali','Leela Sthali','Place of divine pastimes','✨','#9B59B6'),
    ('van','Van (Forest)','Sacred forest area','🌳','#27AE60'),
    ('hill','Hill / Parvat','Sacred elevated formation','⛰️','#8B6914'),
    ('village','Village','Sacred settlement','🏘️','#E67E22'),
    ('ashram','Ashram / Math','Spiritual residence','🏠','#F39C12'),
    ('samadhi','Samadhi Sthal','Resting place of saints','🙏','#C76B8F'),
    ('bhajan_kutir','Bhajan Kutir','Place of meditation','📿','#8E44AD'),
    ('baithak','Baithak','Teaching place of acharya','📖','#2C3E50'),
    ('parikrama','Parikrama Path','Sacred circumambulation route','🔄','#16A085'),
    ('garden','Garden / Nikunj','Sacred grove','🌺','#E91E63'),
    ('cave','Cave / Guha','Meditation or leela cave','🕳️','#795548'),
    ('river','River','Sacred flowing water','🏞️','#0097A7'),
]

# ─── Tier-4 Sub-Spot Categories ───
SUB_SPOT_CATEGORIES = [
    ('altar','Altar / Darshan Area','Main deity viewing area','🪔','#E74C3C'),
    ('samadhi_internal','Samadhi (Internal)','Shrine within complex','🕉️','#C76B8F'),
    ('quarters','Quarters / Residence','Living space of saint','🚪','#8D6E63'),
    ('courtyard','Courtyard','Open gathering area','🏛️','#FF9800'),
    ('ghat_section','Ghat Section','Specific part of ghat','🏊','#00BCD4'),
    ('leela_point','Leela Point','Exact pastime location','📍','#9C27B0'),
    ('shrine','Shrine','Secondary deity area','⛩️','#F44336'),
    ('pathway','Pathway','Internal walking path','🚶','#4CAF50'),
    ('sacred_tree','Sacred Tree','Tree linked to leela','🌲','#2E7D32'),
    ('meditation_spot','Meditation Spot','Place for remembrance','🧘','#673AB7'),
]

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    db = get_db()
    db.executescript('''
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, display_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'editor', permissions TEXT DEFAULT '{}', is_active INTEGER DEFAULT 1, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login TIMESTAMP);
    CREATE TABLE IF NOT EXISTS modules (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, description TEXT, icon TEXT DEFAULT '📁', sort_order INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1, fields_schema TEXT DEFAULT '[]', created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS places (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, short_description TEXT, full_content TEXT, state TEXT, city TEXT, country TEXT DEFAULT 'India', latitude REAL, longitude REAL, featured_image TEXT, status TEXT DEFAULT 'draft', is_featured INTEGER DEFAULT 0, view_count INTEGER DEFAULT 0, field_visibility TEXT DEFAULT '{}', created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS custom_field_defs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, label TEXT NOT NULL, field_type TEXT NOT NULL DEFAULT 'text', placeholder TEXT DEFAULT '', icon TEXT DEFAULT '📋', is_active INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0, applies_to TEXT DEFAULT 'both', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS place_custom_values (id INTEGER PRIMARY KEY AUTOINCREMENT, place_id INTEGER NOT NULL, field_def_id INTEGER NOT NULL, value TEXT DEFAULT '', is_visible INTEGER DEFAULT 1, FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE, FOREIGN KEY (field_def_id) REFERENCES custom_field_defs(id) ON DELETE CASCADE, UNIQUE(place_id, field_def_id));
    CREATE TABLE IF NOT EXISTS key_places (id INTEGER PRIMARY KEY AUTOINCREMENT, parent_place_id INTEGER NOT NULL, title TEXT NOT NULL, slug TEXT, short_description TEXT, full_content TEXT, featured_image TEXT, gallery_images TEXT DEFAULT '', latitude REAL, longitude REAL, sort_order INTEGER DEFAULT 0, is_visible INTEGER DEFAULT 1, field_visibility TEXT DEFAULT '{}', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (parent_place_id) REFERENCES places(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS key_place_custom_values (id INTEGER PRIMARY KEY AUTOINCREMENT, key_place_id INTEGER NOT NULL, field_def_id INTEGER NOT NULL, value TEXT DEFAULT '', is_visible INTEGER DEFAULT 1, FOREIGN KEY (key_place_id) REFERENCES key_places(id) ON DELETE CASCADE, FOREIGN KEY (field_def_id) REFERENCES custom_field_defs(id) ON DELETE CASCADE, UNIQUE(key_place_id, field_def_id));

    /* ─── NEW: Tier 3 & 4 Category Tables ─── */
    CREATE TABLE IF NOT EXISTS spot_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, name TEXT NOT NULL, description TEXT, icon TEXT DEFAULT '📍', color TEXT DEFAULT '#666');
    CREATE TABLE IF NOT EXISTS sub_spot_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, name TEXT NOT NULL, description TEXT, icon TEXT DEFAULT '📍', color TEXT DEFAULT '#666');

    /* ─── NEW: Tier 3 Key Spots ─── */
    CREATE TABLE IF NOT EXISTS key_spots (id INTEGER PRIMARY KEY AUTOINCREMENT, key_place_id INTEGER NOT NULL, category_id INTEGER, title TEXT NOT NULL, slug TEXT, short_description TEXT, full_content TEXT, featured_image TEXT, gallery_images TEXT DEFAULT '', state TEXT, city TEXT, country TEXT DEFAULT '', latitude REAL, longitude REAL, sort_order INTEGER DEFAULT 0, is_visible INTEGER DEFAULT 1, field_visibility TEXT DEFAULT '{}', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (key_place_id) REFERENCES key_places(id) ON DELETE CASCADE, FOREIGN KEY (category_id) REFERENCES spot_categories(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS key_spot_custom_values (id INTEGER PRIMARY KEY AUTOINCREMENT, key_spot_id INTEGER NOT NULL, field_def_id INTEGER NOT NULL, value TEXT DEFAULT '', is_visible INTEGER DEFAULT 1, FOREIGN KEY (key_spot_id) REFERENCES key_spots(id) ON DELETE CASCADE, FOREIGN KEY (field_def_id) REFERENCES custom_field_defs(id) ON DELETE CASCADE, UNIQUE(key_spot_id, field_def_id));

    /* ─── NEW: Tier 4 Key Points ─── */
    CREATE TABLE IF NOT EXISTS sub_spots (id INTEGER PRIMARY KEY AUTOINCREMENT, key_spot_id INTEGER NOT NULL, category_id INTEGER, title TEXT NOT NULL, slug TEXT, short_description TEXT, full_content TEXT, featured_image TEXT, gallery_images TEXT DEFAULT '', state TEXT, city TEXT, country TEXT DEFAULT '', latitude REAL, longitude REAL, sort_order INTEGER DEFAULT 0, is_visible INTEGER DEFAULT 1, field_visibility TEXT DEFAULT '{}', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (key_spot_id) REFERENCES key_spots(id) ON DELETE CASCADE, FOREIGN KEY (category_id) REFERENCES sub_spot_categories(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS sub_spot_custom_values (id INTEGER PRIMARY KEY AUTOINCREMENT, sub_spot_id INTEGER NOT NULL, field_def_id INTEGER NOT NULL, value TEXT DEFAULT '', is_visible INTEGER DEFAULT 1, FOREIGN KEY (sub_spot_id) REFERENCES sub_spots(id) ON DELETE CASCADE, FOREIGN KEY (field_def_id) REFERENCES custom_field_defs(id) ON DELETE CASCADE, UNIQUE(sub_spot_id, field_def_id));

    CREATE TABLE IF NOT EXISTS module_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, module_id INTEGER NOT NULL, place_id INTEGER, title TEXT NOT NULL, slug TEXT NOT NULL, content TEXT, custom_fields TEXT DEFAULT '{}', featured_image TEXT, status TEXT DEFAULT 'draft', sort_order INTEGER DEFAULT 0, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE, FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS media (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL, original_name TEXT NOT NULL, file_type TEXT NOT NULL, mime_type TEXT, file_size INTEGER, folder TEXT DEFAULT 'general', alt_text TEXT, caption TEXT, uploaded_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS place_media (id INTEGER PRIMARY KEY AUTOINCREMENT, place_id INTEGER NOT NULL, media_id INTEGER NOT NULL, media_role TEXT DEFAULT 'gallery', sort_order INTEGER DEFAULT 0, FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE, FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS entry_media (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER NOT NULL, media_id INTEGER NOT NULL, media_role TEXT DEFAULT 'gallery', sort_order INTEGER DEFAULT 0, FOREIGN KEY (entry_id) REFERENCES module_entries(id) ON DELETE CASCADE, FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, slug TEXT UNIQUE NOT NULL, description TEXT, color TEXT DEFAULT '#C76B8F');
    CREATE TABLE IF NOT EXISTS place_tags (place_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, PRIMARY KEY (place_id, tag_id), FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE, FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS nearby_places (place_id INTEGER NOT NULL, nearby_place_id INTEGER NOT NULL, distance_km REAL, PRIMARY KEY (place_id, nearby_place_id));
    CREATE TABLE IF NOT EXISTS permission_definitions (id INTEGER PRIMARY KEY AUTOINCREMENT, permission_key TEXT UNIQUE NOT NULL, label TEXT NOT NULL, description TEXT, category TEXT DEFAULT 'general');
    CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT NOT NULL, entity_type TEXT, entity_id INTEGER, details TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    ''')
    db.commit()

def seed_db():
    db = get_db()
    if db.execute("SELECT id FROM users LIMIT 1").fetchone(): return

    # ─── Seed Tier-3 Spot Categories ───
    for slug,name,desc,icon,color in SPOT_CATEGORIES:
        db.execute("INSERT INTO spot_categories (slug,name,description,icon,color) VALUES (?,?,?,?,?)",(slug,name,desc,icon,color))
    # ─── Seed Tier-4 Sub-Spot Categories ───
    for slug,name,desc,icon,color in SUB_SPOT_CATEGORIES:
        db.execute("INSERT INTO sub_spot_categories (slug,name,description,icon,color) VALUES (?,?,?,?,?)",(slug,name,desc,icon,color))

    # Users
    db.execute("INSERT INTO users (username,email,password_hash,display_name,role,permissions) VALUES (?,?,?,?,?,?)", ('admin','admin@holyplaces.com',hashlib.sha256(b'admin123').hexdigest(),'Super Admin','super_admin','{"all":true}'))
    db.execute("INSERT INTO users (username,email,password_hash,display_name,role,created_by) VALUES (?,?,?,?,?,?)", ('editor','editor@holyplaces.com',hashlib.sha256(b'editor123').hexdigest(),'Content Editor','editor',1))
    # Modules
    for name,slug,desc,icon,order in [('Holy Dhams','holy-dhams','Sacred destinations','🛕',1),('Temples','temples','Temple profiles','🏛️',2),('Sacred Stories','sacred-stories','Mythological tales','📖',3),('Festivals','festivals','Religious events','🎪',4),('Pilgrimage Guides','pilgrimage-guides','Travel guides','🚶',5),('Events','events','Spiritual events','📅',6),('Bhajans & Kirtans','bhajans-kirtans','Devotional music','🎵',7),('Spiritual Articles','spiritual-articles','Spiritual writings','📝',8)]:
        db.execute("INSERT INTO modules (name,slug,description,icon,sort_order,is_active,created_by) VALUES (?,?,?,?,?,1,1)", (name,slug,desc,icon,order))
    # Tags
    for name,slug,color in [('Char Dham','char-dham','#C76B8F'),('Jyotirlinga','jyotirlinga','#E89B4F'),('Heritage','heritage','#8BAB8A'),('Pilgrimage','pilgrimage','#6B8AB5'),('UNESCO','unesco','#B58A6B'),('Sikh Heritage','sikh-heritage','#C4A44E'),('Buddhist','buddhist','#8A6BB5'),('ISKCON','iskcon','#D4A843'),('Braj Dham','braj-dham','#E84855'),('Gaudiya Vaishnava','gaudiya-vaishnava','#6C5CE7')]:
        db.execute("INSERT INTO tags (name,slug,color) VALUES (?,?,?)", (name,slug,color))
    # Custom Fields with icons
    for name,label,ftype,ph,order,applies,icon in [('audio_narration','Audio Narration','audio','Upload audio',1,'both','🎵'),('video_tour','Video Tour','video','Upload or paste URL',2,'both','🎬'),('gallery_images','Gallery Images','images','Upload photos',3,'both','🖼️'),('opening_hours','Opening Hours','text','e.g. 6 AM - 9 PM',4,'both','🕐'),('best_time_to_visit','Best Time to Visit','text','e.g. Oct-Mar',5,'both','🌤️'),('how_to_reach','How to Reach','textarea','Directions',6,'place','🚗'),('accommodation','Accommodation','textarea','Stay options',7,'place','🏨'),('history','History & Significance','richtext','Detailed history',8,'both','📜'),('dress_code','Dress Code','text','If any',9,'both','🥻'),('external_audio_url','External Audio Link','url','Audio URL',11,'both','🔗'),('external_video_url','External Video Link','url','YouTube/Vimeo URL',12,'both','🔗')]:
        db.execute("INSERT INTO custom_field_defs (name,label,field_type,placeholder,sort_order,applies_to,icon) VALUES (?,?,?,?,?,?,?)", (name,label,ftype,ph,order,applies,icon))

    # ─── SAMPLE: Vrindavan Dham (Tier 1) ───
    db.execute("INSERT INTO places (title,slug,short_description,full_content,state,city,country,latitude,longitude,status,is_featured,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
        ('Vrindavan Dham','vrindavan-dham','The divine land of Radha-Krishna leelas, one of the holiest Dhams in Gaudiya Vaishnavism.',
         '<h2>The Eternal Abode of Krishna</h2><p>Vrindavan is the transcendental land where Lord Krishna performed His childhood and youth pastimes. Located in the Braj region of Uttar Pradesh, it is revered by millions as a place where the spiritual world manifests on earth.</p><h3>Significance</h3><p>Vrindavan is one of the most important pilgrimage destinations in Hinduism, especially in the Gaudiya Vaishnava tradition. Sri Chaitanya Mahaprabhu rediscovered the lost holy places of Vrindavan in the 16th century.</p>',
         'Uttar Pradesh','Mathura','India',27.5830,77.6950,'published',1))
    dham_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for tid in [8,4,9,10]: db.execute("INSERT OR IGNORE INTO place_tags VALUES (?,?)", (dham_id,tid))

    # ─── Tier 2: Key Places ───
    kp_data = [
        ('Vrindavan Town','vrindavan-town','The heart of Braj, dense with temples and sacred kunds.','<p>Vrindavan town is the epicenter of Krishna devotion with over 5,000 temples.</p>',27.5830,77.6950,1),
        ('Barsana','barsana','The eternal abode of Srimati Radharani.','<p>Barsana is a hilltop town revered as the birthplace of Radha. It hosts the famous Lathmar Holi.</p>',27.6474,77.3833,2),
        ('Nandgaon','nandgaon','The village of Nanda Maharaja, Krishna\'s foster father.','<p>Nandgaon is where Krishna spent his childhood. The Nand Bhavan temple stands on the hilltop.</p>',27.6714,77.3817,3),
        ('Govardhan','govardhan','Sacred hill lifted by Krishna to protect Braj.','<p>Govardhan Hill is one of the holiest sites, worshipped as a form of Krishna Himself. The parikrama (circumambulation) is a key pilgrimage practice.</p>',27.4929,77.4583,4),
    ]
    kp_ids = {}
    for t,s,sd,fc,lat,lng,o in kp_data:
        db.execute("INSERT INTO key_places (parent_place_id,title,slug,short_description,full_content,latitude,longitude,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,1)", (dham_id,t,s,sd,fc,lat,lng,o))
        kp_ids[s] = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # ─── Tier 3: Key Spots (with categories) ───
    temple_cat = db.execute("SELECT id FROM spot_categories WHERE slug='temple'").fetchone()[0]
    kund_cat = db.execute("SELECT id FROM spot_categories WHERE slug='kund'").fetchone()[0]
    ghat_cat = db.execute("SELECT id FROM spot_categories WHERE slug='ghat'").fetchone()[0]
    van_cat = db.execute("SELECT id FROM spot_categories WHERE slug='van'").fetchone()[0]
    hill_cat = db.execute("SELECT id FROM spot_categories WHERE slug='hill'").fetchone()[0]
    parikrama_cat = db.execute("SELECT id FROM spot_categories WHERE slug='parikrama'").fetchone()[0]

    ks_data = [
        (kp_ids['vrindavan-town'],temple_cat,'ISKCON Krishna Balaram Mandir','iskcon-krishna-balaram','The international headquarters temple of ISKCON in Vrindavan.','<p>Founded by Srila Prabhupada in 1975, this temple features beautiful deities of Krishna-Balaram, Radha-Shyamasundar, and Gaura-Nitai.</p>',27.5815,77.6983,1),
        (kp_ids['vrindavan-town'],temple_cat,'Banke Bihari Temple','banke-bihari','One of the most visited temples in Vrindavan.','<p>Built in 1864, the temple houses the deity of Banke Bihari, an enchanting form of Krishna.</p>',27.5833,77.6954,2),
        (kp_ids['vrindavan-town'],temple_cat,'Radha Raman Temple','radha-raman','A 500-year-old temple with a self-manifested deity.','<p>Established by Gopal Bhatta Goswami, the deity of Radha Raman appeared from a shaligrama shila.</p>',27.5820,77.6940,3),
        (kp_ids['vrindavan-town'],ghat_cat,'Kesi Ghat','kesi-ghat','The most prominent ghat on the Yamuna in Vrindavan.','<p>Where Krishna killed the demon Kesi. A key spot for evening aarti and Yamuna worship.</p>',27.5802,77.6960,4),
        (kp_ids['vrindavan-town'],van_cat,'Nidhivan','nidhivan','Mysterious forest where Radha-Krishna are said to dance every night.','<p>The trees of Nidhivan form natural bowers (kunjas). It is believed that Radha and Krishna perform their Raas Leela here every night.</p>',27.5810,77.6930,5),
        (kp_ids['govardhan'],hill_cat,'Govardhan Hill','govardhan-hill','The sacred hill lifted by Krishna.','<p>Govardhan Hill is worshipped as Govardhan Maharaj. Devotees perform parikrama and worship the shila (stones).</p>',27.4929,77.4583,1),
        (kp_ids['govardhan'],kund_cat,'Radha Kund','radha-kund','The most sacred kund in all of Braj.','<p>Radha Kund is considered the most sacred body of water, representing the mercy of Srimati Radharani.</p>',27.5062,77.4629,2),
        (kp_ids['govardhan'],kund_cat,'Kusum Sarovar','kusum-sarovar','Beautiful lake with stunning architecture.','<p>A historically significant sarovar with Mughal-era architecture, linked to the love pastimes of Radha-Krishna.</p>',27.5010,77.4600,3),
        (kp_ids['govardhan'],parikrama_cat,'Govardhan Parikrama','govardhan-parikrama','21 km circumambulation of the sacred hill.','<p>The parikrama path encircles Govardhan Hill and is walked barefoot by millions of devotees annually.</p>',27.4930,77.4580,4),
    ]
    ks_ids = {}
    for kpid,catid,t,s,sd,fc,lat,lng,o in ks_data:
        db.execute("INSERT INTO key_spots (key_place_id,category_id,title,slug,short_description,full_content,state,city,country,latitude,longitude,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)", (kpid,catid,t,s,sd,fc,'Uttar Pradesh','Mathura','India',lat,lng,o))
        ks_ids[s] = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # ─── Tier 4: Sub-Spots (with categories) ───
    altar_cat = db.execute("SELECT id FROM sub_spot_categories WHERE slug='altar'").fetchone()[0]
    samadhi_cat = db.execute("SELECT id FROM sub_spot_categories WHERE slug='samadhi_internal'").fetchone()[0]
    quarters_cat = db.execute("SELECT id FROM sub_spot_categories WHERE slug='quarters'").fetchone()[0]
    courtyard_cat = db.execute("SELECT id FROM sub_spot_categories WHERE slug='courtyard'").fetchone()[0]

    ss_data = [
        (ks_ids['iskcon-krishna-balaram'],samadhi_cat,'Srila Prabhupada Samadhi','prabhupada-samadhi','The sacred samadhi shrine of ISKCON founder-acharya.','<p>An ornate marble memorial housing the sacred remains of His Divine Grace A.C. Bhaktivedanta Swami Prabhupada.</p>',1),
        (ks_ids['iskcon-krishna-balaram'],quarters_cat,"Srila Prabhupada's Quarters",'prabhupada-quarters','The preserved living quarters of Srila Prabhupada.','<p>The rooms where Srila Prabhupada lived, wrote, and translated. Maintained exactly as they were during his stay.</p>',2),
        (ks_ids['iskcon-krishna-balaram'],altar_cat,'Krishna-Balaram Altar','krishna-balaram-altar','The main altar with the presiding deities.','<p>The central altar features the beautiful deities of Sri Sri Krishna-Balaram, Radha-Shyamasundar, and Gaura-Nitai.</p>',3),
        (ks_ids['iskcon-krishna-balaram'],courtyard_cat,'Temple Courtyard','temple-courtyard','Open gathering space for kirtans.','<p>The spacious courtyard hosts daily kirtans, festivals, and spiritual programs.</p>',4),
    ]
    for ksid,catid,t,s,sd,fc,o in ss_data:
        db.execute("INSERT INTO sub_spots (key_spot_id,category_id,title,slug,short_description,full_content,state,city,country,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,?,?,1)", (ksid,catid,t,s,sd,fc,'Uttar Pradesh','Vrindavan','India',o))

    # More sample dhams
    for t,s,sd,fc,st,ci,lat,lng in [('Mayapur Dham','mayapur-dham','The spiritual headquarters of ISKCON and birthplace of Sri Chaitanya Mahaprabhu.','<h2>The Holy Land of Mayapur</h2><p>Mayapur is one of the most important pilgrimage sites for Gaudiya Vaishnavas.</p>','West Bengal','Nadia',23.4231,88.3884),
        ('Kedarnath Dham','kedarnath-dham','One of the twelve Jyotirlingas of Lord Shiva.','<h2>Sacred Abode of Lord Shiva</h2><p>Located in the Garhwal Himalayas near the Mandakini river.</p>','Uttarakhand','Rudraprayag',30.7352,79.0669),
        ('Jagannath Puri Dham','jagannath-puri-dham','The abode of Lord Jagannath, one of the four Dhams.','<h2>The Land of Lord Jagannath</h2><p>Puri is one of the Char Dham pilgrimage sites.</p>','Odisha','Puri',19.8135,85.8312)]:
        db.execute("INSERT INTO places (title,slug,short_description,full_content,state,city,country,latitude,longitude,status,is_featured,created_by) VALUES (?,?,?,?,?,?,'India',?,?,'published',1,1)", (t,s,sd,fc,st,ci,lat,lng))

    # Module entries
    for mod,pid,t,s,c in [(3,dham_id,'Appearance of Sri Chaitanya','appearance-sri-chaitanya','<p>Sri Chaitanya appeared in Mayapur in 1486 CE amidst ecstatic chanting.</p>'),(3,None,'Legend of Kedarnath','legend-kedarnath','<p>The Pandavas sought Lord Shiva who hid as a bull.</p>'),(4,None,'Gaura Purnima','gaura-purnima','<p>Celebrates the appearance of Sri Chaitanya. Hundreds of thousands visit Mayapur.</p>')]:
        db.execute("INSERT INTO module_entries (module_id,place_id,title,slug,content,status,created_by) VALUES (?,?,?,?,?,'published',1)", (mod,pid,t,s,c))
    # Permissions
    for k,l,d,cat in [('manage_places','Manage Holy Dhams','Create/edit/delete dhams','content'),('manage_modules','Manage Modules','Configure modules','system'),('manage_entries','Manage Entries','Create/edit entries','content'),('manage_media','Manage Media','Upload media','media'),('publish_content','Publish Content','Publish/unpublish','content'),('manage_users','Manage Users','Manage accounts','system'),('manage_tags','Manage Tags','Manage categories','content'),('manage_fields','Manage Fields','Configure custom fields','system')]:
        db.execute("INSERT OR IGNORE INTO permission_definitions (permission_key,label,description,category) VALUES (?,?,?,?)", (k,l,d,cat))
    db.commit()

# ─── Helpers ───
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def slugify(text):
    import re; s=text.lower().strip(); s=re.sub(r'[^\w\s-]','',s); s=re.sub(r'[\s_]+','-',s); return re.sub(r'-+','-',s).strip('-')
def get_current_user():
    if 'user_id' not in session: return None
    return get_db().execute("SELECT * FROM users WHERE id=? AND is_active=1", (session['user_id'],)).fetchone()
def login_required(f):
    @functools.wraps(f)
    def d(*a,**kw):
        if 'user_id' not in session: flash('Please log in.','warning'); return redirect(url_for('admin_login'))
        return f(*a,**kw)
    return d
def role_required(*roles):
    def dec(f):
        @functools.wraps(f)
        def d(*a,**kw):
            u=get_current_user()
            if not u or u['role'] not in roles: flash('Permission denied.','error'); return redirect(url_for('admin_dashboard'))
            return f(*a,**kw)
        return d
    return dec
def has_permission(user,pk):
    if user['role']=='super_admin': return True
    p=json.loads(user['permissions'] or '{}'); return p.get(pk,False) or p.get('all',False)
def save_upload(file, subfolder='images'):
    if not file or file.filename=='': return None
    ext=file.filename.rsplit('.',1)[1].lower() if '.' in file.filename else ''
    if ext in ALLOWED_IMAGE_EXT: subfolder='images'
    elif ext in ALLOWED_AUDIO_EXT: subfolder='audio'
    elif ext in ALLOWED_VIDEO_EXT: subfolder='video'
    else: return None
    fn=secure_filename(f"{uuid.uuid4().hex[:12]}_{file.filename}")
    dp=os.path.join(app.config['UPLOAD_FOLDER'],subfolder); os.makedirs(dp,exist_ok=True)
    fp=os.path.join(dp,fn); file.save(fp)
    db=get_db(); rp=f"{subfolder}/{fn}"; ft='image' if ext in ALLOWED_IMAGE_EXT else 'audio' if ext in ALLOWED_AUDIO_EXT else 'video'
    db.execute("INSERT INTO media (filename,original_name,file_type,mime_type,file_size,folder,uploaded_by) VALUES (?,?,?,?,?,?,?)",
        (rp,file.filename,ft,file.content_type,os.path.getsize(fp),'places',session.get('user_id'))); db.commit()
    return rp
def log_action(uid,action,etype=None,eid=None,details=None):
    get_db().execute("INSERT INTO audit_log (user_id,action,entity_type,entity_id,details) VALUES (?,?,?,?,?)",(uid,action,etype,eid,details)); get_db().commit()

# Helper: get full hierarchy for a dham
def get_dham_hierarchy(place_id):
    db=get_db()
    key_places=db.execute("SELECT * FROM key_places WHERE parent_place_id=? AND is_visible=1 ORDER BY sort_order",(place_id,)).fetchall()
    hierarchy=[]
    for kp in key_places:
        kp_customs=db.execute("SELECT pcv.*,cfd.name,cfd.label,cfd.field_type,cfd.icon as field_icon FROM key_place_custom_values pcv JOIN custom_field_defs cfd ON pcv.field_def_id=cfd.id WHERE pcv.key_place_id=? AND pcv.is_visible=1 AND cfd.is_active=1 ORDER BY cfd.sort_order",(kp['id'],)).fetchall()
        key_spots=db.execute("SELECT ks.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color,sc.slug as cat_slug FROM key_spots ks LEFT JOIN spot_categories sc ON ks.category_id=sc.id WHERE ks.key_place_id=? AND ks.is_visible=1 ORDER BY ks.sort_order",(kp['id'],)).fetchall()
        spots_with_subs=[]
        for ks in key_spots:
            subs=db.execute("SELECT ss.*,ssc.name as cat_name,ssc.icon as cat_icon,ssc.color as cat_color,ssc.slug as cat_slug FROM sub_spots ss LEFT JOIN sub_spot_categories ssc ON ss.category_id=ssc.id WHERE ss.key_spot_id=? AND ss.is_visible=1 ORDER BY ss.sort_order",(ks['id'],)).fetchall()
            spots_with_subs.append({'spot':ks,'sub_spots':subs})
        hierarchy.append({'place':kp,'customs':kp_customs,'key_spots':spots_with_subs})
    return hierarchy

@app.context_processor
def inject_globals():
    db=get_db(); modules=db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall()
    return {'current_user':get_current_user(),'active_modules':modules,'current_year':datetime.now().year,'has_permission':has_permission,'builtin_fields':BUILTIN_FIELDS,'json':json,'field_icons':FIELD_ICONS,'field_default_icons':FIELD_DEFAULT_ICONS}

# ═══════════════════════════════════════════
# FRONTEND ROUTES
# ═══════════════════════════════════════════

@app.route('/')
def home():
    db=get_db()
    # Fetch up to 16 dhams with tier counts
    featured=db.execute("""SELECT p.*,GROUP_CONCAT(DISTINCT t.name) as tag_names,
        (SELECT COUNT(*) FROM key_places kp WHERE kp.parent_place_id=p.id AND kp.is_visible=1) as kp_count,
        (SELECT COUNT(*) FROM key_spots ks JOIN key_places kp2 ON ks.key_place_id=kp2.id WHERE kp2.parent_place_id=p.id AND ks.is_visible=1) as ks_count,
        (SELECT COUNT(*) FROM sub_spots ss JOIN key_spots ks2 ON ss.key_spot_id=ks2.id JOIN key_places kp3 ON ks2.key_place_id=kp3.id WHERE kp3.parent_place_id=p.id AND ss.is_visible=1) as ss_count
        FROM places p LEFT JOIN place_tags pt ON p.id=pt.place_id LEFT JOIN tags t ON pt.tag_id=t.id
        WHERE p.status='published' GROUP BY p.id ORDER BY p.is_featured DESC,p.updated_at DESC LIMIT 16""").fetchall()
    # Collect images from ALL tiers — featured_image AND gallery_images
    hero_images=[]
    def add_hero(img_path, row_dict):
        if img_path and img_path.strip():
            d = dict(row_dict)
            d['image'] = img_path.split(',')[0].strip()  # take first if comma-separated
            hero_images.append(d)
    # T1 Holy Dhams
    for row in db.execute("SELECT featured_image,title,slug,'T1' as tier FROM places WHERE status='published' ORDER BY is_featured DESC LIMIT 6").fetchall():
        add_hero(row['featured_image'], row)
    # Also check place_media for T1 gallery images
    for row in db.execute("""SELECT m.filename as gimg, p.title, p.slug, 'T1' as tier
        FROM media m JOIN place_media pm ON m.id=pm.media_id JOIN places p ON pm.place_id=p.id
        WHERE m.file_type='image' AND p.status='published' LIMIT 4""").fetchall():
        d = dict(row); d['image'] = row['gimg']; hero_images.append(d)
    # T2 Key Places
    for row in db.execute("""SELECT kp.featured_image,kp.gallery_images,kp.title,p.slug as dham_slug,kp.slug,p.title as dham_title,'T2' as tier
        FROM key_places kp JOIN places p ON kp.parent_place_id=p.id WHERE kp.is_visible=1 AND p.status='published' LIMIT 6""").fetchall():
        add_hero(row['featured_image'], row)
        if row['gallery_images']:
            for gf in row['gallery_images'].split(',')[:1]:
                add_hero(gf, row)
    # T3 Key Spots
    for row in db.execute("""SELECT ks.featured_image,ks.gallery_images,ks.title,p.slug as dham_slug,kp.slug as kp_slug,ks.slug,p.title as dham_title,kp.title as kp_title,'T3' as tier
        FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id
        WHERE ks.is_visible=1 AND p.status='published' LIMIT 6""").fetchall():
        add_hero(row['featured_image'], row)
        if row['gallery_images']:
            for gf in row['gallery_images'].split(',')[:1]:
                add_hero(gf, row)
    # T4 Key Points
    for row in db.execute("""SELECT ss.featured_image,ss.gallery_images,ss.title,p.slug as dham_slug,kp.slug as kp_slug,ks.slug as ks_slug,ss.slug,p.title as dham_title,kp.title as kp_title,ks.title as ks_title,'T4' as tier
        FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id
        WHERE ss.is_visible=1 AND p.status='published' LIMIT 6""").fetchall():
        add_hero(row['featured_image'], row)
        if row['gallery_images']:
            for gf in row['gallery_images'].split(',')[:1]:
                add_hero(gf, row)
    # Deduplicate by image path
    seen=set(); unique=[]
    for h in hero_images:
        if h['image'] not in seen:
            seen.add(h['image']); unique.append(h)
    hero_images=unique[:12]
    modules=db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall()
    stories=db.execute("SELECT me.*,m.name as module_name,m.icon as module_icon FROM module_entries me JOIN modules m ON me.module_id=m.id WHERE me.status='published' AND m.slug='sacred-stories' ORDER BY me.created_at DESC LIMIT 4").fetchall()
    stats={'places':db.execute("SELECT COUNT(*) FROM places WHERE status='published'").fetchone()[0],'entries':db.execute("SELECT COUNT(*) FROM module_entries WHERE status='published'").fetchone()[0],'modules':db.execute("SELECT COUNT(*) FROM modules WHERE is_active=1").fetchone()[0]}
    return render_template('frontend/home.html',featured=featured,recent=featured,modules=modules,stories=stories,stats=stats,hero_images=hero_images)

# ─── All Dhams Page ───
@app.route('/all-dhams')
def all_dhams():
    db=get_db(); q=request.args.get('q','')
    query="""SELECT p.*,GROUP_CONCAT(DISTINCT t.name) as tag_names,
        (SELECT COUNT(*) FROM key_places kp WHERE kp.parent_place_id=p.id AND kp.is_visible=1) as kp_count,
        (SELECT COUNT(*) FROM key_spots ks JOIN key_places kp2 ON ks.key_place_id=kp2.id WHERE kp2.parent_place_id=p.id AND ks.is_visible=1) as ks_count,
        (SELECT COUNT(*) FROM sub_spots ss JOIN key_spots ks2 ON ss.key_spot_id=ks2.id JOIN key_places kp3 ON ks2.key_place_id=kp3.id WHERE kp3.parent_place_id=p.id AND ss.is_visible=1) as ss_count
        FROM places p LEFT JOIN place_tags pt ON p.id=pt.place_id LEFT JOIN tags t ON pt.tag_id=t.id WHERE p.status='published'"""
    params=[]
    if q: query+=" AND (p.title LIKE ? OR p.short_description LIKE ? OR p.city LIKE ? OR p.state LIKE ?)"; params.extend([f'%{q}%']*4)
    query+=" GROUP BY p.id ORDER BY p.is_featured DESC,p.title"
    places=db.execute(query,params).fetchall()
    return render_template('frontend/all_dhams.html',places=places,query=q)

# ─── Static Pages ───
@app.route('/about')
def about(): return render_template('frontend/about.html')
@app.route('/privacy')
def privacy(): return render_template('frontend/privacy.html')
@app.route('/terms')
def terms(): return render_template('frontend/terms.html')

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method=='POST':
        name=request.form.get('name','').strip()
        email=request.form.get('email','').strip()
        subject=request.form.get('subject','').strip()
        message=request.form.get('message','').strip()
        captcha_answer=request.form.get('captcha_answer','').strip()
        captcha_expected=request.form.get('captcha_expected','').strip()
        errors=[]
        if not name: errors.append('Please share your name with us.')
        if not email: errors.append('We need your email to get back to you.')
        elif not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$',email): errors.append('That email address doesn\'t look quite right. Could you double-check it?')
        if not subject: errors.append('A brief subject helps us understand your message better.')
        if not message: errors.append('Please write your message so we can help you.')
        if not captcha_answer: errors.append('Please solve the small math puzzle to verify you\'re a real person.')
        elif captcha_answer!=captcha_expected: errors.append('The math answer wasn\'t quite right. Please try again with the new puzzle.')
        if errors:
            a=random.randint(10,50); b=random.randint(10,49)
            op=random.choice(['+','-']); ans=a+b if op=='+' else a-b
            for e in errors: flash(e,'error')
            return render_template('frontend/contact.html',captcha_a=a,captcha_b=b,captcha_op=op,captcha_ans=str(ans),form={'name':name,'email':email,'subject':subject,'message':message})
        # Success
        flash('Thank you for reaching out! Your message has been received with gratitude. We\'ll get back to you soon. 🙏','success')
        a=random.randint(10,50); b=random.randint(10,49)
        op=random.choice(['+','-']); ans=a+b if op=='+' else a-b
        return render_template('frontend/contact.html',captcha_a=a,captcha_b=b,captcha_op=op,captcha_ans=str(ans),form={})
    a=random.randint(10,50); b=random.randint(10,49)
    op=random.choice(['+','-']); ans=a+b if op=='+' else a-b
    return render_template('frontend/contact.html',captcha_a=a,captcha_b=b,captcha_op=op,captcha_ans=str(ans),form={})

# ─── Live Search API (for inline search) ───
@app.route('/api/v1/live-search')
def api_live_search():
    q=request.args.get('q','').strip()
    if not q or len(q)<2: return jsonify([])
    db=get_db(); results=[]
    like=f'%{q}%'
    for r in db.execute("SELECT id,title,slug,city,state,'T1' as tier,'Holy Dham' as tier_label FROM places WHERE status='published' AND (title LIKE ? OR city LIKE ? OR state LIKE ?) LIMIT 5",(like,like,like)).fetchall():
        results.append({'title':r['title'],'tier':r['tier'],'tier_label':r['tier_label'],'location':f"{r['city'] or ''}, {r['state'] or ''}".strip(', '),'url':url_for('place_detail',slug=r['slug'])})
    for r in db.execute("SELECT kp.title,kp.slug,p.slug as dham_slug,p.title as dham_title,'T2' as tier,'Key Place' as tier_label FROM key_places kp JOIN places p ON kp.parent_place_id=p.id WHERE kp.is_visible=1 AND p.status='published' AND kp.title LIKE ? LIMIT 5",(like,)).fetchall():
        results.append({'title':r['title'],'tier':r['tier'],'tier_label':r['tier_label'],'location':r['dham_title'],'url':url_for('key_place_detail',slug=r['dham_slug'],kp_slug=r['slug'])})
    for r in db.execute("SELECT ks.title,ks.slug,kp.slug as kp_slug,p.slug as dham_slug,kp.title as kp_title,p.title as dham_title,'T3' as tier,'Key Spot' as tier_label FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id WHERE ks.is_visible=1 AND p.status='published' AND ks.title LIKE ? LIMIT 5",(like,)).fetchall():
        results.append({'title':r['title'],'tier':r['tier'],'tier_label':r['tier_label'],'location':f"{r['kp_title']} › {r['dham_title']}",'url':url_for('key_spot_detail',slug=r['dham_slug'],kp_slug=r['kp_slug'],ks_slug=r['slug'])})
    for r in db.execute("SELECT ss.title,ss.slug,ks.slug as ks_slug,kp.slug as kp_slug,p.slug as dham_slug,ks.title as ks_title,kp.title as kp_title,p.title as dham_title,'T4' as tier,'Key Point' as tier_label FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id WHERE ss.is_visible=1 AND p.status='published' AND ss.title LIKE ? LIMIT 5",(like,)).fetchall():
        results.append({'title':r['title'],'tier':r['tier'],'tier_label':r['tier_label'],'location':f"{r['ks_title']} › {r['kp_title']} › {r['dham_title']}",'url':url_for('sub_spot_detail',slug=r['dham_slug'],kp_slug=r['kp_slug'],ks_slug=r['ks_slug'],ss_slug=r['slug'])})
    return jsonify(results[:15])

@app.route('/place/<slug>')
def place_detail(slug):
    db=get_db(); place=db.execute("SELECT * FROM places WHERE slug=? AND status='published'",(slug,)).fetchone()
    if not place: abort(404)
    db.execute("UPDATE places SET view_count=view_count+1 WHERE id=?",(place['id'],)); db.commit()
    tags=db.execute("SELECT t.* FROM tags t JOIN place_tags pt ON t.id=pt.tag_id WHERE pt.place_id=?",(place['id'],)).fetchall()
    visibility=json.loads(place['field_visibility'] or '{}')
    custom_values=db.execute("SELECT pcv.*,cfd.name,cfd.label,cfd.field_type,cfd.icon as field_icon FROM place_custom_values pcv JOIN custom_field_defs cfd ON pcv.field_def_id=cfd.id WHERE pcv.place_id=? AND pcv.is_visible=1 AND cfd.is_active=1 ORDER BY cfd.sort_order",(place['id'],)).fetchall()
    hierarchy=get_dham_hierarchy(place['id'])
    media_items=db.execute("SELECT m.*,pm.media_role FROM media m JOIN place_media pm ON m.id=pm.media_id WHERE pm.place_id=? ORDER BY pm.sort_order",(place['id'],)).fetchall()
    nearby=db.execute("SELECT p.*,np.distance_km FROM places p JOIN nearby_places np ON p.id=np.nearby_place_id WHERE np.place_id=? AND p.status='published'",(place['id'],)).fetchall()
    related_entries=db.execute("SELECT me.*,m.name as module_name,m.icon as module_icon,m.slug as module_slug FROM module_entries me JOIN modules m ON me.module_id=m.id WHERE me.place_id=? AND me.status='published' ORDER BY m.sort_order",(place['id'],)).fetchall()
    related=db.execute("SELECT DISTINCT p.* FROM places p JOIN place_tags pt ON p.id=pt.place_id WHERE pt.tag_id IN (SELECT tag_id FROM place_tags WHERE place_id=?) AND p.id!=? AND p.status='published' LIMIT 3",(place['id'],place['id'])).fetchall()
    spot_categories=db.execute("SELECT * FROM spot_categories ORDER BY name").fetchall()
    return render_template('frontend/place.html',place=place,tags=tags,visibility=visibility,custom_values=custom_values,hierarchy=hierarchy,media=media_items,nearby=nearby,related_entries=related_entries,related=related,spot_categories=spot_categories)

@app.route('/place/<slug>/key/<kp_slug>')
def key_place_detail(slug, kp_slug):
    db=get_db(); place=db.execute("SELECT * FROM places WHERE slug=? AND status='published'",(slug,)).fetchone()
    if not place: abort(404)
    kp=db.execute("SELECT * FROM key_places WHERE parent_place_id=? AND slug=? AND is_visible=1",(place['id'],kp_slug)).fetchone()
    if not kp: abort(404)
    kp_customs=db.execute("SELECT kpcv.*,cfd.name,cfd.label,cfd.field_type,cfd.icon as field_icon FROM key_place_custom_values kpcv JOIN custom_field_defs cfd ON kpcv.field_def_id=cfd.id WHERE kpcv.key_place_id=? AND kpcv.is_visible=1 AND cfd.is_active=1 ORDER BY cfd.sort_order",(kp['id'],)).fetchall()
    key_spots=db.execute("SELECT ks.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color FROM key_spots ks LEFT JOIN spot_categories sc ON ks.category_id=sc.id WHERE ks.key_place_id=? AND ks.is_visible=1 ORDER BY ks.sort_order",(kp['id'],)).fetchall()
    spots_with_subs=[]
    for ks in key_spots:
        subs=db.execute("SELECT ss.*,ssc.name as cat_name,ssc.icon as cat_icon,ssc.color as cat_color FROM sub_spots ss LEFT JOIN sub_spot_categories ssc ON ss.category_id=ssc.id WHERE ss.key_spot_id=? AND ss.is_visible=1 ORDER BY ss.sort_order",(ks['id'],)).fetchall()
        spots_with_subs.append({'spot':ks,'sub_spots':subs})
    siblings=db.execute("SELECT * FROM key_places WHERE parent_place_id=? AND is_visible=1 AND id!=? ORDER BY sort_order",(place['id'],kp['id'])).fetchall()
    tags=db.execute("SELECT t.* FROM tags t JOIN place_tags pt ON t.id=pt.tag_id WHERE pt.place_id=?",(place['id'],)).fetchall()
    kp_gallery=[x.strip() for x in (kp['gallery_images'] or '').split(',') if x.strip()]
    return render_template('frontend/key_place.html',place=place,kp=kp,kp_customs=kp_customs,key_spots=spots_with_subs,siblings=siblings,tags=tags,kp_gallery=kp_gallery)

@app.route('/place/<slug>/key/<kp_slug>/spot/<ks_slug>')
def key_spot_detail(slug, kp_slug, ks_slug):
    db=get_db(); place=db.execute("SELECT * FROM places WHERE slug=? AND status='published'",(slug,)).fetchone()
    if not place: abort(404)
    kp=db.execute("SELECT * FROM key_places WHERE parent_place_id=? AND slug=?",(place['id'],kp_slug)).fetchone()
    if not kp: abort(404)
    ks=db.execute("SELECT ks.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color FROM key_spots ks LEFT JOIN spot_categories sc ON ks.category_id=sc.id WHERE ks.key_place_id=? AND ks.slug=? AND ks.is_visible=1",(kp['id'],ks_slug)).fetchone()
    if not ks: abort(404)
    sub_spots=db.execute("SELECT ss.*,ssc.name as cat_name,ssc.icon as cat_icon,ssc.color as cat_color FROM sub_spots ss LEFT JOIN sub_spot_categories ssc ON ss.category_id=ssc.id WHERE ss.key_spot_id=? AND ss.is_visible=1 ORDER BY ss.sort_order",(ks['id'],)).fetchall()
    ks_customs=db.execute("SELECT kscv.*,cfd.name,cfd.label,cfd.field_type,cfd.icon as field_icon FROM key_spot_custom_values kscv JOIN custom_field_defs cfd ON kscv.field_def_id=cfd.id WHERE kscv.key_spot_id=? AND kscv.is_visible=1 AND cfd.is_active=1 ORDER BY cfd.sort_order",(ks['id'],)).fetchall()
    ks_gallery=[x.strip() for x in (ks['gallery_images'] or '').split(',') if x.strip()]
    siblings=db.execute("SELECT ks2.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color FROM key_spots ks2 LEFT JOIN spot_categories sc ON ks2.category_id=sc.id WHERE ks2.key_place_id=? AND ks2.is_visible=1 AND ks2.id!=? ORDER BY ks2.sort_order",(kp['id'],ks['id'])).fetchall()
    return render_template('frontend/key_spot.html',place=place,kp=kp,ks=ks,sub_spots=sub_spots,siblings=siblings,ks_customs=ks_customs,ks_gallery=ks_gallery)

@app.route('/place/<slug>/key/<kp_slug>/spot/<ks_slug>/sub/<ss_slug>')
def sub_spot_detail(slug, kp_slug, ks_slug, ss_slug):
    db=get_db(); place=db.execute("SELECT * FROM places WHERE slug=? AND status='published'",(slug,)).fetchone()
    if not place: abort(404)
    kp=db.execute("SELECT * FROM key_places WHERE parent_place_id=? AND slug=?",(place['id'],kp_slug)).fetchone()
    if not kp: abort(404)
    ks=db.execute("SELECT ks.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color FROM key_spots ks LEFT JOIN spot_categories sc ON ks.category_id=sc.id WHERE ks.key_place_id=? AND ks.slug=?",(kp['id'],ks_slug)).fetchone()
    if not ks: abort(404)
    ss=db.execute("SELECT ss.*,ssc.name as cat_name,ssc.icon as cat_icon,ssc.color as cat_color FROM sub_spots ss LEFT JOIN sub_spot_categories ssc ON ss.category_id=ssc.id WHERE ss.key_spot_id=? AND ss.slug=? AND ss.is_visible=1",(ks['id'],ss_slug)).fetchone()
    if not ss: abort(404)
    ss_customs=db.execute("SELECT sscv.*,cfd.name,cfd.label,cfd.field_type,cfd.icon as field_icon FROM sub_spot_custom_values sscv JOIN custom_field_defs cfd ON sscv.field_def_id=cfd.id WHERE sscv.sub_spot_id=? AND sscv.is_visible=1 AND cfd.is_active=1 ORDER BY cfd.sort_order",(ss['id'],)).fetchall()
    ss_gallery=[x.strip() for x in (ss['gallery_images'] or '').split(',') if x.strip()]
    siblings=db.execute("SELECT ss2.*,ssc.name as cat_name,ssc.icon as cat_icon,ssc.color as cat_color FROM sub_spots ss2 LEFT JOIN sub_spot_categories ssc ON ss2.category_id=ssc.id WHERE ss2.key_spot_id=? AND ss2.is_visible=1 AND ss2.id!=? ORDER BY ss2.sort_order",(ks['id'],ss['id'])).fetchall()
    return render_template('frontend/sub_spot.html',place=place,kp=kp,ks=ks,ss=ss,siblings=siblings,ss_customs=ss_customs,ss_gallery=ss_gallery)

@app.route('/explore')
def explore():
    db=get_db(); page=request.args.get('page',1,type=int); per_page=12; tag=request.args.get('tag',''); state=request.args.get('state',''); q=request.args.get('q','')
    query="SELECT p.*,GROUP_CONCAT(t.name) as tag_names FROM places p LEFT JOIN place_tags pt ON p.id=pt.place_id LEFT JOIN tags t ON pt.tag_id=t.id WHERE p.status='published'"; params=[]
    if q: query+=" AND (p.title LIKE ? OR p.short_description LIKE ? OR p.city LIKE ? OR p.state LIKE ?)"; params.extend([f'%{q}%']*4)
    if tag: query+=" AND t.slug=?"; params.append(tag)
    if state: query+=" AND p.state=?"; params.append(state)
    query+=" GROUP BY p.id ORDER BY p.is_featured DESC,p.updated_at DESC"; total=len(db.execute(query,params).fetchall())
    query+=" LIMIT ? OFFSET ?"; params.extend([per_page,(page-1)*per_page]); places=db.execute(query,params).fetchall()
    return render_template('frontend/explore.html',places=places,tags=db.execute("SELECT * FROM tags ORDER BY name").fetchall(),states=db.execute("SELECT DISTINCT state FROM places WHERE status='published' AND state IS NOT NULL ORDER BY state").fetchall(),current_tag=tag,current_state=state,query=q,page=page,total=total,per_page=per_page)

@app.route('/module/<slug>')
def module_page(slug):
    db=get_db(); module=db.execute("SELECT * FROM modules WHERE slug=? AND is_active=1",(slug,)).fetchone()
    if not module: abort(404)
    entries=db.execute("SELECT me.*,p.title as place_title,p.slug as place_slug FROM module_entries me LEFT JOIN places p ON me.place_id=p.id WHERE me.module_id=? AND me.status='published' ORDER BY me.sort_order,me.created_at DESC",(module['id'],)).fetchall()
    return render_template('frontend/module.html',module=module,entries=entries)

@app.route('/module/<mod_slug>/<entry_slug>')
def entry_detail(mod_slug,entry_slug):
    db=get_db(); module=db.execute("SELECT * FROM modules WHERE slug=?",(mod_slug,)).fetchone()
    if not module: abort(404)
    entry=db.execute("SELECT me.*,p.title as place_title,p.slug as place_slug FROM module_entries me LEFT JOIN places p ON me.place_id=p.id WHERE me.module_id=? AND me.slug=? AND me.status='published'",(module['id'],entry_slug)).fetchone()
    if not entry: abort(404)
    return render_template('frontend/entry.html',module=module,entry=entry,media=[])

@app.route('/search')
def search(): q=request.args.get('q',''); return redirect(url_for('explore',q=q)) if q else redirect(url_for('explore'))

# ═══════════════════════════════════════════
# ADMIN ROUTES
# ═══════════════════════════════════════════

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        db=get_db(); user=db.execute("SELECT * FROM users WHERE username=? AND is_active=1",(request.form.get('username',''),)).fetchone()
        if user and user['password_hash']==hash_password(request.form.get('password','')):
            session['user_id']=user['id']; db.execute("UPDATE users SET last_login=? WHERE id=?",(datetime.now(),user['id'])); db.commit()
            flash('Welcome back, '+user['display_name']+'!','success'); return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials.','error')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout(): session.clear(); flash('Logged out.','info'); return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    db=get_db()
    stats={'places':db.execute("SELECT COUNT(*) FROM places").fetchone()[0],'published':db.execute("SELECT COUNT(*) FROM places WHERE status='published'").fetchone()[0],'key_places':db.execute("SELECT COUNT(*) FROM key_places").fetchone()[0],'entries':db.execute("SELECT COUNT(*) FROM module_entries").fetchone()[0],'media':db.execute("SELECT COUNT(*) FROM media").fetchone()[0],'users':db.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0],'modules':db.execute("SELECT COUNT(*) FROM modules WHERE is_active=1").fetchone()[0],'key_spots':db.execute("SELECT COUNT(*) FROM key_spots").fetchone()[0],'sub_spots':db.execute("SELECT COUNT(*) FROM sub_spots").fetchone()[0]}
    return render_template('admin/dashboard.html',stats=stats,recent_places=db.execute("SELECT * FROM places ORDER BY updated_at DESC LIMIT 5").fetchall(),recent_log=db.execute("SELECT al.*,u.display_name FROM audit_log al LEFT JOIN users u ON al.user_id=u.id ORDER BY al.created_at DESC LIMIT 10").fetchall(),modules=db.execute("SELECT m.*,(SELECT COUNT(*) FROM module_entries me WHERE me.module_id=m.id) as entry_count FROM modules m ORDER BY m.sort_order").fetchall())

# Custom Fields
@app.route('/admin/fields')
@login_required
def admin_fields():
    return render_template('admin/fields.html',fields=get_db().execute("SELECT * FROM custom_field_defs ORDER BY sort_order").fetchall())

@app.route('/admin/fields/new', methods=['POST'])
@login_required
def admin_field_new():
    db=get_db(); name=slugify(request.form['label']).replace('-','_')
    icon=request.form.get('icon','📋')
    try:
        db.execute("INSERT INTO custom_field_defs (name,label,field_type,placeholder,sort_order,applies_to,icon) VALUES (?,?,?,?,?,?,?)",(name,request.form['label'],request.form['field_type'],request.form.get('placeholder',''),request.form.get('sort_order',0,type=int),request.form.get('applies_to','both'),icon))
        db.commit(); flash('Field created!','success')
    except sqlite3.IntegrityError: flash('Field already exists.','error')
    return redirect(url_for('admin_fields'))

@app.route('/admin/fields/<int:field_id>/update', methods=['POST'])
@login_required
def admin_field_update(field_id):
    db=get_db(); f=request.form
    db.execute("UPDATE custom_field_defs SET label=?,field_type=?,placeholder=?,sort_order=?,applies_to=?,icon=? WHERE id=?",
        (f['label'],f['field_type'],f.get('placeholder',''),f.get('sort_order',0,type=int),f.get('applies_to','both'),f.get('icon','📋'),field_id))
    db.commit(); flash('Field updated!','success')
    return redirect(url_for('admin_fields'))

@app.route('/admin/fields/<int:field_id>/toggle', methods=['POST'])
@login_required
def admin_field_toggle(field_id):
    get_db().execute("UPDATE custom_field_defs SET is_active=CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?",(field_id,)); get_db().commit()
    return redirect(url_for('admin_fields'))

@app.route('/admin/fields/<int:field_id>/delete', methods=['POST'])
@login_required
def admin_field_delete(field_id):
    get_db().execute("DELETE FROM custom_field_defs WHERE id=?",(field_id,)); get_db().commit(); flash('Deleted.','info')
    return redirect(url_for('admin_fields'))

# ─── Places (Dham) CRUD ───
@app.route('/admin/places')
@login_required
def admin_places():
    db=get_db(); sf=request.args.get('status',''); q=request.args.get('q','')
    query="SELECT p.*,(SELECT COUNT(*) FROM key_places kp WHERE kp.parent_place_id=p.id) as kp_count FROM places p WHERE 1=1"; params=[]
    if sf: query+=" AND p.status=?"; params.append(sf)
    if q: query+=" AND (p.title LIKE ? OR p.city LIKE ? OR p.state LIKE ?)"; params.extend([f'%{q}%']*3)
    return render_template('admin/places.html',places=db.execute(query+" ORDER BY p.updated_at DESC",params).fetchall(),current_status=sf,query=q)

@app.route('/admin/places/new', methods=['GET','POST'])
@login_required
def admin_place_new():
    db=get_db()
    if request.method=='POST': return _save_place(None)
    return render_template('admin/place_form.html',place=None,tags=db.execute("SELECT * FROM tags ORDER BY name").fetchall(),place_tags=[],custom_fields=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 AND applies_to IN ('both','place') ORDER BY sort_order").fetchall(),custom_values={},key_places=[],key_place_customs={},editing=False,spot_categories=db.execute("SELECT * FROM spot_categories ORDER BY name").fetchall(),sub_spot_categories=db.execute("SELECT * FROM sub_spot_categories ORDER BY name").fetchall())

@app.route('/admin/places/<int:place_id>/edit', methods=['GET','POST'])
@login_required
def admin_place_edit(place_id):
    db=get_db(); place=db.execute("SELECT * FROM places WHERE id=?",(place_id,)).fetchone()
    if not place: abort(404)
    if request.method=='POST': return _save_place(place_id)
    tags=db.execute("SELECT * FROM tags ORDER BY name").fetchall()
    ptags=[r['tag_id'] for r in db.execute("SELECT tag_id FROM place_tags WHERE place_id=?",(place_id,)).fetchall()]
    cfs=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 AND applies_to IN ('both','place') ORDER BY sort_order").fetchall()
    cvs={r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible']} for r in db.execute("SELECT field_def_id,value,is_visible FROM place_custom_values WHERE place_id=?",(place_id,)).fetchall()}
    kps=db.execute("SELECT * FROM key_places WHERE parent_place_id=? ORDER BY sort_order",(place_id,)).fetchall()
    kpc={}
    for kp in kps:
        kpc[kp['id']]={r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible']} for r in db.execute("SELECT field_def_id,value,is_visible FROM key_place_custom_values WHERE key_place_id=?",(kp['id'],)).fetchall()}
    # Get key spots count per key place
    kp_spot_counts={}
    for kp in kps:
        kp_spot_counts[kp['id']]=db.execute("SELECT COUNT(*) FROM key_spots WHERE key_place_id=?",(kp['id'],)).fetchone()[0]
    # Fetch ALL key_spots for this dham (for Tier 3 tab)
    all_spots=db.execute("SELECT ks.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color,kp.title as kp_title,kp.id as kp_id,kp.slug as kp_slug FROM key_spots ks LEFT JOIN spot_categories sc ON ks.category_id=sc.id JOIN key_places kp ON ks.key_place_id=kp.id WHERE kp.parent_place_id=? ORDER BY kp.sort_order,ks.sort_order",(place_id,)).fetchall()
    # Fetch ALL sub_spots (key points) for this dham (for Tier 4 tab)
    all_points=db.execute("SELECT ss.*,ssc.name as cat_name,ssc.icon as cat_icon,ssc.color as cat_color,ks.title as ks_title,ks.id as ks_id,ks.slug as ks_slug,sc2.name as ks_cat_name,sc2.icon as ks_cat_icon,kp.title as kp_title,kp.id as kp_id FROM sub_spots ss LEFT JOIN sub_spot_categories ssc ON ss.category_id=ssc.id JOIN key_spots ks ON ss.key_spot_id=ks.id LEFT JOIN spot_categories sc2 ON ks.category_id=sc2.id JOIN key_places kp ON ks.key_place_id=kp.id WHERE kp.parent_place_id=? ORDER BY kp.sort_order,ks.sort_order,ss.sort_order",(place_id,)).fetchall()
    return render_template('admin/place_form.html',place=place,tags=tags,place_tags=ptags,custom_fields=cfs,custom_values=cvs,key_places=kps,key_place_customs=kpc,editing=True,spot_categories=db.execute("SELECT * FROM spot_categories ORDER BY name").fetchall(),sub_spot_categories=db.execute("SELECT * FROM sub_spot_categories ORDER BY name").fetchall(),kp_spot_counts=kp_spot_counts,all_spots=all_spots,all_points=all_points)

def _save_place(place_id):
    db=get_db(); f=request.form; title=f['title']; slug=slugify(title)
    fi=f.get('featured_image_existing','')
    if 'featured_image_file' in request.files:
        uf=request.files['featured_image_file']
        if uf and uf.filename: u=save_upload(uf,'images'); fi=u if u else fi
    vis={}
    for bf in BUILTIN_FIELDS: vis[bf['key']]=1 if f.get(f"vis_{bf['key']}") else 0
    lat=f.get('latitude',type=float); lng=f.get('longitude',type=float)
    if place_id:
        db.execute("UPDATE places SET title=?,short_description=?,full_content=?,state=?,city=?,country=?,latitude=?,longitude=?,featured_image=?,status=?,is_featured=?,field_visibility=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (title,f.get('short_description',''),f.get('full_content',''),f.get('state',''),f.get('city',''),f.get('country','India'),lat,lng,fi,f.get('status','draft'),1 if f.get('is_featured') else 0,json.dumps(vis),place_id))
    else:
        if db.execute("SELECT id FROM places WHERE slug=?",(slug,)).fetchone(): slug+='-'+uuid.uuid4().hex[:6]
        db.execute("INSERT INTO places (title,slug,short_description,full_content,state,city,country,latitude,longitude,featured_image,status,is_featured,field_visibility,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title,slug,f.get('short_description',''),f.get('full_content',''),f.get('state',''),f.get('city',''),f.get('country','India'),lat,lng,fi,f.get('status','draft'),1 if f.get('is_featured') else 0,json.dumps(vis),session['user_id']))
        place_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("DELETE FROM place_tags WHERE place_id=?",(place_id,))
    for tid in f.getlist('tags'): db.execute("INSERT OR IGNORE INTO place_tags VALUES (?,?)",(place_id,tid))
    # Custom values
    cfs=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 ORDER BY sort_order").fetchall()
    for cf in cfs:
        val=''; fk=f"cf_file_{cf['id']}"
        if fk in request.files:
            uf=request.files[fk]
            if uf and uf.filename: u=save_upload(uf); val=u if u else val
        fmk=f"cf_files_{cf['id']}"
        if fmk in request.files:
            paths=[]
            for uf in request.files.getlist(fmk):
                if uf and uf.filename: u=save_upload(uf); paths.append(u) if u else None
            if paths:
                ev=f.get(f"cf_{cf['id']}",'')
                if ev: paths=ev.split(',')+paths
                val=','.join(paths)
        if not val: val=f.get(f"cf_{cf['id']}",'')
        iv=1 if f.get(f"cf_vis_{cf['id']}") else 0
        db.execute("INSERT OR REPLACE INTO place_custom_values (place_id,field_def_id,value,is_visible) VALUES (?,?,?,?)",(place_id,cf['id'],val,iv))
    # Key Places (Tier 2)
    existing_kpids=[r['id'] for r in db.execute("SELECT id FROM key_places WHERE parent_place_id=?",(place_id,)).fetchall()]
    submitted_kpids=[]; kpi=0
    while True:
        kt=f.get(f'kp_{kpi}_title')
        if kt is None: break
        if not kt.strip(): kpi+=1; continue
        kpid=f.get(f'kp_{kpi}_id',type=int); ks=slugify(kt); ksd=f.get(f'kp_{kpi}_short_description','')
        kfc=f.get(f'kp_{kpi}_full_content',''); klat=f.get(f'kp_{kpi}_latitude',type=float); klng=f.get(f'kp_{kpi}_longitude',type=float)
        kv=1 if f.get(f'kp_{kpi}_is_visible') else 0
        kimg=f.get(f'kp_{kpi}_featured_image_existing','')
        kfk=f'kp_{kpi}_featured_image_file'
        if kfk in request.files:
            uf=request.files[kfk]
            if uf and uf.filename: u=save_upload(uf,'images'); kimg=u if u else kimg
        # Gallery images for T2
        kgallery=f.get(f'kp_{kpi}_gallery_existing','')
        kgk=f'kp_{kpi}_gallery_files'
        if kgk in request.files:
            new_imgs=[]
            for gf in request.files.getlist(kgk):
                if gf and gf.filename: u=save_upload(gf,'images'); new_imgs.append(u) if u else None
            if new_imgs:
                existing_imgs=[x for x in kgallery.split(',') if x.strip()] if kgallery else []
                kgallery=','.join(existing_imgs+new_imgs)
        if kpid and kpid in existing_kpids:
            db.execute("UPDATE key_places SET title=?,slug=?,short_description=?,full_content=?,featured_image=?,gallery_images=?,latitude=?,longitude=?,sort_order=?,is_visible=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (kt,ks,ksd,kfc,kimg,kgallery,klat,klng,kpi,kv,kpid)); submitted_kpids.append(kpid)
        else:
            db.execute("INSERT INTO key_places (parent_place_id,title,slug,short_description,full_content,featured_image,gallery_images,latitude,longitude,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (place_id,kt,ks,ksd,kfc,kimg,kgallery,klat,klng,kpi,kv))
            kpid=db.execute("SELECT last_insert_rowid()").fetchone()[0]; submitted_kpids.append(kpid)
        for cf in cfs:
            kcv=''; kcfk=f"kp_{kpi}_cf_file_{cf['id']}"
            if kcfk in request.files:
                uf=request.files[kcfk]
                if uf and uf.filename: u=save_upload(uf); kcv=u if u else kcv
            if not kcv: kcv=f.get(f"kp_{kpi}_cf_{cf['id']}",'')
            kcvis=1 if f.get(f"kp_{kpi}_cf_vis_{cf['id']}") else 0
            if kcv or kcvis: db.execute("INSERT OR REPLACE INTO key_place_custom_values (key_place_id,field_def_id,value,is_visible) VALUES (?,?,?,?)",(kpid,cf['id'],kcv,kcvis))
        kpi+=1
    for oid in existing_kpids:
        if oid not in submitted_kpids: db.execute("DELETE FROM key_places WHERE id=?",(oid,))
    db.commit(); log_action(session['user_id'],'save_place','place',place_id,title)
    flash(f'Holy Dham "{title}" saved!','success'); return redirect(url_for('admin_places'))

@app.route('/admin/places/<int:place_id>/delete', methods=['POST'])
@login_required
def admin_place_delete(place_id):
    db=get_db(); db.execute("DELETE FROM places WHERE id=?",(place_id,)); db.commit(); flash('Deleted.','info'); return redirect(url_for('admin_places'))

# ─── Key Spots (Tier 3) Admin ───
@app.route('/admin/key-place/<int:kp_id>/spots')
@login_required
def admin_key_place_spots(kp_id):
    db=get_db()
    kp=db.execute("SELECT kp.*,p.title as dham_title,p.slug as dham_slug,p.id as dham_id FROM key_places kp JOIN places p ON kp.parent_place_id=p.id WHERE kp.id=?",(kp_id,)).fetchone()
    if not kp: abort(404)
    spots=db.execute("SELECT ks.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color FROM key_spots ks LEFT JOIN spot_categories sc ON ks.category_id=sc.id WHERE ks.key_place_id=? ORDER BY ks.sort_order",(kp_id,)).fetchall()
    cfs=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 AND applies_to IN ('both','key_place') ORDER BY sort_order").fetchall()
    ks_customs={}
    for s in spots:
        ks_customs[s['id']]={r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible']} for r in db.execute("SELECT field_def_id,value,is_visible FROM key_spot_custom_values WHERE key_spot_id=?",(s['id'],)).fetchall()}
    return render_template('admin/key_spots.html',kp=kp,spots=spots,spot_categories=db.execute("SELECT * FROM spot_categories ORDER BY name").fetchall(),custom_fields=cfs,ks_customs=ks_customs,field_icons=FIELD_ICONS)

@app.route('/admin/key-place/<int:kp_id>/spots/save', methods=['POST'])
@login_required
def admin_key_spots_save(kp_id):
    db=get_db(); f=request.form
    cfs=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 ORDER BY sort_order").fetchall()
    existing=[r['id'] for r in db.execute("SELECT id FROM key_spots WHERE key_place_id=?",(kp_id,)).fetchall()]
    submitted=[]; i=0
    while True:
        t=f.get(f'ks_{i}_title')
        if t is None: break
        if not t.strip(): i+=1; continue
        sid=f.get(f'ks_{i}_id',type=int); slug=slugify(t)
        catid=f.get(f'ks_{i}_category',type=int) or None
        sd=f.get(f'ks_{i}_short_description',''); fc=f.get(f'ks_{i}_full_content','')
        state=f.get(f'ks_{i}_state',''); city=f.get(f'ks_{i}_city',''); country=f.get(f'ks_{i}_country','')
        lat=f.get(f'ks_{i}_latitude',type=float); lng=f.get(f'ks_{i}_longitude',type=float)
        vis=1 if f.get(f'ks_{i}_is_visible') else 0
        img=f.get(f'ks_{i}_featured_image_existing','')
        fk=f'ks_{i}_featured_image_file'
        if fk in request.files:
            uf=request.files[fk]
            if uf and uf.filename: u=save_upload(uf,'images'); img=u if u else img
        # Gallery images
        gallery=f.get(f'ks_{i}_gallery_existing','')
        gk=f'ks_{i}_gallery_files'
        if gk in request.files:
            new_imgs=[]
            for gf in request.files.getlist(gk):
                if gf and gf.filename: u=save_upload(gf,'images'); new_imgs.append(u) if u else None
            if new_imgs:
                existing_imgs=[x for x in gallery.split(',') if x.strip()] if gallery else []
                gallery=','.join(existing_imgs+new_imgs)
        if sid and sid in existing:
            db.execute("UPDATE key_spots SET category_id=?,title=?,slug=?,short_description=?,full_content=?,featured_image=?,gallery_images=?,state=?,city=?,country=?,latitude=?,longitude=?,sort_order=?,is_visible=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (catid,t,slug,sd,fc,img,gallery,state,city,country,lat,lng,i,vis,sid)); submitted.append(sid)
        else:
            db.execute("INSERT INTO key_spots (key_place_id,category_id,title,slug,short_description,full_content,featured_image,gallery_images,state,city,country,latitude,longitude,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (kp_id,catid,t,slug,sd,fc,img,gallery,state,city,country,lat,lng,i,vis))
            sid=db.execute("SELECT last_insert_rowid()").fetchone()[0]; submitted.append(sid)
        # Save custom fields for this spot
        for cf in cfs:
            cv=''; cfk=f"ks_{i}_cf_file_{cf['id']}"
            if cfk in request.files:
                uf=request.files[cfk]
                if uf and uf.filename: u=save_upload(uf); cv=u if u else cv
            cfmk=f"ks_{i}_cf_files_{cf['id']}"
            if cfmk in request.files:
                paths=[]
                for uf in request.files.getlist(cfmk):
                    if uf and uf.filename: u=save_upload(uf); paths.append(u) if u else None
                if paths:
                    ev=f.get(f"ks_{i}_cf_{cf['id']}",'')
                    if ev: paths=ev.split(',')+paths
                    cv=','.join(paths)
            if not cv: cv=f.get(f"ks_{i}_cf_{cf['id']}",'')
            cfvis=1 if f.get(f"ks_{i}_cf_vis_{cf['id']}") else 0
            if cv or cfvis: db.execute("INSERT OR REPLACE INTO key_spot_custom_values (key_spot_id,field_def_id,value,is_visible) VALUES (?,?,?,?)",(sid,cf['id'],cv,cfvis))
        i+=1
    for oid in existing:
        if oid not in submitted: db.execute("DELETE FROM key_spots WHERE id=?",(oid,))
    db.commit(); flash('Key Spots saved!','success'); return redirect(url_for('admin_key_place_spots',kp_id=kp_id))

# ─── Sub-Spots (Tier 4) Admin ───
@app.route('/admin/key-spot/<int:ks_id>/subs')
@login_required
def admin_key_spot_subs(ks_id):
    db=get_db()
    ks=db.execute("SELECT ks.*,sc.name as cat_name,sc.icon as cat_icon,kp.title as kp_title,kp.id as kp_id,p.title as dham_title,p.slug as dham_slug,p.id as dham_id FROM key_spots ks LEFT JOIN spot_categories sc ON ks.category_id=sc.id JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id WHERE ks.id=?",(ks_id,)).fetchone()
    if not ks: abort(404)
    subs=db.execute("SELECT ss.*,ssc.name as cat_name,ssc.icon as cat_icon,ssc.color as cat_color FROM sub_spots ss LEFT JOIN sub_spot_categories ssc ON ss.category_id=ssc.id WHERE ss.key_spot_id=? ORDER BY ss.sort_order",(ks_id,)).fetchall()
    cfs=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 AND applies_to IN ('both','key_place') ORDER BY sort_order").fetchall()
    ss_customs={}
    for s in subs:
        ss_customs[s['id']]={r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible']} for r in db.execute("SELECT field_def_id,value,is_visible FROM sub_spot_custom_values WHERE sub_spot_id=?",(s['id'],)).fetchall()}
    return render_template('admin/sub_spots.html',ks=ks,subs=subs,sub_spot_categories=db.execute("SELECT * FROM sub_spot_categories ORDER BY name").fetchall(),custom_fields=cfs,ss_customs=ss_customs,field_icons=FIELD_ICONS)

@app.route('/admin/key-spot/<int:ks_id>/subs/save', methods=['POST'])
@login_required
def admin_sub_spots_save(ks_id):
    db=get_db(); f=request.form
    cfs=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 ORDER BY sort_order").fetchall()
    existing=[r['id'] for r in db.execute("SELECT id FROM sub_spots WHERE key_spot_id=?",(ks_id,)).fetchall()]
    submitted=[]; i=0
    while True:
        t=f.get(f'ss_{i}_title')
        if t is None: break
        if not t.strip(): i+=1; continue
        sid=f.get(f'ss_{i}_id',type=int); slug=slugify(t)
        catid=f.get(f'ss_{i}_category',type=int) or None
        sd=f.get(f'ss_{i}_short_description',''); fc=f.get(f'ss_{i}_full_content','')
        state=f.get(f'ss_{i}_state',''); city=f.get(f'ss_{i}_city',''); country=f.get(f'ss_{i}_country','')
        lat=f.get(f'ss_{i}_latitude',type=float); lng=f.get(f'ss_{i}_longitude',type=float)
        vis=1 if f.get(f'ss_{i}_is_visible') else 0
        img=f.get(f'ss_{i}_featured_image_existing','')
        fk=f'ss_{i}_featured_image_file'
        if fk in request.files:
            uf=request.files[fk]
            if uf and uf.filename: u=save_upload(uf,'images'); img=u if u else img
        gallery=f.get(f'ss_{i}_gallery_existing','')
        gk=f'ss_{i}_gallery_files'
        if gk in request.files:
            new_imgs=[]
            for gf in request.files.getlist(gk):
                if gf and gf.filename: u=save_upload(gf,'images'); new_imgs.append(u) if u else None
            if new_imgs:
                existing_imgs=[x for x in gallery.split(',') if x.strip()] if gallery else []
                gallery=','.join(existing_imgs+new_imgs)
        if sid and sid in existing:
            db.execute("UPDATE sub_spots SET category_id=?,title=?,slug=?,short_description=?,full_content=?,featured_image=?,gallery_images=?,state=?,city=?,country=?,latitude=?,longitude=?,sort_order=?,is_visible=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (catid,t,slug,sd,fc,img,gallery,state,city,country,lat,lng,i,vis,sid)); submitted.append(sid)
        else:
            db.execute("INSERT INTO sub_spots (key_spot_id,category_id,title,slug,short_description,full_content,featured_image,gallery_images,state,city,country,latitude,longitude,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ks_id,catid,t,slug,sd,fc,img,gallery,state,city,country,lat,lng,i,vis))
            sid=db.execute("SELECT last_insert_rowid()").fetchone()[0]; submitted.append(sid)
        for cf in cfs:
            cv=''; cfk=f"ss_{i}_cf_file_{cf['id']}"
            if cfk in request.files:
                uf=request.files[cfk]
                if uf and uf.filename: u=save_upload(uf); cv=u if u else cv
            cfmk=f"ss_{i}_cf_files_{cf['id']}"
            if cfmk in request.files:
                paths=[]
                for uf in request.files.getlist(cfmk):
                    if uf and uf.filename: u=save_upload(uf); paths.append(u) if u else None
                if paths:
                    ev=f.get(f"ss_{i}_cf_{cf['id']}",'')
                    if ev: paths=ev.split(',')+paths
                    cv=','.join(paths)
            if not cv: cv=f.get(f"ss_{i}_cf_{cf['id']}",'')
            cfvis=1 if f.get(f"ss_{i}_cf_vis_{cf['id']}") else 0
            if cv or cfvis: db.execute("INSERT OR REPLACE INTO sub_spot_custom_values (sub_spot_id,field_def_id,value,is_visible) VALUES (?,?,?,?)",(sid,cf['id'],cv,cfvis))
        i+=1
    for oid in existing:
        if oid not in submitted: db.execute("DELETE FROM sub_spots WHERE id=?",(oid,))
    db.commit(); flash('Key Points saved!','success'); return redirect(url_for('admin_key_spot_subs',ks_id=ks_id))

# ─── Modules ───
@app.route('/admin/modules')
@login_required
def admin_modules():
    return render_template('admin/modules.html',modules=get_db().execute("SELECT m.*,(SELECT COUNT(*) FROM module_entries me WHERE me.module_id=m.id) as entry_count,u.display_name as creator_name FROM modules m LEFT JOIN users u ON m.created_by=u.id ORDER BY m.sort_order").fetchall())

@app.route('/admin/modules/new', methods=['GET','POST'])
@login_required
def admin_module_new():
    if request.method=='POST':
        db=get_db(); name=request.form['name']; slug=slugify(name)
        if db.execute("SELECT id FROM modules WHERE slug=?",(slug,)).fetchone(): slug+='-'+uuid.uuid4().hex[:4]
        db.execute("INSERT INTO modules (name,slug,description,icon,sort_order,fields_schema,created_by) VALUES (?,?,?,?,?,?,?)",(name,slug,request.form.get('description',''),request.form.get('icon','📁'),request.form.get('sort_order',0,type=int),request.form.get('fields_schema','[]'),session['user_id']))
        db.commit(); flash('Module created!','success'); return redirect(url_for('admin_modules'))
    return render_template('admin/module_form.html',module=None,editing=False)

@app.route('/admin/modules/<int:mod_id>/edit', methods=['GET','POST'])
@login_required
def admin_module_edit(mod_id):
    db=get_db(); module=db.execute("SELECT * FROM modules WHERE id=?",(mod_id,)).fetchone()
    if not module: abort(404)
    if request.method=='POST':
        db.execute("UPDATE modules SET name=?,description=?,icon=?,sort_order=?,fields_schema=?,is_active=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
(request.form["name"],request.form.get("description",""),request.form.get("icon","📁"),request.form.get("sort_order",0,type=int),request.form.get("fields_schema","[]"),1 if request.form.get("is_active") else 0,mod_id))
        db.commit(); flash('Updated!','success'); return redirect(url_for('admin_modules'))
    return render_template('admin/module_form.html',module=module,editing=True)

@app.route('/admin/modules/<int:mod_id>/delete', methods=['POST'])
@login_required
def admin_module_delete(mod_id): get_db().execute("DELETE FROM modules WHERE id=?",(mod_id,)); get_db().commit(); flash('Deleted.','info'); return redirect(url_for('admin_modules'))

# ─── Entries ───
@app.route('/admin/entries')
@app.route('/admin/entries/<int:mod_id>')
@login_required
def admin_entries(mod_id=None):
    db=get_db(); q="SELECT me.*,m.name as module_name,m.icon as module_icon,p.title as place_title FROM module_entries me JOIN modules m ON me.module_id=m.id LEFT JOIN places p ON me.place_id=p.id"; params=[]
    if mod_id: q+=" WHERE me.module_id=?"; params.append(mod_id)
    return render_template('admin/entries.html',entries=db.execute(q+" ORDER BY me.updated_at DESC",params).fetchall(),modules=db.execute("SELECT * FROM modules ORDER BY sort_order").fetchall(),current_mod=mod_id)

@app.route('/admin/entries/new', methods=['GET','POST'])
@login_required
def admin_entry_new():
    db=get_db()
    if request.method=='POST':
        t=request.form['title']; s=slugify(t)
        if db.execute("SELECT id FROM module_entries WHERE slug=? AND module_id=?",(s,request.form['module_id'])).fetchone(): s+='-'+uuid.uuid4().hex[:4]
        db.execute("INSERT INTO module_entries (module_id,place_id,title,slug,content,custom_fields,featured_image,status,sort_order,created_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (request.form['module_id'],request.form.get('place_id',type=int) or None,t,s,request.form.get('content',''),request.form.get('custom_fields','{}'),request.form.get('featured_image',''),request.form.get('status','draft'),request.form.get('sort_order',0,type=int),session['user_id']))
        db.commit(); flash('Created!','success'); return redirect(url_for('admin_entries'))
    return render_template('admin/entry_form.html',entry=None,modules=db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall(),places=db.execute("SELECT id,title FROM places ORDER BY title").fetchall(),editing=False)

@app.route('/admin/entries/<int:entry_id>/edit', methods=['GET','POST'])
@login_required
def admin_entry_edit(entry_id):
    db=get_db(); entry=db.execute("SELECT * FROM module_entries WHERE id=?",(entry_id,)).fetchone()
    if not entry: abort(404)
    if request.method=='POST':
        db.execute("UPDATE module_entries SET module_id=?,place_id=?,title=?,content=?,custom_fields=?,featured_image=?,status=?,sort_order=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (request.form['module_id'],request.form.get('place_id',type=int) or None,request.form['title'],request.form.get('content',''),request.form.get('custom_fields','{}'),request.form.get('featured_image',''),request.form.get('status','draft'),request.form.get('sort_order',0,type=int),entry_id))
        db.commit(); flash('Updated!','success'); return redirect(url_for('admin_entries'))
    return render_template('admin/entry_form.html',entry=entry,modules=db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall(),places=db.execute("SELECT id,title FROM places ORDER BY title").fetchall(),editing=True)

@app.route('/admin/entries/<int:entry_id>/delete', methods=['POST'])
@login_required
def admin_entry_delete(entry_id): get_db().execute("DELETE FROM module_entries WHERE id=?",(entry_id,)); get_db().commit(); flash('Deleted.','info'); return redirect(url_for('admin_entries'))

# ─── Media ───
@app.route('/admin/media')
@login_required
def admin_media():
    db=get_db(); q="SELECT * FROM media WHERE 1=1"; p=[]; fl=request.args.get('folder',''); ft=request.args.get('type','')
    if fl: q+=" AND folder=?"; p.append(fl)
    if ft: q+=" AND file_type=?"; p.append(ft)
    return render_template('admin/media.html',media=db.execute(q+" ORDER BY created_at DESC",p).fetchall(),folders=db.execute("SELECT DISTINCT folder FROM media ORDER BY folder").fetchall(),current_folder=fl,current_type=ft)

@app.route('/admin/media/upload', methods=['POST'])
@login_required
def admin_media_upload():
    if 'file' not in request.files: flash('No file.','error'); return redirect(url_for('admin_media'))
    u=save_upload(request.files['file'])
    flash('Uploaded!' if u else 'Not allowed.','success' if u else 'error')
    return redirect(url_for('admin_media'))

@app.route('/admin/media/<int:media_id>/delete', methods=['POST'])
@login_required
def admin_media_delete(media_id):
    db=get_db(); m=db.execute("SELECT * FROM media WHERE id=?",(media_id,)).fetchone()
    if m:
        fp=os.path.join(app.config['UPLOAD_FOLDER'],m['filename'])
        if os.path.exists(fp): os.remove(fp)
        db.execute("DELETE FROM media WHERE id=?",(media_id,)); db.commit()
    flash('Deleted.','info'); return redirect(url_for('admin_media'))

# ─── Users ───
@app.route('/admin/users')
@login_required
@role_required('super_admin')
def admin_users(): return render_template('admin/users.html',users=get_db().execute("SELECT * FROM users ORDER BY created_at DESC").fetchall())

@app.route('/admin/users/new', methods=['GET','POST'])
@login_required
@role_required('super_admin')
def admin_user_new():
    db=get_db()
    if request.method=='POST':
        if db.execute("SELECT id FROM users WHERE username=? OR email=?",(request.form['username'],request.form['email'])).fetchone(): flash('Exists.','error')
        else:
            db.execute("INSERT INTO users (username,email,password_hash,display_name,role,permissions,created_by) VALUES (?,?,?,?,?,?,?)",
                (request.form['username'],request.form['email'],hash_password(request.form['password']),request.form.get('display_name',request.form['username']),request.form.get('role','editor'),json.dumps({k:True for k in request.form.getlist('permissions')}),session['user_id']))
            db.commit(); flash('Created!','success'); return redirect(url_for('admin_users'))
    return render_template('admin/user_form.html',user=None,perm_defs=db.execute("SELECT * FROM permission_definitions ORDER BY category,label").fetchall(),editing=False)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET','POST'])
@login_required
@role_required('super_admin')
def admin_user_edit(user_id):
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
    if not user: abort(404)
    if request.method=='POST':
        u={'email':request.form['email'],'display_name':request.form.get('display_name',user['username']),'role':request.form.get('role','editor'),'permissions':json.dumps({k:True for k in request.form.getlist('permissions')}),'is_active':1 if request.form.get('is_active') else 0}
        if request.form.get('password'): u['password_hash']=hash_password(request.form['password'])
        db.execute(f"UPDATE users SET {','.join(f'{k}=?' for k in u)} WHERE id=?",list(u.values())+[user_id]); db.commit(); flash('Updated!','success'); return redirect(url_for('admin_users'))
    return render_template('admin/user_form.html',user=user,perm_defs=db.execute("SELECT * FROM permission_definitions ORDER BY category,label").fetchall(),user_perms=json.loads(user['permissions'] or '{}'),editing=True)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('super_admin')
def admin_user_delete(user_id):
    if user_id==session['user_id']: flash('Cannot.','error'); return redirect(url_for('admin_users'))
    get_db().execute("UPDATE users SET is_active=0 WHERE id=?",(user_id,)); get_db().commit(); flash('Deactivated.','info'); return redirect(url_for('admin_users'))

# ─── Tags ───
@app.route('/admin/tags', methods=['GET','POST'])
@login_required
def admin_tags():
    db=get_db()
    if request.method=='POST':
        try: db.execute("INSERT INTO tags (name,slug,description,color) VALUES (?,?,?,?)",(request.form['name'],slugify(request.form['name']),request.form.get('description',''),request.form.get('color','#C76B8F'))); db.commit(); flash('Created!','success')
        except sqlite3.IntegrityError: flash('Exists.','error')
        return redirect(url_for('admin_tags'))
    return render_template('admin/tags.html',tags=db.execute("SELECT t.*,COUNT(pt.place_id) as place_count FROM tags t LEFT JOIN place_tags pt ON t.id=pt.tag_id GROUP BY t.id ORDER BY t.name").fetchall())

@app.route('/admin/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def admin_tag_delete(tag_id): get_db().execute("DELETE FROM tags WHERE id=?",(tag_id,)); get_db().commit(); flash('Deleted.','info'); return redirect(url_for('admin_tags'))

# ─── API ───
@app.route('/api/v1/places')
def api_places():
    db=get_db(); page=request.args.get('page',1,type=int); pp=20; q=request.args.get('q','')
    query="SELECT * FROM places WHERE status='published'"; p=[]
    if q: query+=" AND (title LIKE ? OR short_description LIKE ?)"; p.extend([f'%{q}%']*2)
    total=len(db.execute(query,p).fetchall()); query+=" ORDER BY is_featured DESC,updated_at DESC LIMIT ? OFFSET ?"; p.extend([pp,(page-1)*pp])
    return jsonify({'data':[dict(r) for r in db.execute(query,p).fetchall()],'meta':{'page':page,'per_page':pp,'total':total}})

@app.route('/api/v1/places/<slug>')
def api_place_detail(slug):
    db=get_db(); place=db.execute("SELECT * FROM places WHERE slug=? AND status='published'",(slug,)).fetchone()
    if not place: return jsonify({'error':'Not found'}),404
    r=dict(place); r['tags']=[dict(t) for t in db.execute("SELECT t.* FROM tags t JOIN place_tags pt ON t.id=pt.tag_id WHERE pt.place_id=?",(place['id'],)).fetchall()]
    r['key_places']=[dict(kp) for kp in db.execute("SELECT * FROM key_places WHERE parent_place_id=? AND is_visible=1 ORDER BY sort_order",(place['id'],)).fetchall()]
    return jsonify(r)

@app.route('/api/v1/modules')
def api_modules(): return jsonify([dict(m) for m in get_db().execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall()])

@app.route('/api/v1/modules/<slug>/entries')
def api_module_entries(slug):
    db=get_db(); m=db.execute("SELECT * FROM modules WHERE slug=? AND is_active=1",(slug,)).fetchone()
    if not m: return jsonify({'error':'Not found'}),404
    return jsonify({'module':dict(m),'entries':[dict(e) for e in db.execute("SELECT * FROM module_entries WHERE module_id=? AND status='published' ORDER BY sort_order",(m['id'],)).fetchall()]})

@app.route('/api/v1/search')
def api_search():
    q=request.args.get('q','');
    if not q: return jsonify({'results':[]})
    db=get_db(); return jsonify({'places':[dict(r) for r in db.execute("SELECT id,title,slug,short_description,state,city FROM places WHERE status='published' AND (title LIKE ? OR short_description LIKE ?) LIMIT 10",(f'%{q}%',f'%{q}%')).fetchall()]})

# ─── Hierarchy API ───
@app.route('/api/v1/places/<slug>/hierarchy')
def api_place_hierarchy(slug):
    db=get_db(); place=db.execute("SELECT * FROM places WHERE slug=? AND status='published'",(slug,)).fetchone()
    if not place: return jsonify({'error':'Not found'}),404
    h=get_dham_hierarchy(place['id'])
    result=[]
    for kp_data in h:
        kp_dict=dict(kp_data['place'])
        kp_dict['key_spots']=[]
        for ks_data in kp_data['key_spots']:
            ks_dict=dict(ks_data['spot'])
            ks_dict['sub_spots']=[dict(ss) for ss in ks_data['sub_spots']]
            kp_dict['key_spots'].append(ks_dict)
        result.append(kp_dict)
    return jsonify({'dham':dict(place),'key_places':result})

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'): return jsonify({'error':'Not found'}),404
    return render_template('frontend/404.html'),404

with app.app_context(): init_db(); seed_db()
if __name__=='__main__': app.run(debug=True,host='0.0.0.0',port=5000)
