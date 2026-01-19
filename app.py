from tempfile import template
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from pymongo import MongoClient, ReturnDocument
import os
import hashlib
from datetime import datetime
from bson.objectid import ObjectId
from flask import Flask, render_template, request, send_file
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
from collections import defaultdict
import json
from flask import make_response
import uuid
import requests
from collections import defaultdict
import uuid
from datetime import datetime
from collections import defaultdict
from flask_session import Session



app = Flask(__name__)
app.secret_key = "secret123"
qualified_courses_data = {}
app.config['SESSION_TYPE'] = 'filesystem'  # or 'mongodb' if you prefer
app.config['SESSION_PERMANENT'] = False
Session(app)

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

# MongoDB setup
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['course_checker']
# === ADD THIS ===
# Ensure push_subscriptions collection exists
if 'push_subscriptions' not in db.list_collection_names():
    # Create collection
    db.create_collection('push_subscriptions')
    print("✅ Created push_subscriptions collection")
    
    # Create indexes (optional but recommended)
    db['push_subscriptions'].create_index([("endpoint", 1)], unique=True)
    db['push_subscriptions'].create_index([("created_at", -1)])
    print("✅ Created indexes for push_subscriptions")
else:
    print("ℹ️ push_subscriptions collection already exists")
# === END ADDITION ===
courses_collection = db['courses']
institutions_collection = db['institutions']
counters_collection = db['counters']
clusters_collection = db['clusters']
diploma_collection = db['diploma']
certificate_collection = db['certificate']
payments_collection = db['payments']
results_collection = db['results']
kmtc_collection = db['kmtc']
# In your app.py, add these near other collection definitions
notifications_collection = db['notifications']
user_notifications_collection = db['user_notifications']

# Create indexes for better performance
user_notifications_collection.create_index([("user_id", 1), ("is_read", 1)])
user_notifications_collection.create_index([("user_id", 1), ("created_at", -1)])

# Add these collections with your other MongoDB collections
baskets_collection = db['baskets']
basket_items_collection = db['basket_items']

# Create indexes
baskets_collection.create_index([("email", 1), ("index_number", 1)], unique=True)
baskets_collection.create_index([("email", 1)])
baskets_collection.create_index([("last_updated", -1)])

basket_items_collection.create_index([("basket_id", 1), ("program_code", 1)], unique=True)
basket_items_collection.create_index([("basket_id", 1)])
SUBJECT_ALIASES = {
    "English": ["Eng", "ENG", "eng", "English", "english"],
    "Kiswahili": ["Kisw", "KIS", "kisw", "Kiswahili", "kiswahili"],
    "Mathematics": ["Math", "MAT", "math", "Mathematics", "mathematics", "Mat A", "MAT A", "mat a", "MAT B", "mat b", "Mat B", "Math A", "Math B"],
    "Biology": ["Bio", "BIO", "bio", "Biology", "biology"],
    "Chemistry": ["Chem", "CHE", "chem", "Chemistry", "chemistry"],
    "Physics": ["Phys", "PHY", "phys", "Physics", "physics"],
    "Geography": ["Geo", "GEO", "geo", "Geography", "geography"],
    "History": ["Hist", "HAG", "His", "HIS", "hist", "history", "hag", "Hag", "HIST"],
    "Christian Religious Education": ["CRE", "Cre", "cre", "Christian Religious Education"],
    "Islamic Religious Education": ["IRE", "Ire", "ire", "Islamic Religious Education"],
    "Hindu Religious Education": ["HRE", "Hre", "hre", "Hindu Religious Education"],
    "Agriculture": ["Agri", "AGR", "agri", "Agriculture", "agriculture"],
    "Computer Studies": ["Comp", "COMP", "comp", "Computer", "Computer Studies"],
    "Art and Design": ["Art", "ART", "art", "Art and Design", "Design", "design"],
    "Woodwork": ["Wood", "WOOD", "wood", "Woodwork"],
    "HomeScience": ["Home", "HOME", "home", "Home Science", "HomeScience", "HSC"],
    "Business Studies": ["BST", "BUS", "bst", "Business", "Business Studies", "business"],
    "Music": ["Music", "MUC", "music", "Muc"],
    "Building and Construction": ["Build", "BUILD", "build", "Building", "Construction", "Building and Construction"],
    "Electricity and Electronics": ["Elec", "ELEC", "elec", "Electricity", "Electronics", "Electricity and Electronics"],
    "Metalwork": ["Metal", "METAL", "metal", "Metalwork"],
    "French": ["French", "FRE", "fre", "Fren"],
    "German": ["German", "GER", "ger"],
    "Aviation": ["Aviation", "AVT", "avt", "aviation"],
    "General Science": ["GSC", "Gsc", "gsc", "General Science"],
    "Social Education and Ethics": ["SEE", "see", "Social Ethics", "Social Education and Ethics"],
    "Power Mechanics": ["PM", "pm", "Power Mechanics"],
    "Electricity": ["Elec", "Electricity", "ELEC"],
    "Drawing and Design": ["DRD", "drd", "Drawing and Design"],
    "Arabic": ["Arb", "ARB", "arb", "Arabic"],
    "Sign Language": ["KSL", "ksl", "Kenyan Sign Language"],
    "Agricultural Education": ["ARD", "ard", "Agricultural Education"],
    "Welding and Fabrication": ["WW", "ww", "Welding"],
    "Metal Work": ["MW", "mw", "Metal Work"],
    "Building Construction": ["BC", "bc", "Building Construction"],
    "Electricity Technology": ["ECT", "ect", "Electricity Technology"],
    "Aviation Technology": ["AVT", "avt", "Aviation Technology"],
    "Computer": ["CMP", "cmp", "Computer"],
    "Christian Religious Education": ["CRE", "cre", "Christian Religious Education"],
    "Islamic Religious Education": ["IRE", "ire", "Islamic Religious Education"],
    "Hindu Religious Education": ["HRE", "hre", "Hindu Religious Education"],
    "Business": ["BST", "bst", "Business"],
    "Music": ["MUC", "muc", "Music"]
}
subject_aliases = {}
for canonical, aliases in SUBJECT_ALIASES.items():
    for alias in aliases:
        subject_aliases[alias.strip().lower()] = canonical

def grade_to_points(grade):
    conversion = {
        'A': 12, 'A-': 11, 'B+': 10, 'B': 9, 'B-': 8,
        'C+': 7, 'C': 6, 'C-': 5, 'D+': 4, 'D': 3,
        'D-': 2, 'E': 1
    }
    if not grade or not isinstance(grade, str):
        return 0.0
    return conversion.get(grade.upper(), 0.0)

   

def initiate_paystack_payment(email, amount, callback_url):
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "email": email,
        "amount": int(amount * 100),  # Paystack uses kobo
        "callback_url": callback_url
    }
    response = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers)
    return response.json()
# ---------- Home Routes ----------
@app.route('/static/manifest.json')
def manifest():
    return send_file('static/manifest.json')

@app.route('/static/sw.js')
def sw():
    return send_file('static/sw.js', mimetype='application/javascript')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/input')
def input_form():
    return render_template('input.html')

@app.route('/diploma')
def diploma_form():
    return render_template('diploma.html')
from collections import defaultdict
@app.route('/certificate')
def certificate_form():
    return render_template('certificate.html')
@app.route('/kmtc')
def kmtc_form():
    return render_template('kmtc.html')
@app.route('/userguide')
def user_guide():
    return render_template('userguide.html')

def run_degree_eligibility(grades, cluster_points):
    qualified = []

    for course in courses_collection.find():
        cluster_num = course.get('cluster')
        requirements = course.get('requirements', [])
        institutions = course.get('institutions', [])

        for inst in institutions:
            inst_cutoff = float(inst.get('cutoff') or 0.0)
            if cluster_points.get(cluster_num, 0.0) < inst_cutoff:
                continue

            meets_all = True
            for req in requirements:
                if 'condition' in req:
                    condition_met = False
                    for cond in req['condition']:
                        alias = cond['subject'].strip()
                        grade = resolve_grade_from_alias(grades, alias)
                        score = grade_to_points(grade)
                        if score >= grade_to_points(cond['minGrade']):
                            condition_met = True
                            break
                    if not condition_met:
                        meets_all = False
                        break
                elif req.get('type') == 'multi':
                    pool = req['subject_pool']
                    min_points = grade_to_points(req['minGrade'])
                    required_count = req.get('requiredCount', 2)
                    passed = 0
                    for alias in pool:
                        grade = resolve_grade_from_alias(grades, alias)
                        score = grade_to_points(grade)
                        if score >= min_points:
                            passed += 1
                    if passed < required_count:
                        meets_all = False
                        break
                else:
                    req_subject = req.get('subject')
                    req_min = grade_to_points(req.get('minGrade'))
                    scores = []
                    for alias in req_subject.split('/'):
                        grade = resolve_grade_from_alias(grades, alias)
                        scores.append(grade_to_points(grade))
                    if max(scores) < req_min:
                        meets_all = False
                        break

            if meets_all:
                qualified.append({
                    'name': course.get('name', 'N/A'),
                    'cluster': cluster_num,
                    'requirements': requirements,
                    'institution': inst.get('name', 'N/A'),
                    'program_code': inst.get('program_code', 'N/A'),
                    'cutoff': inst_cutoff
                })

    cluster_name_map = {doc['number']: doc['name'] for doc in clusters_collection.find()}
    grouped = defaultdict(list)
    for item in qualified:
        grouped[item['cluster']].append(item)

    # ✅ Sort clusters numerically
    named_clusters = []
    for cluster_num in sorted(grouped.keys()):  # <--- this ensures Cluster 1 first
        items = grouped[cluster_num]
        named_clusters.append({
            'label': f"Cluster {cluster_num}: {cluster_name_map.get(cluster_num, 'Unknown')}",
            'courses': items
        })

    return named_clusters

@app.route('/download-pdf/<data_id>')
def download_pdf(data_id):
    # Ensure data exists
    if data_id not in qualified_courses_data:
        return "Reload page. Data not found. Please generate the courses list again.", 404
    
    data = qualified_courses_data[data_id]
    qualified_courses = data['qualified_courses']
    cluster_name_map = data.get('cluster_name_map', {})
    program_type = data.get('program_type', 'degree')  # store program_type when saving
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                 fontSize=16, spaceAfter=12, alignment=1,
                                 textColor=colors.darkblue)
    table_style = ParagraphStyle('TableStyle', parent=styles['Normal'],
                                 fontSize=9, leading=11, wordWrap='LTR')
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'],
                                  fontSize=10, textColor=colors.white, alignment=1)
    
    content = [Paragraph("QUALIFIED COURSES REPORT", title_style), Spacer(1, 0.3*inch)]
    
    if not qualified_courses:
        content.append(Paragraph("No qualified courses found.", styles['Normal']))
    else:
        # DEGREE → clustered with cutoff
        if program_type == 'degree':
            grouped_courses = defaultdict(list)
            for cluster in qualified_courses:
                cluster_label = cluster.get('label', 'Unknown')
                for course in cluster.get('courses', []):
                    grouped_courses[cluster_label].append(course)
            
            for cluster_label, courses in grouped_courses.items():
                content.append(Paragraph(f"<b>{cluster_label}</b>", styles['Heading2']))
                content.append(Spacer(1, 0.1*inch))
                
                table_data = [[
                    Paragraph('<b>Program Code</b>', header_style),
                    Paragraph('<b>Course Name</b>', header_style),
                    Paragraph('<b>Institution</b>', header_style),
                    Paragraph('<b>Cutoff</b>', header_style)
                ]]
                
                for course in sorted(courses, key=lambda x: x['program_code']):
                    cutoff_value = f"{course['cutoff']:.3f}" if course.get('cutoff') is not None else "N/A"
                    table_data.append([
                        Paragraph(str(course.get('program_code', 'N/A')), table_style),
                        Paragraph(str(course.get('name', 'N/A')), table_style),
                        Paragraph(str(course.get('institution', 'N/A')), table_style),
                        Paragraph(cutoff_value, table_style)
                    ])
                
                table = Table(table_data, repeatRows=1)
                table.setStyle(TableStyle([
                 ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                 ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                    ]))  # keep your styling
                content.append(table)
                content.append(Spacer(1, 0.3*inch))
        
        # DIPLOMA / CERTIFICATE → clustered, no cutoff
        elif program_type in ['diploma', 'certificate']:
            grouped_courses = defaultdict(list)
            for cluster in qualified_courses:
                cluster_label = cluster.get('label', 'Unknown')
                for course in cluster.get('courses', []):
                    grouped_courses[cluster_label].append(course)
            
            for cluster_label, courses in grouped_courses.items():
                content.append(Paragraph(f"<b>{cluster_label}</b>", styles['Heading2']))
                content.append(Spacer(1, 0.1*inch))
                
                table_data = [[
                    Paragraph('<b>Program Code</b>', header_style),
                    Paragraph('<b>Course Name</b>', header_style),
                    Paragraph('<b>Institution</b>', header_style)
                ]]
                
                for course in sorted(courses, key=lambda x: x['program_code']):
                    table_data.append([
                        Paragraph(str(course.get('program_code', 'N/A')), table_style),
                        Paragraph(str(course.get('name', 'N/A')), table_style),
                        Paragraph(str(course.get('institution', 'N/A')), table_style)
                    ])
                
                table = Table(table_data, repeatRows=1)
                table.setStyle(TableStyle([
                 ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                 ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                    ]))  # keep your styling
                content.append(table)
                content.append(Spacer(1, 0.3*inch))
        
        # KMTC → flat alphabetical list, no clusters, no cutoff
        if program_type == 'kmtc':
            table_data = [[
                Paragraph('<b>Program Code</b>', header_style),
                Paragraph('<b>Course Name</b>', header_style),
                Paragraph('<b>Institution</b>', header_style),
                Paragraph('<b>Requirements</b>', header_style)
           ]]

            for course in sorted(qualified_courses, key=lambda x: x['name']):
                reqs = ", ".join([f"{r['subject']} ≥ {r['minGrade']}" for r in course.get('requirements', [])])
                table_data.append([
                   Paragraph(str(course.get('program_code', 'N/A')), table_style),
                    Paragraph(str(course.get('name', 'N/A')), table_style),
                    Paragraph(str(course.get('institution', 'N/A')), table_style),
                    Paragraph(reqs, table_style)
               ])

            
            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                 ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                 ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                    ]))  # keep your styling
            content.append(table)
            content.append(Spacer(1, 0.3*inch))
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    
    # Clean up stored data
    if data_id in qualified_courses_data:
        del qualified_courses_data[data_id]
    
    return send_file(buffer,
                     as_attachment=True,
                     download_name='qualified_courses_report.pdf',
                     mimetype='application/pdf')

# ---------- Admin Routes ----------

@app.route('/admin')
def admin_dashboard():
    return render_template('admin/dashboard.html')

# ----- Institutions -----

@app.route('/admin/institutions')
def list_institutions():
    institutions = list(institutions_collection.find())
    return render_template('admin/list_institutions.html', institutions=institutions)

@app.route('/admin/institutions/add', methods=['GET', 'POST'])
def add_institutions():
    if request.method == 'POST':
        raw_input = request.form.get('institutions')
        if raw_input:
            institution_list = [name.strip() for name in raw_input.split('\n') if name.strip()]
            inserted = 0
            for name in institution_list:
                if not institutions_collection.find_one({"name": name}):
                    institutions_collection.insert_one({"name": name})
                    inserted += 1
            return render_template("admin/add_institutions.html", success=True, count=inserted)
    
    return render_template("admin/add_institutions.html")

@app.route('/admin/institutions/edit/<id>', methods=['GET', 'POST'])
def edit_institution(id):
    institution = institutions_collection.find_one({'_id': ObjectId(id)})
    if not institution:
        return "Institution not found", 404

    if request.method == 'POST':
        new_name = request.form.get('name').strip()
        if new_name:
            institutions_collection.update_one({'_id': ObjectId(id)}, {'$set': {'name': new_name}})
            return redirect(url_for('list_institutions'))

    return render_template('admin/edit_institution.html', institution=institution)

@app.route('/admin/institutions/delete/<id>', methods=['POST'])
def delete_institution(id):
    institutions_collection.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('list_institutions'))
# ----- Courses -----

# Show all courses (Admin view)
@app.route('/admin/courses')
def list_courses():
    courses = list(courses_collection.find())
    return render_template('admin/list_courses.html', courses=courses)

@app.route('/admin/courses/add', methods=['GET', 'POST'])
def add_course():
    institutions = list(institutions_collection.find())
    clusters = list(db.clusters.find({}).sort("number"))

    if request.method == 'POST':
        name = request.form.get('name')
        cluster = int(request.form.get('cluster'))

        # Institutions
        institution_names = request.form.getlist('institution_names[]')
        program_codes = request.form.getlist('program_codes[]')
        cutoffs = request.form.getlist('cutoffs[]')

        institutions_data = []
        for i in range(len(institution_names)):
            institutions_data.append({
                "name": institution_names[i],
                "program_code": program_codes[i],
                "cutoff": float(cutoffs[i])
            })

        # Subject requirements
        subjects = request.form.getlist('subjects[]')
        min_grades = request.form.getlist('min_grades[]')

        requirements = []
        for i in range(len(subjects)):
         requirements.append({
          'subject': subjects[i],        # e.g. 'Eng/Kisw'
          'minGrade': min_grades[i]      # e.g. 'B'
    })


        courses_collection.insert_one({
            "name": name,
            "cluster": cluster,
            "institutions": institutions_data,
            "requirements": requirements
        })

        return redirect('/admin/courses')

    return render_template('admin/add_course.html',clusters=clusters, institutions=institutions)
# Delete course
@app.route('/admin/delete_course/<course_id>')
def delete_course(course_id):
    courses_collection.delete_one({'_id': ObjectId(course_id)})
    flash("Course deleted successfully!", "success")
    return redirect(url_for('list_courses'))

# Edit course (GET to show form, POST to save changes)
@app.route('/admin/edit_course/<course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    course = courses_collection.find_one({'_id': ObjectId(course_id)})

    if request.method == 'POST':
        name = request.form.get('name')
        cluster = int(request.form.get('cluster'))

        # Institutions
        institutions = []
        names = request.form.getlist('institution_names[]')
        codes = request.form.getlist('program_codes[]')
        cutoffs = request.form.getlist('cutoffs[]')

        for n, c, cutoff in zip(names, codes, cutoffs):
            institutions.append({
                'name': n,
                'program_code': c,
                'cutoff': float(cutoff)
            })

        # Requirements
        requirements = []
        subjects = request.form.getlist('subjects[]')
        min_grades = request.form.getlist('min_grades[]')

        for s, g in zip(subjects, min_grades):
            requirements.append({
                'subject': s,
                'minGrade': g
            })

        # Update DB
        courses_collection.update_one(
            {'_id': ObjectId(course_id)},
            {'$set': {
                'name': name,
                'cluster': cluster,
                'institutions': institutions,
                'requirements': requirements
            }}
        )

        flash("Course updated successfully!", "success")
        return redirect(url_for('list_courses'))

    # Show the edit form
    institutions = list(db.institutions.find())
    return render_template('admin/edit_course.html', course=course, institutions=institutions)



from collections import defaultdict
def resolve_grade_from_alias(grades, alias):
    alias = alias.strip().lower()
    for canonical, aliases in SUBJECT_ALIASES.items():
        if alias in [a.lower() for a in aliases]:
            return grades.get(canonical) or grades.get(canonical.lower())
    return None

def run_diploma_eligibility(grades):
    main_grade = grades.get('main_grade')
    if isinstance(main_grade, list):
        main_grade = main_grade[0] if main_grade else None
    main_points = grade_to_points(main_grade) if main_grade else 0.0
    qualified = []

    for course in diploma_collection.find():
        requirements = course.get('requirements', [])
        institutions = course.get('institutions', [])
        meets_all = True

        for req in requirements:
            req_subject = req.get('subject', '')
            req_min = grade_to_points(req.get('minGrade'))
            scores = []

            for alias in req_subject.split('/'):
             grade = resolve_grade_from_alias(grades, alias)
             score = grade_to_points(grade)
            

             scores.append(score)
            user_score = max(scores) if scores else 0.0
            if user_score < req_min:
                meets_all = False
                break

        min_required = grade_to_points(course.get('min_grade'))
        if meets_all and main_points >= min_required:
            for inst in institutions:
                qualified.append({
                    'name': course.get('name', 'N/A'),
                    'cluster': course.get('cluster', 'N/A'),
                    'requirements': requirements,
                    'institution': inst.get('name', 'N/A'),
                    'program_code': inst.get('program_code', 'N/A')
                })

    grouped = defaultdict(list)
    for item in qualified:
        grouped[item['cluster']].append(item)

    named_clusters = []
    for cluster_name, items in grouped.items():
        named_clusters.append({
            'label': cluster_name,
            'courses': items
        })

    return named_clusters

from collections import defaultdict

def run_certificate_eligibility(grades):
    main_grade = grades.get('main_grade')
    main_points = grade_to_points(main_grade) if main_grade else 0.0
    qualified = []

    for course in certificate_collection.find():
        requirements = course.get('requirements', [])
        institutions = course.get('institutions', [])
        meets_all = True

        for req in requirements:
            req_subject = req.get('subject')
            req_min = grade_to_points(req.get('minGrade'))
            scores = []

            for alias in req_subject.split('/'):
                grade = resolve_grade_from_alias(grades, alias)
                score = grade_to_points(grade)
                scores.append(score)

            user_score = max(scores) if scores else 0.0
            if user_score < req_min:
                meets_all = False
                break

        min_required = grade_to_points(course.get('min_grade'))
        if meets_all and main_points >= min_required:
            for inst in institutions:
                qualified.append({
                    'name': course.get('name', 'N/A'),
                    'cluster': course.get('cluster', 'N/A'),
                    'requirements': requirements,
                    'institution': inst.get('name', 'N/A'),
                    'program_code': inst.get('program_code', 'N/A')
                })

    grouped = defaultdict(list)
    for item in qualified:
        grouped[item['cluster']].append(item)

    named_clusters = []
    for cluster_name, items in grouped.items():
        named_clusters.append({
            'label': cluster_name,
            'courses': items
        })

    return named_clusters


def run_kmtc_eligibility(grades):
    main_grade = grades.get('main_grade')
    main_points = grade_to_points(main_grade) if main_grade else 0.0
    qualified = []

    for course in kmtc_collection.find():
        requirements = course.get('requirements', [])
        institutions = course.get('institutions', [])
        meets_all = True

        # Check subject requirements
        for req in requirements:
            req_subject = req.get('subject')
            req_min = grade_to_points(req.get('minGrade'))
            scores = []

            for alias in req_subject.split('/'):
                grade = resolve_grade_from_alias(grades, alias)
                score = grade_to_points(grade)
                scores.append(score)

            user_score = max(scores) if scores else 0.0
            if user_score < req_min:
                meets_all = False
                break

        # Check minimum overall grade requirement
        min_required = grade_to_points(course.get('min_grade'))
        if meets_all and main_points >= min_required:
            for inst in institutions:
                qualified.append({
                    'name': course.get('name', 'N/A'),
                    'requirements': requirements,
                    'institution': inst.get('name', 'N/A'),
                    'program_code': inst.get('program_code', 'N/A')
                })

    # ✅ Sort alphabetically by course name
    qualified_sorted = sorted(qualified, key=lambda x: x['name'])

    return qualified_sorted

def normalize_mongo_grades(raw_grades):
    normalized = {}
    for key, value in raw_grades.items():
        if key.startswith("grades[") and key.endswith("]"):
            alias = key[7:-1].strip().lower()
            canonical = subject_aliases.get(alias, alias)
            normalized[canonical] = value
        elif key == "main_grade":
            normalized["main_grade"] = value
    return normalized
@app.route('/start-check', methods=['POST'])
def start_check():
    program_type = request.form.get('program_type')  # 'degree', 'diploma', or 'certificate'
    session['program_type'] = program_type

    if program_type == 'degree':
        # Store cluster points
        cluster_points = {}
        for i in range(1, 21):
            val = request.form.get(f'clusters[{i}]')
            try:
                cluster_points[i] = float(val)
            except (TypeError, ValueError):
                cluster_points[i] = 0.0
        session['cluster_points'] = cluster_points

    # Store raw grades for all programs
    def flatten_grades(raw_grades):
     return {k: (v[0] if isinstance(v, list) and v else '') for k, v in raw_grades.items()}

    session['raw_grades'] = flatten_grades(request.form.to_dict(flat=False))

    return redirect(url_for('payment_page'))
@app.route('/payment', methods=['GET', 'POST'])
def payment_page():
    program_type = session.get('program_type')
    if not program_type:
        return redirect(url_for('home'))  # fallback if session is missing

    if request.method == 'POST':
        email = request.form['email']
        index_number = request.form['index_number']
        session['email'] = email
        session['index_number'] = index_number

        # Check if user has paid for any program before
        existing = payments_collection.find_one({
            'email': email,
            'index_number': index_number
        })

        # Determine amount
        already_paid_for = existing.get('program_type') if existing else None
        amount = 199 if not already_paid_for else 99
        session['amount'] = amount

        # Initiate Paystack
        callback_url = url_for('verify_payment', _external=True)
        paystack_response = initiate_paystack_payment(email, amount, callback_url)
        if paystack_response.get('status') and paystack_response['data'].get('authorization_url'):
            return redirect(paystack_response['data']['authorization_url'])
        else:
            return "Payment initiation failed. Please try again."

    return render_template('payment.html', program_type=program_type)
@app.route('/verify_payment')
def verify_payment():
    ref = request.args.get('reference')
    if not ref:
        return "Missing payment reference."

    # Verify with Paystack
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }
    response = requests.get(f"https://api.paystack.co/transaction/verify/{ref}", headers=headers)
    data = response.json()

    if not data.get('status') or data['data']['status'] != 'success':
        return "Payment verification failed."

    # Mark session as paid
    session['payment_status'] = 'paid'

    # Extract session data
    email = session.get('email')
    index = session.get('index_number')
    program = session.get('program_type')
    amount = session.get('amount')
    raw_grades = session.get('raw_grades', {})
    grades = normalize_mongo_grades(raw_grades)
    cluster_points = session.get('cluster_points', {}) if program == 'degree' else {}

    # Run eligibility logic
    if program == 'degree':
        results = run_degree_eligibility(grades, cluster_points)
    elif program == 'diploma':
        results = run_diploma_eligibility(grades)
    elif program == 'certificate':
        results = run_certificate_eligibility(grades)
    elif program == 'kmtc':
        results = run_kmtc_eligibility(grades)
    else:
        return "Invalid program type."
    data_id = str(uuid.uuid4())
    cluster_name_map = {doc['number']: doc['name'] for doc in clusters_collection.find()}

    qualified_courses_data[data_id] = {
     'qualified_courses': results,
     'cluster_name_map': cluster_name_map
}


    session['pdf_data_id'] = data_id  # optional: pass to frontend
    # Save to DB
    doc = {
    "email": email,
    "index_number": index,
    "program_type": program,
    "amount": amount,
    "paystack_ref": ref,
    "paid_at": datetime.utcnow(),
    "grades": grades
}

    if program == 'degree' and cluster_points:
      doc["cluster_points"] = {str(k): v for k, v in cluster_points.items()}

    payments_collection.insert_one(doc)
    results_collection.insert_one({
        "email": email,
        "index_number": index,
        "program_type": program,
        "results": results,
        "generated_at": datetime.utcnow()
    })
    print("Session at verify_payment:", dict(session))

    # Store results in session for rendering
    session['results'] = results
    return redirect(url_for('unified_results'))

@app.route('/unified-results')
def unified_results():
    """Unified results page for all program types"""
    if session.get('payment_status') != 'paid':
        return redirect(url_for('payment_page'))

    program = session.get('program_type')
    raw_grades = session.get('raw_grades', {})
    grades = normalize_mongo_grades(raw_grades)
    cluster_points = session.get('cluster_points', {})
    email = session.get('email')
    index = session.get('index_number')

    if not program or not email or not index:
        return redirect(url_for('home'))

    # Run eligibility logic
    if program == 'degree':
        raw_results = run_degree_eligibility(grades, cluster_points)
        result_type = 'clustered'
    elif program == 'diploma':
        raw_results = run_diploma_eligibility(grades)
        result_type = 'clustered'
    elif program == 'certificate':
        raw_results = run_certificate_eligibility(grades)
        result_type = 'clustered'
    elif program == 'kmtc':
        raw_results = run_kmtc_eligibility(grades)
        result_type = 'flat'
    else:
        return "Invalid program type.", 400

    # Debug: Check what's returned
    print(f"\n=== {program.upper()} RESULTS DEBUG ===")
    print(f"Type: {type(raw_results)}")
    
    # Process results to ensure consistent structure
    results_data = []
    
    if result_type == 'clustered':
        # Handle clustered data
        if isinstance(raw_results, list):
            for i, item in enumerate(raw_results):
                if isinstance(item, dict) and 'courses' in item:
                    # Already has correct structure
                    if 'label' not in item:
                        item['label'] = f"Cluster {i+1}"
                    results_data.append(item)
                elif isinstance(item, dict):
                    # Try to find courses
                    for key, value in item.items():
                        if isinstance(value, list) and len(value) > 0:
                            # Check if this looks like courses
                            if isinstance(value[0], dict) and ('program_code' in value[0] or 'name' in value[0]):
                                results_data.append({
                                    'label': f"Cluster {i+1}",
                                    'courses': value
                                })
                                break
                elif isinstance(item, list):
                    # Item is directly courses list
                    results_data.append({
                        'label': f"Cluster {i+1}",
                        'courses': item
                    })
        elif isinstance(raw_results, dict):
            # Single cluster
            if 'courses' in raw_results:
                if 'label' not in raw_results:
                    raw_results['label'] = "Results"
                results_data.append(raw_results)
    else:
        # Flat data (KMTC)
        results_data = raw_results if isinstance(raw_results, list) else []

    # Debug output
    if result_type == 'clustered':
        total_courses = 0
        for i, cluster in enumerate(results_data):
            course_count = len(cluster.get('courses', []))
            print(f"Cluster {i+1}: {course_count} courses")
            total_courses += course_count
        print(f"TOTAL: {total_courses} courses in {len(results_data)} clusters")
    else:
        print(f"KMTC: {len(results_data)} courses")
    print("========================\n")

    # Generate PDF data ID
    data_id = str(uuid.uuid4())
    cluster_name_map = {doc['number']: doc['name'] for doc in clusters_collection.find()}
    
    qualified_courses_data[data_id] = {
        'qualified_courses': results_data,
        'cluster_name_map': cluster_name_map,
        'program_type': program
    }
    session['pdf_data_id'] = data_id

    # Store in session
    session['results_data'] = results_data
    session['result_type'] = result_type

    return render_template('unified_results.html',
                         generated_time=datetime.now().strftime('%Y-%m-%d %H:%M'),
                         program_type=program,
                         results_data=results_data,
                         result_type=result_type,
                         email=email,
                         index_number=index,
                         pdf_data_id=data_id,
                         cluster_name_map=cluster_name_map)

@app.route('/alreadypaid')
def already_paid_form():
    return render_template('alreadypaid.html')
@app.route('/view-paid-results', methods=['POST'])
def view_paid_results():
    index_number = request.form.get('index_number', '').strip()
    email = request.form.get('email', '').strip().lower()
    program_type = request.form.get('program_type', '').strip().lower()

    if not index_number or not email or not program_type:
        return "Missing required fields.", 400

    # Check payment
    paid = payments_collection.find_one({
        'index_number': index_number,
        'email': email,
        'program_type': program_type,
    })

    if not paid:
        return "No payment record found for this combination.", 404

    # Fetch results
    result_doc = results_collection.find_one({
        'index_number': index_number,
        'email': email,
        'program_type': program_type
    })

    if not result_doc or 'results' not in result_doc:
        return "Results not found. Please contact support.", 404

    # Determine result type
    if program_type == 'kmtc':
        result_type = 'flat'
    else:
        result_type = 'clustered'

    # Pass to unified template
    return render_template('unified_results.html',
                         program_type=program_type,
                         results_data=result_doc['results'],
                         result_type=result_type,
                         email=email,
                         index_number=index_number,
                         pdf_data_id=str(uuid.uuid4()),  # Generate new ID for PDF
                         is_paid_view=True)  # Flag to indicate this is paid results view
    


@app.route('/subscribe', methods=['POST'])
def subscribe():
    try:
        print("=== SUBSCRIBE ENDPOINT CALLED ===")
        subscription_data = request.get_json()
        print(f"Received data: {json.dumps(subscription_data, indent=2)[:500]}...")
        
        if not subscription_data:
            print("❌ No subscription data provided")
            return jsonify({"error": "No subscription data provided"}), 400
        
        endpoint = subscription_data.get('endpoint')
        keys = subscription_data.get('keys')
        
        print(f"Endpoint: {endpoint}")
        print(f"Keys present: {bool(keys)}")
        
        if not endpoint or not keys:
            print("❌ Invalid subscription format")
            return jsonify({"error": "Invalid subscription format"}), 400
        
        # Save subscription to MongoDB
        subscriptions_collection = db['push_subscriptions']
        
        print(f"Inserting into collection: push_subscriptions")
        
        # Check if subscription already exists
        existing = subscriptions_collection.find_one({"endpoint": endpoint})
        
        if existing:
            print("⚠️ Updating existing subscription")
            result = subscriptions_collection.update_one(
                {"endpoint": endpoint},
                {"$set": {
                    **subscription_data,
                    "updated_at": datetime.utcnow()
                }}
            )
            print(f"Update result: {result.modified_count} modified")
        else:
            print("✅ Inserting new subscription")
            result = subscriptions_collection.insert_one({
                **subscription_data,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            print(f"Insert ID: {result.inserted_id}")
        
        # Verify it was saved
        count = subscriptions_collection.count_documents({"endpoint": endpoint})
        print(f"✅ Verification: Subscription exists in DB = {count > 0}")
        
        print(f"Subscription saved for endpoint: {endpoint[:50]}...")
        return jsonify({"success": True, "message": "Subscription saved"}), 200
        
    except Exception as e:
        print(f"❌ Error saving subscription: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@app.route("/admin/notifications")
def admin_notifications():
    # You could also check if admin is logged in here
    return render_template("admin_notifications.html")

from pywebpush import webpush, WebPushException

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_CLAIMS = {"sub": "mailto:kuccpshelpdesk.ke@gmail.com"}

# ---------- COLLECTION SETUP ----------

collections = ['notifications', 'global_notifications', 'user_notifications']
for col in collections:
    if col not in db.list_collection_names():
        db.create_collection(col)

notifications_collection = db['notifications']              # Admin history
global_notifications_collection = db['global_notifications']  # Broadcast
user_notifications_collection = db['user_notifications']      # Per-user inbox


# ---------- INDEXES (CRITICAL) ----------

user_notifications_collection.create_index(
    [("user_id", 1), ("notification_id", 1)],
    unique=True
)
user_notifications_collection.create_index([("user_id", 1), ("is_read", 1)])
user_notifications_collection.create_index([("user_id", 1), ("created_at", -1)])
global_notifications_collection.create_index([("created_at", -1)])


# ---------- ANONYMOUS USER (COOKIE BASED) ----------

@app.before_request
def ensure_anon_user():
    if 'anon_user_id' not in request.cookies:
        g.new_anon_user = str(uuid.uuid4())
    else:
        g.new_anon_user = None


@app.after_request
def set_anon_cookie(response):
    if g.get('new_anon_user'):
        response.set_cookie(
            'anon_user_id',
            g.new_anon_user,
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            samesite='Lax'
        )
    return response


def get_user_id():
    return request.cookies.get('anon_user_id')
def deliver_global_notifications(user_id):
    """
    Copies global notifications to user_notifications if not already delivered.
    Uses upsert to avoid duplicates.
    """
    global_notifs = list(global_notifications_collection.find().sort("created_at", -1).limit(10))
    for notif in global_notifs:
        try:
            user_notifications_collection.update_one(
                {
                    "user_id": user_id,
                    "notification_id": notif["_id"]
                },
                {
                    "$setOnInsert": {
                        "title": notif["title"],
                        "message": notif["message"],
                        "type": notif.get("type", "info"),
                        "is_urgent": notif.get("is_urgent", False),
                        "is_read": False,
                        "created_at": notif["created_at"]
                    }
                },
                upsert=True
            )
        except Exception as e:
            print(f"Failed to deliver notification: {e}")



# Collections
notifications_collection = db['notifications']
global_notifications_collection = db['global_notifications']
user_notifications_collection = db['user_notifications']

# Indexes (ensure unique for user notifications)
user_notifications_collection.create_index(
    [("user_id", 1), ("notification_id", 1)],
    unique=True
)
global_notifications_collection.create_index([("created_at", -1)])
notifications_collection.create_index([("created_at", -1)])

# -------------------- Admin: Manage Notifications --------------------
@app.route('/admin/notifications/manage')
def manage_notifications():
    """Admin page to manage notifications"""
    admin_key = request.args.get('admin_key')
    if admin_key != os.getenv('ADMIN_KEY', 'kuccps-admin-2026'):
        return "Unauthorized", 401

    notifications = list(notifications_collection.find().sort("created_at", -1))
    
    stats = {
        "total": notifications_collection.count_documents({}),
        "active": global_notifications_collection.count_documents({}),
        "sent_today": notifications_collection.count_documents({
            "created_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0)}
        })
    }
    
    return render_template('admin/manage_notifications.html', 
                           notifications=notifications,
                           stats=stats)

# -------------------- Admin: Send Notification --------------------
@app.route('/admin/notification/send', methods=['POST'])
def send_notification():
    """Admin endpoint to send a notification with rich formatting support"""
    admin_key = request.form.get('admin_key')
    if admin_key != os.getenv('ADMIN_KEY', 'kuccps-admin-2026'):
        return jsonify({"error": "Unauthorized"}), 401

    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    notification_type = request.form.get('type', 'info')
    target_group = request.form.get('target_group', 'all')
    is_urgent = request.form.get('is_urgent') == 'true'
    enable_rich_formatting = request.form.get('rich_formatting', 'true') == 'true'

    if not title or not message:
        return jsonify({"error": "Title and message are required"}), 400

    # Process message with rich formatting
    processed_message = message
    
    if enable_rich_formatting:
        # Preserve new lines for HTML display (convert \n to <br>)
        html_message = message.replace('\n', '<br>')
        
        # Auto-detect and convert URLs to clickable links
        import re
        
        # Pattern for URLs
        url_pattern = r'(https?://\S+|www\.\S+)'
        
        def make_clickable(match):
            url = match.group(0)
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            return f'<a href="{url}" target="_blank" style="color: #3498db; text-decoration: underline;">{match.group(0)}</a>'
        
        html_message = re.sub(url_pattern, make_clickable, html_message)
        
        # Pattern for email addresses
        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        html_message = re.sub(email_pattern, r'<a href="mailto:\1" style="color: #27ae60;">\1</a>', html_message)
        
        # Pattern for phone numbers (Kenyan format)
        phone_pattern = r'(\+?254[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{3}|07[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{3})'
        html_message = re.sub(phone_pattern, r'<a href="tel:\1" style="color: #e74c3c;">\1</a>', html_message)
        
        # Pattern for important keywords (bold)
        keywords = ['deadline', 'urgent', 'important', 'required', 'action needed', 'deadline', 'final']
        for keyword in keywords:
            if keyword in message.lower():
                html_message = re.sub(fr'\b({keyword})\b', r'<strong>\1</strong>', html_message, flags=re.IGNORECASE)
        
        # Add paragraphs for better structure
        paragraphs = html_message.split('<br><br>')
        if len(paragraphs) > 1:
            html_message = ''.join([f'<p style="margin-bottom: 10px;">{p}</p>' for p in paragraphs])
        
        # Store both plain and HTML versions
        processed_message = html_message
        plain_message = message  # Keep original for push notifications

    notification_id = str(ObjectId())
    now = datetime.utcnow()

    # Save to admin notifications with both versions
    admin_notification = {
        "_id": notification_id,
        "title": title,
        "message": plain_message if enable_rich_formatting else message,  # Store plain version
        "html_message": processed_message if enable_rich_formatting else None,  # Store HTML version if enabled
        "type": notification_type,
        "target_group": target_group,
        "is_urgent": is_urgent,
        "is_active": True,
        "created_at": now,
        "created_by": "admin",
        "has_rich_formatting": enable_rich_formatting,
        "version": 2  # Version to identify rich formatted notifications
    }
    
    notifications_collection.insert_one(admin_notification)

    # Save to global notifications with both versions
    global_notification = {
        "_id": notification_id,
        "title": title,
        "message": plain_message if enable_rich_formatting else message,
        "html_message": processed_message if enable_rich_formatting else None,
        "type": notification_type,
        "is_urgent": is_urgent,
        "created_at": now,
        "target_group": target_group,
        "is_global": True,
        "is_active": True,
        "user_count": 0,
        "has_rich_formatting": enable_rich_formatting,
        "version": 2
    }
    
    global_notifications_collection.insert_one(global_notification)

    # Save to user-specific notifications for targeted groups
    users_collection = db['users']  # Assuming you have a users collection
    
    if target_group != 'all':
        # Query users based on target group
        query = {}
        if target_group == 'paid':
            query = {"has_paid": True}
        elif target_group == 'degree':
            query = {"program_type": "degree"}
        elif target_group == 'diploma':
            query = {"program_type": "diploma"}
        elif target_group == 'certificate':
            query = {"program_type": "certificate"}
        elif target_group == 'kmtc':
            query = {"program_type": "kmtc"}
        
        users = list(users_collection.find(query, {'_id': 1}))
        
        # Create user notifications
        user_notifications = []
        for user in users:
            user_notifications.append({
                "_id": str(ObjectId()),
                "notification_id": notification_id,
                "user_id": user['_id'],
                "title": title,
                "message": plain_message if enable_rich_formatting else message,
                "html_message": processed_message if enable_rich_formatting else None,
                "type": notification_type,
                "is_urgent": is_urgent,
                "is_read": False,
                "created_at": now,
                "has_rich_formatting": enable_rich_formatting,
                "version": 2
            })
        
        if user_notifications:
            db['user_notifications'].insert_many(user_notifications)
    else:
        # For all users, you might want to handle differently
        # Either create notifications for all users or mark as global
        pass

    # Push notifications (optional)
    push_sent = 0
    if 'push_subscriptions' in db.list_collection_names():
        try:
            # For push notifications, use plain text version
            push_body = plain_message if enable_rich_formatting else message
            
            # Truncate if too long for push notification
            if len(push_body) > 200:
                push_body = push_body[:197] + "..."
            
            push_data = {
                "title": title,
                "body": push_body,
                "url": "/notifications",
                "icon": "/static/icon-192.png",
                "notification_id": notification_id,
                "type": notification_type,
                "urgent": is_urgent,
                "actions": [
                    {"action": "view", "title": "View Details"},
                    {"action": "dismiss", "title": "Dismiss"}
                ]
            }
            
            subscriptions = list(db['push_subscriptions'].find())
            for sub in subscriptions:
                try:
                    sub_info = {k: v for k, v in sub.items() if k != "_id"}
                    webpush(
                        subscription_info=sub_info,
                        data=json.dumps(push_data),
                        vapid_private_key=os.getenv("VAPID_PRIVATE_KEY"),
                        vapid_claims={"sub": "mailto:admin@example.com"}
                    )
                    push_sent += 1
                except Exception as e:
                    print(f"Push error for subscription {sub.get('_id')}: {e}")
                    # Optionally remove invalid subscriptions
                    # db['push_subscriptions'].delete_one({"_id": sub['_id']})
                    
        except Exception as e:
            print(f"Push error: {e}")

    # Log the notification
    print(f"Notification sent: {title} | Type: {notification_type} | Target: {target_group} | Rich Formatting: {enable_rich_formatting}")

    return jsonify({
        "success": True, 
        "notification_id": notification_id, 
        "push_sent": push_sent,
        "has_rich_formatting": enable_rich_formatting,
        "message_preview": plain_message[:100] + "..." if len(plain_message) > 100 else plain_message
    })

# -------------------- Admin: Delete Notification --------------------
@app.route('/admin/notification/delete/<notification_id>', methods=['POST'])
def delete_notification(notification_id):
    admin_key = request.form.get('admin_key')
    if admin_key != os.getenv('ADMIN_KEY', 'kuccps-admin-2026'):
        return jsonify({"error": "Unauthorized"}), 401

    result_admin = notifications_collection.delete_one({"_id": notification_id})
    result_global = global_notifications_collection.delete_one({"_id": notification_id})
    result_user = user_notifications_collection.delete_many({"notification_id": notification_id})

    return jsonify({
        "success": True,
        "deleted_admin": result_admin.deleted_count,
        "deleted_global": result_global.deleted_count,
        "deleted_user": result_user.deleted_count,
        "notification_id": notification_id
    })


# ---------- FETCH RECENT (NO INSERTS HERE) ----------

@app.route('/api/notifications/recent')
def get_recent_notifications():
    user_id = get_user_id()
    deliver_global_notifications(user_id)

    notifications = list(
        user_notifications_collection
        .find({"user_id": user_id})
        .sort("created_at", -1)
        .limit(10)
    )

    for n in notifications:
        n["_id"] = str(n["_id"])

    return jsonify({"notifications": notifications})


# ---------- UNREAD COUNT ----------

@app.route('/api/notifications/unread-count')
def get_unread_count():
    user_id = get_user_id()
    if not user_id:
        return jsonify({"count": 0})

    count = user_notifications_collection.count_documents({
        "user_id": user_id,
        "is_read": False
    })

    return jsonify({"count": count})


# ---------- MARK ALL AS READ ----------

@app.route('/api/notifications/mark-all-read', methods=['POST'])
def mark_all_read():
    user_id = get_user_id()

    user_notifications_collection.update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
    )

    return jsonify({"success": True})


# ---------- NOTIFICATIONS PAGE ----------

@app.route('/notifications')
def notifications_page():
    user_id = get_user_id()
    deliver_global_notifications(user_id)

    notifications = list(
        user_notifications_collection
        .find({"user_id": user_id})
        .sort("created_at", -1)
    )

    for n in notifications:
        n["_id"] = str(n["_id"])

    # Mark all as read
    user_notifications_collection.update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
    )

    # Render notifications page
    return render_template("notifications.html", notifications=notifications)


# Add this route to your Flask app
@app.route('/basket')
def basket():
    # Get student info from URL parameters
    email = request.args.get('email', '')
    index_number = request.args.get('index', '')
    
    # If not provided in URL, try to get from session (for backward compatibility)
    if not email:
        email = session.get('email', '')
    if not index_number:
        index_number = session.get('index_number', '')
    
    return render_template('basket.html', 
                         email=email,
                         index_number=index_number)

# ===== BASKET API ENDPOINTS =====

@app.route('/api/basket/save', methods=['POST'])
def save_basket():
    """Save basket to database using email and index"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        email = data.get('email')
        index_number = data.get('index_number')
        items = data.get('items', [])
        
        if not email or not index_number:
            return jsonify({"error": "Email and index number required"}), 400
        
        # Create basket identifier
        basket_id = f"{email}_{index_number}"
        
        # Get or create basket
        basket = baskets_collection.find_one({"email": email, "index_number": index_number})
        
        now = datetime.utcnow()
        
        if not basket:
            # Create new basket
            basket_data = {
                "basket_id": basket_id,
                "email": email,
                "index_number": index_number,
                "created_at": now,
                "last_updated": now,
                "item_count": len(items),
                "program_types": list(set([item.get('program_type') for item in items if item.get('program_type')]))
            }
            baskets_collection.insert_one(basket_data)
            basket = basket_data
        else:
            # Update existing basket
            baskets_collection.update_one(
                {"email": email, "index_number": index_number},
                {
                    "$set": {
                        "last_updated": now,
                        "item_count": len(items),
                        "program_types": list(set([item.get('program_type') for item in items if item.get('program_type')]))
                    }
                }
            )
        
        # Clear old items
        basket_items_collection.delete_many({"basket_id": basket_id})
        
        # Insert new items
        if items:
            items_to_insert = []
            for item in items:
                item_doc = {
                    "_id": str(ObjectId()),
                    "basket_id": basket_id,
                    "program_code": item.get('program_code'),
                    "course_name": item.get('course_name'),
                    "institution": item.get('institution'),
                    "program_type": item.get('program_type'),
                    "cutoff": item.get('cutoff'),
                    "cluster": item.get('cluster'),
                    "priority": item.get('priority', 0),
                    "added_at": now,
                    "updated_at": now
                }
                items_to_insert.append(item_doc)
            
            if items_to_insert:
                basket_items_collection.insert_many(items_to_insert)
        
        return jsonify({
            "success": True,
            "message": "Basket saved successfully",
            "basket_id": basket_id,
            "count": len(items),
            "last_updated": now.isoformat()
        })
        
    except Exception as e:
        print(f"Error saving basket: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/basket/load', methods=['POST'])
def load_basket():
    """Load basket from database using email and index"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        email = data.get('email')
        index_number = data.get('index_number')
        
        if not email or not index_number:
            return jsonify({"error": "Email and index number required"}), 400
        
        basket_id = f"{email}_{index_number}"
        
        # Find basket
        basket = baskets_collection.find_one({"email": email, "index_number": index_number})
        
        if not basket:
            return jsonify({
                "success": True,
                "exists": False,
                "items": [],
                "count": 0
            })
        
        # Get basket items
        items = list(basket_items_collection.find({"basket_id": basket_id}))
        
        # Format items for frontend
        formatted_items = []
        for item in items:
            formatted_items.append({
                "program_code": item.get('program_code'),
                "course_name": item.get('course_name'),
                "institution": item.get('institution'),
                "program_type": item.get('program_type'),
                "cutoff": item.get('cutoff'),
                "cluster": item.get('cluster'),
                "priority": item.get('priority', 0)
            })
        
        return jsonify({
            "success": True,
            "exists": True,
            "items": formatted_items,
            "count": len(formatted_items),
            "last_updated": basket.get('last_updated').isoformat() if basket.get('last_updated') else None
        })
        
    except Exception as e:
        print(f"Error loading basket: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/basket/add-item', methods=['POST'])
def add_basket_item():
    """Add single item to basket"""
    try:
        data = request.get_json()
        email = data.get('email')
        index_number = data.get('index_number')
        item_data = data.get('item')
        
        if not email or not index_number or not item_data:
            return jsonify({"error": "Missing required data"}), 400
        
        basket_id = f"{email}_{index_number}"
        
        # Check if basket exists
        basket = baskets_collection.find_one({"email": email, "index_number": index_number})
        
        now = datetime.utcnow()
        
        if not basket:
            # Create basket with this single item
            basket_data = {
                "basket_id": basket_id,
                "email": email,
                "index_number": index_number,
                "created_at": now,
                "last_updated": now,
                "item_count": 1,
                "program_types": [item_data.get('program_type')] if item_data.get('program_type') else []
            }
            baskets_collection.insert_one(basket_data)
        else:
            # Update basket count
            baskets_collection.update_one(
                {"email": email, "index_number": index_number},
                {
                    "$set": {"last_updated": now},
                    "$inc": {"item_count": 1}
                }
            )
        
        # Check if item already exists
        existing_item = basket_items_collection.find_one({
            "basket_id": basket_id,
            "program_code": item_data.get('program_code')
        })
        
        was_added = True
        if existing_item:
            # Update existing item
            basket_items_collection.update_one(
                {"_id": existing_item["_id"]},
                {
                    "$set": {
                        "course_name": item_data.get('course_name'),
                        "institution": item_data.get('institution'),
                        "program_type": item_data.get('program_type'),
                        "cutoff": item_data.get('cutoff'),
                        "cluster": item_data.get('cluster'),
                        "priority": item_data.get('priority', 0),
                        "updated_at": now
                    }
                }
            )
            was_added = False  # It was an update, not a new addition
        else:
            # Add new item
            item_doc = {
                "_id": str(ObjectId()),
                "basket_id": basket_id,
                "program_code": item_data.get('program_code'),
                "course_name": item_data.get('course_name'),
                "institution": item_data.get('institution'),
                "program_type": item_data.get('program_type'),
                "cutoff": item_data.get('cutoff'),
                "cluster": item_data.get('cluster'),
                "priority": item_data.get('priority', 0),
                "added_at": now,
                "updated_at": now
            }
            basket_items_collection.insert_one(item_doc)
        
        # Get updated count
        basket = baskets_collection.find_one({"email": email, "index_number": index_number})
        
        return jsonify({
            "success": True,
            "was_added": was_added,
            "count": basket.get('item_count', 0) if basket else 1
        })
        
    except Exception as e:
        print(f"Error adding basket item: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/basket/remove-item', methods=['POST'])
def remove_basket_item():
    """Remove item from basket"""
    try:
        data = request.get_json()
        email = data.get('email')
        index_number = data.get('index_number')
        program_code = data.get('program_code')
        
        if not email or not index_number or not program_code:
            return jsonify({"error": "Missing required data"}), 400
        
        basket_id = f"{email}_{index_number}"
        
        # Remove item
        result = basket_items_collection.delete_one({
            "basket_id": basket_id,
            "program_code": program_code
        })
        
        if result.deleted_count > 0:
            # Update basket count
            baskets_collection.update_one(
                {"email": email, "index_number": index_number},
                {
                    "$set": {"last_updated": datetime.utcnow()},
                    "$inc": {"item_count": -1}
                }
            )
        
        # Get updated basket
        basket = baskets_collection.find_one({"email": email, "index_number": index_number})
        
        return jsonify({
            "success": True,
            "deleted": result.deleted_count > 0,
            "count": basket.get('item_count', 0) if basket else 0
        })
        
    except Exception as e:
        print(f"Error removing basket item: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/basket/clear', methods=['POST'])
def clear_user_basket():
    """Clear entire basket for user"""
    try:
        data = request.get_json()
        email = data.get('email')
        index_number = data.get('index_number')
        
        if not email or not index_number:
            return jsonify({"error": "Email and index number required"}), 400
        
        basket_id = f"{email}_{index_number}"
        
        # Delete all items
        basket_items_collection.delete_many({"basket_id": basket_id})
        
        # Reset basket count
        baskets_collection.update_one(
            {"email": email, "index_number": index_number},
            {
                "$set": {
                    "last_updated": datetime.utcnow(),
                    "item_count": 0,
                    "program_types": []
                }
            }
        )
        
        return jsonify({
            "success": True,
            "message": "Basket cleared successfully"
        })
        
    except Exception as e:
        print(f"Error clearing basket: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/basket/stats', methods=['POST'])
def get_basket_stats():
    """Get basket statistics"""
    try:
        data = request.get_json()
        email = data.get('email')
        index_number = data.get('index_number')
        
        if not email or not index_number:
            return jsonify({"error": "Email and index number required"}), 400
        
        basket = baskets_collection.find_one({"email": email, "index_number": index_number})
        
        if not basket:
            return jsonify({
                "exists": False,
                "count": 0,
                "last_updated": None
            })
        
        return jsonify({
            "exists": True,
            "count": basket.get('item_count', 0),
            "last_updated": basket.get('last_updated').isoformat() if basket.get('last_updated') else None,
            "created_at": basket.get('created_at').isoformat() if basket.get('created_at') else None,
            "program_types": basket.get('program_types', [])
        })
        
    except Exception as e:
        print(f"Error getting basket stats: {e}")
        return jsonify({"error": str(e)}), 500
    


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
