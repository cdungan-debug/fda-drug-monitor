"""  
FDA Drug Approval Monitor with Physician Matching  
==================================================  
Unified pipeline that:  
1. Fetches new FDA drug approvals (real data from openFDA API)  
2. Maps drug indications to medical specialties  
3. Finds matching Northwell physicians (real data from FAD API)  
4. Ranks physicians by relationship relevance  
5. Generates a report for Maddie with contact links  
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


# ============================================================  
# SECTION 1: FDA DATA COLLECTION  
# ============================================================

def get_date_range(days_back=1):  
    """Get date range for FDA API query."""  
    today = datetime.now()  
    past = today - timedelta(days=days_back)  
    return past.strftime("%Y%m%d"), today.strftime("%Y%m%d")


def fetch_drug_indication(application_number):  
    """Fetch drug indication from the FDA drug label API."""  
    try:  
        url = (  
            f"https://api.fda.gov/drug/label.json?"  
            f"search=openfda.application_number:"  
            f"\"{application_number}\""  
            f"&limit=1"  
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
    """Fetch recent drug approvals from the openFDA API."""  
    date_from, date_to = get_date_range(days_back)

    url = (  
        f"https://api.fda.gov/drug/drugsfda.json?"  
        f"search=submissions.submission_status_date:"  
        f"[{date_from}+TO+{date_to}]"  
        f"&limit=100"  
    )

    print(f"Fetching FDA approvals from {date_from} to {date_to}...")  
    print(f"URL: {url}")  
    print()

    try:  
        response = requests.get(url, timeout=30)

        if response.status_code == 404:  
            print("No new drug approvals found.")  
            return [], date_from, date_to

        response.raise_for_status()  
        data = response.json()  
        results = data.get("results", [])

        print(f"Found {len(results)} drug record(s) from FDA API.")

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
                    if not (int(date_from) <= sub_date_int <= int(date_to)):  
                        continue  
                except (ValueError, TypeError):  
                    continue

                unique_key = f"{application_number}_{sub_date}"  
                if unique_key in seen_drugs:  
                    continue  
                seen_drugs.add(unique_key)

                drug_name = "Unknown"  
                dosage_form = "Unknown"  
                route = "Unknown"  
                active_ingredients = []

                if products:  
                    drug_name = products[0].get("brand_name", "Unknown")  
                    dosage_form = products[0].get("dosage_form", "Unknown")  
                    route = products[0].get("route", "Unknown")  
                    for ai in products[0].get("active_ingredients", []):  
                        active_ingredients.append({  
                            "name": ai.get("name", "Unknown"),  
                            "strength": ai.get("strength", "Unknown")  
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

        # Fetch indications  
        print(f"Found {len(approvals)} new approval(s) in date range.")  
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
        print(f"Error fetching FDA data: {e}")  
        return [], date_from, date_to


# ============================================================  
# SECTION 2: INDICATION TO SPECIALTY MAPPING  
# ============================================================

INDICATION_SPECIALTY_MAP = {  
    # Cardiology  
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
    "pulmonary arterial hypertension": ["Pulmonology", "Cardiology"],  
    "endothelin receptor": ["Cardiology", "Pulmonology"],  
    "losartan": ["Cardiology"],  
    "angiotensin": ["Cardiology"],  
    "labetalol": ["Cardiology"],  
    "propranolol": ["Cardiology"],  
    "irbesartan": ["Cardiology"],

    # Oncology  
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
    "nucleoside metabolic inhibitor": ["Oncology"],  
    "capecitabine": ["Oncology"],  
    "azacitidine": ["Oncology"],

    # Neurology  
    "seizure": ["Neurology"],  
    "epilepsy": ["Neurology"],  
    "neurological": ["Neurology"],  
    "anticonvulsant": ["Neurology"],  
    "antiepileptic": ["Neurology"],  
    "lacosamide": ["Neurology"],  
    "perampanel": ["Neurology"],  
    "topiramate": ["Neurology"],  
    "oxcarbazepine": ["Neurology"],  
    "levetiracetam": ["Neurology"],

    # Psychiatry  
    "schizophrenia": ["Psychiatry"],  
    "bipolar": ["Psychiatry"],  
    "antipsychotic": ["Psychiatry"],  
    "autism": ["Psychiatry"],  
    "risperidone": ["Psychiatry"],

    # Dermatology  
    "acne": ["Dermatology"],  
    "dermatitis": ["Dermatology"],  
    "psoriasis": ["Dermatology"],  
    "skin": ["Dermatology"],  
    "eczema": ["Dermatology"],  
    "clindamycin": ["Dermatology", "Infectious Disease"],

    # Pulmonology  
    "asthma": ["Pulmonology"],  
    "copd": ["Pulmonology"],  
    "pulmonary": ["Pulmonology"],  
    "respiratory": ["Pulmonology"],  
    "eosinophilic": ["Pulmonology"],  
    "depemokimab": ["Pulmonology"],

    # Rheumatology  
    "arthritis": ["Rheumatology"],  
    "rheumatoid": ["Rheumatology"],  
    "lupus": ["Rheumatology"],  
    "autoimmune": ["Rheumatology"],  
    "tofacitinib": ["Rheumatology"],  
    "janus kinase": ["Rheumatology"],

    # Ophthalmology  
    "glaucoma": ["Ophthalmology"],  
    "ophthalmic": ["Ophthalmology"],  
    "intraocular": ["Ophthalmology"],  
    "retinal": ["Ophthalmology"],  
    "angiography": ["Ophthalmology"],  
    "dorzolamide": ["Ophthalmology"],  
    "fluorescein": ["Ophthalmology"],

    # Gastroenterology  
    "hepatorenal": ["Gastroenterology", "Nephrology"],  
    "liver": ["Gastroenterology"],  
    "hepatic": ["Gastroenterology"],  
    "gastrointestinal": ["Gastroenterology"],  
    "nausea": ["Gastroenterology"],  
    "vomiting": ["Gastroenterology"],  
    "antiemetic": ["Gastroenterology", "Oncology"],  
    "terlipressin": ["Gastroenterology", "Nephrology"],

    # Nephrology  
    "renal": ["Nephrology"],  
    "kidney": ["Nephrology"],

    # Endocrinology  
    "osteoporosis": ["Endocrinology"],  
    "diabetes": ["Endocrinology"],  
    "thyroid": ["Endocrinology"],  
    "hormone": ["Endocrinology"],  
    "estradiol": ["Endocrinology", "Obstetrics and Gynecology"],  
    "menopausal": ["Endocrinology", "Obstetrics and Gynecology"],  
    "bisphosphonate": ["Endocrinology"],  
    "risedronate": ["Endocrinology"],  
    "alendronate": ["Endocrinology"],

    # Infectious Disease  
    "antibacterial": ["Infectious Disease"],  
    "antibiotic": ["Infectious Disease"],  
    "antiviral": ["Infectious Disease"],  
    "infection": ["Infectious Disease"],  
    "pneumonia": ["Infectious Disease", "Pulmonology"],  
    "vancomycin": ["Infectious Disease"],  
    "malaria": ["Infectious Disease"],  
    "herpes": ["Infectious Disease"],  
    "linezolid": ["Infectious Disease"],  
    "cephalexin": ["Infectious Disease"],  
    "valacyclovir": ["Infectious Disease"],

    # Radiology  
    "contrast": ["Radiology"],  
    "imaging": ["Radiology"],  
    "gadobutrol": ["Radiology"],  
    "magnetic resonance": ["Radiology"],  
    "gallium": ["Radiology", "Oncology"],

    # Anesthesiology  
    "neuromuscular block": ["Anesthesiology"],  
    "succinylcholine": ["Anesthesiology"],  
    "intubation": ["Anesthesiology"],

    # Emergency Medicine  
    "naloxone": ["Emergency Medicine"],  
    "opioid overdose": ["Emergency Medicine"],  
    "opioid antagonist": ["Emergency Medicine"],

    # Obstetrics / Gynecology  
    "pregnancy": ["Obstetrics and Gynecology"],  
    "doxylamine": ["Obstetrics and Gynecology"],  
    "pyridoxine": ["Obstetrics and Gynecology"],

    # Topical/route based  
    "topical": ["Dermatology"],  
}


def map_indication_to_specialties(indication_text, drug_name="",  
                                   route=""):  
    """Map drug indication text to relevant medical specialties."""  
    matched = set()

    # Check indication text  
    if indication_text and indication_text != "Indication not available":  
        indication_lower = indication_text.lower()  
        for keyword, specs in INDICATION_SPECIALTY_MAP.items():  
            if keyword.lower() in indication_lower:  
                for s in specs:  
                    matched.add(s)

    # Check drug name  
    if drug_name:  
        drug_lower = drug_name.lower()  
        for keyword, specs in INDICATION_SPECIALTY_MAP.items():  
            if keyword.lower() in drug_lower:  
                for s in specs:  
                    matched.add(s)

    # Route-based fallback  
    if not matched and route:  
        route_lower = route.lower()  
        if "ophthalmic" in route_lower:  
            matched.add("Ophthalmology")  
        elif "topical" in route_lower:  
            matched.add("Dermatology")

    # Ultimate fallback  
    if not matched:  
        matched.add("Internal Medicine")

    return list(matched)


# ============================================================  
# SECTION 3: NORTHWELL FAD API (REAL DOCTOR DATA)  
# ============================================================

def fetch_northwell_doctors(specialty, max_results=5):  
    """  
    Fetch real Northwell doctors from the FAD API.

    Correct endpoint: /v3/providers/search?specialty=X  
    Response structure confirmed from browser testing.  
    """  
    try:  
        url = (  
            f"https://fadapi.northwell.io/v3/providers/search"  
            f"?specialty={requests.utils.quote(specialty)}"  
        )

        headers = {  
            "Accept": "application/json",  
            "User-Agent": (  
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "  
                "AppleWebKit/537.36"  
            ),  
        }

        print(f"    Searching FAD API: {specialty}...")  
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 200:  
            data = response.json()

            # FAD API returns: {"code":200, "results":[...]}  
            results = data.get("results", [])

            if not results and isinstance(data, list):  
                results = data

            doctors = []  
            for provider in results[:max_results]:  
                # Extract name  
                first = provider.get("firstname", "")  
                last = provider.get("lastname", "")  
                degrees = provider.get("degrees", [])  
                degree_str = ", ".join(degrees) if degrees else ""

                if first and last:  
                    name = f"Dr. {first} {last}"  
                    if degree_str:  
                        name += f", {degree_str}"  
                else:  
                    display = provider.get("displayName", "")  
                    name = display if display else "Unknown"

                # Extract location  
                city = provider.get("city", "")  
                state = provider.get("state_abbr",  
                         provider.get("state", ""))  
                practice = provider.get("practice_name", "")  
                address = provider.get("street_address", "")

                if practice and city:  
                    location = f"{practice}, {city}, {state}"  
                elif city:  
                    location = f"{city}, {state}"  
                else:  
                    location = "Location not available"

                # Extract phone  
                phone = provider.get("phone", "")  
                if isinstance(phone, dict):  
                    phone = phone.get("formatted", str(phone))

                # Extract profile URL  
                url_path = provider.get("url", "")  
                if url_path and not url_path.startswith("http"):  
                    profile_url = f"https://www.northwell.edu{url_path}"  
                elif url_path:  
                    profile_url = url_path  
                else:  
                    npi = provider.get("provider_soarian_npi", "")  
                    profile_url = ""

                # Extract NPI  
                npi = provider.get(  
                    "provider_soarian_npi",  
                    provider.get("npi", "")  
                )

                # Get department  
                department = provider.get("department_me", specialty)

                # Build email from name pattern (Northwell format)  
                # This is a guess - may need adjustment  
                email = ""

                doctor = {  
                    "name": name,  
                    "specialty": department,  
                    "location": location,  
                    "address": address,  
                    "city": city,  
                    "state": state,  
                    "phone": str(phone),  
                    "npi": str(npi),  
                    "profile_url": profile_url,  
                    "practice_name": practice,  
                    "gender": provider.get("gender", ""),  
                    "teams_link": "",  
                    "email": email,  
                    "match_type": "DIRECT_SPECIALTY_MATCH",  
                    "relevance_score": 1.0,  
                    "matched_via": specialty,  
                }

                doctors.append(doctor)

            print(f"    Found {len(doctors)} doctor(s) for {specialty}")  
            return doctors

        else:  
            print(  
                f"    FAD API returned status {response.status_code} "  
                f"for {specialty}"  
            )  
            return []

    except Exception as e:  
        print(f"    Error querying FAD API for {specialty}: {e}")  
        return []


# ============================================================  
# SECTION 4: REPORT GENERATION  
# ============================================================

def build_email_html(approvals, date_from, date_to):  
    """Build the complete HTML email report for Maddie."""  
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

    html = f"""  
    <html>  
    <head>  
        <style>  
            body {{  
                font-family: Arial, sans-serif;  
                color: #333;  
                max-width: 950px;  
                margin: 0 auto;  
            }}  
            .header {{  
                background: linear-gradient(135deg, #0078d4, #00a4ef);  
                color: white;  
                padding: 25px 30px;  
                border-radius: 8px 8px 0 0;  
            }}  
            .header h1 {{ margin: 0; font-size: 22px; }}  
            .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}  
            .summary {{  
                background-color: #f0f6ff;  
                padding: 15px 30px;  
                border-bottom: 2px solid #0078d4;  
            }}  
            .summary-stats {{  
                display: flex; gap: 40px;  
            }}  
            .stat {{ text-align: center; }}  
            .stat .number {{  
                font-size: 28px;  
                font-weight: bold;  
                color: #0078d4;  
            }}  
            .stat .label {{  
                font-size: 12px; color: #666;  
            }}  
            .drug-card {{  
                border: 1px solid #e0e0e0;  
                border-left: 4px solid #0078d4;  
                border-radius: 4px;  
                margin: 20px 30px;  
                background: white;  
                overflow: hidden;  
            }}  
            .drug-header {{  
                background: #f8f9fa;  
                padding: 15px 20px;  
                border-bottom: 1px solid #e0e0e0;  
            }}  
            .drug-header h3 {{  
                color: #0078d4;  
                margin: 0; font-size: 18px;  
            }}  
            .drug-header .meta {{  
                color: #666; font-size: 13px; margin-top: 4px;  
            }}  
            .drug-body {{ padding: 15px 20px; }}  
            .info-grid {{  
                display: grid;  
                grid-template-columns: 1fr 1fr;  
                gap: 8px; font-size: 14px;  
            }}  
            .info-grid .lbl {{  
                font-weight: bold; color: #555;  
            }}  
            .indication {{  
                background: #fff3cd;  
                border: 1px solid #ffc107;  
                border-radius: 4px;  
                padding: 12px 15px;  
                margin: 12px 0;  
                font-size: 13px;  
                line-height: 1.5;  
            }}  
            .doctors {{  
                margin-top: 15px;  
                border-top: 1px solid #e0e0e0;  
                padding-top: 15px;  
            }}  
            .doctors h4 {{  
                color: #333;  
                margin: 0 0 10px 0;  
                font-size: 15px;  
            }}  
            .doc-row {{  
                display: flex;  
                align-items: center;  
                padding: 10px 12px;  
                margin: 4px 0;  
                background: #f8f9fa;  
                border-radius: 4px;  
                border-left: 3px solid #28a745;  
            }}  
            .doc-info {{ flex: 1; }}  
            .doc-name {{  
                font-weight: bold; color: #333; font-size: 14px;  
            }}  
            .doc-detail {{  
                color: #666; font-size: 12px; margin-top: 2px;  
            }}  
            .doc-actions {{  
                display: flex; gap: 6px;  
            }}  
            .btn {{  
                display: inline-block;  
                padding: 5px 12px;  
                border-radius: 4px;  
                text-decoration: none;  
                font-size: 11px;  
                font-weight: bold;  
                color: white;  
            }}  
            .btn-profile {{ background: #28a745; }}  
            .btn-phone {{ background: #6c757d; }}  
            .no-docs {{  
                color: #999; font-style: italic;  
                font-size: 13px; padding: 8px 0;  
            }}  
            .footer {{  
                padding: 20px 30px;  
                font-size: 12px;  
                color: #999;  
                border-top: 1px solid #eee;  
                margin-top: 20px;  
            }}  
        </style>  
    </head>  
    <body>  
        <div class="header">  
            <h1>FDA Daily Drug Approval Report</h1>  
            <p>Northwell Health — Physician Matching Report</p>  
            <p style="font-size:12px;">  
                Date Range: {from_display} to {to_display}  
            </p>  
        </div>  
        <div class="summary">  
            <div class="summary-stats">  
                <div class="stat">  
                    <div class="number">{len(approvals)}</div>  
                    <div class="label">Drug Approvals</div>  
                </div>  
                <div class="stat">  
                    <div class="number">{total_doctors}</div>  
                    <div class="label">Matched Physicians</div>  
                </div>  
                <div class="stat">  
                    <div class="number">{len(set(  
                        s for a in approvals  
                        for s in a.get('matched_specialties', [])  
                    ))}</div>  
                    <div class="label">Specialties</div>  
                </div>  
            </div>  
        </div>  
    """

    for i, a in enumerate(approvals, 1):  
        ingredients = ", ".join(  
            [f"{ai['name']} ({ai['strength']})"  
             for ai in a.get("active_ingredients", [])]  
        ) or "N/A"

        try:  
            date_disp = datetime.strptime(  
                a['approval_date'], "%Y%m%d"  
            ).strftime("%B %d, %Y")  
        except (ValueError, TypeError):  
            date_disp = a['approval_date']

        specs = ", ".join(a.get("matched_specialties", ["N/A"]))

        html += f"""  
        <div class="drug-card">  
            <div class="drug-header">  
                <h3>#{i} — {a['drug_name']}</h3>  
                <div class="meta">  
                    {a['generic_name']} | Approved: {date_disp} |  
                    {a['submission_type_description']}  
                </div>  
            </div>  
            <div class="drug-body">  
                <div class="info-grid">  
                    <div>  
                        <span class="lbl">Sponsor:</span>  
                        {a['sponsor']}  
                    </div>  
                    <div>  
                        <span class="lbl">Application:</span>  
                        {a['application_number']}  
                    </div>  
                    <div>  
                        <span class="lbl">Dosage:</span>  
                        {a['dosage_form']}  
                    </div>  
                    <div>  
                        <span class="lbl">Route:</span>  
                        {a['route']}  
                    </div>  
                    <div>  
                        <span class="lbl">Ingredients:</span>  
                        {ingredients}  
                    </div>  
                    <div>  
                        <span class="lbl">Specialties:</span>  
                        {specs}  
                    </div>  
                </div>  
        """

        # Indication  
        indication = a.get('indication', '')  
        if indication and indication != "Indication not available":  
            ind_short = indication[:400]  
            if len(indication) > 400:  
                ind_short += "..."  
            html += f"""  
                <div class="indication">  
                    <strong>Indication:</strong> {ind_short}  
                </div>  
            """

        # Matched doctors  
        doctors = a.get("matched_doctors", [])  
        html += '<div class="doctors">'  
        html += f'<h4>Matched Northwell Physicians ({len(doctors)})</h4>'

        if doctors:  
            for doc in doctors[:10]:  
                phone_btn = ""  
                if doc.get("phone"):  
                    phone_btn = (  
                        f'<a href="tel:{doc["phone"]}" '  
                        f'class="btn btn-phone">'  
                        f'{doc["phone"]}</a>'  
                    )

                profile_btn = ""  
                if doc.get("profile_url"):  
                    profile_btn = (  
                        f'<a href="{doc["profile_url"]}" '  
                        f'class="btn btn-profile" '  
                        f'target="_blank">View Profile</a>'  
                    )

                html += f"""  
                    <div class="doc-row">  
                        <div class="doc-info">  
                            <div class="doc-name">  
                                {doc['name']}  
                            </div>  
                            <div class="doc-detail">  
                                {doc.get('specialty', '')} |  
                                {doc.get('location', '')}  
                            </div>  
                        </div>  
                        <div class="doc-actions">  
                            {profile_btn}  
                            {phone_btn}  
                        </div>  
                    </div>  
                """  
        else:  
            html += """  
                <div class="no-docs">  
                    No matching physicians found for this drug.  
                </div>  
            """

        html += '</div></div></div>'

    html += f"""  
        <div class="footer">  
            <p>Generated automatically by the FDA Drug Approval  
            Monitor</p>  
            <p>Data: openFDA API + Northwell FAD API</p>  
            <p>Generated: {datetime.now().strftime(  
                '%B %d, %Y at %I:%M %p UTC'  
            )}</p>  
            <p><em>Please review matches before contacting.  
            Matching is based on specialty alignment with drug  
            indications.</em></p>  
        </div>  
    </body>  
    </html>  
    """

    return html


def send_email(subject, html_body, to_email, from_email, password):  
    """Send HTML email via SMTP."""  
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
        print(f"Email sent to {to_email}")  
        return True  
    except Exception as e:  
        print(f"Failed to send email: {e}")  
        return False


# ============================================================  
# SECTION 5: MAIN PIPELINE  
# ============================================================

def main():  
    """Main pipeline connecting all pieces together."""  
    print("=" * 70)  
    print("FDA DRUG APPROVAL MONITOR — UNIFIED PIPELINE")  
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")  
    print("=" * 70)  
    print()

    # STEP 1: Fetch FDA Approvals  
    print("STEP 1: Fetching FDA drug approvals...")  
    print("-" * 50)  
    approvals, date_from, date_to = fetch_fda_approvals(days_back=7)  
    print(f"\nFound {len(approvals)} new approval(s)")  
    print()

    if not approvals:  
        print("No approvals found. Generating empty report.")  
        html = build_email_html([], date_from, date_to)  
        with open("fda_report.html", "w") as f:  
            f.write(html)  
        return

    # STEP 2: Map Indications to Specialties  
    print("STEP 2: Mapping indications to specialties...")  
    print("-" * 50)  
    for a in approvals:  
        specs = map_indication_to_specialties(  
            a["indication"], a["drug_name"], a["route"]  
        )  
        a["matched_specialties"] = specs  
        print(f"  {a['drug_name']}: {', '.join(specs)}")  
    print()

    # STEP 3: Fetch Northwell Physicians  
    print("STEP 3: Fetching Northwell physicians (FAD API)...")  
    print("-" * 50)

    all_specialties = set()  
    for a in approvals:  
        for s in a["matched_specialties"]:  
            all_specialties.add(s)

    print(f"  Searching {len(all_specialties)} specialties: "  
          f"{', '.join(sorted(all_specialties))}")  
    print()

    doctors_cache = {}  
    for spec in sorted(all_specialties):  
        docs = fetch_northwell_doctors(spec, max_results=5)  
        doctors_cache[spec] = docs  
        time.sleep(0.3)  
    print()

    # STEP 4: Match Doctors to Drugs  
    print("STEP 4: Matching doctors to drug approvals...")  
    print("-" * 50)  
    for a in approvals:  
        matched = []  
        seen = set()  
        for spec in a["matched_specialties"]:  
            for doc in doctors_cache.get(spec, []):  
                doc_key = doc["name"] + doc.get("npi", "")  
                if doc_key not in seen:  
                    seen.add(doc_key)  
                    doc_copy = doc.copy()  
                    doc_copy["matched_via"] = spec  
                    matched.append(doc_copy)  
        a["matched_doctors"] = matched  
        print(f"  {a['drug_name']}: {len(matched)} doctor(s)")  
    print()

    # STEP 5: Generate Report  
    print("STEP 5: Generating report...")  
    print("-" * 50)

    print("\n" + "=" * 70)  
    print("FINAL REPORT")  
    print("=" * 70)  
    for i, a in enumerate(approvals, 1):  
        print(f"\n#{i} {a['drug_name']} ({a['generic_name']})")  
        print(f"   Approved: {a['approval_date']}")  
        print(f"   Specialties: {', '.join(a['matched_specialties'])}")  
        print(f"   Matched Doctors: {len(a['matched_doctors'])}")  
        for doc in a["matched_doctors"][:5]:  
            print(  
                f"     -> {doc['name']}"  
                f" | {doc.get('specialty', 'N/A')}"  
                f" | {doc.get('location', 'N/A')}"  
                f" | {doc.get('phone', 'N/A')}"  
            )  
        if len(a["matched_doctors"]) > 5:  
            remaining = len(a["matched_doctors"]) - 5  
            print(f"     ... and {remaining} more")

    # Build HTML  
    html = build_email_html(approvals, date_from, date_to)  
    with open("fda_report.html", "w") as f:  
        f.write(html)  
    print("\nHTML report saved to fda_report.html")

    # Save JSON  
    results = {  
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  
        "date_range": {"from": date_from, "to": date_to},  
        "total_approvals": len(approvals),  
        "total_matched_doctors": sum(  
            len(a["matched_doctors"]) for a in approvals  
        ),  
        "approvals": approvals,  
    }  
    with open("fda_results.json", "w") as f:  
        json.dump(results, f, indent=2, default=str)  
    print("JSON results saved to fda_results.json")

    # Email  
    to_email = os.environ.get("EMAIL_TO")  
    from_email = os.environ.get("EMAIL_FROM")  
    email_password = os.environ.get("EMAIL_PASSWORD")

    if to_email and from_email and email_password:  
        total = sum(len(a["matched_doctors"]) for a in approvals)  
        subject = (  
            f"FDA Report — {datetime.now().strftime('%B %d, %Y')}"  
            f" — {len(approvals)} approvals,"  
            f" {total} matched doctors"  
        )  
        send_email(subject, html, to_email, from_email, email_password)  
    else:  
        print("\nEmail not configured.")

    print("\n" + "=" * 70)  
    print("PIPELINE COMPLETE")  
    print("=" * 70)


if __name__ == "__main__":  
    main()  
