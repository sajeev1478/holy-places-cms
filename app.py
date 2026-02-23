"""
Holy Places CMS - Main Application (v2)
Enhanced with: Custom Fields, Field Visibility, Key Places, File Uploads
"""

import os, json, uuid, hashlib, sqlite3, functools
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
    CREATE TABLE IF NOT EXISTS custom_field_defs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, label TEXT NOT NULL, field_type TEXT NOT NULL DEFAULT 'text', placeholder TEXT DEFAULT '', is_active INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0, applies_to TEXT DEFAULT 'both', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS place_custom_values (id INTEGER PRIMARY KEY AUTOINCREMENT, place_id INTEGER NOT NULL, field_def_id INTEGER NOT NULL, value TEXT DEFAULT '', is_visible INTEGER DEFAULT 1, FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE, FOREIGN KEY (field_def_id) REFERENCES custom_field_defs(id) ON DELETE CASCADE, UNIQUE(place_id, field_def_id));
    CREATE TABLE IF NOT EXISTS key_places (id INTEGER PRIMARY KEY AUTOINCREMENT, parent_place_id INTEGER NOT NULL, title TEXT NOT NULL, slug TEXT, short_description TEXT, full_content TEXT, featured_image TEXT, latitude REAL, longitude REAL, sort_order INTEGER DEFAULT 0, is_visible INTEGER DEFAULT 1, field_visibility TEXT DEFAULT '{}', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (parent_place_id) REFERENCES places(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS key_place_custom_values (id INTEGER PRIMARY KEY AUTOINCREMENT, key_place_id INTEGER NOT NULL, field_def_id INTEGER NOT NULL, value TEXT DEFAULT '', is_visible INTEGER DEFAULT 1, FOREIGN KEY (key_place_id) REFERENCES key_places(id) ON DELETE CASCADE, FOREIGN KEY (field_def_id) REFERENCES custom_field_defs(id) ON DELETE CASCADE, UNIQUE(key_place_id, field_def_id));
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
    db.execute("INSERT INTO users (username,email,password_hash,display_name,role,permissions) VALUES (?,?,?,?,?,?)", ('admin','admin@holyplaces.com',hashlib.sha256(b'admin123').hexdigest(),'Super Admin','super_admin','{"all":true}'))
    db.execute("INSERT INTO users (username,email,password_hash,display_name,role,created_by) VALUES (?,?,?,?,?,?)", ('editor','editor@holyplaces.com',hashlib.sha256(b'editor123').hexdigest(),'Content Editor','editor',1))
    for name,slug,desc,icon,order in [('Holy Places','holy-places','Sacred destinations','🛕',1),('Temples','temples','Temple profiles','🏛️',2),('Sacred Stories','sacred-stories','Mythological tales','📖',3),('Festivals','festivals','Religious events','🎪',4),('Pilgrimage Guides','pilgrimage-guides','Travel guides','🚶',5),('Events','events','Spiritual events','📅',6),('Bhajans & Kirtans','bhajans-kirtans','Devotional music','🎵',7),('Spiritual Articles','spiritual-articles','Spiritual writings','📝',8)]:
        db.execute("INSERT INTO modules (name,slug,description,icon,sort_order,is_active,created_by) VALUES (?,?,?,?,?,1,1)", (name,slug,desc,icon,order))
    for name,slug,color in [('Char Dham','char-dham','#C76B8F'),('Jyotirlinga','jyotirlinga','#E89B4F'),('Heritage','heritage','#8BAB8A'),('Pilgrimage','pilgrimage','#6B8AB5'),('UNESCO','unesco','#B58A6B'),('Sikh Heritage','sikh-heritage','#C4A44E'),('Buddhist','buddhist','#8A6BB5'),('ISKCON','iskcon','#D4A843')]:
        db.execute("INSERT INTO tags (name,slug,color) VALUES (?,?,?)", (name,slug,color))
    for name,label,ftype,ph,order,applies in [('audio_narration','Audio Narration','audio','Upload audio',1,'both'),('video_tour','Video Tour','video','Upload or paste URL',2,'both'),('gallery_images','Gallery Images','images','Upload photos',3,'both'),('opening_hours','Opening Hours','text','e.g. 6 AM - 9 PM',4,'both'),('best_time_to_visit','Best Time to Visit','text','e.g. Oct-Mar',5,'both'),('how_to_reach','How to Reach','textarea','Directions',6,'place'),('accommodation','Accommodation','textarea','Stay options',7,'place'),('history','History & Significance','richtext','Detailed history',8,'both'),('dress_code','Dress Code','text','If any',9,'both'),('entry_fee','Entry Fee','text','e.g. Free',10,'both'),('external_audio_url','External Audio Link','url','Audio URL',11,'both'),('external_video_url','External Video Link','url','YouTube/Vimeo URL',12,'both')]:
        db.execute("INSERT INTO custom_field_defs (name,label,field_type,placeholder,sort_order,applies_to) VALUES (?,?,?,?,?,?)", (name,label,ftype,ph,order,applies))
    # Sample: Mayapur
    db.execute("INSERT INTO places (title,slug,short_description,full_content,state,city,country,latitude,longitude,status,is_featured,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
        ('Mayapur','mayapur','The spiritual headquarters of ISKCON and birthplace of Sri Chaitanya Mahaprabhu.',
         '<h2>The Holy Land of Mayapur</h2><p>Mayapur, in Nadia district of West Bengal, is one of the most important pilgrimage sites for Gaudiya Vaishnavas. It is the birthplace of Sri Chaitanya Mahaprabhu (1486 CE).</p><h3>ISKCON World Headquarters</h3><p>Mayapur serves as the international headquarters of ISKCON. The Temple of the Vedic Planetarium (TOVP) is being built here.</p>',
         'West Bengal','Nadia','India',23.4231,88.3884,'published',1))
    mid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for tid in [8,4]: db.execute("INSERT OR IGNORE INTO place_tags VALUES (?,?)", (mid,tid))
    for t,s,sd,fc,lat,lng,o in [('Navadvipa','navadvipa','Nine islands representing nine processes of devotional service.','<p>Navadvipa consists of nine islands, each representing one limb of bhakti. Pilgrims walk all nine during Navadvipa Parikrama.</p>',23.4145,88.3750,1),
        ('Antardvipa','antardvipa','Central island where Sri Chaitanya appeared, representing self-surrender.','<p>Antardvipa is the central and most sacred island — birthplace of Sri Chaitanya Mahaprabhu. The Yogapitha temple marks the exact spot.</p>',23.4231,88.3884,2),
        ('Yogapitha','yogapitha','The exact birthplace of Sri Chaitanya Mahaprabhu.','<p>Yogapitha marks the exact location where Sri Chaitanya appeared on the full moon evening of Phalguna 1486 CE.</p>',23.4248,88.3891,3),
        ('ISKCON Chandrodaya Mandir','iskcon-chandrodaya-mandir','Main ISKCON temple with beautiful deity worship.','<p>Houses Sri Sri Radha Madhava, Krishna Balarama, Jagannath Baladeva Subhadra, and Pancha Tattva deities.</p>',23.4227,88.3894,4)]:
        db.execute("INSERT INTO key_places (parent_place_id,title,slug,short_description,full_content,latitude,longitude,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,1)", (mid,t,s,sd,fc,lat,lng,o))
    for t,s,sd,fc,st,ci,lat,lng in [('Kedarnath Temple','kedarnath-temple','One of the twelve Jyotirlingas of Lord Shiva.','<h2>Sacred Abode of Lord Shiva</h2><p>Located in the Garhwal Himalayas near the Mandakini river.</p>','Uttarakhand','Rudraprayag',30.7352,79.0669),
        ('Somnath Temple','somnath-temple','First among twelve Jyotirlinga shrines.','<h2>The Eternal Shrine</h2><p>Located at the shore of the Arabian Sea in Gujarat.</p>','Gujarat','Veraval',20.8880,70.4012),
        ('Varanasi Ghats','varanasi-ghats','The oldest living city on the Ganges.','<h2>City of Light</h2><p>Spiritual capital of India with 88 ghats.</p>','Uttar Pradesh','Varanasi',25.3176,83.0078),
        ('Golden Temple','golden-temple','Holiest Gurdwara of Sikhism.','<h2>Harmandir Sahib</h2><p>Most visited religious site in the world.</p>','Punjab','Amritsar',31.6200,74.8765)]:
        db.execute("INSERT INTO places (title,slug,short_description,full_content,state,city,country,latitude,longitude,status,is_featured,created_by) VALUES (?,?,?,?,?,?,'India',?,?,'published',1,1)", (t,s,sd,fc,st,ci,lat,lng))
    for mod,pid,t,s,c in [(3,mid,'Appearance of Sri Chaitanya','appearance-sri-chaitanya','<p>Sri Chaitanya appeared in Mayapur in 1486 CE amidst ecstatic chanting.</p>'),(3,None,'Legend of Kedarnath','legend-kedarnath','<p>The Pandavas sought Lord Shiva who hid as a bull. His hump remained at Kedarnath.</p>'),(4,None,'Gaura Purnima','gaura-purnima','<p>Celebrates the appearance of Sri Chaitanya. Hundreds of thousands visit Mayapur.</p>')]:
        db.execute("INSERT INTO module_entries (module_id,place_id,title,slug,content,status,created_by) VALUES (?,?,?,?,?,'published',1)", (mod,pid,t,s,c))
    for k,l,d,cat in [('manage_places','Manage Holy Places','Create/edit/delete places','content'),('manage_modules','Manage Modules','Configure modules','system'),('manage_entries','Manage Entries','Create/edit entries','content'),('manage_media','Manage Media','Upload media','media'),('publish_content','Publish Content','Publish/unpublish','content'),('manage_users','Manage Users','Manage accounts','system'),('manage_tags','Manage Tags','Manage categories','content'),('manage_fields','Manage Fields','Configure custom fields','system')]:
        db.execute("INSERT OR IGNORE INTO permission_definitions (permission_key,label,description,category) VALUES (?,?,?,?)", (k,l,d,cat))
    db.commit()

# Helpers
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

@app.context_processor
def inject_globals():
    db=get_db(); modules=db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall()
    return {'current_user':get_current_user(),'active_modules':modules,'current_year':datetime.now().year,'has_permission':has_permission,'builtin_fields':BUILTIN_FIELDS,'json':json}

# ═══ FRONTEND ═══
@app.route('/')
def home():
    db=get_db()
    featured=db.execute("SELECT p.*,GROUP_CONCAT(t.name) as tag_names FROM places p LEFT JOIN place_tags pt ON p.id=pt.place_id LEFT JOIN tags t ON pt.tag_id=t.id WHERE p.status='published' AND p.is_featured=1 GROUP BY p.id ORDER BY p.updated_at DESC LIMIT 6").fetchall()
    modules=db.execute("SELECT * FROM modules WHERE is_active=1 ORDER BY sort_order").fetchall()
    stories=db.execute("SELECT me.*,m.name as module_name,m.icon as module_icon FROM module_entries me JOIN modules m ON me.module_id=m.id WHERE me.status='published' AND m.slug='sacred-stories' ORDER BY me.created_at DESC LIMIT 4").fetchall()
    stats={'places':db.execute("SELECT COUNT(*) FROM places WHERE status='published'").fetchone()[0],'entries':db.execute("SELECT COUNT(*) FROM module_entries WHERE status='published'").fetchone()[0],'modules':db.execute("SELECT COUNT(*) FROM modules WHERE is_active=1").fetchone()[0]}
    return render_template('frontend/home.html',featured=featured,recent=featured,modules=modules,stories=stories,stats=stats)

@app.route('/place/<slug>')
def place_detail(slug):
    db=get_db(); place=db.execute("SELECT * FROM places WHERE slug=? AND status='published'",(slug,)).fetchone()
    if not place: abort(404)
    db.execute("UPDATE places SET view_count=view_count+1 WHERE id=?",(place['id'],)); db.commit()
    tags=db.execute("SELECT t.* FROM tags t JOIN place_tags pt ON t.id=pt.tag_id WHERE pt.place_id=?",(place['id'],)).fetchall()
    visibility=json.loads(place['field_visibility'] or '{}')
    custom_values=db.execute("SELECT pcv.*,cfd.name,cfd.label,cfd.field_type FROM place_custom_values pcv JOIN custom_field_defs cfd ON pcv.field_def_id=cfd.id WHERE pcv.place_id=? AND pcv.is_visible=1 AND cfd.is_active=1 ORDER BY cfd.sort_order",(place['id'],)).fetchall()
    key_places=db.execute("SELECT * FROM key_places WHERE parent_place_id=? AND is_visible=1 ORDER BY sort_order",(place['id'],)).fetchall()
    key_places_data=[]
    for kp in key_places:
        kpc=db.execute("SELECT kpcv.*,cfd.name,cfd.label,cfd.field_type FROM key_place_custom_values kpcv JOIN custom_field_defs cfd ON kpcv.field_def_id=cfd.id WHERE kpcv.key_place_id=? AND kpcv.is_visible=1 AND cfd.is_active=1 ORDER BY cfd.sort_order",(kp['id'],)).fetchall()
        key_places_data.append({'place':kp,'customs':kpc})
    media_items=db.execute("SELECT m.*,pm.media_role FROM media m JOIN place_media pm ON m.id=pm.media_id WHERE pm.place_id=? ORDER BY pm.sort_order",(place['id'],)).fetchall()
    nearby=db.execute("SELECT p.*,np.distance_km FROM places p JOIN nearby_places np ON p.id=np.nearby_place_id WHERE np.place_id=? AND p.status='published'",(place['id'],)).fetchall()
    related_entries=db.execute("SELECT me.*,m.name as module_name,m.icon as module_icon,m.slug as module_slug FROM module_entries me JOIN modules m ON me.module_id=m.id WHERE me.place_id=? AND me.status='published' ORDER BY m.sort_order",(place['id'],)).fetchall()
    related=db.execute("SELECT DISTINCT p.* FROM places p JOIN place_tags pt ON p.id=pt.place_id WHERE pt.tag_id IN (SELECT tag_id FROM place_tags WHERE place_id=?) AND p.id!=? AND p.status='published' LIMIT 3",(place['id'],place['id'])).fetchall()
    return render_template('frontend/place.html',place=place,tags=tags,visibility=visibility,custom_values=custom_values,key_places_data=key_places_data,media=media_items,nearby=nearby,related_entries=related_entries,related=related)

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

# ═══ ADMIN ═══
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
    stats={'places':db.execute("SELECT COUNT(*) FROM places").fetchone()[0],'published':db.execute("SELECT COUNT(*) FROM places WHERE status='published'").fetchone()[0],'entries':db.execute("SELECT COUNT(*) FROM module_entries").fetchone()[0],'media':db.execute("SELECT COUNT(*) FROM media").fetchone()[0],'users':db.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0],'modules':db.execute("SELECT COUNT(*) FROM modules WHERE is_active=1").fetchone()[0]}
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
    try:
        db.execute("INSERT INTO custom_field_defs (name,label,field_type,placeholder,sort_order,applies_to) VALUES (?,?,?,?,?,?)",(name,request.form['label'],request.form['field_type'],request.form.get('placeholder',''),request.form.get('sort_order',0,type=int),request.form.get('applies_to','both')))
        db.commit(); flash('Field created!','success')
    except sqlite3.IntegrityError: flash('Field already exists.','error')
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

# Places CRUD
@app.route('/admin/places')
@login_required
def admin_places():
    db=get_db(); sf=request.args.get('status',''); q=request.args.get('q','')
    query="SELECT * FROM places WHERE 1=1"; params=[]
    if sf: query+=" AND status=?"; params.append(sf)
    if q: query+=" AND (title LIKE ? OR city LIKE ? OR state LIKE ?)"; params.extend([f'%{q}%']*3)
    return render_template('admin/places.html',places=db.execute(query+" ORDER BY updated_at DESC",params).fetchall(),current_status=sf,query=q)

@app.route('/admin/places/new', methods=['GET','POST'])
@login_required
def admin_place_new():
    db=get_db()
    if request.method=='POST': return _save_place(None)
    return render_template('admin/place_form.html',place=None,tags=db.execute("SELECT * FROM tags ORDER BY name").fetchall(),place_tags=[],custom_fields=db.execute("SELECT * FROM custom_field_defs WHERE is_active=1 AND applies_to IN ('both','place') ORDER BY sort_order").fetchall(),custom_values={},key_places=[],key_place_customs={},editing=False)

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
    return render_template('admin/place_form.html',place=place,tags=tags,place_tags=ptags,custom_fields=cfs,custom_values=cvs,key_places=kps,key_place_customs=kpc,editing=True)

def _save_place(place_id):
    db=get_db(); f=request.form; title=f['title']; slug=slugify(title)
    fi=f.get('featured_image_existing','')
    if 'featured_image_file' in request.files:
        uf=request.files['featured_image_file']
        if uf and uf.filename: u=save_upload(uf,'images'); fi=u if u else fi
    vis={}
    for bf in BUILTIN_FIELDS: vis[bf['key']]=1 if f.get(f"vis_{bf['key']}") else 0
    lat=f.get('latitude',type=float); lng=f.get('longitude',type=float)
    if pid:
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
    # Key Places
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
        if kpid and kpid in existing_kpids:
            db.execute("UPDATE key_places SET title=?,slug=?,short_description=?,full_content=?,featured_image=?,latitude=?,longitude=?,sort_order=?,is_visible=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (kt,ks,ksd,kfc,kimg,klat,klng,kpi,kv,kpid)); submitted_kpids.append(kpid)
        else:
            db.execute("INSERT INTO key_places (parent_place_id,title,slug,short_description,full_content,featured_image,latitude,longitude,sort_order,is_visible) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (place_id,kt,ks,ksd,kfc,kimg,klat,klng,kpi,kv))
            kplace_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]; submitted_kpids.append(kpid)
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
    flash(f'Place "{title}" saved!','success'); return redirect(url_for('admin_places'))

@app.route('/admin/places/<int:place_id>/delete', methods=['POST'])
@login_required
def admin_place_delete(place_id):
    db=get_db(); p=db.execute("SELECT title FROM places WHERE id=?",(place_id,)).fetchone()
    db.execute("DELETE FROM places WHERE id=?",(place_id,)); db.commit(); flash('Deleted.','info'); return redirect(url_for('admin_places'))

# Modules
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

# Entries
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

# Media
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
    db=get_db(); m=db.execute("SELECT * FROM media WHERE id=?",(mod_id,)).fetchone()
    if m:
        fp=os.path.join(app.config['UPLOAD_FOLDER'],m['filename'])
        if os.path.exists(fp): os.remove(fp)
        db.execute("DELETE FROM media WHERE id=?",(mod_id,)); db.commit()
    flash('Deleted.','info'); return redirect(url_for('admin_media'))

# Users
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

# Tags
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

# API
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

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'): return jsonify({'error':'Not found'}),404
    return render_template('frontend/404.html'),404

with app.app_context(): init_db(); seed_db()
if __name__=='__main__': app.run(debug=True,host='0.0.0.0',port=5000)
