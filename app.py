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
    ('teerth','Teerth','Sacred pilgrimage spot or tank','🙏','#00897B'),
    ('shakti_peeth','Shakti Peeth','Sacred seat of the Goddess','🔱','#AD1457'),
    ('sacred_site','Sacred Site','Site of divine significance','⭐','#FF6F00'),
    ('sacred_throne','Sacred Throne','Divine throne or singhasan','👑','#FFD600'),
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

# ─── Module Field Schemas ───
MODULE_SCHEMAS = {
    'holy-dhams': [
        {'name':'alternate_names','type':'text','label':'Alternate Names','placeholder':'Other known names','icon':'📝'},
        {'name':'short_description','type':'textarea','label':'Short Description','placeholder':'Brief intro','icon':'📋'},
        {'name':'detailed_description','type':'richtext','label':'Detailed Description','placeholder':'','icon':'📖'},
        {'name':'spiritual_significance','type':'richtext','label':'Spiritual Significance','placeholder':'','icon':'🙏'},
        {'name':'associated_pastimes','type':'richtext','label':'Associated Pastimes','placeholder':'','icon':'✨'},
        {'name':'country','type':'text','label':'Country','placeholder':'India','icon':'🌍'},
        {'name':'state','type':'text','label':'State','placeholder':'','icon':'🗺️'},
        {'name':'city','type':'text','label':'City','placeholder':'','icon':'🏙️'},
        {'name':'map_embed','type':'textarea','label':'Map Embed Code','placeholder':'Google Maps iframe','icon':'🗺️'},
        {'name':'coordinates','type':'text','label':'Coordinates','placeholder':'lat, lng','icon':'📍'},
        {'name':'best_time_to_visit','type':'text','label':'Best Time to Visit','placeholder':'Oct-Mar','icon':'🌤️'},
        {'name':'major_festivals','type':'textarea','label':'Major Festivals','placeholder':'List key festivals','icon':'🎪'},
        {'name':'parikrama_details','type':'richtext','label':'Parikrama Details','placeholder':'','icon':'🔄'},
        {'name':'related_temples','type':'textarea','label':'Related Temples','placeholder':'Comma-separated','icon':'🛕'},
        {'name':'related_stories','type':'textarea','label':'Related Stories','placeholder':'Comma-separated','icon':'📖'},
        {'name':'related_festivals','type':'textarea','label':'Related Festivals','placeholder':'Comma-separated','icon':'🎪'},
    ],
    'temples': [
        {'name':'presiding_deities','type':'text','label':'Presiding Deities','placeholder':'Main deities worshipped','icon':'🙏'},
        {'name':'history','type':'richtext','label':'History','placeholder':'Temple history','icon':'📜'},
        {'name':'darshan_timings','type':'text','label':'Darshan Timings','placeholder':'e.g. 6 AM - 12 PM, 4 PM - 9 PM','icon':'🕐'},
        {'name':'aarti_timings','type':'textarea','label':'Aarti Timings','placeholder':'Morning, afternoon, evening aarti schedule','icon':'🪔'},
        {'name':'entry_rules','type':'textarea','label':'Entry Rules','placeholder':'Dress code, prohibited items, etc.','icon':'📋'},
        {'name':'address','type':'textarea','label':'Address','placeholder':'Full address','icon':'📍'},
        {'name':'contact_details','type':'textarea','label':'Contact Details','placeholder':'Phone, email','icon':'☎️'},
        {'name':'description','type':'richtext','label':'Description','placeholder':'Detailed info','icon':'📖'},
        {'name':'pastimes','type':'richtext','label':'Pastimes','placeholder':'Associated divine pastimes','icon':'✨'},
    ],
    'sacred-stories': [
        {'name':'story_type','type':'select','label':'Story Type','options':['Mythology','Historical','Miracle','Pastime','Teaching','Other'],'icon':'📚'},
        {'name':'summary','type':'textarea','label':'Summary','placeholder':'Brief summary','icon':'📋'},
        {'name':'full_content','type':'richtext','label':'Full Content','placeholder':'','icon':'📖'},
        {'name':'spiritual_lesson','type':'richtext','label':'Spiritual Lesson / Insight','placeholder':'','icon':'🙏'},
        {'name':'scriptural_references','type':'textarea','label':'Scriptural References','placeholder':'Bhagavad Gita 4.7, Ramayana etc.','icon':'📜'},
    ],
    'festivals': [
        {'name':'festival_date','type':'text','label':'Date','placeholder':'e.g. March/April (varies)','icon':'📅'},
        {'name':'tithi','type':'text','label':'Tithi','placeholder':'e.g. Chaitra Shukla Navami','icon':'🌙'},
        {'name':'duration','type':'text','label':'Duration','placeholder':'e.g. 9 days','icon':'⏰'},
        {'name':'significance','type':'richtext','label':'Significance','placeholder':'','icon':'🙏'},
        {'name':'celebration_method','type':'richtext','label':'Celebration Method','placeholder':'How it is celebrated','icon':'🎪'},
        {'name':'key_temples','type':'textarea','label':'Key Temples','placeholder':'Where this festival is grand','icon':'🛕'},
        {'name':'visitor_tips','type':'textarea','label':'Visitor Tips','placeholder':'What to know before visiting','icon':'💡'},
    ],
    'pilgrimage-guides': [
        {'name':'photo','type':'image','label':'Photo','icon':'📷'},
        {'name':'mobile_number','type':'text','label':'Mobile Number','placeholder':'+91-XXXXX','icon':'📞'},
        {'name':'whatsapp_number','type':'text','label':'WhatsApp Number','placeholder':'+91-XXXXX','icon':'📱'},
        {'name':'email','type':'text','label':'Email','placeholder':'guide@email.com','icon':'✉️'},
        {'name':'website','type':'url','label':'Website','placeholder':'https://...','icon':'🌐'},
        {'name':'years_of_experience','type':'number','label':'Years of Experience','placeholder':'','icon':'📅'},
        {'name':'languages_spoken','type':'text','label':'Languages Spoken','placeholder':'Hindi, English, Sanskrit','icon':'🗣️'},
        {'name':'specialization','type':'text','label':'Specialization','placeholder':'Vrindavan, Ayodhya etc.','icon':'⭐'},
        {'name':'type_of_guide','type':'select','label':'Type of Guide','options':['Government Certified','Temple Guide','Freelance','Travel Agency','Volunteer'],'icon':'🏷️'},
        {'name':'packages_offered','type':'textarea','label':'Packages Offered','placeholder':'Describe tour packages','icon':'📦'},
        {'name':'charges','type':'text','label':'Charges','placeholder':'e.g. ₹500/day','icon':'💰'},
        {'name':'availability','type':'text','label':'Availability','placeholder':'Year-round / Seasonal','icon':'📅'},
        {'name':'verification_status','type':'select','label':'Verification Status','options':['Pending','Verified','Rejected'],'icon':'✅'},
        {'name':'ratings_reviews','type':'textarea','label':'Ratings & Reviews','placeholder':'Summary of reviews','icon':'⭐'},
    ],
    'events': [
        {'name':'event_type','type':'select','label':'Event Type','options':['Satsang','Yatra','Workshop','Retreat','Lecture','Kirtanmela','Festival','Other'],'icon':'🏷️'},
        {'name':'start_date_time','type':'datetime','label':'Start Date & Time','placeholder':'','icon':'📅'},
        {'name':'end_date_time','type':'datetime','label':'End Date & Time','placeholder':'','icon':'📅'},
        {'name':'location','type':'text','label':'Location','placeholder':'Venue & address','icon':'📍'},
        {'name':'organizer_details','type':'textarea','label':'Organizer Details','placeholder':'Name, contact','icon':'👤'},
        {'name':'description','type':'richtext','label':'Description','placeholder':'Event details','icon':'📖'},
        {'name':'speaker','type':'text','label':'Speaker / Guest','placeholder':'','icon':'🎤'},
        {'name':'registration_link','type':'url','label':'Registration Link','placeholder':'https://...','icon':'🔗'},
        {'name':'fees','type':'text','label':'Fees','placeholder':'Free / ₹XXX','icon':'💰'},
    ],
    'bhajans-kirtans': [
        {'name':'singer_artist','type':'text','label':'Singer / Artist','placeholder':'','icon':'🎤'},
        {'name':'category','type':'select','label':'Category','options':['Bhajan','Kirtan','Abhang','Pad','Dhun','Stuti','Aarti','Other'],'icon':'🏷️'},
        {'name':'audio_description','type':'textarea','label':'Audio Description','placeholder':'Describe the audio content (mandatory if audio exists)','icon':'📋','required':True},
        {'name':'video_link','type':'url','label':'Video Link','placeholder':'YouTube/Vimeo URL','icon':'🎬'},
        {'name':'lyrics','type':'richtext','label':'Lyrics','placeholder':'','icon':'📝'},
        {'name':'meaning_explanation','type':'richtext','label':'Meaning / Explanation','placeholder':'','icon':'📖'},
        {'name':'tags_deity_mood','type':'text','label':'Tags (Deity, Mood)','placeholder':'Krishna, Devotional, Separation','icon':'🏷️'},
    ],
    'spiritual-articles': [
        {'name':'author','type':'text','label':'Author','placeholder':'','icon':'✍️'},
        {'name':'summary','type':'textarea','label':'Summary','placeholder':'Brief summary','icon':'📋'},
        {'name':'full_content','type':'richtext','label':'Full Content','placeholder':'','icon':'📖'},
        {'name':'category','type':'select','label':'Category','options':['Philosophy','Devotion','History','Practice','Commentary','Interview','Other'],'icon':'🏷️'},
        {'name':'tags','type':'text','label':'Tags','placeholder':'Comma-separated','icon':'🏷️'},
        {'name':'related_dham_festival','type':'text','label':'Related Dham / Festival','placeholder':'','icon':'🔗'},
    ],
}

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
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, display_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'editor', permissions TEXT DEFAULT '{}', is_active INTEGER DEFAULT 1, receive_reports INTEGER DEFAULT 0, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login TIMESTAMP);
    CREATE TABLE IF NOT EXISTS modules (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, description TEXT, icon TEXT DEFAULT '📁', sort_order INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1, fields_schema TEXT DEFAULT '[]', created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS places (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, short_description TEXT, full_content TEXT, state TEXT, city TEXT, country TEXT DEFAULT 'India', latitude REAL, longitude REAL, featured_image TEXT, status TEXT DEFAULT 'draft', is_featured INTEGER DEFAULT 0, view_count INTEGER DEFAULT 0, field_visibility TEXT DEFAULT '{}', dham_code TEXT, hierarchy_id TEXT UNIQUE, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS custom_field_defs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, label TEXT NOT NULL, field_type TEXT NOT NULL DEFAULT 'text', placeholder TEXT DEFAULT '', icon TEXT DEFAULT '📋', is_active INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0, applies_to TEXT DEFAULT 'both', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS place_custom_values (id INTEGER PRIMARY KEY AUTOINCREMENT, place_id INTEGER NOT NULL, field_def_id INTEGER NOT NULL, value TEXT DEFAULT '', is_visible INTEGER DEFAULT 1, FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE, FOREIGN KEY (field_def_id) REFERENCES custom_field_defs(id) ON DELETE CASCADE, UNIQUE(place_id, field_def_id));
    CREATE TABLE IF NOT EXISTS key_places (id INTEGER PRIMARY KEY AUTOINCREMENT, parent_place_id INTEGER NOT NULL, title TEXT NOT NULL, slug TEXT, short_description TEXT, full_content TEXT, featured_image TEXT, gallery_images TEXT DEFAULT '', latitude REAL, longitude REAL, sort_order INTEGER DEFAULT 0, is_visible INTEGER DEFAULT 1, field_visibility TEXT DEFAULT '{}', hierarchy_id TEXT UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (parent_place_id) REFERENCES places(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS key_place_custom_values (id INTEGER PRIMARY KEY AUTOINCREMENT, key_place_id INTEGER NOT NULL, field_def_id INTEGER NOT NULL, value TEXT DEFAULT '', is_visible INTEGER DEFAULT 1, FOREIGN KEY (key_place_id) REFERENCES key_places(id) ON DELETE CASCADE, FOREIGN KEY (field_def_id) REFERENCES custom_field_defs(id) ON DELETE CASCADE, UNIQUE(key_place_id, field_def_id));

    /* ─── NEW: Tier 3 & 4 Category Tables ─── */
    CREATE TABLE IF NOT EXISTS spot_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, name TEXT NOT NULL, description TEXT, icon TEXT DEFAULT '📍', color TEXT DEFAULT '#666');
    CREATE TABLE IF NOT EXISTS sub_spot_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, name TEXT NOT NULL, description TEXT, icon TEXT DEFAULT '📍', color TEXT DEFAULT '#666');

    /* ─── NEW: Tier 3 Key Spots ─── */
    CREATE TABLE IF NOT EXISTS key_spots (id INTEGER PRIMARY KEY AUTOINCREMENT, key_place_id INTEGER NOT NULL, category_id INTEGER, title TEXT NOT NULL, slug TEXT, short_description TEXT, full_content TEXT, featured_image TEXT, gallery_images TEXT DEFAULT '', state TEXT, city TEXT, country TEXT DEFAULT '', latitude REAL, longitude REAL, sort_order INTEGER DEFAULT 0, is_visible INTEGER DEFAULT 1, field_visibility TEXT DEFAULT '{}', hierarchy_id TEXT UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (key_place_id) REFERENCES key_places(id) ON DELETE CASCADE, FOREIGN KEY (category_id) REFERENCES spot_categories(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS key_spot_custom_values (id INTEGER PRIMARY KEY AUTOINCREMENT, key_spot_id INTEGER NOT NULL, field_def_id INTEGER NOT NULL, value TEXT DEFAULT '', is_visible INTEGER DEFAULT 1, FOREIGN KEY (key_spot_id) REFERENCES key_spots(id) ON DELETE CASCADE, FOREIGN KEY (field_def_id) REFERENCES custom_field_defs(id) ON DELETE CASCADE, UNIQUE(key_spot_id, field_def_id));

    /* ─── NEW: Tier 4 Key Points ─── */
    CREATE TABLE IF NOT EXISTS sub_spots (id INTEGER PRIMARY KEY AUTOINCREMENT, key_spot_id INTEGER NOT NULL, category_id INTEGER, title TEXT NOT NULL, slug TEXT, short_description TEXT, full_content TEXT, featured_image TEXT, gallery_images TEXT DEFAULT '', state TEXT, city TEXT, country TEXT DEFAULT '', latitude REAL, longitude REAL, sort_order INTEGER DEFAULT 0, is_visible INTEGER DEFAULT 1, field_visibility TEXT DEFAULT '{}', hierarchy_id TEXT UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (key_spot_id) REFERENCES key_spots(id) ON DELETE CASCADE, FOREIGN KEY (category_id) REFERENCES sub_spot_categories(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS sub_spot_custom_values (id INTEGER PRIMARY KEY AUTOINCREMENT, sub_spot_id INTEGER NOT NULL, field_def_id INTEGER NOT NULL, value TEXT DEFAULT '', is_visible INTEGER DEFAULT 1, FOREIGN KEY (sub_spot_id) REFERENCES sub_spots(id) ON DELETE CASCADE, FOREIGN KEY (field_def_id) REFERENCES custom_field_defs(id) ON DELETE CASCADE, UNIQUE(sub_spot_id, field_def_id));

    CREATE TABLE IF NOT EXISTS module_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, module_id INTEGER NOT NULL, place_id INTEGER, title TEXT NOT NULL, slug TEXT NOT NULL, content TEXT, custom_fields TEXT DEFAULT '{}', featured_image TEXT, gallery_images TEXT DEFAULT '', status TEXT DEFAULT 'draft', sort_order INTEGER DEFAULT 0, tier_link_type TEXT DEFAULT '', tier_link_id INTEGER DEFAULT 0, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE, FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS entry_audio_video (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER NOT NULL, media_type TEXT NOT NULL DEFAULT 'audio', source_type TEXT NOT NULL DEFAULT 'upload', file_path TEXT DEFAULT '', external_url TEXT DEFAULT '', description TEXT DEFAULT '', sort_order INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (entry_id) REFERENCES module_entries(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS media (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL, original_name TEXT NOT NULL, file_type TEXT NOT NULL, mime_type TEXT, file_size INTEGER, folder TEXT DEFAULT 'general', alt_text TEXT, caption TEXT, uploaded_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS place_media (id INTEGER PRIMARY KEY AUTOINCREMENT, place_id INTEGER NOT NULL, media_id INTEGER NOT NULL, media_role TEXT DEFAULT 'gallery', sort_order INTEGER DEFAULT 0, FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE, FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS entry_media (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER NOT NULL, media_id INTEGER NOT NULL, media_role TEXT DEFAULT 'gallery', sort_order INTEGER DEFAULT 0, FOREIGN KEY (entry_id) REFERENCES module_entries(id) ON DELETE CASCADE, FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, slug TEXT UNIQUE NOT NULL, description TEXT, color TEXT DEFAULT '#C76B8F');
    CREATE TABLE IF NOT EXISTS place_tags (place_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, PRIMARY KEY (place_id, tag_id), FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE, FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS nearby_places (place_id INTEGER NOT NULL, nearby_place_id INTEGER NOT NULL, distance_km REAL, PRIMARY KEY (place_id, nearby_place_id));
    CREATE TABLE IF NOT EXISTS permission_definitions (id INTEGER PRIMARY KEY AUTOINCREMENT, permission_key TEXT UNIQUE NOT NULL, label TEXT NOT NULL, description TEXT, category TEXT DEFAULT 'general');
    CREATE TABLE IF NOT EXISTS site_settings (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE NOT NULL, value TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS feedback_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, report_type TEXT DEFAULT 'error', name TEXT, email TEXT NOT NULL, message TEXT NOT NULL, page_url TEXT, tier_info TEXT, captcha_ok INTEGER DEFAULT 0, status TEXT DEFAULT 'new', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT NOT NULL, entity_type TEXT, entity_id INTEGER, details TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

    /* ─── Itinerary System ─── */
    CREATE TABLE IF NOT EXISTS itineraries (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, leader_name TEXT DEFAULT '', group_name TEXT DEFAULT '', short_description TEXT DEFAULT '', full_content TEXT DEFAULT '', status TEXT DEFAULT 'draft', created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS itinerary_places (id INTEGER PRIMARY KEY AUTOINCREMENT, itinerary_id INTEGER NOT NULL, tier TEXT NOT NULL, place_ref_id INTEGER NOT NULL, sort_order INTEGER DEFAULT 0, admin_notes TEXT DEFAULT '', time_group TEXT DEFAULT '', FOREIGN KEY (itinerary_id) REFERENCES itineraries(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS place_audio_video (id INTEGER PRIMARY KEY AUTOINCREMENT, tier TEXT NOT NULL, place_ref_id INTEGER NOT NULL, media_type TEXT NOT NULL DEFAULT 'audio', source_type TEXT NOT NULL DEFAULT 'upload', file_path TEXT DEFAULT '', external_url TEXT DEFAULT '', description TEXT DEFAULT '', sort_order INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    ''')
    db.commit()
    # Migration: add gallery_captions column if not exists
    for table in ('key_places','key_spots','sub_spots'):
        cols=[c['name'] for c in db.execute(f"PRAGMA table_info({table})").fetchall()]
        if 'gallery_captions' not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN gallery_captions TEXT DEFAULT '{{}}'")
    # Migration: add hierarchy_id columns if not exists
    pcols=[c['name'] for c in db.execute("PRAGMA table_info(places)").fetchall()]
    if 'dham_code' not in pcols:
        db.execute("ALTER TABLE places ADD COLUMN dham_code TEXT")
    if 'hierarchy_id' not in pcols:
        db.execute("ALTER TABLE places ADD COLUMN hierarchy_id TEXT UNIQUE")
    for table in ('key_places','key_spots','sub_spots'):
        cols=[c['name'] for c in db.execute(f"PRAGMA table_info({table})").fetchall()]
        if 'hierarchy_id' not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN hierarchy_id TEXT UNIQUE")
    # Backfill hierarchy_ids for existing data that lacks them
    _backfill_hierarchy_ids(db)
    # Migration: add description column to custom value tables
    for table in ('place_custom_values','key_place_custom_values','key_spot_custom_values','sub_spot_custom_values'):
        cols=[c['name'] for c in db.execute(f"PRAGMA table_info({table})").fetchall()]
        if 'description' not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN description TEXT DEFAULT ''")
    # Migration: add gallery_images to module_entries
    me_cols=[c['name'] for c in db.execute("PRAGMA table_info(module_entries)").fetchall()]
    if 'gallery_images' not in me_cols:
        db.execute("ALTER TABLE module_entries ADD COLUMN gallery_images TEXT DEFAULT ''")
    # Migration: add tier_link columns to module_entries
    if 'tier_link_type' not in me_cols:
        db.execute("ALTER TABLE module_entries ADD COLUMN tier_link_type TEXT DEFAULT ''")
    if 'tier_link_id' not in me_cols:
        db.execute("ALTER TABLE module_entries ADD COLUMN tier_link_id INTEGER DEFAULT 0")
    # Migration: ensure entry_audio_video table exists
    db.execute("""CREATE TABLE IF NOT EXISTS entry_audio_video (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER NOT NULL, media_type TEXT NOT NULL DEFAULT 'audio', source_type TEXT NOT NULL DEFAULT 'upload', file_path TEXT DEFAULT '', external_url TEXT DEFAULT '', description TEXT DEFAULT '', sort_order INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (entry_id) REFERENCES module_entries(id) ON DELETE CASCADE)""")
    # Migration: update module fields_schema for predefined modules
    for slug, schema in MODULE_SCHEMAS.items():
        existing = db.execute("SELECT id, fields_schema FROM modules WHERE slug=?", (slug,)).fetchone()
        if existing and (not existing['fields_schema'] or existing['fields_schema'] in ('[]', '')):
            db.execute("UPDATE modules SET fields_schema=? WHERE id=?", (json.dumps(schema), existing['id']))
    db.commit()
    # Migration: add view_count column to tables that need global views
    for table in ('itineraries','key_places','key_spots','sub_spots'):
        cols=[c['name'] for c in db.execute(f"PRAGMA table_info({table})").fetchall()]
        if 'view_count' not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN view_count INTEGER DEFAULT 0")
    # Migration: add location tracking columns (who updated location & when)
    for table in ('places','key_places','key_spots','sub_spots'):
        cols=[c['name'] for c in db.execute(f"PRAGMA table_info({table})").fetchall()]
        if 'location_updated_at' not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN location_updated_at TEXT DEFAULT ''")
        if 'location_updated_by' not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN location_updated_by TEXT DEFAULT ''")
    # Migration: add featured_image_desc column for all tiers
    for table in ('places','key_places','key_spots','sub_spots'):
        cols=[c['name'] for c in db.execute(f"PRAGMA table_info({table})").fetchall()]
        if 'featured_image_desc' not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN featured_image_desc TEXT DEFAULT ''")
    db.commit()

def _generate_dham_code(title, db):
    """Generate unique 3-letter dham code from title."""
    # Try first 3 consonants, then first 3 chars, then abbreviation
    t=title.upper().replace(' ','')
    consonants=''.join(c for c in t if c.isalpha() and c not in 'AEIOU')
    candidates=[]
    if len(consonants)>=3: candidates.append(consonants[:3])
    if len(t)>=3: candidates.append(t[:3])
    # Try word initials
    words=[w for w in title.upper().split() if w.isalpha()]
    if len(words)>=3: candidates.append(words[0][0]+words[1][0]+words[2][0])
    if len(words)>=2: candidates.append(words[0][:2]+words[1][0])
    candidates.append(t[:3] if len(t)>=3 else t.ljust(3,'X'))
    existing=set(r[0] for r in db.execute("SELECT dham_code FROM places WHERE dham_code IS NOT NULL").fetchall())
    for code in candidates:
        code=code[:3].upper()
        if len(code)==3 and code.isalpha() and code not in existing:
            return code
    # Fallback: append number
    base=t[:2].upper() if len(t)>=2 else 'DH'
    for i in range(1,10):
        code=base+str(i)
        if code not in existing: return code[:3]
    return uuid.uuid4().hex[:3].upper()

def _gen_t1_id(dham_code):
    return f"{dham_code}000000"

def _gen_t2_id(dham_code, db, parent_place_id):
    """Generate next T2 hierarchy_id: DHAMPP0000"""
    rows=db.execute("SELECT hierarchy_id FROM key_places WHERE parent_place_id=? AND hierarchy_id IS NOT NULL",(parent_place_id,)).fetchall()
    max_seq=0
    for r in rows:
        hid=r['hierarchy_id'] if isinstance(r,dict) else r[0]
        if hid and len(hid)==10:
            try: seq=int(hid[3:5]); max_seq=max(max_seq,seq)
            except: pass
    next_seq=max_seq+1
    if next_seq>99: raise ValueError("Maximum 99 Key Places per Dham reached")
    return f"{dham_code}{next_seq:02d}0000"

def _gen_t3_id(dham_code, db, key_place_id):
    """Generate next T3 hierarchy_id: DHAMPPSS00"""
    kp=db.execute("SELECT hierarchy_id FROM key_places WHERE id=?",(key_place_id,)).fetchone()
    if not kp or not kp['hierarchy_id']: return None
    kp_prefix=kp['hierarchy_id'][:5]  # e.g. VRN01
    rows=db.execute("SELECT hierarchy_id FROM key_spots WHERE key_place_id=? AND hierarchy_id IS NOT NULL",(key_place_id,)).fetchall()
    max_seq=0
    for r in rows:
        hid=r['hierarchy_id'] if isinstance(r,dict) else r[0]
        if hid and len(hid)==10:
            try: seq=int(hid[5:7]); max_seq=max(max_seq,seq)
            except: pass
    next_seq=max_seq+1
    if next_seq>99: raise ValueError("Maximum 99 Key Spots per Key Place reached")
    return f"{kp_prefix}{next_seq:02d}00"

def _gen_t4_id(dham_code, db, key_spot_id):
    """Generate next T4 hierarchy_id: DHAMPPSSTT"""
    ks=db.execute("SELECT hierarchy_id FROM key_spots WHERE id=?",(key_spot_id,)).fetchone()
    if not ks or not ks['hierarchy_id']: return None
    ks_prefix=ks['hierarchy_id'][:7]  # e.g. VRN0101
    rows=db.execute("SELECT hierarchy_id FROM sub_spots WHERE key_spot_id=? AND hierarchy_id IS NOT NULL",(key_spot_id,)).fetchall()
    max_seq=0
    for r in rows:
        hid=r['hierarchy_id'] if isinstance(r,dict) else r[0]
        if hid and len(hid)==10:
            try: seq=int(hid[7:9]); max_seq=max(max_seq,seq)
            except: pass
    next_seq=max_seq+1
    if next_seq>99: raise ValueError("Maximum 99 Key Points per Key Spot reached")
    return f"{ks_prefix}{next_seq:02d}"

def _backfill_hierarchy_ids(db):
    """Backfill hierarchy_ids for existing data that doesn't have them.
    Uses in-memory counters to avoid transaction visibility issues."""
    # T1: Places without hierarchy_id
    for p in db.execute("SELECT id,title FROM places WHERE hierarchy_id IS NULL OR hierarchy_id=''").fetchall():
        code=_generate_dham_code(p['title'],db)
        hid=_gen_t1_id(code)
        db.execute("UPDATE places SET dham_code=?,hierarchy_id=? WHERE id=?",(code,hid,p['id']))
    db.commit()
    # Build lookup: place_id → dham_code
    dham_codes={r['id']:r['dham_code'] for r in db.execute("SELECT id,dham_code FROM places WHERE dham_code IS NOT NULL").fetchall()}
    # T2: Key places — group by parent, assign sequential IDs in-memory
    # First get existing max sequences per parent
    t2_seqs={}  # parent_place_id → current max seq
    for r in db.execute("SELECT parent_place_id,hierarchy_id FROM key_places WHERE hierarchy_id IS NOT NULL AND hierarchy_id!=''").fetchall():
        pid=r['parent_place_id']; hid=r['hierarchy_id']
        if hid and len(hid)==10:
            try: seq=int(hid[3:5]); t2_seqs[pid]=max(t2_seqs.get(pid,0),seq)
            except: pass
    for kp in db.execute("SELECT id,parent_place_id FROM key_places WHERE hierarchy_id IS NULL OR hierarchy_id='' ORDER BY parent_place_id,sort_order,id").fetchall():
        code=dham_codes.get(kp['parent_place_id'])
        if code:
            pid=kp['parent_place_id']
            t2_seqs[pid]=t2_seqs.get(pid,0)+1
            hid=f"{code}{t2_seqs[pid]:02d}0000"
            db.execute("UPDATE key_places SET hierarchy_id=? WHERE id=?",(hid,kp['id']))
    db.commit()
    # T3: Key spots — group by key_place, assign in-memory
    # Build lookup: kp_id → hierarchy_id prefix (first 5 chars)
    kp_prefixes={r['id']:r['hierarchy_id'][:5] for r in db.execute("SELECT id,hierarchy_id FROM key_places WHERE hierarchy_id IS NOT NULL AND hierarchy_id!=''").fetchall()}
    t3_seqs={}  # key_place_id → current max seq
    for r in db.execute("SELECT key_place_id,hierarchy_id FROM key_spots WHERE hierarchy_id IS NOT NULL AND hierarchy_id!=''").fetchall():
        kpid=r['key_place_id']; hid=r['hierarchy_id']
        if hid and len(hid)==10:
            try: seq=int(hid[5:7]); t3_seqs[kpid]=max(t3_seqs.get(kpid,0),seq)
            except: pass
    for ks in db.execute("SELECT id,key_place_id FROM key_spots WHERE hierarchy_id IS NULL OR hierarchy_id='' ORDER BY key_place_id,sort_order,id").fetchall():
        prefix=kp_prefixes.get(ks['key_place_id'])
        if prefix:
            kpid=ks['key_place_id']
            t3_seqs[kpid]=t3_seqs.get(kpid,0)+1
            hid=f"{prefix}{t3_seqs[kpid]:02d}00"
            db.execute("UPDATE key_spots SET hierarchy_id=? WHERE id=?",(hid,ks['id']))
    db.commit()
    # T4: Sub spots — group by key_spot, assign in-memory
    ks_prefixes={r['id']:r['hierarchy_id'][:7] for r in db.execute("SELECT id,hierarchy_id FROM key_spots WHERE hierarchy_id IS NOT NULL AND hierarchy_id!=''").fetchall()}
    t4_seqs={}  # key_spot_id → current max seq
    for r in db.execute("SELECT key_spot_id,hierarchy_id FROM sub_spots WHERE hierarchy_id IS NOT NULL AND hierarchy_id!=''").fetchall():
        ksid=r['key_spot_id']; hid=r['hierarchy_id']
        if hid and len(hid)==10:
            try: seq=int(hid[7:9]); t4_seqs[ksid]=max(t4_seqs.get(ksid,0),seq)
            except: pass
    for ss in db.execute("SELECT id,key_spot_id FROM sub_spots WHERE hierarchy_id IS NULL OR hierarchy_id='' ORDER BY key_spot_id,sort_order,id").fetchall():
        prefix=ks_prefixes.get(ss['key_spot_id'])
        if prefix:
            ksid=ss['key_spot_id']
            t4_seqs[ksid]=t4_seqs.get(ksid,0)+1
            hid=f"{prefix}{t4_seqs[ksid]:02d}"
            db.execute("UPDATE sub_spots SET hierarchy_id=? WHERE id=?",(hid,ss['id']))
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

    # Users — Super Admins
    db.execute("INSERT INTO users (username,email,password_hash,display_name,role,permissions,receive_reports) VALUES (?,?,?,?,?,?,?)", ('admin','admin@holyplaces.com',hashlib.sha256(b'admin123').hexdigest(),'Super Admin','super_admin','{"all":true}',1))
    db.execute("INSERT INTO users (username,email,password_hash,display_name,role,permissions,receive_reports) VALUES (?,?,?,?,?,?,?)", ('sajeev','sajeev1478@gmail.com',hashlib.sha256(b'holyplace2025').hexdigest(),'Sajeev','super_admin','{"all":true}',1))
    db.execute("INSERT INTO users (username,email,password_hash,display_name,role,permissions,receive_reports) VALUES (?,?,?,?,?,?,?)", ('manoj','manojrpai@gmail.com',hashlib.sha256(b'holyplace2025').hexdigest(),'Manoj','super_admin','{"all":true}',1))
    db.execute("INSERT INTO users (username,email,password_hash,display_name,role,permissions,receive_reports) VALUES (?,?,?,?,?,?,?)", ('madana','madana.murari.rns@iskcon.net',hashlib.sha256(b'holyplace2025').hexdigest(),'Madana Murari','super_admin','{"all":true}',1))
    db.execute("INSERT INTO users (username,email,password_hash,display_name,role,created_by) VALUES (?,?,?,?,?,?)", ('editor','editor@holyplaces.com',hashlib.sha256(b'editor123').hexdigest(),'Content Editor','editor',1))
    # Default email settings
    db.execute("INSERT OR IGNORE INTO site_settings (key,value) VALUES (?,?)",('report_emails','sajeev1478@gmail.com,manojrpai@gmail.com,madana.murari.rns@iskcon.net'))
    db.execute("INSERT OR IGNORE INTO site_settings (key,value) VALUES (?,?)",('smtp_host',''))
    db.execute("INSERT OR IGNORE INTO site_settings (key,value) VALUES (?,?)",('smtp_port','587'))
    db.execute("INSERT OR IGNORE INTO site_settings (key,value) VALUES (?,?)",('smtp_user',''))
    db.execute("INSERT OR IGNORE INTO site_settings (key,value) VALUES (?,?)",('smtp_pass',''))
    # Modules with field schemas
    for name,slug,desc,icon,order in [('Holy Dhams','holy-dhams','Sacred destinations','\U0001f6d5',1),('Temples','temples','Temple profiles','\U0001f3db\ufe0f',2),('Sacred Stories','sacred-stories','Mythological tales','\U0001f4d6',3),('Festivals','festivals','Religious events','\U0001f3ea',4),('Pilgrimage Guides','pilgrimage-guides','Travel guides','\U0001f6b6',5),('Events','events','Spiritual events','\U0001f4c5',6),('Bhajans & Kirtans','bhajans-kirtans','Devotional music','\U0001f3b5',7),('Spiritual Articles','spiritual-articles','Spiritual writings','\U0001f4dd',8)]:
        schema_json = json.dumps(MODULE_SCHEMAS.get(slug, []))
        db.execute("INSERT INTO modules (name,slug,description,icon,sort_order,is_active,fields_schema,created_by) VALUES (?,?,?,?,?,1,?,1)", (name,slug,desc,icon,order,schema_json))
    # Tags
    for name,slug,color in [('Char Dham','char-dham','#C76B8F'),('Jyotirlinga','jyotirlinga','#E89B4F'),('Heritage','heritage','#8BAB8A'),('Pilgrimage','pilgrimage','#6B8AB5'),('UNESCO','unesco','#B58A6B'),('Sikh Heritage','sikh-heritage','#C4A44E'),('Buddhist','buddhist','#8A6BB5'),('ISKCON','iskcon','#D4A843'),('Braj Dham','braj-dham','#E84855'),('Gaudiya Vaishnava','gaudiya-vaishnava','#6C5CE7'),('Sapta Puri','sapta-puri','#FF6B35'),('Ram Bhakti','ram-bhakti','#E53935'),('Sapt Hari','sapt-hari','#1E88E5')]:
        db.execute("INSERT INTO tags (name,slug,color) VALUES (?,?,?)", (name,slug,color))
    # Custom Fields with icons
    for name,label,ftype,ph,order,applies,icon in [('audio_narration','Audio Narration','audio','Upload audio',1,'both','\U0001f3b5'),('video_tour','Video Tour','video','Upload or paste URL',2,'both','\U0001f3ac'),('gallery_images','Gallery Images','images','Upload photos',3,'both','\U0001f5bc\ufe0f'),('opening_hours','Opening Hours','text','e.g. 6 AM - 9 PM',4,'both','\U0001f550'),('best_time_to_visit','Best Time to Visit','text','e.g. Oct-Mar',5,'both','\U0001f324\ufe0f'),('how_to_reach','How to Reach','textarea','Directions',6,'place','\U0001f697'),('accommodation','Accommodation','textarea','Stay options',7,'place','\U0001f3e8'),('history','History & Significance','richtext','Detailed history',8,'both','\U0001f4dc'),('dress_code','Dress Code','text','If any',9,'both','\U0001f97b'),('external_audio_url','External Audio Link','url','Audio URL',11,'both','\U0001f517'),('external_video_url','External Video Link','url','YouTube/Vimeo URL',12,'both','\U0001f517')]:
        db.execute("INSERT INTO custom_field_defs (name,label,field_type,placeholder,sort_order,applies_to,icon) VALUES (?,?,?,?,?,?,?)", (name,label,ftype,ph,order,applies,icon))

    # ═══════════════════════════════════════════════════════════════
    # ─── AYODHYA DHAM (Tier 1) — Primary Dham ───
    # ═══════════════════════════════════════════════════════════════
    ayd_content = '<h2>The Invincible City of Lord Rama</h2><p>Ayodhya, derived from the Sanskrit <em>a-yodhya</em> meaning "invincible," is one of the most ancient and sacred cities in the world. Mentioned in the Atharvaveda as the unconquerable city of the gods, Ayodhya has been the spiritual beacon of Sanatana Dharma since time immemorial.</p><h3>Sapta Mokshapuri</h3><p>As proclaimed in the Garuda Purana: <em>"Ayodhya Mathura Maya Kashi Kanchi Avantika, Puri Dwaravati chaiva saptaite mokshadayikah"</em> — Ayodhya stands first among the seven cities that bestow liberation (moksha). A pilgrimage here is believed to free the soul from the cycle of birth and death.</p><h3>Capital of the Ikshvaku Dynasty</h3><p>According to the Ramayana, Ayodhya was established by Manu himself, taking a piece of Vaikuntha from Lord Narayana. It served as the magnificent capital of the Solar Dynasty (Surya Vansha) kings, including the great Raghu, Aja, Dasharatha, and the Supreme Lord Rama. The city is described as being shaped like a fish, spanning 12 yojanas in length and 3 yojanas in breadth.</p><h3>Birthplace of Lord Rama</h3><p>Lord Rama, the seventh avatara of Lord Vishnu, appeared here on the Navami tithi of Chaitra Shukla Paksha. He ruled the earth for eleven thousand years, establishing the ideal kingdom known as Ram Rajya. After His divine departure, the sacred tirthas, temples, kunds, and ghats of Ayodhya continue to radiate His spiritual presence.</p><h3>Saryu River</h3><p>The holy Saryu (Sarayu) river flows along the northern boundary of Ayodhya. Bathing in Saryu is considered highly meritorious. The famous ghats — Ram Ki Paidi, Guptar Ghat, Swargdwar — are centers of daily worship and grand festivals. The Saryu is described in the Padma Purana as flowing from the divine realm of Vaikuntha itself.</p><h3>Spiritual Heritage</h3><p>With over 100 temples, numerous sacred kunds, ancient ghats, and the newly consecrated Ram Janmabhoomi Mandir (inaugurated January 2024), Ayodhya attracts millions of pilgrims annually. The city also holds deep significance for Jainism — five Tirthankaras (Rishabhanatha, Ajitanatha, Abhinandananatha, Sumatinatha, and Anantanatha) were born here.</p>'
    db.execute("INSERT INTO places (title,slug,short_description,full_content,state,city,country,latitude,longitude,status,is_featured,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
        ('Ayodhya Dham','ayodhya-dham',
         'The sacred birthplace of Lord Rama, first of the Sapta Mokshapuris. Situated on the banks of River Saryu in Uttar Pradesh, Ayodhya is the eternal capital of the Ikshvaku dynasty.',
         ayd_content,'Uttar Pradesh','Ayodhya','India',26.7922,82.1998,'published',1))
    ayd_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for tid in [11,4,3,12]: db.execute("INSERT OR IGNORE INTO place_tags VALUES (?,?)", (ayd_id,tid))
    # Custom fields for Ayodhya
    cf_hours = db.execute("SELECT id FROM custom_field_defs WHERE name='opening_hours'").fetchone()[0]
    cf_best = db.execute("SELECT id FROM custom_field_defs WHERE name='best_time_to_visit'").fetchone()[0]
    cf_reach = db.execute("SELECT id FROM custom_field_defs WHERE name='how_to_reach'").fetchone()[0]
    cf_accom = db.execute("SELECT id FROM custom_field_defs WHERE name='accommodation'").fetchone()[0]
    cf_dress = db.execute("SELECT id FROM custom_field_defs WHERE name='dress_code'").fetchone()[0]
    cf_hist = db.execute("SELECT id FROM custom_field_defs WHERE name='history'").fetchone()[0]
    db.execute("INSERT INTO place_custom_values (place_id,field_def_id,value) VALUES (?,?,?)", (ayd_id,cf_hours,'Temples generally open 6 AM - 12 PM & 4 PM - 10 PM. Ram Janmabhoomi: 7 AM - 11:30 AM & 2 PM - 7 PM.'))
    db.execute("INSERT INTO place_custom_values (place_id,field_def_id,value) VALUES (?,?,?)", (ayd_id,cf_best,'October to March (pleasant weather). Ram Navami (Chaitra Shukla Navami) is the grandest festival.'))
    db.execute("INSERT INTO place_custom_values (place_id,field_def_id,value) VALUES (?,?,?)", (ayd_id,cf_reach,'By Air: Maharishi Valmiki Intl Airport (~8 km), Lucknow Airport (~135 km). By Rail: Ayodhya Dham Jn well-connected to Delhi, Lucknow, Varanasi. By Road: NH-27 to Lucknow (134 km), Varanasi (209 km).'))
    db.execute("INSERT INTO place_custom_values (place_id,field_def_id,value) VALUES (?,?,?)", (ayd_id,cf_accom,'Government dharamshalas, IRCTC Ramayan Yatri Niwas, numerous private hotels and guest houses.'))
    db.execute("INSERT INTO place_custom_values (place_id,field_def_id,value) VALUES (?,?,?)", (ayd_id,cf_dress,'Modest traditional clothing recommended. Avoid western casuals in temples.'))
    db.execute("INSERT INTO place_custom_values (place_id,field_def_id,value) VALUES (?,?,?)", (ayd_id,cf_hist,'<p>Ayodhya is one of the oldest continuously inhabited cities in India, with archaeological evidence dating to around 600 BCE. Known as Saketa in early Buddhist and Jain texts, the city was renamed during the Gupta period. King Vikramaditya restored its glory, building 360 temples. The Ram Janmabhoomi Mandir, built in Nagara style with Bansi Paharpur sandstone, was consecrated on 22 January 2024.</p>'))

    # ── AYODHYA: Tier 2 — Key Places (6 areas) ──
    akp = {}
    t2_data = [
        ('Ram Janmabhoomi Kshetra','ram-janmabhoomi-kshetra','The sacred precinct around Lord Rama\'s birthplace — the spiritual heart of Ayodhya.','<h3>The Holy Birthplace</h3><p>Ram Janmabhoomi Kshetra is the most sacred area in Ayodhya, centered on the exact spot where Lord Rama appeared. The newly constructed Ram Mandir stands 161 feet tall with three stories in Nagara style. The complex includes the Ratna Singhasan, ancient Sita Kup well, Vidya Kund, Mani Parvat, Kanak Bhawan, and Vashistha Kund.</p>',26.7955,82.1942,1),
        ('Central Ayodhya','central-ayodhya','The bustling heart of Ayodhya city — home to the iconic Hanuman Garhi fort-temple, Sapt Sagar tank, and Matta Gajendra.','<h3>Heart of the Sacred City</h3><p>Central Ayodhya is dominated by Hanuman Garhi — the tallest structure in the city, visible from all directions. This 10th-century fort-temple sits atop 76 steps and houses Bal Hanuman in Anjani\'s lap. Lord Rama appointed Hanuman as Ayodhya\'s eternal guardian. The area includes Sapt Sagar and the Matta Gajendra shrine.</p>',26.7965,82.2000,2),
        ('Swargdwar & Saryu Ghat Area','swargdwar-saryu-ghat-area','The sacred Saryu riverfront — Sapt Hari temples, Lakshman\'s Shesha Sthali, and Guptar Ghat where citizens attained Vaikuntha.','<h3>The Divine Riverfront</h3><p>The Saryu riverfront from Swargdwar to Guptar Ghat is among the holiest stretches of any river in India. Chandrahari and Nageshwarnath temples stand at Swargdwar. Sahasradhara is where Lakshman assumed Shesha form. At Guptar Ghat, Ayodhya\'s citizens entered Saryu for Vaikuntha. Nirmali Kund is so pure that Teerth-raj Prayag bathes here daily.</p>',26.8032,82.1910,3),
        ('Surrounding Teerth Kshetras','surrounding-teerth-kshetras','Sacred kunds, Shakti peethas, and teerths surrounding the main city — Surya Kund, Devkali, and Manorama Teerth.','<h3>Teerths Around the City</h3><p>Beyond central Ayodhya are powerful teerths described in the Skanda Purana. Surya Kund cures diseases. Devkali is the seat of Adi Shakti in Ashtabhuja form. Manorama Teerth across the Saryu is where King Dasharatha performed the Putrakameshti Yagya that led to Rama\'s birth.</p>',26.7870,82.1950,4),
        ('Bilvahari & Punyahari Area','bilvahari-punyahari-area','Part of the Sapt Hari pilgrimage circuit — sacred Vishnu temples ~16 km east of Ayodhya on Saryu bank.','<h3>The Eastern Sapt Hari Temples</h3><p>About 16 km east of the city on the Saryu bank stand Bilvahari and Punyahari — two of the Sapt Hari temples. Bilvahari liberates from Rina Traya. Punyahari cures Pandu Roga. These remote teerths preserve ancient pilgrimage traditions predating even the Ramayana.</p>',26.8000,82.3500,5),
        ('Nandigram','nandigram','18 km south — where Bharat installed Rama\'s Padukas and lived 14 years in austere penance.','<h3>Bharat\'s Seat of Devotion</h3><p>Nandigram, 18 km south of Ayodhya, is where Bharat installed Rama\'s Charan Padukas on the throne and administered the kingdom for 14 years as an ascetic. The first reunion with Rama after Lanka occurred here. The Skanda Purana declares darshan here equals 1000 Manvantaras of Kashi-vaas.</p>',26.6700,82.2100,6),
    ]
    for t,s,sd,fc,lat,lng,o in t2_data:
        db.execute("INSERT INTO key_places (parent_place_id,title,slug,short_description,full_content,latitude,longitude,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,1)", (ayd_id,t,s,sd,fc,lat,lng,o))
        akp[s] = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # ── AYODHYA: Tier 3 — Key Spots (20 spots) ──
    temple_cat = db.execute("SELECT id FROM spot_categories WHERE slug='temple'").fetchone()[0]
    kund_cat = db.execute("SELECT id FROM spot_categories WHERE slug='kund'").fetchone()[0]
    ghat_cat = db.execute("SELECT id FROM spot_categories WHERE slug='ghat'").fetchone()[0]
    hill_cat = db.execute("SELECT id FROM spot_categories WHERE slug='hill'").fetchone()[0]
    teerth_cat = db.execute("SELECT id FROM spot_categories WHERE slug='teerth'").fetchone()[0]
    shakti_cat = db.execute("SELECT id FROM spot_categories WHERE slug='shakti_peeth'").fetchone()[0]
    sacred_site_cat = db.execute("SELECT id FROM spot_categories WHERE slug='sacred_site'").fetchone()[0]
    sacred_throne_cat = db.execute("SELECT id FROM spot_categories WHERE slug='sacred_throne'").fetchone()[0]
    village_cat = db.execute("SELECT id FROM spot_categories WHERE slug='village'").fetchone()[0]
    van_cat = db.execute("SELECT id FROM spot_categories WHERE slug='van'").fetchone()[0]
    parikrama_cat = db.execute("SELECT id FROM spot_categories WHERE slug='parikrama'").fetchone()[0]

    aks = {}
    t3_data = [
        # T2-01: Ram Janmabhoomi Kshetra (6 spots)
        (akp['ram-janmabhoomi-kshetra'],sacred_throne_cat,'Ratna Singhasan','ratna-singhasan','The jewel-studded divine throne beneath the Kalpa Vriksha where Lord Rama sits eternally with Sita, Lakshman, Bharat and Shatrughna.','<h3>The Jewelled Throne</h3><p><em>"Ayodhyanagare ramye ratna mandapamadhyagam, dhyayet kalpatarormule ratnasinhasana shubham"</em></p><p>In the beautiful city of Ayodhya, beneath the Kalpa Vriksha, within a gem-laden pavilion, stands the Ratna Singhasan — the jewelled throne where Lord Rama sits in Virasana with Sita Maharani, while Lakshman, Bharat, and Shatrughna stand in attendance. Devotees who meditate upon this scene and prostrate are blessed with fulfillment of all desires.</p>',26.7955,82.1942,1),
        (akp['ram-janmabhoomi-kshetra'],kund_cat,'Sita Kup Teerth','sita-kup-teerth','Sacred well in the Agnikona of Janmasthan. Also known as Gyan Kup — drinking its water grants wisdom equal to Brihaspati.','<h3>The Well of Divine Wisdom</h3><p><em>"Janmasthanacca bho devi agnikonam virajate, Sitakupa iti vikhyatam jnanakupam iti shrutam"</em></p><p>Lord Shiva tells Parvati: In the Agnikona (southeast) of Janmasthan stands Sita Kup, also known as Gyan Kup. Regular drinking of its water makes intellect equal to Brihaspati and bestows Brahmavidya. This well is located within the courtyard of Kanak Bhawan temple.</p>',26.7950,82.1948,2),
        (akp['ram-janmabhoomi-kshetra'],temple_cat,'Kanak Bhawan','kanak-bhawan','The magnificent Golden Palace — gifted by Queen Kaikeyi to Sita at her wedding. Houses three pairs of golden-crowned Rama-Sita deities in Bundelkhand architecture.','<h3>The Palace of Gold</h3><p>Kanak Bhawan (Sone-ka-Ghar), one of Ayodhya\'s most beautiful temples, was gifted by Queen Kaikeyi to Sita at her marriage. The present Bundelkhand-style structure was built by Queen Vrishabhanu Kunwari of Orchha in 1891. The sanctum houses three pairs of golden-crowned Rama-Sita deities under a silver roof: the largest by Queen Vrishabhanu, the medium pair preserved by Vikramaditya, and the smallest gifted by Lord Krishna Himself to a devotee. Major festivals: Ram Navami, Phool Bangla (April-July), 15-day Jhula Festival, Sharad Purnima. Timings: 8 AM - 11 AM & 4:30 PM - 9 PM.</p>',26.7978,82.1950,3),
        (akp['ram-janmabhoomi-kshetra'],kund_cat,'Vashistha Kund','vashistha-kund','Sacred kund west of Janmasthan — residence of Guru Vashistha and Arundhati. Bathing destroys all sins.','<h3>Abode of the Royal Guru</h3><p><em>"Janmasthana tapascime tu kunda papapranashanam, Vasisthasya nivasastu Arundhatyaksha Parvati"</em></p><p>West of Janmasthan lies Vashistha Kund — the residence of Brahmarshi Vashistha, royal guru of the Ikshvaku dynasty, and his wife Arundhati. Bathing here fulfills all desires. Annual yatra on Shukla Paksha of Bhadrapada.</p>',26.7955,82.1930,4),
        (akp['ram-janmabhoomi-kshetra'],kund_cat,'Vidya Kund','vidya-kund','East of Janmasthan — where Guru Vashistha taught Rama the 14 Vidyas and 64 Kalas. Japa of all mantras attains siddhi here.','<h3>The Pool of Sacred Learning</h3><p><em>"Janmasthanat purvabhage Vidyakundasya cottamam"</em></p><p>East of Janmasthan, Guru Vashistha imparted the 14 Vidyas and 64 Kalas to Lord Rama here. The scriptures declare that chanting of all mantras — Shaiva, Vaishnava, Ganesha, Shakta, or Saura — attains siddhi at this supremely potent site.</p>',26.7958,82.1960,5),
        (akp['ram-janmabhoomi-kshetra'],hill_cat,'Mani Parvat','mani-parvat','Sacred gem-hill west of Vidya Kund — brought by Garuda on Rama\'s command for Sita\'s pleasure. Mere darshan grants all siddhis.','<h3>The Hill of Gems</h3><p><em>"Garudena samanitah parvato manisamjnakah, tasya darshanamtrena karasthat sarvasiddhayah"</em></p><p>On Lord Rama\'s command, Garuda brought this gem-studded hill for Sita\'s recreation. Merely seeing Mani Parvat grants all siddhis. Today it offers panoramic views of Ayodhya.</p>',26.7955,82.1955,6),
        # T2-02: Central Ayodhya (3 spots)
        (akp['central-ayodhya'],temple_cat,'Hanuman Garhi Temple','hanuman-garhi-temple','The iconic 10th-century fort-temple atop 76 steps — tallest structure in Ayodhya. Tradition requires visiting here before Ram Janmabhoomi.','<h3>The Fortress of Hanuman</h3><p>Hanuman Garhi is Ayodhya\'s most prominent landmark — a fort-temple visible from all directions, accessed by 76 steps. As per Valmiki Ramayana (Uttara Kanda 108): Lord Rama told Hanuman to remain here protecting Ayodhya as long as His katha exists in the world. The main deity is Bal Hanuman in Anjani\'s lap. King Vikramaditya built the original shrine as part of 360 temples. Present structure built ~1799 CE by Diwan Tikait Rai. Complex spreads over 52 bighas. Special festivals: Hanuman Jayanti, Ram Navami. Tuesdays & Saturdays are especially auspicious. Timings: 5 AM - 11 AM & 4 PM - 10 PM.</p>',26.7982,82.2007,1),
        (akp['central-ayodhya'],sacred_site_cat,'Matta Gajendra','matta-gajendra','Guardian deity in the east of Ramkot — protector of the virtuous, punisher of the wicked. Darshan removes all obstacles.','<h3>The Mighty Guardian</h3><p><em>"Koshalarakshane daksho dushtadanatparah, yasya darshana nrinam vighnalesho na jayate"</em></p><p>Matta Gajendra, identified with Vibhishana\'s son appointed by Rama as Kotwal of Ramkot, protects all virtuous residents and punishes the wicked. Mere darshan removes all obstacles. Traditionally the first stop in an Ayodhya pilgrimage.</p>',26.7990,82.2020,2),
        (akp['central-ayodhya'],kund_cat,'Sapt Sagar Teerth','sapt-sagar-teerth','Ancient seven-ocean tank in the heart of Ayodhya — bathing equals ocean-bathing merit on Purnima. Grants all wishes.','<h3>The Seven Oceans</h3><p><em>"Ayodhya madhyabhage tu ramyam patakanashakam, Saptasagara vikhyatam sarvakamarthasiddhidam"</em></p><p>In the heart of Ayodhya, the Sapt Sagar kund grants the merit of ocean-bathing on Purnima on any ordinary day. Special merit during Ashvina Purnima for those desiring progeny.</p>',26.7970,82.2000,3),
        # T2-03: Swargdwar & Saryu Ghat Area (5 spots)
        (akp['swargdwar-saryu-ghat-area'],temple_cat,'Chandrahari Mandir','chandrahari-mandir','Sapt Hari temple at Swargdwar — worship declared essential for all pilgrims. Annual yatra on Jyeshtha Shukla Purnima.','<h3>The Sapt Hari Temple</h3><p>Ayodhya\'s Sapt Hari circuit includes seven Vishnu temples: Guptahari, Chakrahari, Vishnuhari, Dharmahari, Punyahari, Bilvahari, and Chandrahari. Of these, Chandrahari at Swargdwar is the most essential. Annual yatra on Jyeshtha Shukla Purnima. Adjacent Nageshwarnath temple makes this a convergence of Vaishnava and Shaiva worship.</p>',26.8050,82.1900,1),
        (akp['swargdwar-saryu-ghat-area'],temple_cat,'Nageshwarnath Mandir','nageshwarnath-mandir','Presiding deity temple of Ayodhya — built by King Kusha (Rama\'s son). Ancient Shivalinga. Edifice circa 750 AD.','<h3>The Presiding Deity of Ayodhya</h3><p><em>"Svargadvare narah snatva drishtva Nageshvaram Shivam, pujayitva ca vidhivat sarvan kaman avapnuyat"</em></p><p>Built by King Kusha, Lord Rama\'s son. Legend: Kusha\'s armlet fell in Saryu, a Naag Kanya who loved him retrieved it. Being a Shiva devotee, she inspired Kusha to build this temple. The ancient Shivalinga here is the Nagar Devata. Present edifice ~750 AD. Major festivals: Trayodashi & Mahashivratri.</p>',26.8048,82.1908,2),
        (akp['swargdwar-saryu-ghat-area'],teerth_cat,'Sahasradhara & Lakshman Mandir','sahasradhara-lakshman-mandir','Where Lakshman shed his mortal body through yoga and assumed Shesha form on Rama\'s command. A thousand streams of amrit flow.','<h3>Where Lakshman Became Shesha</h3><p><em>"Yasmin Ramajnaya viro Laksmanah paravirdha, pranan utsrijya yogena yayau Sheshatmatam pura"</em></p><p>East of Papmochan Teerth, thousand streams of amrit flow from Shesha\'s hoods. Here, mighty Lakshman shed his mortal body by yoga and assumed his eternal Shesha form on Rama\'s command. Bathing with devotion, charity, and worship of Shesha-Lakshman grants Vishnu Lok and freedom from snake-bite.</p>',26.8060,82.1920,3),
        (akp['swargdwar-saryu-ghat-area'],ghat_cat,'Guptahari (Guptar Ghat)','guptahari-guptar-ghat','Vishnu\'s abode west of Ayodhya — where Ayodhya\'s citizens entered Saryu and attained Vaikuntha. Snaan destroys all sins.','<h3>Gateway to Vaikuntha</h3><p><em>"Vishnusthanam ca tatraiva namna Guptaharih smritah"</em></p><p>West of Ayodhya lies Guptahari (Guptar Ghat) — a great Vishnu sthana where Lord Rama performed His Jal Samadhi. By Rama\'s command, the citizens of Ayodhya entered the Saryu and attained Vaikuntha. Bathing here with devotion purifies all sins and grants Vishnu Lok. Today one of Ayodhya\'s most visited ghats.</p>',26.8100,82.1780,4),
        (akp['swargdwar-saryu-ghat-area'],kund_cat,'Nirmali Kund','nirmali-kund','So supremely pure that Teerth-raj Prayag comes to bathe here daily. Bathing destroys even sins equal to Brahmahatya.','<h3>The Purest of All Teerths</h3><p><em>"Yatra vai tirtharajo pi snatum ayati nityashah"</em></p><p>In the western part of Ayodhya, so pristine that Teerth-raj Prayag himself comes daily to bathe. All sins, even Brahmahatya-grade, are destroyed by bathing in Nirmali Kund — one of the most powerful purification teerths in all of Ayodhya.</p>',26.8090,82.1790,5),
        # T2-04: Surrounding Teerth Kshetras (3 spots)
        (akp['surrounding-teerth-kshetras'],kund_cat,'Surya Kund','surya-kund','South of Vaitarni river — bathing cures leprosy, boils, poverty, all diseases. Special merit on Sundays and in Bhadra/Pausha/Magha.','<h3>The Sun\'s Healing Pool</h3><p><em>"Suryakundam itikhyatam sarvakamarthasiddhidam"</em></p><p>South of Vaitarni river, Surya Kund cures boils, leprosy, poverty, and all diseases through ritual bathing. Especially meritorious on Sundays during Bhadrapada, Pausha, and Magha months. Devotees perform Surya Namaskar and offer arghya here.</p>',26.7880,82.1940,1),
        (akp['surrounding-teerth-kshetras'],shakti_cat,'Devkali','devkali','Adi Shakti Durga Kund — seat of the Goddess in eight-armed (Ashtabhuja) form. Darshan-pujan grants all desires.','<h3>Seat of the Primal Goddess</h3><p><em>"Adya cashbhujau tatra sarvanchitadayini"</em></p><p>West of Surya Kund lies the Durga Kund — seat of Devkali, Adi Shakti in her Ashtabhuja (eight-armed) form, described as the grantor of all desires. Special worship during Navratri and Durga Puja.</p>',26.7875,82.1930,2),
        (akp['surrounding-teerth-kshetras'],teerth_cat,'Manorama Teerth','manorama-teerth','Opposite bank of Saryu — Manorama-Saryu confluence where King Dasharatha performed Putrakameshti Yagya leading to Rama\'s birth.','<h3>Where Dasharatha\'s Yagya Bore Fruit</h3><p><em>"Yatra Raja Dasharatho putresti kritavan pura"</em></p><p>On the far bank of Saryu, at the Manorama river confluence, King Dasharatha performed the Putrakameshti Yagya. By its power, Lord Rama and His three brothers were born. Annual yatra on Chaitra Purnima. Especially auspicious for those desiring children.</p>',26.8000,82.1880,3),
        # T2-05: Bilvahari & Punyahari Area (2 spots)
        (akp['bilvahari-punyahari-area'],temple_cat,'Bilvahari','bilvahari','16 km east on Saryu bank — Sapt Hari. Liberates from Rina Traya (three debts). Darshan removes enemy fear. Yatra in Madhava month.','<h3>Liberation from the Three Debts</h3><p><em>"Tatra snatva naro devi mucyate ca rinatrayat"</em></p><p>Sixteen km east of Ayodhya on the Saryu bank, Bilvahari liberates from Rina Traya — debts to gods, sages, and ancestors. Darshan removes all enemy fear. Annual yatra in Vaishakha month.</p>',26.8000,82.3500,1),
        (akp['bilvahari-punyahari-area'],temple_cat,'Punyahari','punyahari','~1 km west of Bilvahari — Sapt Hari. Bathing cures Pandu Roga (jaundice/anemia). Sundays especially auspicious.','<h3>The Merit-Bestowing Hari</h3><p><em>"Snatva datva ca vidhivat Pandurogadi nashyati"</em></p><p>One km west of Bilvahari, Punyahari cures Pandu Roga (jaundice, anemia) through bathing and charity. Sundays are declared especially auspicious for worship.</p>',26.8000,82.3400,2),
        # T2-06: Nandigram (1 spot)
        (akp['nandigram'],village_cat,'Nandigram & Bharat Kund','nandigram-bharat-kund','Bharat installed Rama\'s Padukas, lived 14 years in penance. Darshan equals 1000 Manvantaras of Kashi-vaas.','<h3>Bharat\'s Supreme Devotion</h3><p><em>"Manvantarasahasraistu Kashivasena yatphalam, tatphalam samprapnoti Nandigramasya darshanat"</em></p><p>Eighteen km south of Ayodhya, Bharat installed Rama\'s Charan Padukas and lived 14 years without food. The first reunion after Lanka occurred here. Darshan merit equals 1000 Manvantaras of Kashi-vaas. All snaan and shraddha here yield inexhaustible merit.</p>',26.6700,82.2100,1),
    ]
    for kpid,catid,t,s,sd,fc,lat,lng,o in t3_data:
        db.execute("INSERT INTO key_spots (key_place_id,category_id,title,slug,short_description,full_content,state,city,country,latitude,longitude,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)", (kpid,catid,t,s,sd,fc,'Uttar Pradesh','Ayodhya','India',lat,lng,o))
        aks[s] = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # ═══════════════════════════════════════════════════════════════
    # ─── VRINDAVAN DHAM (Tier 1) — Secondary Dham (no images) ───
    # ═══════════════════════════════════════════════════════════════
    db.execute("INSERT INTO places (title,slug,short_description,full_content,state,city,country,latitude,longitude,status,is_featured,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
        ('Vrindavan Dham','vrindavan-dham','The divine land of Radha-Krishna leelas, one of the holiest Dhams in Gaudiya Vaishnavism.',
         '<h2>The Eternal Abode of Krishna</h2><p>Vrindavan is the transcendental land where Lord Krishna performed His childhood and youth pastimes. Located in the Braj region of Uttar Pradesh, it is revered by millions.</p>',
         'Uttar Pradesh','Mathura','India',27.5830,77.6950,'published',1))
    vrn_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for tid in [8,4,9,10]: db.execute("INSERT OR IGNORE INTO place_tags VALUES (?,?)", (vrn_id,tid))

    kp_ids = {}
    for t,s,sd,fc,lat,lng,o in [
        ('Vrindavan Town','vrindavan-town','The heart of Vrindavan with ancient temples.','<p>Spiritual center of Braj, home to thousands of Radha-Krishna temples.</p>',27.5830,77.6950,1),
        ('Govardhan','govardhan','The sacred hill lifted by Lord Krishna.','<p>The hill Krishna lifted for seven days to protect Braj from Indra\'s wrath.</p>',27.4929,77.4583,2),
        ('Barsana','barsana','The birthplace of Srimati Radharani.','<p>Sacred village where Srimati Radharani appeared.</p>',27.6474,77.3776,3),
        ('Nandgaon','nandgaon','Village of Nanda Maharaj where Krishna was raised.','<p>Nanda Maharaj\'s village where Krishna spent His early childhood.</p>',27.6717,77.3803,4),
    ]:
        db.execute("INSERT INTO key_places (parent_place_id,title,slug,short_description,full_content,latitude,longitude,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,1)", (vrn_id,t,s,sd,fc,lat,lng,o))
        kp_ids[s] = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    ks_ids = {}
    for kpid,catid,t,s,sd,fc,lat,lng,o in [
        (kp_ids['vrindavan-town'],temple_cat,'ISKCON Krishna Balaram Mandir','iskcon-krishna-balaram','ISKCON headquarters in Vrindavan.','<p>Founded by Srila Prabhupada in 1975 with deities of Krishna-Balaram, Radha-Shyamasundar, Gaura-Nitai.</p>',27.5815,77.6983,1),
        (kp_ids['vrindavan-town'],temple_cat,'Banke Bihari Temple','banke-bihari','Most visited temple in Vrindavan.','<p>Built in 1864, houses the enchanting Banke Bihari deity of Krishna.</p>',27.5833,77.6954,2),
        (kp_ids['vrindavan-town'],temple_cat,'Radha Raman Temple','radha-raman','500-year-old temple with self-manifested deity.','<p>Established by Gopal Bhatta Goswami, the deity appeared from a shaligrama shila.</p>',27.5820,77.6940,3),
        (kp_ids['vrindavan-town'],ghat_cat,'Kesi Ghat','kesi-ghat','Most prominent ghat on the Yamuna.','<p>Where Krishna killed demon Kesi. Key spot for evening aarti.</p>',27.5802,77.6960,4),
        (kp_ids['vrindavan-town'],van_cat,'Nidhivan','nidhivan','Mysterious forest of nightly Raas Leela.','<p>Trees form natural bowers where Radha-Krishna perform Raas Leela every night.</p>',27.5810,77.6930,5),
        (kp_ids['govardhan'],hill_cat,'Govardhan Hill','govardhan-hill','The sacred hill lifted by Krishna.','<p>Worshipped as Govardhan Maharaj. Devotees perform parikrama.</p>',27.4929,77.4583,1),
        (kp_ids['govardhan'],kund_cat,'Radha Kund','radha-kund','Most sacred kund in all of Braj.','<p>Represents the mercy of Srimati Radharani.</p>',27.5062,77.4629,2),
        (kp_ids['govardhan'],kund_cat,'Kusum Sarovar','kusum-sarovar','Beautiful lake with Mughal-era architecture.','<p>Historically significant sarovar linked to Radha-Krishna pastimes.</p>',27.5010,77.4600,3),
        (kp_ids['govardhan'],parikrama_cat,'Govardhan Parikrama','govardhan-parikrama','21 km circumambulation of the sacred hill.','<p>Walked barefoot by millions of devotees annually.</p>',27.4930,77.4580,4),
    ]:
        db.execute("INSERT INTO key_spots (key_place_id,category_id,title,slug,short_description,full_content,state,city,country,latitude,longitude,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)", (kpid,catid,t,s,sd,fc,'Uttar Pradesh','Mathura','India',lat,lng,o))
        ks_ids[s] = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    altar_cat = db.execute("SELECT id FROM sub_spot_categories WHERE slug='altar'").fetchone()[0]
    samadhi_cat = db.execute("SELECT id FROM sub_spot_categories WHERE slug='samadhi_internal'").fetchone()[0]
    quarters_cat = db.execute("SELECT id FROM sub_spot_categories WHERE slug='quarters'").fetchone()[0]
    courtyard_cat = db.execute("SELECT id FROM sub_spot_categories WHERE slug='courtyard'").fetchone()[0]
    for ksid,catid,t,s,sd,fc,o in [
        (ks_ids['iskcon-krishna-balaram'],samadhi_cat,'Srila Prabhupada Samadhi','prabhupada-samadhi','Sacred samadhi of ISKCON founder-acharya.','<p>Ornate marble memorial of A.C. Bhaktivedanta Swami Prabhupada.</p>',1),
        (ks_ids['iskcon-krishna-balaram'],quarters_cat,"Srila Prabhupada's Quarters",'prabhupada-quarters','Preserved living quarters.','<p>Rooms where Srila Prabhupada lived and translated, maintained as-is.</p>',2),
        (ks_ids['iskcon-krishna-balaram'],altar_cat,'Krishna-Balaram Altar','krishna-balaram-altar','Main altar with presiding deities.','<p>Sri Sri Krishna-Balaram, Radha-Shyamasundar, and Gaura-Nitai.</p>',3),
        (ks_ids['iskcon-krishna-balaram'],courtyard_cat,'Temple Courtyard','temple-courtyard','Open gathering space for kirtans.','<p>Spacious courtyard for daily kirtans, festivals, and programs.</p>',4),
    ]:
        db.execute("INSERT INTO sub_spots (key_spot_id,category_id,title,slug,short_description,full_content,state,city,country,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,?,?,1)", (ksid,catid,t,s,sd,fc,'Uttar Pradesh','Vrindavan','India',o))

    # Other sample dhams (no images)
    for t,s,sd,fc,st,ci,lat,lng in [('Mayapur Dham','mayapur-dham','Spiritual headquarters of ISKCON.','<h2>The Holy Land of Mayapur</h2><p>One of the most important Gaudiya Vaishnava pilgrimage sites.</p>','West Bengal','Nadia',23.4231,88.3884),
        ('Kedarnath Dham','kedarnath-dham','One of the twelve Jyotirlingas.','<h2>Sacred Abode of Lord Shiva</h2><p>Located in the Garhwal Himalayas.</p>','Uttarakhand','Rudraprayag',30.7352,79.0669),
        ('Jagannath Puri Dham','jagannath-puri-dham','Abode of Lord Jagannath, one of the Char Dham.','<h2>Land of Lord Jagannath</h2><p>One of the Char Dham pilgrimage sites.</p>','Odisha','Puri',19.8135,85.8312)]:
        db.execute("INSERT INTO places (title,slug,short_description,full_content,state,city,country,latitude,longitude,status,is_featured,created_by) VALUES (?,?,?,?,?,?,'India',?,?,'published',1,1)", (t,s,sd,fc,st,ci,lat,lng))

    # Module entries
    for mod,pid,t,s,c in [(3,ayd_id,'The Ramayana of Ayodhya','ramayana-of-ayodhya','<p>Ayodhya is the setting for the beginning and end of the Ramayana. From Rama\'s birth to His coronation after 14 years of exile, Ayodhya witnessed the leelas that defined dharma for all ages.</p>'),(3,ayd_id,'Sapt Hari Yatra','sapt-hari-yatra','<p>The Sapt Hari pilgrimage covers seven Vishnu temples: Guptahari, Chakrahari, Vishnuhari, Dharmahari, Bilvahari, Punyahari, and Chandrahari.</p>'),(4,ayd_id,'Ram Navami in Ayodhya','ram-navami-ayodhya','<p>Ram Navami on Chaitra Shukla Navami is Ayodhya\'s grandest festival with millions of devotees, grand processions, and Ramayana recitation.</p>'),(3,vrn_id,'Appearance of Sri Chaitanya','appearance-sri-chaitanya','<p>Sri Chaitanya appeared in Mayapur in 1486 CE amidst ecstatic chanting.</p>'),(4,None,'Gaura Purnima','gaura-purnima','<p>Celebrates Sri Chaitanya\'s appearance. Hundreds of thousands visit Mayapur.</p>')]:
        db.execute("INSERT INTO module_entries (module_id,place_id,title,slug,content,status,created_by) VALUES (?,?,?,?,?,'published',1)", (mod,pid,t,s,c))
    # Permissions
    for k,l,d,cat in [('manage_places','Manage Holy Dhams','Create/edit/delete dhams','content'),('manage_modules','Manage Modules','Configure modules','system'),('manage_entries','Manage Entries','Create/edit entries','content'),('manage_media','Manage Media','Upload media','media'),('publish_content','Publish Content','Publish/unpublish','content'),('manage_users','Manage Users','Manage accounts','system'),('manage_tags','Manage Tags','Manage categories','content'),('manage_fields','Manage Fields','Configure custom fields','system'),('capture_photo','📷 Capture Photos Only','Upload/capture photos for all tiers. No other content can be changed.','field_access'),('update_location','📍 Update Location Only','Update GPS coordinates for all tiers. No other content can be changed.','field_access')]:
        db.execute("INSERT OR IGNORE INTO permission_definitions (permission_key,label,description,category) VALUES (?,?,?,?)", (k,l,d,cat))
    db.commit()
    _backfill_hierarchy_ids(db)
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
    # Compress images with Pillow
    if ext in ALLOWED_IMAGE_EXT and ext != 'svg':
        try:
            from PIL import Image, ExifTags
            img=Image.open(fp)
            # Auto-rotate based on EXIF (mobile photos often rotated)
            try:
                for k,v in (img._getexif() or {}).items():
                    if ExifTags.TAGS.get(k)=='Orientation':
                        if v==3: img=img.rotate(180,expand=True)
                        elif v==6: img=img.rotate(270,expand=True)
                        elif v==8: img=img.rotate(90,expand=True)
                        break
            except: pass
            # Resize if too large (max 1920px on longest side)
            max_dim=1920
            w,h=img.size
            if w>max_dim or h>max_dim:
                ratio=min(max_dim/w,max_dim/h)
                img=img.resize((int(w*ratio),int(h*ratio)),Image.LANCZOS)
            # Convert RGBA to RGB for JPEG
            if img.mode in ('RGBA','P') and ext in ('jpg','jpeg'):
                bg=Image.new('RGB',img.size,(255,255,255))
                if img.mode=='P': img=img.convert('RGBA')
                bg.paste(img,mask=img.split()[3])
                img=bg
            # Save with optimization
            if ext in ('jpg','jpeg'):
                img.save(fp,'JPEG',quality=82,optimize=True)
            elif ext=='png':
                img.save(fp,'PNG',optimize=True)
            elif ext=='webp':
                img.save(fp,'WEBP',quality=82)
            else:
                img.save(fp)
        except Exception as e:
            print(f"Image compression warning: {e}")
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
    return {'current_user':get_current_user(),'active_modules':modules,'current_year':datetime.now().year,'has_permission':has_permission,'builtin_fields':BUILTIN_FIELDS,'json':json,'field_icons':FIELD_ICONS,'field_default_icons':FIELD_DEFAULT_ICONS,'module_schemas':MODULE_SCHEMAS}

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
    # Add all T1 gallery images to each place for random display
    featured_list = []
    for f in featured:
        fd = dict(f)
        all_imgs = []
        if fd.get('featured_image'): all_imgs.append(fd['featured_image'])
        # Also get gallery images from place_media
        for m in db.execute("SELECT m.filename FROM media m JOIN place_media pm ON m.id=pm.media_id WHERE pm.place_id=? AND m.file_type='image'",(fd['id'],)).fetchall():
            if m['filename'] and m['filename'] not in all_imgs: all_imgs.append(m['filename'])
        fd['all_images'] = ','.join(all_imgs) if all_imgs else ''
        featured_list.append(fd)
    featured = featured_list
    # Collect images from ALL tiers for hero slider (randomized)
    hero_images=[]
    # T1 Holy Dhams
    for row in db.execute("SELECT featured_image,title,slug,'T1' as tier,'' as dham_slug,'' as dham_title,'' as kp_slug,'' as kp_title,'' as ks_slug,'' as ks_title FROM places WHERE status='published' AND featured_image IS NOT NULL AND featured_image!='' ORDER BY RANDOM() LIMIT 4").fetchall():
        d=dict(row); d['image']=row['featured_image']; hero_images.append(d)
    # T1 gallery from place_media
    for row in db.execute("""SELECT m.filename as image,p.title,p.slug,'T1' as tier,'' as dham_slug,p.title as dham_title,'' as kp_slug,'' as kp_title,'' as ks_slug,'' as ks_title
        FROM media m JOIN place_media pm ON m.id=pm.media_id JOIN places p ON pm.place_id=p.id WHERE m.file_type='image' AND p.status='published' ORDER BY RANDOM() LIMIT 3""").fetchall():
        hero_images.append(dict(row))
    # T2 Key Places
    for row in db.execute("""SELECT kp.featured_image as image,kp.title,kp.slug,p.slug as dham_slug,p.title as dham_title,'T2' as tier,'' as kp_slug,'' as kp_title,'' as ks_slug,'' as ks_title
        FROM key_places kp JOIN places p ON kp.parent_place_id=p.id WHERE kp.is_visible=1 AND p.status='published' AND kp.featured_image IS NOT NULL AND kp.featured_image!='' ORDER BY RANDOM() LIMIT 4""").fetchall():
        hero_images.append(dict(row))
    # T2 gallery images
    for row in db.execute("""SELECT kp.gallery_images,kp.title,kp.slug,p.slug as dham_slug,p.title as dham_title,'T2' as tier,'' as kp_slug,'' as kp_title,'' as ks_slug,'' as ks_title
        FROM key_places kp JOIN places p ON kp.parent_place_id=p.id WHERE kp.is_visible=1 AND p.status='published' AND kp.gallery_images IS NOT NULL AND kp.gallery_images!='' ORDER BY RANDOM() LIMIT 3""").fetchall():
        for gi in row['gallery_images'].split(',')[:1]:
            if gi.strip(): d=dict(row); d['image']=gi.strip(); hero_images.append(d)
    # T3 Key Spots
    for row in db.execute("""SELECT ks.featured_image as image,ks.title,ks.slug,p.slug as dham_slug,p.title as dham_title,kp.slug as kp_slug,kp.title as kp_title,'T3' as tier,'' as ks_slug,'' as ks_title
        FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id
        WHERE ks.is_visible=1 AND p.status='published' AND ks.featured_image IS NOT NULL AND ks.featured_image!='' ORDER BY RANDOM() LIMIT 4""").fetchall():
        hero_images.append(dict(row))
    # T3 gallery
    for row in db.execute("""SELECT ks.gallery_images,ks.title,ks.slug,p.slug as dham_slug,p.title as dham_title,kp.slug as kp_slug,kp.title as kp_title,'T3' as tier,'' as ks_slug,'' as ks_title
        FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id
        WHERE ks.is_visible=1 AND p.status='published' AND ks.gallery_images IS NOT NULL AND ks.gallery_images!='' ORDER BY RANDOM() LIMIT 3""").fetchall():
        for gi in row['gallery_images'].split(',')[:1]:
            if gi.strip(): d=dict(row); d['image']=gi.strip(); hero_images.append(d)
    # T4 Key Points
    for row in db.execute("""SELECT ss.featured_image as image,ss.title,ss.slug,p.slug as dham_slug,p.title as dham_title,kp.slug as kp_slug,kp.title as kp_title,ks.slug as ks_slug,ks.title as ks_title,'T4' as tier
        FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id
        WHERE ss.is_visible=1 AND p.status='published' AND ss.featured_image IS NOT NULL AND ss.featured_image!='' ORDER BY RANDOM() LIMIT 4""").fetchall():
        hero_images.append(dict(row))
    # T4 gallery
    for row in db.execute("""SELECT ss.gallery_images,ss.title,ss.slug,p.slug as dham_slug,p.title as dham_title,kp.slug as kp_slug,kp.title as kp_title,ks.slug as ks_slug,ks.title as ks_title,'T4' as tier
        FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id
        WHERE ss.is_visible=1 AND p.status='published' AND ss.gallery_images IS NOT NULL AND ss.gallery_images!='' ORDER BY RANDOM() LIMIT 3""").fetchall():
        for gi in row['gallery_images'].split(',')[:1]:
            if gi.strip(): d=dict(row); d['image']=gi.strip(); hero_images.append(d)
    # Deduplicate and shuffle
    seen=set(); unique=[]
    for h in hero_images:
        if h.get('image') and h['image'] not in seen: seen.add(h['image']); unique.append(h)
    random.shuffle(unique)
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

# ─── Static Pages (section-based with DB content) ───
import json as _json

def _get_page_sections(page_key):
    """Load page sections from DB, return list of section dicts."""
    db=get_db()
    row=db.execute("SELECT value FROM site_settings WHERE key=?",(f"page_{page_key}_sections",)).fetchone()
    if row and row['value']:
        try: return _json.loads(row['value'])
        except: pass
    return None

@app.route('/about')
def about():
    sections=_get_page_sections('about')
    return render_template('frontend/about.html', sections=sections)
@app.route('/privacy')
def privacy():
    sections=_get_page_sections('privacy')
    return render_template('frontend/privacy.html', sections=sections)
@app.route('/terms')
def terms():
    sections=_get_page_sections('terms')
    return render_template('frontend/terms.html', sections=sections)

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
    db.execute("UPDATE key_places SET view_count=view_count+1 WHERE id=?",(kp['id'],)); db.commit()
    kp_customs=db.execute("SELECT kpcv.*,cfd.name,cfd.label,cfd.field_type,cfd.icon as field_icon FROM key_place_custom_values kpcv JOIN custom_field_defs cfd ON kpcv.field_def_id=cfd.id WHERE kpcv.key_place_id=? AND kpcv.is_visible=1 AND cfd.is_active=1 ORDER BY cfd.sort_order",(kp['id'],)).fetchall()
    key_spots=db.execute("SELECT ks.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color FROM key_spots ks LEFT JOIN spot_categories sc ON ks.category_id=sc.id WHERE ks.key_place_id=? AND ks.is_visible=1 ORDER BY ks.sort_order",(kp['id'],)).fetchall()
    spots_with_subs=[]
    for ks in key_spots:
        subs=db.execute("SELECT ss.*,ssc.name as cat_name,ssc.icon as cat_icon,ssc.color as cat_color FROM sub_spots ss LEFT JOIN sub_spot_categories ssc ON ss.category_id=ssc.id WHERE ss.key_spot_id=? AND ss.is_visible=1 ORDER BY ss.sort_order",(ks['id'],)).fetchall()
        spots_with_subs.append({'spot':ks,'sub_spots':subs})
    siblings=db.execute("SELECT * FROM key_places WHERE parent_place_id=? AND is_visible=1 AND id!=? ORDER BY sort_order",(place['id'],kp['id'])).fetchall()
    tags=db.execute("SELECT t.* FROM tags t JOIN place_tags pt ON t.id=pt.tag_id WHERE pt.place_id=?",(place['id'],)).fetchall()
    kp_gallery=[x.strip() for x in (kp['gallery_images'] or '').split(',') if x.strip()]
    try:
        kp_captions=json.loads(kp['gallery_captions'] or '{}') if kp['gallery_captions'] else {}
    except (KeyError, IndexError):
        kp_captions={}
    return render_template('frontend/key_place.html',place=place,kp=kp,kp_customs=kp_customs,key_spots=spots_with_subs,siblings=siblings,tags=tags,kp_gallery=kp_gallery,kp_captions=kp_captions)

@app.route('/place/<slug>/key/<kp_slug>/spot/<ks_slug>')
def key_spot_detail(slug, kp_slug, ks_slug):
    db=get_db(); place=db.execute("SELECT * FROM places WHERE slug=? AND status='published'",(slug,)).fetchone()
    if not place: abort(404)
    kp=db.execute("SELECT * FROM key_places WHERE parent_place_id=? AND slug=?",(place['id'],kp_slug)).fetchone()
    if not kp: abort(404)
    ks=db.execute("SELECT ks.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color FROM key_spots ks LEFT JOIN spot_categories sc ON ks.category_id=sc.id WHERE ks.key_place_id=? AND ks.slug=? AND ks.is_visible=1",(kp['id'],ks_slug)).fetchone()
    if not ks: abort(404)
    db.execute("UPDATE key_spots SET view_count=view_count+1 WHERE id=?",(ks['id'],)); db.commit()
    sub_spots=db.execute("SELECT ss.*,ssc.name as cat_name,ssc.icon as cat_icon,ssc.color as cat_color FROM sub_spots ss LEFT JOIN sub_spot_categories ssc ON ss.category_id=ssc.id WHERE ss.key_spot_id=? AND ss.is_visible=1 ORDER BY ss.sort_order",(ks['id'],)).fetchall()
    ks_customs=db.execute("SELECT kscv.*,cfd.name,cfd.label,cfd.field_type,cfd.icon as field_icon FROM key_spot_custom_values kscv JOIN custom_field_defs cfd ON kscv.field_def_id=cfd.id WHERE kscv.key_spot_id=? AND kscv.is_visible=1 AND cfd.is_active=1 ORDER BY cfd.sort_order",(ks['id'],)).fetchall()
    ks_gallery=[x.strip() for x in (ks['gallery_images'] or '').split(',') if x.strip()]
    try:
        ks_captions=json.loads(ks['gallery_captions'] or '{}') if ks['gallery_captions'] else {}
    except (KeyError, IndexError):
        ks_captions={}
    siblings=db.execute("SELECT ks2.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color FROM key_spots ks2 LEFT JOIN spot_categories sc ON ks2.category_id=sc.id WHERE ks2.key_place_id=? AND ks2.is_visible=1 AND ks2.id!=? ORDER BY ks2.sort_order",(kp['id'],ks['id'])).fetchall()
    return render_template('frontend/key_spot.html',place=place,kp=kp,ks=ks,sub_spots=sub_spots,siblings=siblings,ks_customs=ks_customs,ks_gallery=ks_gallery,ks_captions=ks_captions)

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
    db.execute("UPDATE sub_spots SET view_count=view_count+1 WHERE id=?",(ss['id'],)); db.commit()
    ss_customs=db.execute("SELECT sscv.*,cfd.name,cfd.label,cfd.field_type,cfd.icon as field_icon FROM sub_spot_custom_values sscv JOIN custom_field_defs cfd ON sscv.field_def_id=cfd.id WHERE sscv.sub_spot_id=? AND sscv.is_visible=1 AND cfd.is_active=1 ORDER BY cfd.sort_order",(ss['id'],)).fetchall()
    ss_gallery=[x.strip() for x in (ss['gallery_images'] or '').split(',') if x.strip()]
    try:
        ss_captions=json.loads(ss['gallery_captions'] or '{}') if ss['gallery_captions'] else {}
    except (KeyError, IndexError):
        ss_captions={}
    siblings=db.execute("SELECT ss2.*,ssc.name as cat_name,ssc.icon as cat_icon,ssc.color as cat_color FROM sub_spots ss2 LEFT JOIN sub_spot_categories ssc ON ss2.category_id=ssc.id WHERE ss2.key_spot_id=? AND ss2.is_visible=1 AND ss2.id!=? ORDER BY ss2.sort_order",(ks['id'],ss['id'])).fetchall()
    return render_template('frontend/sub_spot.html',place=place,kp=kp,ks=ks,ss=ss,siblings=siblings,ss_customs=ss_customs,ss_gallery=ss_gallery,ss_captions=ss_captions)

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
    entry=db.execute("SELECT me.*,p.title as place_title,p.slug as place_slug FROM module_entries me LEFT JOIN places p ON me.place_id=p.id WHERE me.module_id=? AND me.slug=?",(module['id'],entry_slug)).fetchone()
    if not entry: abort(404)
    # Get tier link info
    tier_link_info=None
    if entry['tier_link_type'] and entry['tier_link_id']:
        tlt=entry['tier_link_type']; tlid=entry['tier_link_id']
        if tlt=='dham': tier_link_info=db.execute("SELECT title,slug,'dham' as tier FROM places WHERE id=?",(tlid,)).fetchone()
        elif tlt=='key_place': tier_link_info=db.execute("SELECT kp.title,kp.slug,p.slug as dham_slug,'key_place' as tier FROM key_places kp JOIN places p ON kp.parent_place_id=p.id WHERE kp.id=?",(tlid,)).fetchone()
        elif tlt=='key_spot': tier_link_info=db.execute("SELECT ks.title,ks.slug,kp.slug as kp_slug,p.slug as dham_slug,'key_spot' as tier FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id WHERE ks.id=?",(tlid,)).fetchone()
        elif tlt=='sub_spot': tier_link_info=db.execute("SELECT ss.title,ss.slug,ks.slug as ks_slug,kp.slug as kp_slug,p.slug as dham_slug,'sub_spot' as tier FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id WHERE ss.id=?",(tlid,)).fetchone()
    # Get audio/video items
    audio_video=db.execute("SELECT * FROM entry_audio_video WHERE entry_id=? ORDER BY sort_order",(entry['id'],)).fetchall()
    # Parse custom fields
    try: custom_fields=json.loads(entry['custom_fields'] or '{}')
    except: custom_fields={}
    schema=json.loads(module['fields_schema'] or '[]')
    # Gallery images
    gallery=[x.strip() for x in (entry['gallery_images'] or '').split(',') if x.strip()]
    return render_template('frontend/entry.html',module=module,entry=entry,custom_fields=custom_fields,schema=schema,tier_link_info=tier_link_info,audio_video=audio_video,gallery=gallery)

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
    stats={'places':db.execute("SELECT COUNT(*) FROM places").fetchone()[0],'published':db.execute("SELECT COUNT(*) FROM places WHERE status='published'").fetchone()[0],'key_places':db.execute("SELECT COUNT(*) FROM key_places").fetchone()[0],'entries':db.execute("SELECT COUNT(*) FROM module_entries").fetchone()[0],'media':db.execute("SELECT COUNT(*) FROM media").fetchone()[0],'users':db.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0],'modules':db.execute("SELECT COUNT(*) FROM modules WHERE is_active=1").fetchone()[0],'key_spots':db.execute("SELECT COUNT(*) FROM key_spots").fetchone()[0],'sub_spots':db.execute("SELECT COUNT(*) FROM sub_spots").fetchone()[0],'itineraries':db.execute("SELECT COUNT(*) FROM itineraries").fetchone()[0]}
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
    if q: query+=" AND (p.title LIKE ? OR p.city LIKE ? OR p.state LIKE ? OR p.hierarchy_id LIKE ? OR p.dham_code LIKE ?)"; params.extend([f'%{q}%']*5)
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
    cvs={r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible'],'description':r['description'] or ''} for r in db.execute("SELECT field_def_id,value,is_visible,description FROM place_custom_values WHERE place_id=?",(place_id,)).fetchall()}
    kps=db.execute("SELECT * FROM key_places WHERE parent_place_id=? ORDER BY sort_order",(place_id,)).fetchall()
    kpc={}
    for kp in kps:
        kpc[kp['id']]={r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible'],'description':r['description'] or ''} for r in db.execute("SELECT field_def_id,value,is_visible,description FROM key_place_custom_values WHERE key_place_id=?",(kp['id'],)).fetchall()}
    # Get key spots count per key place
    kp_spot_counts={}
    for kp in kps:
        kp_spot_counts[kp['id']]=db.execute("SELECT COUNT(*) FROM key_spots WHERE key_place_id=?",(kp['id'],)).fetchone()[0]
    # Fetch ALL key_spots for this dham (for Tier 3 tab)
    all_spots=db.execute("SELECT ks.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color,kp.title as kp_title,kp.id as kp_id,kp.slug as kp_slug FROM key_spots ks LEFT JOIN spot_categories sc ON ks.category_id=sc.id JOIN key_places kp ON ks.key_place_id=kp.id WHERE kp.parent_place_id=? ORDER BY kp.sort_order,ks.sort_order",(place_id,)).fetchall()
    # Fetch ALL sub_spots (key points) for this dham (for Tier 4 tab)
    all_points=db.execute("SELECT ss.*,ssc.name as cat_name,ssc.icon as cat_icon,ssc.color as cat_color,ks.title as ks_title,ks.id as ks_id,ks.slug as ks_slug,sc2.name as ks_cat_name,sc2.icon as ks_cat_icon,kp.title as kp_title,kp.id as kp_id FROM sub_spots ss LEFT JOIN sub_spot_categories ssc ON ss.category_id=ssc.id JOIN key_spots ks ON ss.key_spot_id=ks.id LEFT JOIN spot_categories sc2 ON ks.category_id=sc2.id JOIN key_places kp ON ks.key_place_id=kp.id WHERE kp.parent_place_id=? ORDER BY kp.sort_order,ks.sort_order,ss.sort_order",(place_id,)).fetchall()
    # Fetch gallery images from place_media
    gallery_media=db.execute("SELECT m.id,m.filename,m.original_name,m.file_type,m.caption FROM media m JOIN place_media pm ON m.id=pm.media_id WHERE pm.place_id=? AND m.file_type='image' ORDER BY pm.sort_order",(place_id,)).fetchall()
    return render_template('admin/place_form.html',place=place,tags=tags,place_tags=ptags,custom_fields=cfs,custom_values=cvs,key_places=kps,key_place_customs=kpc,editing=True,spot_categories=db.execute("SELECT * FROM spot_categories ORDER BY name").fetchall(),sub_spot_categories=db.execute("SELECT * FROM sub_spot_categories ORDER BY name").fetchall(),kp_spot_counts=kp_spot_counts,all_spots=all_spots,all_points=all_points,gallery_media=gallery_media,t1_av=db.execute("SELECT * FROM place_audio_video WHERE tier='T1' AND place_ref_id=? ORDER BY sort_order",(place_id,)).fetchall())

def _save_place(place_id):
    db=get_db(); f=request.form; title=f['title']; slug=slugify(title)
    fi=f.get('featured_image_existing','').strip()
    if not fi: fi=''  # Handle cleared by delete
    orig_fi=fi  # Track original to detect if regular upload changed it
    if 'featured_image_file' in request.files:
        uf=request.files['featured_image_file']
        if uf and uf.filename: u=save_upload(uf,'images'); fi=u if u else fi
    # Camera capture fallback for featured image (mobile)
    if fi==orig_fi and 'featured_image_cam' in request.files:
        uf=request.files['featured_image_cam']
        if uf and uf.filename: u=save_upload(uf,'images'); fi=u if u else fi
    vis={}
    for bf in BUILTIN_FIELDS: vis[bf['key']]=1 if f.get(f"vis_{bf['key']}") else 0
    lat=f.get('latitude',type=float); lng=f.get('longitude',type=float)
    fi_desc=f.get('featured_image_desc','').strip()
    _loc_user = get_current_user()
    _loc_username = _loc_user['display_name'] if _loc_user else 'Unknown'
    _loc_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if place_id:
        db.execute("UPDATE places SET title=?,short_description=?,full_content=?,state=?,city=?,country=?,latitude=?,longitude=?,featured_image=?,featured_image_desc=?,status=?,is_featured=?,field_visibility=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (title,f.get('short_description',''),f.get('full_content',''),f.get('state',''),f.get('city',''),f.get('country','India'),lat,lng,fi,fi_desc,f.get('status','draft'),1 if f.get('is_featured') else 0,json.dumps(vis),place_id))
        if lat is not None and lng is not None:
            db.execute("UPDATE places SET location_updated_at=?,location_updated_by=? WHERE id=?",(_loc_now,_loc_username,place_id))
    else:
        if db.execute("SELECT id FROM places WHERE slug=?",(slug,)).fetchone(): slug+='-'+uuid.uuid4().hex[:6]
        dham_code=_generate_dham_code(title,db)
        hid=_gen_t1_id(dham_code)
        db.execute("INSERT INTO places (title,slug,short_description,full_content,state,city,country,latitude,longitude,featured_image,featured_image_desc,status,is_featured,field_visibility,dham_code,hierarchy_id,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title,slug,f.get('short_description',''),f.get('full_content',''),f.get('state',''),f.get('city',''),f.get('country','India'),lat,lng,fi,fi_desc,f.get('status','draft'),1 if f.get('is_featured') else 0,json.dumps(vis),dham_code,hid,session['user_id']))
        place_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]
        if lat is not None and lng is not None:
            db.execute("UPDATE places SET location_updated_at=?,location_updated_by=? WHERE id=?",(_loc_now,_loc_username,place_id))
    db.execute("DELETE FROM place_tags WHERE place_id=?",(place_id,))
    for tid in f.getlist('tags'): db.execute("INSERT OR IGNORE INTO place_tags VALUES (?,?)",(place_id,tid))
    # Handle T1 gallery image uploads (individual)
    idx=0
    while True:
        nk=f't1_new_gallery_{idx}'
        if nk not in request.files: break
        gf=request.files[nk]
        if gf and gf.filename:
            rp = save_upload(gf, 'images')
            if rp:
                mid = db.execute("SELECT id FROM media WHERE filename=?",(rp,)).fetchone()
                if mid:
                    db.execute("INSERT INTO place_media (place_id,media_id,media_role) VALUES (?,?,?)",(place_id,mid['id'],'gallery'))
                    nc=f.get(f't1_new_caption_{idx}','').strip()
                    if nc: db.execute("UPDATE media SET caption=? WHERE id=?",(nc,mid['id']))
        idx+=1
    # Also handle old-style multi-upload for backward compat
    if 'gallery_files' in request.files:
        for gf in request.files.getlist('gallery_files'):
            if gf and gf.filename:
                rp = save_upload(gf, 'images')
                if rp:
                    mid = db.execute("SELECT id FROM media WHERE filename=?",(rp,)).fetchone()
                    if mid: db.execute("INSERT INTO place_media (place_id,media_id,media_role) VALUES (?,?,?)",(place_id,mid['id'],'gallery'))
    # Update captions for existing T1 media
    for key in f:
        if key.startswith('t1_media_caption_'):
            media_id=int(key.replace('t1_media_caption_',''))
            cap_val=f[key].strip()
            db.execute("UPDATE media SET caption=? WHERE id=?",(cap_val,media_id))
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
        desc=f.get(f"cf_desc_{cf['id']}",'')
        db.execute("INSERT OR REPLACE INTO place_custom_values (place_id,field_def_id,value,is_visible,description) VALUES (?,?,?,?,?)",(place_id,cf['id'],val,iv,desc))
    # Key Places (Tier 2)
    existing_kpids=[r['id'] for r in db.execute("SELECT id FROM key_places WHERE parent_place_id=?",(place_id,)).fetchall()]
    # Get dham_code for hierarchy ID generation
    _place_row=db.execute("SELECT dham_code FROM places WHERE id=?",(place_id,)).fetchone()
    _dham_code=_place_row['dham_code'] if _place_row and _place_row['dham_code'] else None
    submitted_kpids=[]; kpi=0
    while True:
        kt=f.get(f'kp_{kpi}_title')
        if kt is None: break
        if not kt.strip(): kpi+=1; continue
        kpid=f.get(f'kp_{kpi}_id',type=int); ks=slugify(kt); ksd=f.get(f'kp_{kpi}_short_description','')
        kfc=f.get(f'kp_{kpi}_full_content',''); klat=f.get(f'kp_{kpi}_latitude',type=float); klng=f.get(f'kp_{kpi}_longitude',type=float)
        kfi_desc=f.get(f'kp_{kpi}_featured_image_desc','').strip()
        kv=1 if f.get(f'kp_{kpi}_is_visible') else 0
        kimg=f.get(f'kp_{kpi}_featured_image_existing','')
        kfk=f'kp_{kpi}_featured_image_file'
        orig_kimg=kimg
        if kfk in request.files:
            uf=request.files[kfk]
            if uf and uf.filename: u=save_upload(uf,'images'); kimg=u if u else kimg
        # Camera capture fallback for T2 featured image (mobile)
        kcam=f'kp_{kpi}_featured_cam'
        if kimg==orig_kimg and kcam in request.files:
            uf=request.files[kcam]
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
        # Individual gallery uploads for T2
        new_kp_captions = {}
        idx=0
        while True:
            nk=f'kp_{kpi}_new_gallery_{idx}'
            if nk not in request.files: break
            uf=request.files[nk]
            if uf and uf.filename:
                u=save_upload(uf,'images')
                if u:
                    existing_imgs=[x for x in kgallery.split(',') if x.strip()] if kgallery else []
                    existing_imgs.append(u); kgallery=','.join(existing_imgs)
                    nc=f.get(f'kp_{kpi}_new_caption_{idx}','').strip()
                    if nc: new_kp_captions[u]=nc
            idx+=1
        # Gather T2 captions
        kp_captions={}
        kp_captions.update(new_kp_captions)
        for key in f:
            if key.startswith(f'kp_{kpi}_caption_'):
                img_path=key[len(f'kp_{kpi}_caption_'):]
                cap_val=f[key].strip()
                if cap_val: kp_captions[img_path]=cap_val
        kp_captions_json=json.dumps(kp_captions)
        if kpid and kpid in existing_kpids:
            db.execute("UPDATE key_places SET title=?,slug=?,short_description=?,full_content=?,featured_image=?,featured_image_desc=?,gallery_images=?,gallery_captions=?,latitude=?,longitude=?,sort_order=?,is_visible=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (kt,ks,ksd,kfc,kimg,kfi_desc,kgallery,kp_captions_json,klat,klng,kpi,kv,kpid)); submitted_kpids.append(kpid)
            if klat is not None and klng is not None:
                db.execute("UPDATE key_places SET location_updated_at=?,location_updated_by=? WHERE id=?",(_loc_now,_loc_username,kpid))
        else:
            kp_hid=_gen_t2_id(_dham_code,db,place_id) if _dham_code else None
            db.execute("INSERT INTO key_places (parent_place_id,title,slug,short_description,full_content,featured_image,featured_image_desc,gallery_images,gallery_captions,latitude,longitude,sort_order,is_visible,hierarchy_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (place_id,kt,ks,ksd,kfc,kimg,kfi_desc,kgallery,kp_captions_json,klat,klng,kpi,kv,kp_hid))
            kpid=db.execute("SELECT last_insert_rowid()").fetchone()[0]; submitted_kpids.append(kpid)
            if klat is not None and klng is not None:
                db.execute("UPDATE key_places SET location_updated_at=?,location_updated_by=? WHERE id=?",(_loc_now,_loc_username,kpid))
        for cf in cfs:
            kcv=''; kcfk=f"kp_{kpi}_cf_file_{cf['id']}"
            if kcfk in request.files:
                uf=request.files[kcfk]
                if uf and uf.filename: u=save_upload(uf); kcv=u if u else kcv
            if not kcv: kcv=f.get(f"kp_{kpi}_cf_{cf['id']}",'')
            kcvis=1 if f.get(f"kp_{kpi}_cf_vis_{cf['id']}") else 0
            kcdesc=f.get(f"kp_{kpi}_cf_desc_{cf['id']}",'')
            if kcv or kcvis: db.execute("INSERT OR REPLACE INTO key_place_custom_values (key_place_id,field_def_id,value,is_visible,description) VALUES (?,?,?,?,?)",(kpid,cf['id'],kcv,kcvis,kcdesc))
        kpi+=1
    for oid in existing_kpids:
        if oid not in submitted_kpids: db.execute("DELETE FROM key_places WHERE id=?",(oid,))
    db.commit(); log_action(session['user_id'],'save_place','place',place_id,title)
    flash(f'Holy Dham "{title}" saved!','success'); return redirect(url_for('admin_places'))

@app.route('/admin/places/<int:place_id>/delete', methods=['POST'])
@login_required
def admin_place_delete(place_id):
    db=get_db(); db.execute("DELETE FROM places WHERE id=?",(place_id,)); db.commit(); flash('Deleted.','info'); return redirect(url_for('admin_places'))

# ═══════════════════════════════════════════════════════════════
# ─── Restricted Access: Photo-Only & Location-Only Pages ───
# ═══════════════════════════════════════════════════════════════

def _load_full_dham_data(place_id):
    """Load ALL dham data across all tiers for read-only display."""
    db = get_db()
    place = db.execute("SELECT * FROM places WHERE id=?", (place_id,)).fetchone()
    if not place: return None
    data = {'place': place}
    # Tags
    data['tags'] = [r['name'] for r in db.execute("SELECT t.name FROM tags t JOIN place_tags pt ON t.id=pt.tag_id WHERE pt.place_id=?", (place_id,)).fetchall()]
    # T1 custom fields
    cfs = db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 AND applies_to IN ('both','place') ORDER BY sort_order").fetchall()
    cvs = {r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible'],'description':r['description'] or ''} for r in db.execute("SELECT field_def_id,value,is_visible,description FROM place_custom_values WHERE place_id=?",(place_id,)).fetchall()}
    data['custom_fields'] = cfs
    data['custom_values'] = cvs
    # Gallery
    data['gallery_media'] = db.execute("SELECT m.id,m.filename,m.caption FROM media m JOIN place_media pm ON m.id=pm.media_id WHERE pm.place_id=? AND m.file_type='image' ORDER BY pm.sort_order",(place_id,)).fetchall()
    # T2 Key Places
    kps = db.execute("SELECT * FROM key_places WHERE parent_place_id=? ORDER BY sort_order", (place_id,)).fetchall()
    data['kps'] = kps
    kpc = {}
    for kp in kps:
        kpc[kp['id']] = {r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible'],'description':r['description'] or ''} for r in db.execute("SELECT field_def_id,value,is_visible,description FROM key_place_custom_values WHERE key_place_id=?",(kp['id'],)).fetchall()}
    data['kp_customs'] = kpc
    # T3 Key Spots
    data['kss'] = db.execute("SELECT ks.*,kp.title as kp_title,sc.name as cat_name,sc.icon as cat_icon FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id LEFT JOIN spot_categories sc ON ks.category_id=sc.id WHERE kp.parent_place_id=? ORDER BY kp.sort_order,ks.sort_order",(place_id,)).fetchall()
    # T3 custom fields
    ksc = {}
    for ks in data['kss']:
        ksc[ks['id']] = {r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible'],'description':r['description'] or ''} for r in db.execute("SELECT field_def_id,value,is_visible,description FROM key_spot_custom_values WHERE key_spot_id=?",(ks['id'],)).fetchall()}
    data['ks_customs'] = ksc
    # T4 Sub Spots
    data['sss'] = db.execute("SELECT ss.*,ks.title as ks_title,kp.title as kp_title FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id JOIN key_places kp ON ks.key_place_id=kp.id WHERE kp.parent_place_id=? ORDER BY kp.sort_order,ks.sort_order,ss.sort_order",(place_id,)).fetchall()
    # T4 custom fields
    ssc = {}
    for ss in data['sss']:
        ssc[ss['id']] = {r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible'],'description':r['description'] or ''} for r in db.execute("SELECT field_def_id,value,is_visible,description FROM sub_spot_custom_values WHERE sub_spot_id=?",(ss['id'],)).fetchall()}
    data['ss_customs'] = ssc
    # kp custom field definitions (applies to key_place)
    data['kp_field_defs'] = db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 AND applies_to IN ('both','key_place') ORDER BY sort_order").fetchall()
    return data

# ─── Photo Capture Page (Restricted — Full Read-Only View) ───
@app.route('/admin/places/<int:place_id>/photos', methods=['GET','POST'])
@login_required
def admin_place_photos(place_id):
    db = get_db()
    u = get_current_user()
    if not has_permission(u, 'capture_photo') and not has_permission(u, 'manage_places'):
        flash('Permission denied.', 'error'); return redirect(url_for('admin_dashboard'))
    d = _load_full_dham_data(place_id)
    if not d: abort(404)
    place = d['place']
    if request.method == 'POST':
        # Save T1 featured image
        fi = place['featured_image'] or ''
        for fname in ('t1_featured_file', 't1_featured_cam'):
            if fname in request.files:
                uf = request.files[fname]
                if uf and uf.filename:
                    u_path = save_upload(uf, 'images')
                    if u_path: fi = u_path
        if fi != (place['featured_image'] or ''):
            db.execute("UPDATE places SET featured_image=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (fi, place_id))
        # Save T1 gallery images
        idx = 0
        while True:
            nk = f't1_photo_gallery_{idx}'
            if nk not in request.files: break
            gf = request.files[nk]
            if gf and gf.filename:
                rp = save_upload(gf, 'images')
                if rp:
                    mid = db.execute("SELECT id FROM media WHERE filename=?", (rp,)).fetchone()
                    if mid: db.execute("INSERT INTO place_media (place_id,media_id,media_role) VALUES (?,?,?)", (place_id, mid['id'], 'gallery'))
            idx += 1
        # Save T2 images
        for kp in d['kps']:
            kpid = kp['id']
            kfi = kp['featured_image'] or ''
            for fname in (f'kp_{kpid}_featured_file', f'kp_{kpid}_featured_cam'):
                if fname in request.files:
                    uf = request.files[fname]
                    if uf and uf.filename:
                        u_path = save_upload(uf, 'images')
                        if u_path: kfi = u_path
            if kfi != (kp['featured_image'] or ''):
                db.execute("UPDATE key_places SET featured_image=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (kfi, kpid))
            gidx = 0
            while True:
                nk = f'kp_{kpid}_photo_gallery_{gidx}'
                if nk not in request.files: break
                gf = request.files[nk]
                if gf and gf.filename:
                    rp = save_upload(gf, 'images')
                    if rp:
                        eg = kp['gallery_images'] or ''
                        ng = (eg + ',' + rp) if eg else rp
                        db.execute("UPDATE key_places SET gallery_images=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (ng, kpid))
                gidx += 1
        # Save T3 images
        for ks in d['kss']:
            ksid = ks['id']
            kfi = ks['featured_image'] or ''
            for fname in (f'ks_{ksid}_featured_file', f'ks_{ksid}_featured_cam'):
                if fname in request.files:
                    uf = request.files[fname]
                    if uf and uf.filename:
                        u_path = save_upload(uf, 'images')
                        if u_path: kfi = u_path
            if kfi != (ks['featured_image'] or ''):
                db.execute("UPDATE key_spots SET featured_image=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (kfi, ksid))
            gidx = 0
            while True:
                nk = f'ks_{ksid}_photo_gallery_{gidx}'
                if nk not in request.files: break
                gf = request.files[nk]
                if gf and gf.filename:
                    rp = save_upload(gf, 'images')
                    if rp:
                        eg = ks['gallery_images'] or ''
                        ng = (eg + ',' + rp) if eg else rp
                        db.execute("UPDATE key_spots SET gallery_images=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (ng, ksid))
                gidx += 1
        # Save T4 images
        for ss in d['sss']:
            ssid = ss['id']
            sfi = ss['featured_image'] or ''
            for fname in (f'ss_{ssid}_featured_file', f'ss_{ssid}_featured_cam'):
                if fname in request.files:
                    uf = request.files[fname]
                    if uf and uf.filename:
                        u_path = save_upload(uf, 'images')
                        if u_path: sfi = u_path
            if sfi != (ss['featured_image'] or ''):
                db.execute("UPDATE sub_spots SET featured_image=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (sfi, ssid))
            gidx = 0
            while True:
                nk = f'ss_{ssid}_photo_gallery_{gidx}'
                if nk not in request.files: break
                gf = request.files[nk]
                if gf and gf.filename:
                    rp = save_upload(gf, 'images')
                    if rp:
                        eg = ss['gallery_images'] or ''
                        ng = (eg + ',' + rp) if eg else rp
                        db.execute("UPDATE sub_spots SET gallery_images=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (ng, ssid))
                gidx += 1
        db.commit()
        log_action(session.get('user_id'), 'photo_update', 'place', place_id, place['title'])
        flash('Photos updated successfully!', 'success')
        return redirect(url_for('admin_place_photos', place_id=place_id))
    return render_template('admin/place_photos.html', d=d)

# ─── Location Update Page (Restricted — Full Read-Only View) ───
@app.route('/admin/places/<int:place_id>/location', methods=['GET','POST'])
@login_required
def admin_place_location(place_id):
    db = get_db()
    u = get_current_user()
    if not has_permission(u, 'update_location') and not has_permission(u, 'manage_places'):
        flash('Permission denied.', 'error'); return redirect(url_for('admin_dashboard'))
    d = _load_full_dham_data(place_id)
    if not d: abort(404)
    place = d['place']
    if request.method == 'POST':
        f = request.form
        _loc_username = u['display_name'] if u else 'Unknown'
        _loc_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lat = f.get('t1_latitude', type=float); lng = f.get('t1_longitude', type=float)
        if lat is not None and lng is not None:
            db.execute("UPDATE places SET latitude=?,longitude=?,location_updated_at=?,location_updated_by=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (lat, lng, _loc_now, _loc_username, place_id))
        for kp in d['kps']:
            klat = f.get(f'kp_{kp["id"]}_latitude', type=float); klng = f.get(f'kp_{kp["id"]}_longitude', type=float)
            if klat is not None and klng is not None:
                db.execute("UPDATE key_places SET latitude=?,longitude=?,location_updated_at=?,location_updated_by=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (klat, klng, _loc_now, _loc_username, kp['id']))
        for ks in d['kss']:
            klat = f.get(f'ks_{ks["id"]}_latitude', type=float); klng = f.get(f'ks_{ks["id"]}_longitude', type=float)
            if klat is not None and klng is not None:
                db.execute("UPDATE key_spots SET latitude=?,longitude=?,location_updated_at=?,location_updated_by=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (klat, klng, _loc_now, _loc_username, ks['id']))
        for ss in d['sss']:
            slat = f.get(f'ss_{ss["id"]}_latitude', type=float); slng = f.get(f'ss_{ss["id"]}_longitude', type=float)
            if slat is not None and slng is not None:
                db.execute("UPDATE sub_spots SET latitude=?,longitude=?,location_updated_at=?,location_updated_by=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (slat, slng, _loc_now, _loc_username, ss['id']))
        db.commit()
        log_action(session.get('user_id'), 'location_update', 'place', place_id, place['title'])
        flash('Locations updated successfully!', 'success')
        return redirect(url_for('admin_place_location', place_id=place_id))
    return render_template('admin/place_location.html', d=d)

# ─── Key Spots (Tier 3) Admin ───
@app.route('/admin/key-place/<int:kp_id>/spots')
@login_required
def admin_key_place_spots(kp_id):
    db=get_db()
    kp=db.execute("SELECT kp.*,p.title as dham_title,p.slug as dham_slug,p.id as dham_id FROM key_places kp JOIN places p ON kp.parent_place_id=p.id WHERE kp.id=?",(kp_id,)).fetchone()
    if not kp: abort(404)
    spots=db.execute("SELECT ks.*,sc.name as cat_name,sc.icon as cat_icon,sc.color as cat_color FROM key_spots ks LEFT JOIN spot_categories sc ON ks.category_id=sc.id WHERE ks.key_place_id=? ORDER BY ks.sort_order",(kp_id,)).fetchall()
    cfs=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 AND applies_to IN ('both','key_place','key_spot') ORDER BY sort_order").fetchall()
    ks_customs={}
    for s in spots:
        ks_customs[s['id']]={r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible'],'description':r['description'] or ''} for r in db.execute("SELECT field_def_id,value,is_visible,description FROM key_spot_custom_values WHERE key_spot_id=?",(s['id'],)).fetchall()}
    return render_template('admin/key_spots.html',kp=kp,spots=spots,spot_categories=db.execute("SELECT * FROM spot_categories ORDER BY name").fetchall(),custom_fields=cfs,ks_customs=ks_customs,field_icons=FIELD_ICONS)

@app.route('/admin/key-place/<int:kp_id>/spots/save', methods=['POST'])
@login_required
def admin_key_spots_save(kp_id):
    db=get_db(); f=request.form
    cfs=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 ORDER BY sort_order").fetchall()
    existing=[r['id'] for r in db.execute("SELECT id FROM key_spots WHERE key_place_id=?",(kp_id,)).fetchall()]
    # Get dham_code for hierarchy ID
    _kp_row=db.execute("SELECT kp.parent_place_id,p.dham_code FROM key_places kp JOIN places p ON kp.parent_place_id=p.id WHERE kp.id=?",(kp_id,)).fetchone()
    _dham_code=_kp_row['dham_code'] if _kp_row else None
    _loc_user=get_current_user(); _loc_username=_loc_user['display_name'] if _loc_user else 'Unknown'
    _loc_now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
        fi_desc=f.get(f'ks_{i}_featured_image_desc','').strip()
        vis=1 if f.get(f'ks_{i}_is_visible') else 0
        img=f.get(f'ks_{i}_featured_image_existing','')
        orig_img=img
        fk=f'ks_{i}_featured_image_file'
        if fk in request.files:
            uf=request.files[fk]
            if uf and uf.filename: u=save_upload(uf,'images'); img=u if u else img
        # Camera capture fallback for T3 featured image (mobile)
        cam_fk=f'ks_{i}_featured_cam'
        if img==orig_img and cam_fk in request.files:
            uf=request.files[cam_fk]
            if uf and uf.filename: u=save_upload(uf,'images'); img=u if u else img
        # Gallery images
        gallery=f.get(f'ks_{i}_gallery_existing','')
        # Handle old-style multi-file upload (backward compat)
        gk=f'ks_{i}_gallery_files'
        if gk in request.files:
            new_imgs=[]
            for gf in request.files.getlist(gk):
                if gf and gf.filename: u=save_upload(gf,'images'); new_imgs.append(u) if u else None
            if new_imgs:
                existing_imgs=[x for x in gallery.split(',') if x.strip()] if gallery else []
                gallery=','.join(existing_imgs+new_imgs)
        # Handle new individual gallery uploads
        new_upload_captions = {}
        idx=0
        while True:
            nk=f'ks_{i}_new_gallery_{idx}'
            if nk not in request.files: break
            uf=request.files[nk]
            if uf and uf.filename:
                u=save_upload(uf,'images')
                if u:
                    existing_imgs=[x for x in gallery.split(',') if x.strip()] if gallery else []
                    existing_imgs.append(u); gallery=','.join(existing_imgs)
                    # Capture caption for this new upload
                    nc=f.get(f'ks_{i}_new_caption_{idx}','').strip()
                    if nc: new_upload_captions[u]=nc
            idx+=1
        # Gather captions
        captions={}
        captions.update(new_upload_captions)
        for key in f:
            if key.startswith(f'ks_{i}_caption_'):
                img_path=key[len(f'ks_{i}_caption_'):]
                cap_val=f[key].strip()
                if cap_val: captions[img_path]=cap_val
        captions_json=json.dumps(captions)
        if sid and sid in existing:
            db.execute("UPDATE key_spots SET category_id=?,title=?,slug=?,short_description=?,full_content=?,featured_image=?,featured_image_desc=?,gallery_images=?,gallery_captions=?,state=?,city=?,country=?,latitude=?,longitude=?,sort_order=?,is_visible=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (catid,t,slug,sd,fc,img,fi_desc,gallery,captions_json,state,city,country,lat,lng,i,vis,sid)); submitted.append(sid)
            if lat is not None and lng is not None:
                db.execute("UPDATE key_spots SET location_updated_at=?,location_updated_by=? WHERE id=?",(_loc_now,_loc_username,sid))
        else:
            ks_hid=_gen_t3_id(_dham_code,db,kp_id) if _dham_code else None
            db.execute("INSERT INTO key_spots (key_place_id,category_id,title,slug,short_description,full_content,featured_image,featured_image_desc,gallery_images,gallery_captions,state,city,country,latitude,longitude,sort_order,is_visible,hierarchy_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (kp_id,catid,t,slug,sd,fc,img,fi_desc,gallery,captions_json,state,city,country,lat,lng,i,vis,ks_hid))
            sid=db.execute("SELECT last_insert_rowid()").fetchone()[0]; submitted.append(sid)
            if lat is not None and lng is not None:
                db.execute("UPDATE key_spots SET location_updated_at=?,location_updated_by=? WHERE id=?",(_loc_now,_loc_username,sid))
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
            cfdesc=f.get(f"ks_{i}_cf_desc_{cf['id']}",'')
            if cv or cfvis: db.execute("INSERT OR REPLACE INTO key_spot_custom_values (key_spot_id,field_def_id,value,is_visible,description) VALUES (?,?,?,?,?)",(sid,cf['id'],cv,cfvis,cfdesc))
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
    cfs=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 AND applies_to IN ('both','key_place','sub_spot') ORDER BY sort_order").fetchall()
    ss_customs={}
    for s in subs:
        ss_customs[s['id']]={r['field_def_id']:{'value':r['value'],'is_visible':r['is_visible'],'description':r['description'] or ''} for r in db.execute("SELECT field_def_id,value,is_visible,description FROM sub_spot_custom_values WHERE sub_spot_id=?",(s['id'],)).fetchall()}
    return render_template('admin/sub_spots.html',ks=ks,subs=subs,sub_spot_categories=db.execute("SELECT * FROM sub_spot_categories ORDER BY name").fetchall(),custom_fields=cfs,ss_customs=ss_customs,field_icons=FIELD_ICONS)

@app.route('/admin/key-spot/<int:ks_id>/subs/save', methods=['POST'])
@login_required
def admin_sub_spots_save(ks_id):
    db=get_db(); f=request.form
    cfs=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 ORDER BY sort_order").fetchall()
    existing=[r['id'] for r in db.execute("SELECT id FROM sub_spots WHERE key_spot_id=?",(ks_id,)).fetchall()]
    # Get dham_code for hierarchy ID
    _ks_row=db.execute("SELECT p.dham_code FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id WHERE ks.id=?",(ks_id,)).fetchone()
    _dham_code=_ks_row['dham_code'] if _ks_row else None
    _loc_user=get_current_user(); _loc_username=_loc_user['display_name'] if _loc_user else 'Unknown'
    _loc_now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
        fi_desc=f.get(f'ss_{i}_featured_image_desc','').strip()
        vis=1 if f.get(f'ss_{i}_is_visible') else 0
        img=f.get(f'ss_{i}_featured_image_existing','')
        orig_img=img
        fk=f'ss_{i}_featured_image_file'
        if fk in request.files:
            uf=request.files[fk]
            if uf and uf.filename: u=save_upload(uf,'images'); img=u if u else img
        # Camera capture fallback for T4 featured image (mobile)
        cam_fk=f'ss_{i}_featured_cam'
        if img==orig_img and cam_fk in request.files:
            uf=request.files[cam_fk]
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
        # Handle new individual gallery uploads
        new_upload_captions = {}
        idx=0
        while True:
            nk=f'ss_{i}_new_gallery_{idx}'
            if nk not in request.files: break
            uf=request.files[nk]
            if uf and uf.filename:
                u=save_upload(uf,'images')
                if u:
                    existing_imgs=[x for x in gallery.split(',') if x.strip()] if gallery else []
                    existing_imgs.append(u); gallery=','.join(existing_imgs)
                    nc=f.get(f'ss_{i}_new_caption_{idx}','').strip()
                    if nc: new_upload_captions[u]=nc
            idx+=1
        # Gather captions
        captions={}
        captions.update(new_upload_captions)
        for key in f:
            if key.startswith(f'ss_{i}_caption_'):
                img_path=key[len(f'ss_{i}_caption_'):]
                cap_val=f[key].strip()
                if cap_val: captions[img_path]=cap_val
        captions_json=json.dumps(captions)
        if sid and sid in existing:
            db.execute("UPDATE sub_spots SET category_id=?,title=?,slug=?,short_description=?,full_content=?,featured_image=?,featured_image_desc=?,gallery_images=?,gallery_captions=?,state=?,city=?,country=?,latitude=?,longitude=?,sort_order=?,is_visible=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (catid,t,slug,sd,fc,img,fi_desc,gallery,captions_json,state,city,country,lat,lng,i,vis,sid)); submitted.append(sid)
            if lat is not None and lng is not None:
                db.execute("UPDATE sub_spots SET location_updated_at=?,location_updated_by=? WHERE id=?",(_loc_now,_loc_username,sid))
        else:
            ss_hid=_gen_t4_id(_dham_code,db,ks_id) if _dham_code else None
            db.execute("INSERT INTO sub_spots (key_spot_id,category_id,title,slug,short_description,full_content,featured_image,featured_image_desc,gallery_images,gallery_captions,state,city,country,latitude,longitude,sort_order,is_visible,hierarchy_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ks_id,catid,t,slug,sd,fc,img,fi_desc,gallery,captions_json,state,city,country,lat,lng,i,vis,ss_hid))
            sid=db.execute("SELECT last_insert_rowid()").fetchone()[0]; submitted.append(sid)
            if lat is not None and lng is not None:
                db.execute("UPDATE sub_spots SET location_updated_at=?,location_updated_by=? WHERE id=?",(_loc_now,_loc_username,sid))
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
            cfdesc=f.get(f"ss_{i}_cf_desc_{cf['id']}",'')
            if cv or cfvis: db.execute("INSERT OR REPLACE INTO sub_spot_custom_values (sub_spot_id,field_def_id,value,is_visible,description) VALUES (?,?,?,?,?)",(sid,cf['id'],cv,cfvis,cfdesc))
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
    db=get_db(); params=[]; where_clauses=[]
    if mod_id: where_clauses.append("me.module_id=?"); params.append(mod_id)
    status_filter=request.args.get('status','')
    if status_filter: where_clauses.append("me.status=?"); params.append(status_filter)
    search_q=request.args.get('q','').strip()
    if search_q: where_clauses.append("me.title LIKE ?"); params.append(f'%{search_q}%')
    dham_filter=request.args.get('dham','',type=int)
    if dham_filter: where_clauses.append("me.tier_link_id=? AND me.tier_link_type='dham'"); params.append(dham_filter)
    q="SELECT me.*,m.name as module_name,m.icon as module_icon,m.slug as module_slug,p.title as place_title FROM module_entries me JOIN modules m ON me.module_id=m.id LEFT JOIN places p ON me.place_id=p.id"
    if where_clauses: q+=" WHERE "+" AND ".join(where_clauses)
    q+=" ORDER BY me.updated_at DESC"
    entries=db.execute(q,params).fetchall()
    modules=db.execute("SELECT * FROM modules ORDER BY sort_order").fetchall()
    dhams=db.execute("SELECT id,title FROM places ORDER BY title").fetchall()
    return render_template('admin/entries.html',entries=entries,modules=modules,current_mod=mod_id,dhams=dhams,status_filter=status_filter,search_q=search_q,dham_filter=dham_filter)

@app.route('/admin/entries/new', methods=['GET','POST'])
@login_required
def admin_entry_new():
    db=get_db()
    if request.method=='POST':
        f=request.form; t=f['title']; s=slugify(t); mid=f['module_id']
        if db.execute("SELECT id FROM module_entries WHERE slug=? AND module_id=?",(s,mid)).fetchone(): s+='-'+uuid.uuid4().hex[:4]
        # Build custom_fields JSON from module schema
        module=db.execute("SELECT * FROM modules WHERE id=?",(mid,)).fetchone()
        schema=json.loads(module['fields_schema'] or '[]') if module else []
        cf={}
        for field in schema:
            fname=field['name']; ftype=field.get('type','text')
            if ftype=='richtext':
                cf[fname]=f.get(f'cf_{fname}','')
            elif ftype=='image':
                # Handle image upload for schema fields
                if f'cf_{fname}_file' in request.files:
                    uf=request.files[f'cf_{fname}_file']
                    if uf and uf.filename: u=save_upload(uf,'images'); cf[fname]=u if u else ''
                    else: cf[fname]=''
                else: cf[fname]=''
            else:
                cf[fname]=f.get(f'cf_{fname}','')
        # Handle featured image
        fi=''
        if 'featured_image_file' in request.files:
            uf=request.files['featured_image_file']
            if uf and uf.filename: u=save_upload(uf,'images'); fi=u if u else fi
        if not fi and 'featured_image_cam' in request.files:
            uf=request.files['featured_image_cam']
            if uf and uf.filename: u=save_upload(uf,'images'); fi=u if u else fi
        # Handle gallery images
        gi_paths=[]
        idx=0
        while True:
            nk=f'entry_new_gallery_{idx}'
            if nk not in request.files: break
            gf=request.files[nk]
            if gf and gf.filename: rp=save_upload(gf,'images'); gi_paths.append(rp) if rp else None
            idx+=1
        if 'gallery_files' in request.files:
            for gf in request.files.getlist('gallery_files'):
                if gf and gf.filename: rp=save_upload(gf,'images'); gi_paths.append(rp) if rp else None
        gi_str=','.join(gi_paths)
        # Tier linking
        tier_link_type=f.get('tier_link_type','')
        tier_link_id=f.get('tier_link_id',0,type=int)
        db.execute("INSERT INTO module_entries (module_id,place_id,title,slug,content,custom_fields,featured_image,gallery_images,status,sort_order,tier_link_type,tier_link_id,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (mid,f.get('place_id',type=int) or None,t,s,f.get('content',''),json.dumps(cf),fi,gi_str,f.get('status','draft'),f.get('sort_order',0,type=int),tier_link_type,tier_link_id,session['user_id']))
        db.commit()
        entry_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]
        # Handle audio/video items
        _save_entry_audio_video(db, entry_id, request)
        db.commit()
        flash('Created!','success'); return redirect(url_for('admin_entries'))
    modules=db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall()
    places=db.execute("SELECT id,title FROM places ORDER BY title").fetchall()
    key_places=db.execute("SELECT kp.id,kp.title,p.title as dham_title FROM key_places kp JOIN places p ON kp.parent_place_id=p.id ORDER BY p.title,kp.title").fetchall()
    key_spots=db.execute("SELECT ks.id,ks.title,kp.title as kp_title FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id ORDER BY kp.title,ks.title").fetchall()
    sub_spots=db.execute("SELECT ss.id,ss.title,ks.title as ks_title FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id ORDER BY ks.title,ss.title").fetchall()
    preselect_mod=request.args.get('module_id',type=int)
    return render_template('admin/entry_form.html',entry=None,modules=modules,places=places,key_places=key_places,key_spots=key_spots,sub_spots=sub_spots,editing=False,module_schemas=MODULE_SCHEMAS,audio_video_items=[],preselect_mod=preselect_mod)

@app.route('/admin/entries/<int:entry_id>/edit', methods=['GET','POST'])
@login_required
def admin_entry_edit(entry_id):
    db=get_db(); entry=db.execute("SELECT * FROM module_entries WHERE id=?",(entry_id,)).fetchone()
    if not entry: abort(404)
    if request.method=='POST':
        f=request.form
        # Build custom_fields JSON from module schema
        module=db.execute("SELECT * FROM modules WHERE id=?",(f['module_id'],)).fetchone()
        schema=json.loads(module['fields_schema'] or '[]') if module else []
        # Start with existing custom fields to preserve any that aren't in schema
        try: cf=json.loads(entry['custom_fields'] or '{}')
        except: cf={}
        for field in schema:
            fname=field['name']; ftype=field.get('type','text')
            if ftype=='richtext':
                cf[fname]=f.get(f'cf_{fname}','')
            elif ftype=='image':
                existing_val=cf.get(fname,'')
                if f'cf_{fname}_file' in request.files:
                    uf=request.files[f'cf_{fname}_file']
                    if uf and uf.filename: u=save_upload(uf,'images'); cf[fname]=u if u else existing_val
                    else: cf[fname]=f.get(f'cf_{fname}_existing',existing_val)
                else: cf[fname]=f.get(f'cf_{fname}_existing',existing_val)
            else:
                cf[fname]=f.get(f'cf_{fname}','')
        # Handle featured image
        fi=f.get('featured_image_existing','').strip()
        orig_fi=fi
        if 'featured_image_file' in request.files:
            uf=request.files['featured_image_file']
            if uf and uf.filename: u=save_upload(uf,'images'); fi=u if u else fi
        if fi==orig_fi and 'featured_image_cam' in request.files:
            uf=request.files['featured_image_cam']
            if uf and uf.filename: u=save_upload(uf,'images'); fi=u if u else fi
        # Handle gallery images
        existing_gi=f.get('gallery_existing','').strip()
        gi_list=[x.strip() for x in existing_gi.split(',') if x.strip()] if existing_gi else []
        idx=0
        while True:
            nk=f'entry_new_gallery_{idx}'
            if nk not in request.files: break
            gf=request.files[nk]
            if gf and gf.filename: rp=save_upload(gf,'images'); gi_list.append(rp) if rp else None
            idx+=1
        if 'gallery_files' in request.files:
            for gf in request.files.getlist('gallery_files'):
                if gf and gf.filename: rp=save_upload(gf,'images'); gi_list.append(rp) if rp else None
        gi_str=','.join(gi_list)
        # Tier linking
        tier_link_type=f.get('tier_link_type','')
        tier_link_id=f.get('tier_link_id',0,type=int)
        db.execute("UPDATE module_entries SET module_id=?,place_id=?,title=?,content=?,custom_fields=?,featured_image=?,gallery_images=?,status=?,sort_order=?,tier_link_type=?,tier_link_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (f['module_id'],f.get('place_id',type=int) or None,f['title'],f.get('content',''),json.dumps(cf),fi,gi_str,f.get('status','draft'),f.get('sort_order',0,type=int),tier_link_type,tier_link_id,entry_id))
        # Handle audio/video: delete removed, add new
        db.execute("DELETE FROM entry_audio_video WHERE entry_id=?",(entry_id,))
        _save_entry_audio_video(db, entry_id, request)
        db.commit(); flash('Updated!','success'); return redirect(url_for('admin_entries'))
    modules=db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall()
    places=db.execute("SELECT id,title FROM places ORDER BY title").fetchall()
    key_places=db.execute("SELECT kp.id,kp.title,p.title as dham_title FROM key_places kp JOIN places p ON kp.parent_place_id=p.id ORDER BY p.title,kp.title").fetchall()
    key_spots=db.execute("SELECT ks.id,ks.title,kp.title as kp_title FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id ORDER BY kp.title,ks.title").fetchall()
    sub_spots=db.execute("SELECT ss.id,ss.title,ks.title as ks_title FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id ORDER BY ks.title,ss.title").fetchall()
    audio_video_items=db.execute("SELECT * FROM entry_audio_video WHERE entry_id=? ORDER BY sort_order",(entry_id,)).fetchall()
    return render_template('admin/entry_form.html',entry=entry,modules=modules,places=places,key_places=key_places,key_spots=key_spots,sub_spots=sub_spots,editing=True,module_schemas=MODULE_SCHEMAS,audio_video_items=audio_video_items,preselect_mod=None)

def _save_entry_audio_video(db, entry_id, req):
    """Save audio/video items from entry form."""
    idx=0
    while True:
        mt=req.form.get(f'av_type_{idx}')
        if mt is None: break
        src_type=req.form.get(f'av_source_{idx}','upload')
        desc=req.form.get(f'av_desc_{idx}','')
        ext_url=req.form.get(f'av_url_{idx}','')
        fp=''
        if src_type=='upload' and f'av_file_{idx}' in req.files:
            uf=req.files[f'av_file_{idx}']
            if uf and uf.filename:
                allowed=ALLOWED_AUDIO_EXT if mt=='audio' else ALLOWED_VIDEO_EXT
                ext=uf.filename.rsplit('.',1)[-1].lower() if '.' in uf.filename else ''
                if ext in allowed: fp=save_upload(uf,'audio' if mt=='audio' else 'videos')
        # Keep existing file path if re-saving
        if not fp: fp=req.form.get(f'av_existing_{idx}','')
        if fp or ext_url:
            db.execute("INSERT INTO entry_audio_video (entry_id,media_type,source_type,file_path,external_url,description,sort_order) VALUES (?,?,?,?,?,?,?)",
                (entry_id,mt,src_type,fp or '',ext_url or '',desc,idx))

@app.route('/admin/entries/<int:entry_id>/delete', methods=['POST'])
@login_required
def admin_entry_delete(entry_id): get_db().execute("DELETE FROM module_entries WHERE id=?",(entry_id,)); get_db().commit(); flash('Deleted.','info'); return redirect(url_for('admin_entries'))

# ─── Audio/Video Management (Multi-item per place) ───
@app.route('/admin/audio-video/add', methods=['POST'])
@login_required
def admin_av_add():
    db = get_db()
    f = request.form
    tier = f.get('tier','T1')
    place_ref_id = f.get('place_ref_id', type=int)
    media_type = f.get('media_type','audio')
    description = f.get('description','').strip()
    source_type = 'upload'
    file_path = ''
    external_url = f.get('external_url','').strip()
    if external_url:
        source_type = 'url'
    elif f'av_file' in request.files:
        uf = request.files['av_file']
        if uf and uf.filename:
            rp = save_upload(uf, 'audio' if media_type == 'audio' else 'video')
            if rp: file_path = rp
    if not file_path and not external_url:
        flash('Please upload a file or provide a URL.','error')
        return redirect(request.referrer or url_for('admin_places'))
    max_sort = db.execute("SELECT COALESCE(MAX(sort_order),0) FROM place_audio_video WHERE tier=? AND place_ref_id=?", (tier, place_ref_id)).fetchone()[0]
    db.execute("INSERT INTO place_audio_video (tier,place_ref_id,media_type,source_type,file_path,external_url,description,sort_order) VALUES (?,?,?,?,?,?,?,?)",
        (tier, place_ref_id, media_type, source_type, file_path, external_url, description, max_sort + 1))
    db.commit()
    flash(f'{media_type.title()} added!','success')
    return redirect(request.referrer or url_for('admin_places'))

@app.route('/admin/audio-video/<int:av_id>/delete', methods=['POST'])
@login_required
def admin_av_delete(av_id):
    db = get_db()
    db.execute("DELETE FROM place_audio_video WHERE id=?", (av_id,))
    db.commit()
    flash('Deleted.','info')
    return redirect(request.referrer or url_for('admin_places'))

@app.route('/admin/api/audio-video/<tier>/<int:ref_id>')
@login_required
def admin_av_list(tier, ref_id):
    """API: Get audio/video items for a place."""
    db = get_db()
    items = db.execute("SELECT * FROM place_audio_video WHERE tier=? AND place_ref_id=? ORDER BY sort_order", (tier, ref_id)).fetchall()
    return json.dumps([dict(r) for r in items]), 200, {'Content-Type': 'application/json'}

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
            db.execute("INSERT INTO users (username,email,password_hash,display_name,role,permissions,receive_reports,created_by) VALUES (?,?,?,?,?,?,?,?)",
                (request.form['username'],request.form['email'],hash_password(request.form['password']),request.form.get('display_name',request.form['username']),request.form.get('role','editor'),json.dumps({k:True for k in request.form.getlist('permissions')}),1 if request.form.get('receive_reports') else 0,session['user_id']))
            db.commit(); flash('Created!','success'); return redirect(url_for('admin_users'))
    return render_template('admin/user_form.html',user=None,perm_defs=db.execute("SELECT * FROM permission_definitions ORDER BY category,label").fetchall(),editing=False)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET','POST'])
@login_required
@role_required('super_admin')
def admin_user_edit(user_id):
    db=get_db(); user=db.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
    if not user: abort(404)
    if request.method=='POST':
        u={'email':request.form['email'],'display_name':request.form.get('display_name',user['username']),'role':request.form.get('role','editor'),'permissions':json.dumps({k:True for k in request.form.getlist('permissions')}),'is_active':1 if request.form.get('is_active') else 0,'receive_reports':1 if request.form.get('receive_reports') else 0}
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
    spot_categories=db.execute("SELECT sc.*,(SELECT COUNT(*) FROM key_spots WHERE category_id=sc.id) as spot_count FROM spot_categories sc ORDER BY sc.name").fetchall()
    sub_spot_categories=db.execute("SELECT ssc.*,(SELECT COUNT(*) FROM sub_spots WHERE category_id=ssc.id) as point_count FROM sub_spot_categories ssc ORDER BY ssc.name").fetchall()
    return render_template('admin/tags.html',tags=db.execute("SELECT t.*,COUNT(pt.place_id) as place_count FROM tags t LEFT JOIN place_tags pt ON t.id=pt.tag_id GROUP BY t.id ORDER BY t.name").fetchall(),spot_categories=spot_categories,sub_spot_categories=sub_spot_categories)

@app.route('/admin/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def admin_tag_delete(tag_id): get_db().execute("DELETE FROM tags WHERE id=?",(tag_id,)); get_db().commit(); flash('Deleted.','info'); return redirect(url_for('admin_tags'))

# ─── T3 Spot Category CRUD ───
@app.route('/admin/spot-category/new', methods=['POST'])
@login_required
def admin_spot_category_new():
    db=get_db(); f=request.form
    try:
        db.execute("INSERT INTO spot_categories (slug,name,description,icon,color) VALUES (?,?,?,?,?)",(slugify(f['name']),f['name'],f.get('description',''),f.get('icon','📍'),f.get('color','#666')))
        db.commit(); flash('T3 category created!','success')
    except sqlite3.IntegrityError: flash('Category already exists.','error')
    return redirect(url_for('admin_tags'))

@app.route('/admin/spot-category/<int:cat_id>/update', methods=['POST'])
@login_required
def admin_spot_category_update(cat_id):
    db=get_db(); f=request.form
    db.execute("UPDATE spot_categories SET name=?,slug=?,description=?,icon=?,color=? WHERE id=?",(f['name'],slugify(f['name']),f.get('description',''),f.get('icon','📍'),f.get('color','#666'),cat_id))
    db.commit(); flash('T3 category updated!','success')
    return redirect(url_for('admin_tags'))

@app.route('/admin/spot-category/<int:cat_id>/delete', methods=['POST'])
@login_required
def admin_spot_category_delete(cat_id):
    db=get_db()
    db.execute("UPDATE key_spots SET category_id=NULL WHERE category_id=?",(cat_id,))
    db.execute("DELETE FROM spot_categories WHERE id=?",(cat_id,))
    db.commit(); flash('T3 category deleted.','info')
    return redirect(url_for('admin_tags'))

# ─── T4 Sub-Spot Category CRUD ───
@app.route('/admin/sub-category/new', methods=['POST'])
@login_required
def admin_sub_category_new():
    db=get_db(); f=request.form
    try:
        db.execute("INSERT INTO sub_spot_categories (slug,name,description,icon,color) VALUES (?,?,?,?,?)",(slugify(f['name']),f['name'],f.get('description',''),f.get('icon','📍'),f.get('color','#666')))
        db.commit(); flash('T4 category created!','success')
    except sqlite3.IntegrityError: flash('Category already exists.','error')
    return redirect(url_for('admin_tags'))

@app.route('/admin/sub-category/<int:cat_id>/update', methods=['POST'])
@login_required
def admin_sub_category_update(cat_id):
    db=get_db(); f=request.form
    db.execute("UPDATE sub_spot_categories SET name=?,slug=?,description=?,icon=?,color=? WHERE id=?",(f['name'],slugify(f['name']),f.get('description',''),f.get('icon','📍'),f.get('color','#666'),cat_id))
    db.commit(); flash('T4 category updated!','success')
    return redirect(url_for('admin_tags'))

@app.route('/admin/sub-category/<int:cat_id>/delete', methods=['POST'])
@login_required
def admin_sub_category_delete(cat_id):
    db=get_db()
    db.execute("UPDATE sub_spots SET category_id=NULL WHERE category_id=?",(cat_id,))
    db.execute("DELETE FROM sub_spot_categories WHERE id=?",(cat_id,))
    db.commit(); flash('T4 category deleted.','info')
    return redirect(url_for('admin_tags'))

# ─── Admin Help Guide ───
@app.route('/admin/help')
@login_required
def admin_help():
    return render_template('admin/help_guide.html')

# ─── Gallery Image Delete API ───
@app.route('/admin/api/delete-gallery-image', methods=['POST'])
@login_required
def admin_delete_gallery_image():
    import json as json_mod
    data = request.get_json()
    tier = data.get('tier')
    parent_id = data.get('parent_id')
    image = data.get('image','').strip()
    if not tier or not parent_id or not image:
        return jsonify({'ok':False,'error':'Missing parameters'})
    db = get_db()
    table_map = {'t1':'places','t2':'key_places','t3':'key_spots','t4':'sub_spots'}
    table = table_map.get(tier)
    col = 'gallery_images' if tier != 't1' else None
    if not table:
        return jsonify({'ok':False,'error':'Invalid tier'})
    try:
        if tier == 't1':
            # T1 uses place_media table
            media = db.execute("SELECT m.id FROM media m JOIN place_media pm ON m.id=pm.media_id WHERE pm.place_id=? AND m.filename=?",(parent_id,image)).fetchone()
            if media:
                db.execute("DELETE FROM place_media WHERE media_id=?",(media['id'],))
                db.execute("DELETE FROM media WHERE id=?",(media['id'],))
            # Also clear featured_image if it matches
            db.execute(f"UPDATE {table} SET featured_image=NULL WHERE id=? AND featured_image=?",(parent_id,image))
        else:
            row = db.execute(f"SELECT gallery_images FROM {table} WHERE id=?",(parent_id,)).fetchone()
            if row and row['gallery_images']:
                imgs = [x.strip() for x in row['gallery_images'].split(',') if x.strip() and x.strip() != image]
                db.execute(f"UPDATE {table} SET gallery_images=? WHERE id=?",((','.join(imgs) if imgs else None),parent_id))
            # Also clear featured_image if it matches
            db.execute(f"UPDATE {table} SET featured_image=NULL WHERE id=? AND featured_image=?",(parent_id,image))
        db.commit()
        # Delete file from disk
        import os as os_mod
        fp = os_mod.path.join(app.config['UPLOAD_FOLDER'], image)
        if os_mod.path.exists(fp): os_mod.remove(fp)
        return jsonify({'ok':True})
    except Exception as e:
        return jsonify({'ok':False,'error':str(e)})

@app.route('/admin/api/hierarchy-search')
@login_required
def admin_hierarchy_search():
    """Live search across all 4 tiers by name or hierarchy_id."""
    q=request.args.get('q','').strip()
    if not q or len(q)<1: return jsonify([])
    db=get_db(); like=f'%{q}%'; results=[]
    # T1: Holy Dhams
    for r in db.execute("SELECT id,title,hierarchy_id,dham_code,city,state,slug FROM places WHERE (title LIKE ? OR hierarchy_id LIKE ? OR dham_code LIKE ? OR city LIKE ? OR state LIKE ?) ORDER BY title LIMIT 10",(like,like,like,like,like)).fetchall():
        # Count children
        kp_count=db.execute("SELECT COUNT(*) FROM key_places WHERE parent_place_id=?",(r['id'],)).fetchone()[0]
        results.append({'tier':'T1','tier_label':'Holy Dham','icon':'🏛️','color':'#C76B8F','title':r['title'],'hid':r['hierarchy_id'] or '','code':r['dham_code'] or '','location':f"{r['city'] or ''}{', ' if r['city'] and r['state'] else ''}{r['state'] or ''}",'children':f"{kp_count} Key Places",'url':f"/admin/places/{r['id']}/edit"})
    # T2: Key Places
    for r in db.execute("SELECT kp.id,kp.title,kp.hierarchy_id,kp.parent_place_id,p.title as dham_title,p.dham_code,p.hierarchy_id as dham_hid FROM key_places kp JOIN places p ON kp.parent_place_id=p.id WHERE (kp.title LIKE ? OR kp.hierarchy_id LIKE ?) ORDER BY kp.title LIMIT 10",(like,like)).fetchall():
        ks_count=db.execute("SELECT COUNT(*) FROM key_spots WHERE key_place_id=?",(r['id'],)).fetchone()[0]
        results.append({'tier':'T2','tier_label':'Key Place','icon':'📍','color':'#2E86AB','title':r['title'],'hid':r['hierarchy_id'] or '','parent':r['dham_title'],'parent_hid':r['dham_hid'] or '','children':f"{ks_count} Key Spots",'url':f"/admin/places/{r['parent_place_id']}/edit"})
    # T3: Key Spots
    for r in db.execute("SELECT ks.id,ks.title,ks.hierarchy_id,ks.key_place_id,kp.title as kp_title,kp.hierarchy_id as kp_hid,kp.parent_place_id,p.title as dham_title,p.dham_code,p.hierarchy_id as dham_hid FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id WHERE (ks.title LIKE ? OR ks.hierarchy_id LIKE ?) ORDER BY ks.title LIMIT 10",(like,like)).fetchall():
        ss_count=db.execute("SELECT COUNT(*) FROM sub_spots WHERE key_spot_id=?",(r['id'],)).fetchone()[0]
        results.append({'tier':'T3','tier_label':'Key Spot','icon':'🎯','color':'#E74845','title':r['title'],'hid':r['hierarchy_id'] or '','parent':r['kp_title'],'parent_hid':r['kp_hid'] or '','grandparent':r['dham_title'],'grandparent_hid':r['dham_hid'] or '','children':f"{ss_count} Key Points",'url':f"/admin/key-place/{r['key_place_id']}/spots"})
    # T4: Key Points
    for r in db.execute("SELECT ss.id,ss.title,ss.hierarchy_id,ss.key_spot_id,ks.title as ks_title,ks.hierarchy_id as ks_hid,ks.key_place_id,kp.title as kp_title,kp.hierarchy_id as kp_hid,kp.parent_place_id,p.title as dham_title,p.hierarchy_id as dham_hid FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id WHERE (ss.title LIKE ? OR ss.hierarchy_id LIKE ?) ORDER BY ss.title LIMIT 10",(like,like)).fetchall():
        results.append({'tier':'T4','tier_label':'Key Point','icon':'✦','color':'#9C27B0','title':r['title'],'hid':r['hierarchy_id'] or '','parent':r['ks_title'],'parent_hid':r['ks_hid'] or '','grandparent':r['kp_title'],'grandparent_hid':r['kp_hid'] or '','great_grandparent':r['dham_title'],'great_grandparent_hid':r['dham_hid'] or '','children':'','url':f"/admin/key-spot/{r['key_spot_id']}/sub-spots"})
    return jsonify(results[:25])

# ─── Report Error / Feedback (Frontend) ───
@app.route('/report-error', methods=['POST'])
def report_error():
    f = request.form
    name = f.get('report_name','').strip()
    email = f.get('report_email','').strip()
    msg = f.get('report_message','').strip()
    rtype = f.get('report_type','error')
    page_url = f.get('page_url','')
    tier_info = f.get('tier_info','')
    captcha_a = f.get('captcha_answer','').strip()
    captcha_e = f.get('captcha_expected','').strip()
    errors = []
    if not name: errors.append('Name is required')
    if not email or not re.match(r'^[\w.+-]+@[\w-]+\.[\w.-]+$', email): errors.append('Valid email is required')
    if not msg: errors.append('Message is required')
    if captcha_a != captcha_e: errors.append('Captcha answer is incorrect')
    if errors:
        return jsonify({'ok':False,'errors':errors})
    db = get_db()
    db.execute("INSERT INTO feedback_reports (report_type,name,email,message,page_url,tier_info,captcha_ok) VALUES (?,?,?,?,?,?,1)",
        (rtype,name,email,msg,page_url,tier_info))
    db.commit()
    # Try sending email
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        smtp_host = db.execute("SELECT value FROM site_settings WHERE key='smtp_host'").fetchone()
        smtp_port = db.execute("SELECT value FROM site_settings WHERE key='smtp_port'").fetchone()
        smtp_user = db.execute("SELECT value FROM site_settings WHERE key='smtp_user'").fetchone()
        smtp_pass = db.execute("SELECT value FROM site_settings WHERE key='smtp_pass'").fetchone()
        recipients_row = db.execute("SELECT value FROM site_settings WHERE key='report_emails'").fetchone()
        recipients = [e.strip() for e in (recipients_row['value'] if recipients_row else '').split(',') if e.strip()]
        # Also add users with receive_reports=1
        for u in db.execute("SELECT email FROM users WHERE receive_reports=1 AND is_active=1").fetchall():
            if u['email'] and u['email'] not in recipients: recipients.append(u['email'])
        if smtp_host and smtp_host['value'] and smtp_user and smtp_user['value'] and recipients:
            type_label = 'Error Reported' if rtype == 'error' else 'General Feedback'
            subject = f"Holy Place - Tier {type_label} Form submitted for review"
            body = f"<h2>🛕 {type_label}</h2><table border='1' cellpadding='8' style='border-collapse:collapse'>"
            body += f"<tr><td><b>Type</b></td><td>{'🔴 Error Report' if rtype=='error' else '💬 General Feedback'}</td></tr>"
            body += f"<tr><td><b>Name</b></td><td>{name}</td></tr>"
            body += f"<tr><td><b>Email</b></td><td>{email}</td></tr>"
            body += f"<tr><td><b>Tier Info</b></td><td>{tier_info}</td></tr>"
            body += f"<tr><td><b>Page URL</b></td><td><a href='{page_url}'>{page_url}</a></td></tr>"
            body += f"<tr><td><b>Message</b></td><td>{msg}</td></tr></table>"
            mime = MIMEMultipart('alternative')
            mime['Subject'] = subject
            mime['From'] = smtp_user['value']
            mime['To'] = ', '.join(recipients)
            mime.attach(MIMEText(body, 'html'))
            server = smtplib.SMTP(smtp_host['value'], int(smtp_port['value'] if smtp_port else '587'))
            server.starttls()
            server.login(smtp_user['value'], smtp_pass['value'] if smtp_pass else '')
            server.sendmail(smtp_user['value'], recipients, mime.as_string())
            server.quit()
    except Exception as e:
        print(f"Email send failed (report saved to DB): {e}")
    return jsonify({'ok':True,'message':'Thank you! Your report has been submitted.'})

# ─── Admin: View Reports ───
@app.route('/admin/reports')
@login_required
def admin_reports():
    db = get_db()
    reports = db.execute("SELECT * FROM feedback_reports ORDER BY created_at DESC LIMIT 100").fetchall()
    return render_template('admin/reports.html', reports=reports)

@app.route('/admin/reports/<int:rid>/status', methods=['POST'])
@login_required
def admin_report_status(rid):
    db = get_db()
    new_status = request.form.get('status','reviewed')
    db.execute("UPDATE feedback_reports SET status=? WHERE id=?",(new_status,rid))
    db.commit()
    flash(f'Report #{rid} marked as {new_status}','success')
    return redirect(url_for('admin_reports'))

@app.route('/admin/reports/<int:rid>/delete', methods=['POST'])
@login_required
def admin_report_delete(rid):
    get_db().execute("DELETE FROM feedback_reports WHERE id=?",(rid,)); get_db().commit()
    flash('Report deleted','info'); return redirect(url_for('admin_reports'))

# ─── Admin: Email Settings ───
@app.route('/admin/settings/emails', methods=['GET','POST'])
@login_required
def admin_email_settings():
    db = get_db()
    user = db.execute("SELECT role FROM users WHERE id=?",(session.get('user_id'),)).fetchone()
    if not user or user['role'] != 'super_admin':
        flash('Only Super Admins can access email settings','error')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        for key in ['report_emails','smtp_host','smtp_port','smtp_user','smtp_pass']:
            val = request.form.get(key,'')
            db.execute("INSERT INTO site_settings (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=?",(key,val,val))
        # Update receive_reports for users
        db.execute("UPDATE users SET receive_reports=0")
        for uid in request.form.getlist('receive_users'):
            db.execute("UPDATE users SET receive_reports=1 WHERE id=?",(uid,))
        db.commit()
        flash('Email settings saved!','success')
        return redirect(url_for('admin_email_settings'))
    settings = {r['key']:r['value'] for r in db.execute("SELECT key,value FROM site_settings").fetchall()}
    users = db.execute("SELECT id,username,email,display_name,role,receive_reports FROM users WHERE is_active=1 ORDER BY role DESC,username").fetchall()
    return render_template('admin/email_settings.html', settings=settings, users=users)

# ─── Admin: User management — super_admin check ───
@app.route('/admin/users/<int:uid>/update-role', methods=['POST'])
@login_required
def admin_user_update_role(uid):
    db = get_db()
    caller = db.execute("SELECT role FROM users WHERE id=?",(session.get('user_id'),)).fetchone()
    if not caller or caller['role'] != 'super_admin':
        flash('Only Super Admins can change roles','error')
        return redirect(url_for('admin_users'))
    new_role = request.form.get('role','editor')
    receive = 1 if request.form.get('receive_reports') else 0
    db.execute("UPDATE users SET role=?,receive_reports=? WHERE id=?",(new_role,receive,uid))
    db.commit()
    flash(f'User #{uid} updated','success')
    return redirect(url_for('admin_users'))

# ─── Admin: Site Pages — Section-Based Builder ───
SITE_PAGES = [
    {'key': 'about', 'title': 'About Us', 'icon': 'ℹ️', 'url_endpoint': 'about'},
    {'key': 'privacy', 'title': 'Privacy Policy', 'icon': '🔒', 'url_endpoint': 'privacy'},
    {'key': 'terms', 'title': 'Terms of Service', 'icon': '📜', 'url_endpoint': 'terms'},
]

# Default sections extracted from current templates
DEFAULT_SECTIONS = {
    'about': [
        {'id':'hero','type':'hero','title':'🪷 About HolyDham','subtitle':'We are on a sacred mission to digitally preserve and share India\'s holiest destinations, spiritual stories, and devotional heritage with seekers around the world.'},
        {'id':'mission','type':'text_image','heading':'Our Sacred Mission','content':'<p>HolyDham was born from a deep reverence for India\'s spiritual landscape — a land where every river, mountain, and temple carries the echo of divine pastimes. We recognized that this immense spiritual heritage, passed down through millennia, deserved a modern, accessible, and beautifully crafted digital home.</p><p>Our platform meticulously catalogs holy dhams across India using a unique 4-tier hierarchy system — from the broadest sacred regions (Tier 1 – Holy Dhams) down to the exact meditation micro-points (Tier 4 – Key Points) where seekers can connect with the divine.</p><p>Every entry is curated with love, featuring detailed descriptions, gallery images, audio recordings, location data, and custom spiritual metadata that helps pilgrims, researchers, and devotees alike discover the sacred geography of Bharat.</p>','emoji':'🙏','image':'','position':'right'},
        {'id':'stats','type':'stats_row','items':[{'number':'4','label':'Tier Hierarchy'},{'number':'100+','label':'Sacred Locations'},{'number':'50+','label':'Spiritual Stories'},{'number':'∞','label':'Divine Grace'}]},
        {'id':'values','type':'values_grid','items':[
            {'icon':'📜','title':'Authentic Content','desc':'Every piece of information is sourced from authentic scriptural texts, local traditions, and verified accounts. We respect the sanctity of each sacred place and present information with utmost devotion and accuracy.'},
            {'icon':'🗺️','title':'4-Tier Mapping','desc':'Our unique hierarchy system (Holy Dham → Key Places → Key Spots → Key Points) provides granular navigation from broad sacred regions down to exact spots where divine pastimes occurred — a level of detail found nowhere else.'},
            {'icon':'🎵','title':'Multimedia Experience','desc':'Beyond text, we offer gallery images, audio recordings of bhajans and aarti, video tours, and rich custom fields for each location — creating an immersive spiritual experience that transcends the screen.'},
            {'icon':'🌍','title':'Open & Accessible','desc':'We believe sacred knowledge should be freely available to all seekers regardless of geography. HolyDham is designed to be accessible on all devices, fast-loading, and easy to navigate for users worldwide.'},
            {'icon':'🔔','title':'Living Platform','desc':'This is not a static archive. We continuously add new dhams, update existing entries, and enrich content with fresh media, stories, and community contributions. The platform grows as our collective devotion grows.'},
            {'icon':'🙏','title':'Seva-Driven','desc':'HolyDham is a labor of love — a digital seva. Our team works with the spirit of selfless service, motivated not by commercial gain but by the desire to help every soul find their sacred connection with the divine.'}
        ]},
        {'id':'team','type':'team_note','title':'Built With Love & Devotion','content':'HolyDham is created and maintained by a small team of devotees, technologists, and spiritual seekers who share a common passion — preserving India\'s sacred heritage for future generations. We welcome contributions, corrections, and suggestions from the community.','cta_text':'Get In Touch →','cta_link':'/contact'},
    ],
    'privacy': [
        {'id':'s1','type':'legal_section','title':'1. Introduction','content':'<p>Welcome to HolyDham ("we," "our," or "us"). We are deeply committed to protecting your privacy and handling your personal information with care and respect. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit our website and use our services.</p><p>By using HolyDham, you agree to the collection and use of information in accordance with this policy. If you do not agree with any part of this policy, please discontinue use of our services.</p>'},
        {'id':'s2','type':'legal_section','title':'2. Information We Collect','content':'<p><strong>Information You Provide Directly:</strong></p><ul><li><strong>Contact Information:</strong> When you use our contact form, you may provide your name, email address, subject, and message content.</li><li><strong>Newsletter Subscription:</strong> If you subscribe to our newsletter, we collect your email address.</li><li><strong>Account Information:</strong> If you create an admin account, we collect your username, email, and password (stored securely using one-way hashing).</li><li><strong>User-Generated Content:</strong> Any content you submit, including images, descriptions, or comments.</li></ul><p><strong>Information Collected Automatically:</strong></p><ul><li><strong>Usage Data:</strong> Pages visited, time spent on pages, click patterns, and navigation paths.</li><li><strong>Device Information:</strong> Browser type, operating system, screen resolution, and device type.</li><li><strong>Log Data:</strong> IP address, access times, referring URLs, and pages viewed.</li><li><strong>Cookies:</strong> Small data files stored on your device to enhance your browsing experience and maintain session state.</li></ul>'},
        {'id':'s3','type':'legal_section','title':'3. How We Use Your Information','content':'<p>We use the information we collect for the following purposes:</p><ul><li><strong>Service Delivery:</strong> To operate, maintain, and improve the HolyDham platform and its features.</li><li><strong>Communication:</strong> To respond to your inquiries, send newsletter updates (if subscribed), and provide customer support.</li><li><strong>Analytics:</strong> To understand how users interact with our platform, identify popular content, and improve user experience.</li><li><strong>Security:</strong> To detect, prevent, and address technical issues, fraud, or unauthorized access.</li><li><strong>Content Curation:</strong> To personalize and improve the spiritual content we present based on aggregated usage patterns.</li></ul>'},
        {'id':'s4','type':'legal_section','title':'4. Data Sharing & Disclosure','content':'<p>We deeply value your trust and do <strong>not sell, trade, or rent</strong> your personal information to third parties. We may share information only in the following limited circumstances:</p><ul><li><strong>Service Providers:</strong> With trusted third-party services that help us operate our platform (hosting, analytics, email delivery), bound by confidentiality agreements.</li><li><strong>Legal Requirements:</strong> When required by law, court order, or governmental regulation.</li><li><strong>Safety:</strong> To protect the rights, property, or safety of HolyDham, our users, or the public.</li><li><strong>Consent:</strong> With your explicit consent for any other purpose.</li></ul>'},
        {'id':'s5','type':'legal_section','title':'5. Cookies & Tracking','content':'<p>HolyDham uses essential cookies to maintain your session and remember your preferences. We may also use analytics cookies to understand site usage. You can control cookie settings through your browser preferences. Disabling cookies may affect some functionality of the platform.</p><p>We do not use advertising cookies or tracking pixels from third-party advertisers.</p>'},
        {'id':'s6','type':'legal_section','title':'6. Data Security','content':'<p>We implement industry-standard security measures to protect your personal information, including:</p><ul><li>Secure password hashing (SHA-256 with salting) for all accounts</li><li>HTTPS encryption for all data transmission</li><li>Regular security audits and vulnerability assessments</li><li>Access controls limiting data access to authorized personnel only</li><li>Regular data backups with encrypted storage</li></ul><p>While we strive to protect your information, no method of electronic transmission or storage is 100% secure. We encourage you to use strong, unique passwords and exercise caution when sharing personal information online.</p>'},
        {'id':'s7','type':'legal_section','title':'7. Data Retention','content':'<p>We retain your personal information only for as long as necessary to fulfill the purposes outlined in this policy, unless a longer retention period is required or permitted by law. Contact form submissions are retained for up to 12 months. Analytics data is retained in aggregated, anonymized form.</p>'},
        {'id':'s8','type':'legal_section','title':'8. Your Rights','content':'<p>Depending on your jurisdiction, you may have the following rights regarding your personal data:</p><ul><li><strong>Access:</strong> Request a copy of the personal data we hold about you.</li><li><strong>Correction:</strong> Request correction of inaccurate or incomplete data.</li><li><strong>Deletion:</strong> Request deletion of your personal data (subject to legal requirements).</li><li><strong>Objection:</strong> Object to the processing of your data for certain purposes.</li><li><strong>Portability:</strong> Request transfer of your data in a machine-readable format.</li><li><strong>Withdrawal:</strong> Withdraw consent for data processing at any time.</li></ul><p>To exercise any of these rights, please contact us through our contact page.</p>'},
        {'id':'s9','type':'legal_section','title':'9. Children\'s Privacy','content':'<p>HolyDham is a spiritual knowledge platform suitable for all ages. We do not knowingly collect personal information from children under 13 without parental consent. If we discover that a child under 13 has provided personal information, we will promptly delete it.</p>'},
        {'id':'s10','type':'legal_section','title':'10. Third-Party Links','content':'<p>Our platform may contain links to external websites or services. We are not responsible for the privacy practices of these third-party sites. We encourage you to read the privacy policies of any external sites you visit.</p>'},
        {'id':'s11','type':'legal_section','title':'11. Changes to This Policy','content':'<p>We may update this Privacy Policy from time to time. Any changes will be posted on this page with an updated "Effective Date." We encourage you to review this policy periodically.</p>'},
        {'id':'s12','type':'legal_section','title':'12. Contact Us','content':'<p>If you have any questions, concerns, or requests regarding this Privacy Policy or our data practices, please reach out to us via our contact page or email privacy@holydham.com.</p><p>We take every privacy inquiry seriously and will respond within a reasonable timeframe. Thank you for trusting HolyDham with your spiritual journey. 🙏</p>'},
    ],
    'terms': [
        {'id':'t1','type':'legal_section','title':'1. Acceptance of Terms','content':'<p>By accessing or using the HolyDham platform ("Service"), you agree to be bound by these Terms of Service ("Terms"). If you disagree with any part of these terms, you may not access the Service. These Terms apply to all visitors, users, contributors, and administrators of the platform.</p>'},
        {'id':'t2','type':'legal_section','title':'2. Description of Service','content':'<p>HolyDham is a spiritual knowledge platform that curates information about India\'s holy destinations (dhams), temples, sacred stories, festivals, and devotional content. The Service provides:</p><ul><li>A searchable directory of holy places organized in a 4-tier hierarchy</li><li>Detailed information including descriptions, images, audio, video, and location data</li><li>Sacred stories, articles, and educational content about Indian spiritual heritage</li><li>Contact and communication features</li><li>An administrative interface for authorized content managers</li></ul>'},
        {'id':'t3','type':'legal_section','title':'3. User Responsibilities','content':'<p>As a user of HolyDham, you agree to:</p><ul><li><strong>Respectful Usage:</strong> Use the platform respectfully, acknowledging the sacred nature of the content.</li><li><strong>Accurate Information:</strong> Provide accurate and truthful information when using contact forms or contributing content.</li><li><strong>Legal Compliance:</strong> Use the Service in compliance with all applicable laws and regulations.</li><li><strong>Account Security:</strong> If you have an admin account, maintain the confidentiality of your credentials.</li><li><strong>No Automated Access:</strong> Do not use bots, scrapers, or automated tools without prior written permission.</li></ul>'},
        {'id':'t4','type':'legal_section','title':'4. Intellectual Property','content':'<p><strong>Platform Content:</strong> All content on HolyDham — including text, descriptions, images, audio, video, graphics, logos, and the distinctive 4-tier hierarchy system — is the intellectual property of HolyDham or its content contributors.</p><p><strong>Scriptural Content:</strong> Sacred texts, mantras, shlokas, and scriptural references are from traditional sources and are shared in the spirit of spiritual education.</p><p><strong>User Contributions:</strong> By submitting content to HolyDham, you grant us a non-exclusive, royalty-free, worldwide license to use, display, modify, and distribute that content in connection with the Service.</p><p><strong>Fair Use:</strong> You may share or reference HolyDham content for personal, educational, or non-commercial purposes with proper attribution.</p>'},
        {'id':'t5','type':'legal_section','title':'5. Content Standards','content':'<p>All content on HolyDham must adhere to the following standards:</p><ul><li>Must be respectful of all spiritual traditions and religious sentiments</li><li>Must not contain false, misleading, or unverified claims about sacred places</li><li>Must not include promotional, commercial, or spam content</li><li>Must not infringe on any third party\'s intellectual property rights</li><li>Must not contain malicious code, viruses, or harmful content</li><li>Images and media must be original, properly licensed, or in the public domain</li></ul>'},
        {'id':'t6','type':'legal_section','title':'6. Admin Accounts','content':'<p>Administrative access to HolyDham is provided at our discretion. Administrators agree to use their access only for authorized content management purposes, not share credentials, follow editorial standards, and report security vulnerabilities immediately.</p>'},
        {'id':'t7','type':'legal_section','title':'7. Disclaimer of Warranties','content':'<p>HolyDham is provided "as is" and "as available" without warranties of any kind. While we strive for accuracy, spiritual knowledge is vast and interpretations may vary across traditions. We encourage users to verify information through multiple authentic sources.</p>'},
        {'id':'t8','type':'legal_section','title':'8. Limitation of Liability','content':'<p>To the fullest extent permitted by law, HolyDham and its team shall not be liable for any indirect, incidental, special, consequential, or punitive damages arising from your use of or inability to use the Service.</p>'},
        {'id':'t9','type':'legal_section','title':'9. Indemnification','content':'<p>You agree to indemnify, defend, and hold harmless HolyDham and its team from any claims, damages, obligations, losses, or expenses arising from your use of the Service or violation of these Terms.</p>'},
        {'id':'t10','type':'legal_section','title':'10. Modifications to Service','content':'<p>We reserve the right to modify, suspend, or discontinue any aspect of the Service at any time without prior notice. We may also update these Terms from time to time. Continued use constitutes acceptance.</p>'},
        {'id':'t11','type':'legal_section','title':'11. Governing Law','content':'<p>These Terms shall be governed by and construed in accordance with the laws of India. Any disputes shall be resolved in the courts of competent jurisdiction in India.</p>'},
        {'id':'t12','type':'legal_section','title':'12. Severability','content':'<p>If any provision of these Terms is found to be unenforceable or invalid, that provision shall be limited or eliminated to the minimum extent necessary, and the remaining provisions shall remain in full force and effect.</p>'},
        {'id':'t13','type':'legal_section','title':'13. Contact','content':'<p>If you have any questions about these Terms of Service, please contact us via our contact page or email legal@holydham.com. We appreciate your respect for these terms and your participation in preserving India\'s sacred heritage. 🙏</p>'},
    ],
}

SECTION_TYPES = {
    'hero': {'label':'Hero Banner','icon':'🎯','fields':['title','subtitle']},
    'text_image': {'label':'Text + Image Block','icon':'📝','fields':['heading','content','emoji','position']},
    'stats_row': {'label':'Statistics Row','icon':'📊','fields':['items']},
    'values_grid': {'label':'Values / Features Grid','icon':'💎','fields':['items']},
    'team_note': {'label':'CTA / Team Banner','icon':'📣','fields':['title','content','cta_text','cta_link']},
    'legal_section': {'label':'Legal / Content Section','icon':'📄','fields':['title','content']},
    'rich_text': {'label':'Rich Text Block','icon':'✏️','fields':['content']},
}

@app.route('/admin/pages', methods=['GET','POST'])
@login_required
def admin_pages():
    db=get_db()
    selected_key=request.args.get('page','')
    if request.method=='POST':
        selected_key=request.form.get('page_key','')
        sections_json=request.form.get('sections_json','[]')
        try:
            sections=_json.loads(sections_json)
        except:
            sections=[]
        db.execute("INSERT INTO site_settings (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=?",(f"page_{selected_key}_sections",_json.dumps(sections,ensure_ascii=False),_json.dumps(sections,ensure_ascii=False)))
        db.commit()
        page_info=next((p for p in SITE_PAGES if p['key']==selected_key),None)
        log_action(session.get('user_id'),'update_page','site_page',None,f"Updated {page_info['title'] if page_info else selected_key} sections")
        flash(f"Page sections saved successfully!",'success')
        return redirect(url_for('admin_pages',page=selected_key))
    # Build pages list with status
    pages=[]
    for p in SITE_PAGES:
        row=db.execute("SELECT value FROM site_settings WHERE key=?",(f"page_{p['key']}_sections",)).fetchone()
        has_custom=bool(row and row['value'] and row['value']!='[]')
        pages.append({**p,'has_content':has_custom})
    # Load sections for selected page
    sections=[]; selected_page=None
    if selected_key:
        selected_page=next((p for p in pages if p['key']==selected_key),None)
        if selected_page:
            row=db.execute("SELECT value FROM site_settings WHERE key=?",(f"page_{selected_key}_sections",)).fetchone()
            if row and row['value']:
                try: sections=_json.loads(row['value'])
                except: sections=[]
            if not sections:
                sections=DEFAULT_SECTIONS.get(selected_key,[])
    sj=_json.dumps(sections,ensure_ascii=False).replace('</','<\\/')
    dj=_json.dumps(DEFAULT_SECTIONS.get(selected_key,[]),ensure_ascii=False).replace('</','<\\/') if selected_key else '[]'
    return render_template('admin/pages.html',pages=pages,selected_key=selected_key,selected_page=selected_page,sections=sj,section_types=SECTION_TYPES,default_sections=dj)

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

@app.route('/api/v1/module-schema/<int:mod_id>')
def api_module_schema(mod_id):
    db=get_db(); m=db.execute("SELECT * FROM modules WHERE id=?",(mod_id,)).fetchone()
    if not m: return jsonify({'error':'Not found'}),404
    try: schema=json.loads(m['fields_schema'] or '[]')
    except: schema=[]
    return jsonify({'module':dict(m),'schema':schema})

@app.route('/api/v1/tier-options/<tier_type>')
def api_tier_options(tier_type):
    db=get_db()
    if tier_type=='dham':
        return jsonify([{'id':r['id'],'title':r['title']} for r in db.execute("SELECT id,title FROM places ORDER BY title").fetchall()])
    elif tier_type=='key_place':
        return jsonify([{'id':r['id'],'title':r['title'],'parent':r['dham_title']} for r in db.execute("SELECT kp.id,kp.title,p.title as dham_title FROM key_places kp JOIN places p ON kp.parent_place_id=p.id ORDER BY p.title,kp.title").fetchall()])
    elif tier_type=='key_spot':
        return jsonify([{'id':r['id'],'title':r['title'],'parent':r['kp_title']} for r in db.execute("SELECT ks.id,ks.title,kp.title as kp_title FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id ORDER BY kp.title,ks.title").fetchall()])
    elif tier_type=='sub_spot':
        return jsonify([{'id':r['id'],'title':r['title'],'parent':r['ks_title']} for r in db.execute("SELECT ss.id,ss.title,ks.title as ks_title FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id ORDER BY ks.title,ss.title").fetchall()])
    return jsonify([])

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

# ═══════════════════════════════════════════════════════════════
# ─── Itinerary System: Admin + Frontend ───
# ═══════════════════════════════════════════════════════════════

def _resolve_itinerary_place(tier, ref_id, db):
    """Fetch place data from appropriate tier table with full custom field info."""
    def _get_audio_video(tier, ref_id):
        return [dict(r) for r in db.execute("SELECT * FROM place_audio_video WHERE tier=? AND place_ref_id=? ORDER BY sort_order", (tier, ref_id)).fetchall()]
    if tier == 'T1':
        r = db.execute("SELECT id,title,slug,short_description,full_content,featured_image,latitude,longitude,state,city,country,hierarchy_id FROM places WHERE id=?", (ref_id,)).fetchone()
        if r:
            cfs = db.execute("SELECT cfd.label, cfd.name as field_name, cfd.field_type, pcv.value, pcv.description FROM place_custom_values pcv JOIN custom_field_defs cfd ON pcv.field_def_id=cfd.id WHERE pcv.place_id=? AND pcv.is_visible=1 AND pcv.value != ''", (ref_id,)).fetchall()
            gal = db.execute("SELECT GROUP_CONCAT(m.filename) as gi FROM media m JOIN place_media pm ON m.id=pm.media_id WHERE pm.place_id=? AND m.file_type='image'", (ref_id,)).fetchone()
            d = dict(r)
            d['gallery_images'] = gal['gi'] if gal and gal['gi'] else ''
            d['custom_fields'] = [dict(c) for c in cfs]
            d['audio_video_items'] = _get_audio_video('T1', ref_id)
            d['tier'] = 'T1'; d['tier_label'] = 'Holy Dham'; d['url'] = f"/place/{r['slug']}"
            return d
    elif tier == 'T2':
        r = db.execute("SELECT kp.*, p.slug as dham_slug FROM key_places kp JOIN places p ON kp.parent_place_id=p.id WHERE kp.id=?", (ref_id,)).fetchone()
        if r:
            cfs = db.execute("SELECT cfd.label, cfd.name as field_name, cfd.field_type, kpcv.value, kpcv.description FROM key_place_custom_values kpcv JOIN custom_field_defs cfd ON kpcv.field_def_id=cfd.id WHERE kpcv.key_place_id=? AND kpcv.is_visible=1 AND kpcv.value != ''", (ref_id,)).fetchall()
            d = dict(r)
            d['custom_fields'] = [dict(c) for c in cfs]
            d['audio_video_items'] = _get_audio_video('T2', ref_id)
            d['tier'] = 'T2'; d['tier_label'] = 'Key Place'; d['url'] = f"/place/{r['dham_slug']}/key/{r['slug']}"
            return d
    elif tier == 'T3':
        r = db.execute("SELECT ks.*, kp.slug as kp_slug, p.slug as dham_slug FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id WHERE ks.id=?", (ref_id,)).fetchone()
        if r:
            cfs = db.execute("SELECT cfd.label, cfd.name as field_name, cfd.field_type, kscv.value, kscv.description FROM key_spot_custom_values kscv JOIN custom_field_defs cfd ON kscv.field_def_id=cfd.id WHERE kscv.key_spot_id=? AND kscv.is_visible=1 AND kscv.value != ''", (ref_id,)).fetchall()
            d = dict(r)
            d['custom_fields'] = [dict(c) for c in cfs]
            d['audio_video_items'] = _get_audio_video('T3', ref_id)
            d['tier'] = 'T3'; d['tier_label'] = 'Key Spot'; d['url'] = f"/place/{r['dham_slug']}/key/{r['kp_slug']}/spot/{r['slug']}"
            return d
    elif tier == 'T4':
        r = db.execute("SELECT ss.*, ks.slug as ks_slug, kp.slug as kp_slug, p.slug as dham_slug FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id WHERE ss.id=?", (ref_id,)).fetchone()
        if r:
            cfs = db.execute("SELECT cfd.label, cfd.name as field_name, cfd.field_type, sscv.value, sscv.description FROM sub_spot_custom_values sscv JOIN custom_field_defs cfd ON sscv.field_def_id=cfd.id WHERE sscv.sub_spot_id=? AND sscv.is_visible=1 AND sscv.value != ''", (ref_id,)).fetchall()
            d = dict(r)
            d['custom_fields'] = [dict(c) for c in cfs]
            d['audio_video_items'] = _get_audio_video('T4', ref_id)
            d['tier'] = 'T4'; d['tier_label'] = 'Key Point'; d['url'] = f"/place/{r['dham_slug']}/key/{r['kp_slug']}/spot/{r['ks_slug']}/sub/{r['slug']}"
            return d
    return None

# ─── Admin: Itinerary List ───
@app.route('/admin/itineraries')
@login_required
def admin_itineraries():
    db = get_db()
    itineraries = db.execute("""
        SELECT i.*, u.display_name as creator_name,
        (SELECT COUNT(*) FROM itinerary_places ip WHERE ip.itinerary_id=i.id) as place_count
        FROM itineraries i LEFT JOIN users u ON i.created_by=u.id
        ORDER BY i.updated_at DESC
    """).fetchall()
    return render_template('admin/itineraries.html', itineraries=itineraries)

# ─── Admin: Create Itinerary ───
@app.route('/admin/itineraries/new', methods=['GET','POST'])
@login_required
def admin_itinerary_new():
    if request.method == 'POST':
        return _save_itinerary(None)
    return render_template('admin/itinerary_form.html', itinerary=None, selected_places=[])

# ─── Admin: Edit Itinerary ───
@app.route('/admin/itineraries/<int:itin_id>/edit', methods=['GET','POST'])
@login_required
def admin_itinerary_edit(itin_id):
    db = get_db()
    itin = db.execute("SELECT * FROM itineraries WHERE id=?", (itin_id,)).fetchone()
    if not itin: flash('Itinerary not found.','error'); return redirect(url_for('admin_itineraries'))
    if request.method == 'POST':
        return _save_itinerary(itin_id)
    # Load selected places with resolved data
    raw_places = db.execute("SELECT * FROM itinerary_places WHERE itinerary_id=? ORDER BY sort_order", (itin_id,)).fetchall()
    selected_places = []
    for rp in raw_places:
        resolved = _resolve_itinerary_place(rp['tier'], rp['place_ref_id'], db)
        if resolved:
            selected_places.append({
                'tier': rp['tier'], 'place_ref_id': rp['place_ref_id'],
                'title': resolved['title'], 'short_description': resolved.get('short_description',''),
                'admin_notes': rp['admin_notes'] or '', 'time_group': rp['time_group'] or '',
                'latitude': resolved.get('latitude'), 'longitude': resolved.get('longitude'),
                'tier_label': resolved.get('tier_label',''),
                'hierarchy_id': resolved.get('hierarchy_id','')
            })
    return render_template('admin/itinerary_form.html', itinerary=itin, selected_places=selected_places)

def _save_itinerary(itin_id):
    db = get_db()
    f = request.form
    title = f.get('title','').strip()
    leader_name = f.get('leader_name','').strip()
    group_name = f.get('group_name','').strip()
    short_description = f.get('short_description','').strip()
    full_content = f.get('full_content','').strip()
    status = f.get('status','draft')

    if not title:
        flash('Yatra name is required.','error')
        return redirect(request.url)

    if not leader_name:
        flash('Leader name is required.','error')
        return redirect(request.url)

    if not group_name:
        flash('Group name is required.','error')
        return redirect(request.url)

    # Generate slug: ddmmyyyy-itinerary-groupname (only for new itineraries)
    if itin_id:
        # Keep existing slug on edit to avoid breaking shared links
        existing_itin = db.execute("SELECT slug FROM itineraries WHERE id=?", (itin_id,)).fetchone()
        slug = existing_itin['slug'] if existing_itin else ''
    
    if not itin_id or not slug:
        slug_base = group_name if group_name else title
        date_prefix = datetime.now().strftime('%d%m%Y')
        slug = date_prefix + '-itinerary-' + slugify(slug_base)
        # Check slug uniqueness
        existing = db.execute("SELECT id FROM itineraries WHERE slug=? AND id!=?", (slug, itin_id or 0)).fetchone()
        if existing:
            slug = slug + '-' + str(int(datetime.now().timestamp()) % 10000)

    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if itin_id:
        db.execute("""UPDATE itineraries SET title=?, slug=?, leader_name=?, group_name=?, short_description=?,
            full_content=?, status=?, updated_at=? WHERE id=?""",
            (title, slug, leader_name, group_name, short_description, full_content, status, now, itin_id))
    else:
        cur = db.execute("""INSERT INTO itineraries (title,slug,leader_name,group_name,short_description,full_content,status,created_by,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (title, slug, leader_name, group_name, short_description, full_content, status,
             session.get('user_id'), now, now))
        itin_id = cur.lastrowid

    # Save places
    db.execute("DELETE FROM itinerary_places WHERE itinerary_id=?", (itin_id,))
    tiers = f.getlist('place_tier[]')
    ref_ids = f.getlist('place_ref_id[]')
    notes = f.getlist('place_notes[]')
    time_groups = f.getlist('place_time_group[]')
    for idx, (tier, ref_id) in enumerate(zip(tiers, ref_ids)):
        note = notes[idx] if idx < len(notes) else ''
        tg = time_groups[idx] if idx < len(time_groups) else ''
        db.execute("INSERT INTO itinerary_places (itinerary_id,tier,place_ref_id,sort_order,admin_notes,time_group) VALUES (?,?,?,?,?,?)",
            (itin_id, tier, int(ref_id), idx, note, tg))

    db.commit()
    log_action(session.get('user_id'), 'update' if itin_id else 'create', 'itinerary', itin_id)
    flash('Itinerary saved successfully!', 'success')
    return redirect(url_for('admin_itinerary_edit', itin_id=itin_id))

# ─── Admin: Delete Itinerary ───
@app.route('/admin/itineraries/<int:itin_id>/delete', methods=['POST'])
@login_required
def admin_itinerary_delete(itin_id):
    db = get_db()
    db.execute("DELETE FROM itineraries WHERE id=?", (itin_id,))
    db.commit()
    log_action(session.get('user_id'), 'delete', 'itinerary', itin_id)
    flash('Itinerary deleted.', 'info')
    return redirect(url_for('admin_itineraries'))

# ─── Admin: Duplicate Itinerary ───
@app.route('/admin/itineraries/<int:itin_id>/duplicate', methods=['POST'])
@login_required
def admin_itinerary_duplicate(itin_id):
    db = get_db()
    
    orig = db.execute("SELECT * FROM itineraries WHERE id=?", (itin_id,)).fetchone()
    if not orig: flash('Not found.','error'); return redirect(url_for('admin_itineraries'))
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_title = orig['title'] + ' (Copy)'
    new_slug = datetime.now().strftime('%d%m%Y') + '-itinerary-' + slugify(new_title) + '-' + str(int(datetime.now().timestamp()) % 10000)
    cur = db.execute("""INSERT INTO itineraries (title,slug,leader_name,group_name,short_description,full_content,status,created_by,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (new_title, new_slug, orig['leader_name'], orig['group_name'] + ' Copy',
         orig['short_description'], orig['full_content'], 'draft', session.get('user_id'), now, now))
    new_id = cur.lastrowid
    for p in db.execute("SELECT * FROM itinerary_places WHERE itinerary_id=? ORDER BY sort_order", (itin_id,)).fetchall():
        db.execute("INSERT INTO itinerary_places (itinerary_id,tier,place_ref_id,sort_order,admin_notes,time_group) VALUES (?,?,?,?,?,?)",
            (new_id, p['tier'], p['place_ref_id'], p['sort_order'], p['admin_notes'], p['time_group']))
    db.commit()
    flash('Itinerary duplicated!', 'success')
    return redirect(url_for('admin_itinerary_edit', itin_id=new_id))

# ─── API: Search Places for Itinerary Builder ───
@app.route('/admin/api/itinerary-place-search')
@login_required
def admin_itinerary_place_search():
    q = request.args.get('q','').strip()
    if not q or len(q) < 1: return jsonify([])
    db = get_db(); like = f'%{q}%'; results = []
    # T1 — search title, city, state, hierarchy_id, short_description (no status filter for admin)
    for r in db.execute("SELECT id,title,short_description,hierarchy_id,city,state,latitude,longitude FROM places WHERE (title LIKE ? OR city LIKE ? OR state LIKE ? OR hierarchy_id LIKE ? OR short_description LIKE ?) ORDER BY title LIMIT 10", (like,like,like,like,like)).fetchall():
        results.append({'tier':'T1','tier_label':'Holy Dham','icon':'\U0001f3db\ufe0f','color':'#C76B8F','id':r['id'],'title':r['title'],'desc':r['short_description'] or '','hid':r['hierarchy_id'] or '','location':f"{r['city'] or ''}{', '+r['state'] if r['state'] else ''}",'lat':r['latitude'],'lng':r['longitude']})
    # T2 — search title, hierarchy_id, short_description, parent dham title, city, state
    for r in db.execute("SELECT kp.id,kp.title,kp.short_description,kp.hierarchy_id,kp.latitude,kp.longitude,p.title as dham_title,p.city,p.state FROM key_places kp JOIN places p ON kp.parent_place_id=p.id WHERE (kp.title LIKE ? OR kp.hierarchy_id LIKE ? OR kp.short_description LIKE ? OR p.title LIKE ? OR p.city LIKE ? OR p.state LIKE ?) ORDER BY kp.title LIMIT 10", (like,like,like,like,like,like)).fetchall():
        results.append({'tier':'T2','tier_label':'Key Place','icon':'\U0001f4cd','color':'#2E86AB','id':r['id'],'title':r['title'],'desc':r['short_description'] or '','hid':r['hierarchy_id'] or '','parent':r['dham_title'],'location':f"{r['city'] or ''}{', '+r['state'] if r['state'] else ''}",'lat':r['latitude'],'lng':r['longitude']})
    # T3 — search title, hierarchy_id, short_description, parent key_place title, dham title
    for r in db.execute("SELECT ks.id,ks.title,ks.short_description,ks.hierarchy_id,ks.latitude,ks.longitude,kp.title as kp_title,p.title as dham_title FROM key_spots ks JOIN key_places kp ON ks.key_place_id=kp.id JOIN places p ON kp.parent_place_id=p.id WHERE (ks.title LIKE ? OR ks.hierarchy_id LIKE ? OR ks.short_description LIKE ? OR kp.title LIKE ? OR p.title LIKE ?) ORDER BY ks.title LIMIT 10", (like,like,like,like,like)).fetchall():
        results.append({'tier':'T3','tier_label':'Key Spot','icon':'\U0001f3af','color':'#E74845','id':r['id'],'title':r['title'],'desc':r['short_description'] or '','hid':r['hierarchy_id'] or '','parent':f"{r['kp_title']} \u2192 {r['dham_title']}",'lat':r['latitude'],'lng':r['longitude']})
    # T4 — search title, hierarchy_id, short_description, parent key_spot title, key_place title
    for r in db.execute("SELECT ss.id,ss.title,ss.short_description,ss.hierarchy_id,ss.latitude,ss.longitude,ks.title as ks_title,kp.title as kp_title FROM sub_spots ss JOIN key_spots ks ON ss.key_spot_id=ks.id JOIN key_places kp ON ks.key_place_id=kp.id WHERE (ss.title LIKE ? OR ss.hierarchy_id LIKE ? OR ss.short_description LIKE ? OR ks.title LIKE ? OR kp.title LIKE ?) ORDER BY ss.title LIMIT 10", (like,like,like,like,like)).fetchall():
        results.append({'tier':'T4','tier_label':'Key Point','icon':'\u2726','color':'#9C27B0','id':r['id'],'title':r['title'],'desc':r['short_description'] or '','hid':r['hierarchy_id'] or '','parent':f"{r['ks_title']} \u2192 {r['kp_title']}",'lat':r['latitude'],'lng':r['longitude']})
    return jsonify(results[:40])


# ─── Frontend: Public Itinerary View ───
@app.route('/<slug>')
def public_itinerary(slug):
    db = get_db()
    # Match date-prefixed itinerary slugs (e.g., 26022026-itinerary-chitra)
    if 'itinerary' not in slug:
        abort(404)
    itin = db.execute("SELECT * FROM itineraries WHERE slug=? AND status='published'", (slug,)).fetchone()
    if not itin:
        return render_template('frontend/404.html'), 404
    db.execute("UPDATE itineraries SET view_count=view_count+1 WHERE id=?", (itin['id'],)); db.commit()
    raw_places = db.execute("SELECT * FROM itinerary_places WHERE itinerary_id=? ORDER BY sort_order", (itin['id'],)).fetchall()
    places = []
    for rp in raw_places:
        resolved = _resolve_itinerary_place(rp['tier'], rp['place_ref_id'], db)
        if resolved:
            resolved['admin_notes'] = rp['admin_notes'] or ''
            resolved['time_group'] = rp['time_group'] or ''
            resolved['sort_order'] = rp['sort_order']
            places.append(resolved)
    return render_template('frontend/itinerary.html', itinerary=itin, places=places)

with app.app_context(): init_db(); seed_db()
if __name__=='__main__': app.run(debug=True,host='0.0.0.0',port=5000)
