"""  
FDA Drug Approval Monitor with Physician Matching  
"""

import requests  
import json  
import smtplib  
from email.mime.text import MIMEText  
from email.mime.multipart import MIMEMultipart  
from datetime import datetime, timedelta  
from collections import defaultdict  
import os  
import time


def get_date_range(days_back=1):  
    today = datetime.now()  
    past = today - timedelta(days=days_back)  
    return past.strftime("%Y%m%d"), today.strftime("%Y%m%d")


def fetch_drug_indication(application_number):  
    try:  
        url = (  
            "https://api.fda.gov/drug/label.json?"  
            "search=openfda.application_number:"  
            "\"" + application_number + "\""  
            "&limit=1"  
        )  
        response = requests.get(url, timeout=10)  
        if response.status_code == 200:  
            data = response.json()  
            results = data.get("results", [])  
            if results:  
                label = results[0]  
                indications = label.get(  
                    "indications_and_usage", [""]  
                )  
                if indications and indications[0]:  
                    return indications[0]  
                purpose = label.get("purpose", [""])  
                if purpose and purpose[0]:  
                    return purpose[0]  
        return "Indication not available"  
    except Exception:  
        return "Indication not available"


def fetch_fda_approvals(days_back=7):  
    date_from, date_to = get_date_range(days_back)  
    url = (  
        "https://api.fda.gov/drug/drugsfda.json?"  
        "search=submissions.submission_status_date:"  
        "[" + date_from + "+TO+" + date_to + "]"  
        "&limit=100"  
    )

    print("Fetching FDA approvals from " + date_from +  
          " to " + date_to + "...")  
    print("URL: " + url)  
    print()

    try:  
        response = requests.get(url, timeout=30)  
        if response.status_code == 404:  
            print("No new drug approvals found.")  
            return [], date_from, date_to

        response.raise_for_status()  
        data = response.json()  
        results = data.get("results", [])  
        print("Found " + str(len(results)) +  
              " drug record(s) from FDA API.")

        approvals = []  
        seen_drugs = set()

        for drug in results:  
            submissions = drug.get("submissions", [])  
            products = drug.get("products", [])  
            openfda = drug.get("openfda", {})  
            application_number = drug.get(  
                "application_number", "Unknown"  
            )

            for sub in submissions:  
                sub_date = sub.get("submission_status_date", "")  
                sub_status = sub.get("submission_status", "")

                if not sub_date or sub_status != "AP":  
                    continue

                try:  
                    sub_date_int = int(sub_date)  
                    if not (int(date_from) <= sub_date_int  
                            <= int(date_to)):  
                        continue  
                except (ValueError, TypeError):  
                    continue

                unique_key = application_number + "_" + sub_date  
                if unique_key in seen_drugs:  
                    continue  
                seen_drugs.add(unique_key)

                drug_name = "Unknown"  
                dosage_form = "Unknown"  
                route = "Unknown"  
                active_ingredients = []

                if products:  
                    drug_name = products[0].get(  
                        "brand_name", "Unknown"  
                    )  
                    dosage_form = products[0].get(  
                        "dosage_form", "Unknown"  
                    )  
                    route = products[0].get("route", "Unknown")  
                    for ai in products[0].get(  
                        "active_ingredients", []  
                    ):  
                        active_ingredients.append({  
                            "name": ai.get("name", "Unknown"),  
                            "strength": ai.get(  
                                "strength", "Unknown"  
                            )  
                        })

                generic_name = "Unknown"  
                generic_names = openfda.get("generic_name", [])  
                if generic_names:  
                    generic_name = generic_names[0]

                sub_type = sub.get("submission_type", "Unknown")  
                sub_type_desc = {  
                    "ORIG": "Original New Drug Application",  
                    "SUPPL": "Supplemental Application",  
                    "ABBR": "Abbreviated New Drug Application",  
                }.get(sub_type, sub_type)

                approvals.append({  
                    "drug_name": drug_name,  
                    "generic_name": generic_name,  
                    "approval_date": sub_date,  
                    "application_number": application_number,  
                    "submission_type": sub_type,  
                    "submission_type_description": sub_type_desc,  
                    "sponsor": drug.get("sponsor_name", "Unknown"),  
                    "dosage_form": dosage_form,  
                    "route": route,  
                    "active_ingredients": active_ingredients,  
                    "indication": "",  
                    "matched_specialties": [],  
                    "matched_doctors": [],  
                })

        print("Found " + str(len(approvals)) +  
              " new approval(s) in range.")  
        print("Fetching drug indications...")

        fetched_indications = {}  
        for approval in approvals:  
            app_num = approval["application_number"]  
            if app_num not in fetched_indications:  
                indication = fetch_drug_indication(app_num)  
                fetched_indications[app_num] = indication  
                time.sleep(0.1)  
            approval["indication"] = fetched_indications[app_num]

        return approvals, date_from, date_to

    except Exception as e:  
        print("Error fetching FDA data: " + str(e))  
        return [], date_from, date_to


# ============================================================  
# INDICATION TO SPECIALTY MAPPING  
# ============================================================

INDICATION_SPECIALTY_MAP = {  
    "hypertension": ["Cardiology"],  
    "blood pressure": ["Cardiology"],  
    "heart failure": ["Cardiology"],  
    "cardiac": ["Cardiology"],  
    "cardiovascular": ["Cardiology"],  
    "angina": ["Cardiology"],  
    "arrhythmia": ["Cardiology"],  
    "atrial fibrillation": ["Cardiology"],  
    "anticoagulant": ["Cardiology"],  
    "thrombin inhibitor": ["Cardiology"],  
    "pulmonary arterial hypertension": [  
        "Pulmonology", "Cardiology"  
    ],  
    "endothelin receptor": ["Cardiology", "Pulmonology"],  
    "losartan": ["Cardiology"],  
    "angiotensin": ["Cardiology"],  
    "labetalol": ["Cardiology"],  
    "propranolol": ["Cardiology"],  
    "irbesartan": ["Cardiology"],  
    "cancer": ["Oncology"],  
    "tumor": ["Oncology"],  
    "melanoma": ["Oncology", "Dermatology"],  
    "carcinoma": ["Oncology"],  
    "lymphoma": ["Oncology"],  
    "leukemia": ["Oncology"],  
    "neoplasm": ["Oncology"],  
    "glioma": ["Oncology", "Neurology"],  
    "metastatic": ["Oncology"],  
    "myelodysplastic": ["Oncology"],  
    "capecitabine": ["Oncology"],  
    "azacitidine": ["Oncology"],  
    "seizure": ["Neurology"],  
    "epilepsy": ["Neurology"],  
    "neurological": ["Neurology"],  
    "anticonvulsant": ["Neurology"],  
    "antiepileptic": ["Neurology"],  
    "partial onset": ["Neurology"],  
    "tonic-clonic": ["Neurology"],  
    "lacosamide": ["Neurology"],  
    "perampanel": ["Neurology"],  
    "topiramate": ["Neurology"],  
    "oxcarbazepine": ["Neurology"],  
    "levetiracetam": ["Neurology"],  
    "schizophrenia": ["Psychiatry"],  
    "bipolar": ["Psychiatry"],  
    "antipsychotic": ["Psychiatry"],  
    "risperidone": ["Psychiatry"],  
    "acne": ["Dermatology"],  
    "dermatitis": ["Dermatology"],  
    "psoriasis": ["Dermatology"],  
    "skin": ["Dermatology"],  
    "eczema": ["Dermatology"],  
    "clindamycin": ["Dermatology"],  
    "asthma": ["Pulmonology"],  
    "copd": ["Pulmonology"],  
    "pulmonary": ["Pulmonology"],  
    "respiratory": ["Pulmonology"],  
    "eosinophilic": ["Pulmonology"],  
    "depemokimab": ["Pulmonology"],  
    "arthritis": ["Rheumatology"],  
    "rheumatoid": ["Rheumatology"],  
    "lupus": ["Rheumatology"],  
    "autoimmune": ["Rheumatology"],  
    "tofacitinib": ["Rheumatology"],  
    "glaucoma": ["Ophthalmology"],  
    "ophthalmic": ["Ophthalmology"],  
    "intraocular": ["Ophthalmology"],  
    "retinal": ["Ophthalmology"],  
    "dorzolamide": ["Ophthalmology"],  
    "fluorescein": ["Ophthalmology"],  
    "hepatorenal": ["Gastroenterology", "Nephrology"],  
    "liver": ["Gastroenterology"],  
    "hepatic": ["Gastroenterology"],  
    "gastrointestinal": ["Gastroenterology"],  
    "nausea": ["Gastroenterology"],  
    "antiemetic": ["Gastroenterology"],  
    "terlipressin": ["Gastroenterology", "Nephrology"],  
    "renal": ["Nephrology"],  
    "kidney": ["Nephrology"],  
    "osteoporosis": ["Endocrinology"],  
    "diabetes": ["Endocrinology"],  
    "thyroid": ["Endocrinology"],  
    "estradiol": ["Endocrinology"],  
    "bisphosphonate": ["Endocrinology"],  
    "risedronate": ["Endocrinology"],  
    "alendronate": ["Endocrinology"],  
    "antibacterial": ["Infectious Disease"],  
    "antibiotic": ["Infectious Disease"],  
    "antiviral": ["Infectious Disease"],  
    "infection": ["Infectious Disease"],  
    "vancomycin": ["Infectious Disease"],  
    "malaria": ["Infectious Disease"],  
    "herpes": ["Infectious Disease"],  
    "linezolid": ["Infectious Disease"],  
    "cephalexin": ["Infectious Disease"],  
    "valacyclovir": ["Infectious Disease"],  
    "contrast": ["Radiology"],  
    "imaging": ["Radiology"],  
    "gadobutrol": ["Radiology"],  
    "gallium": ["Radiology", "Oncology"],  
    "succinylcholine": ["Anesthesiology"],  
    "intubation": ["Anesthesiology"],  
    "naloxone": ["Emergency Medicine"],  
    "opioid overdose": ["Emergency Medicine"],  
    "opioid antagonist": ["Emergency Medicine"],  
    "rextovy": ["Emergency Medicine"],  
    "pregnancy": ["OB-GYN"],  
    "doxylamine": ["OB-GYN"],  
    "topical": ["Dermatology"],  
}


def map_indication_to_specialties(indication_text, drug_name="",  
                                   route=""):  
    matched = set()

    check_text = ""  
    if (indication_text  
            and indication_text != "Indication not available"):  
        check_text = indication_text.lower()

    drug_lower = drug_name.lower() if drug_name else ""

    for keyword, specs in INDICATION_SPECIALTY_MAP.items():  
        kw = keyword.lower()  
        if kw in check_text or kw in drug_lower:  
            for s in specs:  
                matched.add(s)

    if not matched and route:  
        route_lower = route.lower()  
        if "ophthalmic" in route_lower:  
            matched.add("Ophthalmology")  
        elif "topical" in route_lower:  
            matched.add("Dermatology")

    if not matched:  
        matched.add("Internal Medicine")

    return list(matched)


# ============================================================  
# NORTHWELL FAD API  
# ============================================================

FAD_SPECIALTY_MAP = {  
    "Cardiology": "cardiology",  
    "Oncology": "oncology",  
    "Neurology": "neurology",  
    "Dermatology": "dermatology",  
    "Pulmonology": "pulmonology",  
    "Rheumatology": "rheumatology",  
    "Ophthalmology": "ophthalmology",  
    "Gastroenterology": "gastroenterology",  
    "Nephrology": "nephrology",  
    "Endocrinology": "endocrinology",  
    "Infectious Disease": "infectious-disease",  
    "Psychiatry": "psychiatry",  
    "Radiology": "radiology",  
    "Anesthesiology": "anesthesiology",  
    "Emergency Medicine": "emergency-medicine",  
    "Internal Medicine": "internal-medicine",  
    "OB-GYN": "obstetrics-gynecology",  
    "Hematology": "hematology",  
}


def fetch_northwell_doctors(specialty, max_results=5):  
    fad_specialty = FAD_SPECIALTY_MAP.get(  
        specialty, specialty.lower().replace(" ", "-")  
    )

    try:  
        url = (  
            "https://fadapi.northwell.io/v3/providers/search"  
            "?specialty=" + fad_specialty  
        )

        headers = {  
            "Accept": "application/json, text/plain, */*",  
            "Accept-Language": "en-US,en;q=0.9",  
            "User-Agent": (  
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "  
                "AppleWebKit/537.36 (KHTML, like Gecko) "  
                "Chrome/137.0.0.0 Safari/537.36"  
            ),  
            "Referer": "https://www.northwell.edu/",  
            "Origin": "https://www.northwell.edu",  
        }

        print("    FAD URL: " + url)  
        response = requests.get(url, headers=headers, timeout=15)  
        print("    Status: " + str(response.status_code))

        if response.status_code == 200:  
            data = response.json()  
            results = data.get("results", [])

            if not results and isinstance(data, list):  
                results = data

            print("    Raw results count: " + str(len(results)))

            doctors = []  
            for provider in results[:max_results]:  
                first = provider.get("firstname", "")  
                last = provider.get("lastname", "")  
                degrees = provider.get("degrees", [])

                if isinstance(degrees, list) and degrees:  
                    degree_str = ", ".join(degrees)  
                else:  
                    degree_str = ""

                if first and last:  
                    name = "Dr. " + first + " " + last  
                    if degree_str:  
                        name = name + ", " + degree_str  
                else:  
                    name = "Unknown"

                city = provider.get("city", "")  
                state_abbr = provider.get("state_abbr", "")  
                practice = provider.get("practice_name", "")  
                address = provider.get("street_address", "")  
                phone = provider.get("phone", "")

                if isinstance(phone, dict):  
                    phone = str(phone)

                if practice and city:  
                    location = practice + ", " + city  
                    if state_abbr:  
                        location = location + ", " + state_abbr  
                elif city:  
                    location = city + ", " + state_abbr  
                else:  
                    location = "Location not available"

                url_path = provider.get("url", "")  
                if url_path and not url_path.startswith("http"):  
                    profile_url = (  
                        "https://www.northwell.edu" + url_path  
                    )  
                else:  
                    profile_url = url_path if url_path else ""

                npi = str(provider.get(  
                    "provider_soarian_npi",  
                    provider.get("npi", "")  
                ))

                department = provider.get(  
                    "department_me", specialty  
                )

                doctors.append({  
                    "name": name,  
                    "specialty": department,  
                    "location": location,  
                    "address": address,  
                    "city": city,  
                    "state": state_abbr,  
                    "phone": str(phone),  
                    "npi": npi,  
                    "profile_url": profile_url,  
                    "practice_name": practice,  
                    "match_type": "DIRECT_SPECIALTY_MATCH",  
                    "relevance_score": 1.0,  
                    "matched_via": specialty,  
                })

            print("    Extracted " + str(len(doctors)) +  
                  " doctor(s)")  
            return doctors

        else:  
            body_preview = response.text[:200]  
            print("    Error body: " + body_preview)  
            return []

    except Exception as e:  
        print("    Exception: " + str(e))  
        return []


# ============================================================  
# REPORT GENERATION  
# ============================================================

def build_email_html(approvals, date_from, date_to):  
    try:  
        from_display = datetime.strptime(  
            date_from, "%Y%m%d"  
        ).strftime("%B %d, %Y")  
        to_display = datetime.strptime(  
            date_to, "%Y%m%d"  
        ).strftime("%B %d, %Y")  
    except ValueError:  
        from_display = date_from  
        to_display = date_to

    total_doctors = sum(  
        len(a.get("matched_doctors", [])) for a in approvals  
    )

    html = """<html><head><style>  
    body{font-family:Arial,sans-serif;color:#333;max-width:950px;margin:0 auto}  
    .header{background:linear-gradient(135deg,#0078d4,#00a4ef);color:white;padding:25px 30px;border-radius:8px 8px 0 0}  
    .header h1{margin:0;font-size:22px}  
    .header p{margin:5px 0 0 0;opacity:0.9}  
    .summary{background:#f0f6ff;padding:15px 30px;border-bottom:2px solid #0078d4;font-size:16px}  
    .drug-card{border:1px solid #e0e0e0;border-left:4px solid #0078d4;border-radius:4px;margin:20px 30px;background:white;overflow:hidden}  
    .drug-header{background:#f8f9fa;padding:15px 20px;border-bottom:1px solid #e0e0e0}  
    .drug-header h3{color:#0078d4;margin:0;font-size:18px}  
    .drug-header .meta{color:#666;font-size:13px;margin-top:4px}  
    .drug-body{padding:15px 20px}  
    .info-row{margin:4px 0;font-size:14px}  
    .info-row .lbl{font-weight:bold;color:#555}  
    .indication{background:#fff3cd;border:1px solid #ffc107;border-radius:4px;padding:12px 15px;margin:12px 0;font-size:13px;line-height:1.5}  
    .doctors{margin-top:15px;border-top:1px solid #e0e0e0;padding-top:15px}  
    .doctors h4{color:#333;margin:0 0 10px 0;font-size:15px}  
    .doc-row{padding:10px 12px;margin:4px 0;background:#f8f9fa;border-radius:4px;border-left:3px solid #28a745}  
    .doc-name{font-weight:bold;color:#333;font-size:14px}  
    .doc-detail{color:#666;font-size:12px;margin-top:2px}  
    .doc-actions{margin-top:4px}  
    .btn{display:inline-block;padding:4px 10px;border-radius:4px;text-decoration:none;font-size:11px;font-weight:bold;color:white;margin-right:4px}  
    .btn-profile{background:#28a745}  
    .btn-phone{background:#6c757d}  
    .no-docs{color:#999;font-style:italic;font-size:13px;padding:8px 0}  
    .footer{padding:20px 30px;font-size:12px;color:#999;border-top:1px solid #eee;margin-top:20px}  
    </style></head><body>"""

    html += '<div class="header">'  
    html += "<h1>FDA Daily Drug Approval Report</h1>"  
    html += "<p>Northwell Health Physician Matching</p>"  
    html += ("<p style='font-size:12px'>" +  
             from_display + " to " + to_display + "</p>")  
    html += "</div>"

    html += '<div class="summary">'  
    html += ("<strong>" + str(len(approvals)) +  
             "</strong> Drug Approvals | ")  
    html += ("<strong>" + str(total_doctors) +  
             "</strong> Matched Physicians")  
    html += "</div>"

    for i, a in enumerate(approvals, 1):  
        ingredients = ", ".join(  
            [ai["name"] + " (" + ai["strength"] + ")"  
             for ai in a.get("active_ingredients", [])]  
        )  
        if not ingredients:  
            ingredients = "N/A"

        try:  
            date_disp = datetime.strptime(  
                a["approval_date"], "%Y%m%d"  
            ).strftime("%B %d, %Y")  
        except (ValueError, TypeError):  
            date_disp = a["approval_date"]

        specs = ", ".join(  
            a.get("matched_specialties", ["N/A"])  
        )

        html += '<div class="drug-card">'  
        html += '<div class="drug-header">'  
        html += ("<h3>#" + str(i) + " — " +  
                 a["drug_name"] + "</h3>")  
        html += ('<div class="meta">' +  
                 a["generic_name"] + " | Approved: " +  
                 date_disp + " | " +  
                 a["submission_type_description"] + "</div>")  
        html += "</div>"

        html += '<div class="drug-body">'  
        html += ('<div class="info-row"><span class="lbl">'  
                 'Sponsor:</span> ' + a["sponsor"] + "</div>")  
        html += ('<div class="info-row"><span class="lbl">'  
                 'Application:</span> ' +  
                 a["application_number"] + "</div>")  
        html += ('<div class="info-row"><span class="lbl">'  
                 'Dosage:</span> ' + a["dosage_form"] + "</div>")  
        html += ('<div class="info-row"><span class="lbl">'  
                 'Route:</span> ' + a["route"] + "</div>")  
        html += ('<div class="info-row"><span class="lbl">'  
                 'Ingredients:</span> ' + ingredients + "</div>")  
        html += ('<div class="info-row"><span class="lbl">'  
                 'Specialties:</span> ' + specs + "</div>")

        indication = a.get("indication", "")  
        if (indication  
                and indication != "Indication not available"):  
            ind_short = indication[:400]  
            if len(indication) > 400:  
                ind_short += "..."  
            html += ('<div class="indication"><strong>'  
                     'Indication:</strong> ' +  
                     ind_short + "</div>")

        doctors = a.get("matched_doctors", [])  
        html += '<div class="doctors">'  
        html += ("<h4>Matched Northwell Physicians (" +  
                 str(len(doctors)) + ")</h4>")

        if doctors:  
            for doc in doctors[:10]:  
                html += '<div class="doc-row">'  
                html += ('<div class="doc-name">' +  
                         doc["name"] + "</div>")  
                html += ('<div class="doc-detail">' +  
                         doc.get("specialty", "") + " | " +  
                         doc.get("location", "") + "</div>")  
                html += '<div class="doc-actions">'  
                if doc.get("profile_url"):  
                    html += ('<a href="' +  
                             doc["profile_url"] +  
                             '" class="btn btn-profile"'  
                             ' target="_blank">Profile</a>')  
                if doc.get("phone"):  
                    html += ('<a href="tel:' +  
                             doc["phone"] +  
                             '" class="btn btn-phone">' +  
                             doc["phone"] + "</a>")  
                html += "</div></div>"  
        else:  
            html += ('<div class="no-docs">'  
                     'No matching physicians found.</div>')

        html += "</div></div></div>"

    html += '<div class="footer">'  
    html += "<p>Generated by FDA Drug Approval Monitor</p>"  
    html += "<p>Sources: openFDA API + Northwell FAD API</p>"  
    html += ("<p>" + datetime.now().strftime(  
        "%B %d, %Y at %I:%M %p UTC") + "</p>")  
    html += "</div></body></html>"

    return html


def send_email(subject, html_body, to_email, from_email,  
               password):  
    msg = MIMEMultipart("alternative")  
    msg["Subject"] = subject  
    msg["From"] = from_email  
    msg["To"] = to_email  
    html_part = MIMEText(html_body, "html")  
    msg.attach(html_part)  
    try:  
        with smtplib.SMTP("smtp.gmail.com", 587) as server:  
            server.starttls()  
            server.login(from_email, password)  
            server.sendmail(from_email, to_email, msg.as_string())  
        print("Email sent to " + to_email)  
        return True  
    except Exception as e:  
        print("Failed to send email: " + str(e))  
        return False


# ============================================================  
# MAIN PIPELINE  
# ============================================================

def main():  
    print("=" * 70)  
    print("FDA DRUG APPROVAL MONITOR — UNIFIED PIPELINE")  
    print("Run: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  
    print("=" * 70)  
    print()

    # STEP 1  
    print("STEP 1: Fetching FDA drug approvals...")  
    print("-" * 50)  
    approvals, date_from, date_to = fetch_fda_approvals(  
        days_back=7  
    )  
    print()  
    print("Found " + str(len(approvals)) + " new approval(s)")  
    print()

    if not approvals:  
        print("No approvals found.")  
        html = build_email_html([], date_from, date_to)  
        with open("fda_report.html", "w") as f:  
            f.write(html)  
        return

    # STEP 2  
    print("STEP 2: Mapping indications to specialties...")  
    print("-" * 50)  
    for a in approvals:  
        specs = map_indication_to_specialties(  
            a["indication"], a["drug_name"], a["route"]  
        )  
        a["matched_specialties"] = specs  
        print("  " + a["drug_name"] + ": " + ", ".join(specs))  
    print()

    # STEP 3  
    print("STEP 3: Fetching Northwell physicians...")  
    print("-" * 50)

    all_specs = set()  
    for a in approvals:  
        for s in a["matched_specialties"]:  
            all_specs.add(s)

    print("  Specialties: " + ", ".join(sorted(all_specs)))  
    print()

    doctors_cache = {}  
    for spec in sorted(all_specs):  
        print("  --- Searching: " + spec + " ---")  
        docs = fetch_northwell_doctors(spec, max_results=5)  
        doctors_cache[spec] = docs  
        print()  
        time.sleep(0.5)

    # STEP 4  
    print("STEP 4: Matching doctors to drugs...")  
    print("-" * 50)  
    for a in approvals:  
        matched = []  
        seen = set()  
        for spec in a["matched_specialties"]:  
            for doc in doctors_cache.get(spec, []):  
                key = doc["name"] + doc.get("npi", "")  
                if key not in seen:  
                    seen.add(key)  
                    doc_copy = doc.copy()  
                    doc_copy["matched_via"] = spec  
                    matched.append(doc_copy)  
        a["matched_doctors"] = matched  
        print("  " + a["drug_name"] + ": " +  
              str(len(matched)) + " doctor(s)")  
    print()

    # STEP 5  
    print("STEP 5: Generating report...")  
    print("-" * 50)

    print()  
    print("=" * 70)  
    print("FINAL REPORT")  
    print("=" * 70)  
    for i, a in enumerate(approvals, 1):  
        print()  
        print("#" + str(i) + " " + a["drug_name"] +  
              " (" + a["generic_name"] + ")")  
        print("   Approved: " + a["approval_date"])  
        print("   Specialties: " +  
              ", ".join(a["matched_specialties"]))  
        print("   Doctors: " +  
              str(len(a["matched_doctors"])))  
        for doc in a["matched_doctors"][:5]:  
            print("     -> " + doc["name"] +  
                  " | " + doc.get("specialty", "") +  
                  " | " + doc.get("city", "") +  
                  " | " + doc.get("phone", ""))

    html = build_email_html(approvals, date_from, date_to)  
    with open("fda_report.html", "w") as f:  
        f.write(html)  
    print()  
    print("HTML report saved to fda_report.html")

    results = {  
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  
        "date_range": {"from": date_from, "to": date_to},  
        "total_approvals": len(approvals),  
        "total_doctors": sum(  
            len(a["matched_doctors"]) for a in approvals  
        ),  
        "approvals": approvals,  
    }  
    with open("fda_results.json", "w") as f:  
        json.dump(results, f, indent=2, default=str)  
    print("JSON results saved to fda_results.json")

    to_email = os.environ.get("EMAIL_TO")  
    from_email = os.environ.get("EMAIL_FROM")  
    email_password = os.environ.get("EMAIL_PASSWORD")

    if to_email and from_email and email_password:  
        total = sum(  
            len(a["matched_doctors"]) for a in approvals  
        )  
        subject = (  
            "FDA Report - " +  
            datetime.now().strftime("%B %d, %Y") +  
            " - " + str(len(approvals)) + " approvals, " +  
            str(total) + " doctors"  
        )  
        send_email(  
            subject, html, to_email, from_email, email_password  
        )  
    else:  
        print()  
        print("Email not configured.")

    print()  
    print("=" * 70)  
    print("PIPELINE COMPLETE")  
    print("=" * 70)


if __name__ == "__main__":  
    main()  
