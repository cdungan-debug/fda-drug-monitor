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
import sys


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
                    if not (int(date_from) <= sub_date_int  
                            <= int(date_to)):  
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

        # Fetch indications  
        print(f"Found {len(approvals)} new approval(s) in range.")  
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
    "pulmonary arterial hypertension": [  
        "Pulmonology", "Cardiology"  
    ],  
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
    "capecitabine": ["Oncology"],  
    "azacitidine": ["Oncology"],

    # Neurology  
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
    "estradiol": ["Endocrinology", "OB/GYN"],  
    "menopausal": ["Endocrinology", "OB/GYN"],  
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
    "rextovy": ["Emergency Medicine"],

    # OB/GYN  
    "pregnancy": ["OB/GYN"],  
    "doxylamine": ["OB/GYN"],  
    "pyridoxine": ["OB/GYN"],

    # Topical/route based  
    "topical": ["Dermatology"],  
}


def map_indication_to_specialties(indication_text, drug_name="",  
                                   route=""):  
    """Map drug indication to relevant medical specialties."""  
    matched = set()

    if indication_text and indication_text != \  
            "Indication not available":  
        indication_lower = indication_text.lower()  
        for keyword, specs in INDICATION_SPECIALTY_MAP.items():  
            if keyword.lower() in indication_lower:  
                for s in specs:  
                    matched.add(s)

    if drug_name:  
        drug_lower = drug_name.lower()  
        for keyword, specs in INDICATION_SPECIALTY_MAP.items():  
            if keyword.lower() in drug_lower:  
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
# SECTION 3: NORTHWELL FAD API (REAL DOCTOR DATA)  
# ============================================================

# Map our specialty names to what FAD API expects  
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
    "OB/GYN": "obstetrics-and-gynecology",  
    "Obstetrics and Gynecology": "obstetrics-and-gynecology",  
}


def fetch_northwell_doctors(specialty, max_results=5):  
    """  
    Fetch real Northwell doctors from the FAD API.

    Confirmed working endpoint from browser testing:  
    GET https://fadapi.northwell.io/v3/providers/search  
        ?specialty=cardiology

    Response: {"code":200, "results":[{doctor data}...]}  
    """  
    # Map specialty to FAD API format  
    fad_specialty = FAD_SPECIALTY_MAP.get(  
        specialty, specialty.lower().replace(" ", "-")  
    )

    try:  
        url = (  
            f"https://fadapi.northwell.io/v3/providers/search"  
            f"?specialty={fad_specialty}"  
        )

        # Mimic browser headers exactly  
        headers = {  
            "Accept": (  
                "text/html,application/xhtml+xml,"  
                "application/xml;q=0.9,"  
                "image/avif,image/webp,image/apng,*/*;q=0.8"  
            ),  
            "Accept-Language": "en-US,en;q=0.9",  
            "User-Agent": (  
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "  
                "AppleWebKit/537.36 (KHTML, like Gecko) "  
                "Chrome/137.0.0.0 Safari/537.36"  
            ),  
            "Connection": "keep-alive",  
            "Cache-Control": "no-cache",  
        }

        print(f"    FAD API: {url}")  
        response = requests.get(url, headers=headers, timeout=15)

        print(f"    Status: {response.status_code}")  
        print(f"    Response length: {len(response.text)} chars")

        # Debug: show first 200 chars of response  
        preview = response.text[:200]  
        print(f"    Preview: {preview}")

        if response.status_code == 200:  
            data = response.json()

            # FAD API structure:  
            # {"code":200, "results":[...]}  
            results = data.get("results", [])

            print(f"    Parsed {len(results)} provider(s)")

            doctors = []  
            for provider in results[:max_results]:  
                first = provider.get("firstname", "")  
                last = provider.get("lastname", "")  
                degrees = provider.get("degrees", [])  
                degree_str = ", ".join(degrees) if degrees else ""

                if first and last:  
                    name = f"Dr. {first} {last}"  
                    if degree_str:  
                        name += f", {degree_str}"  
                else:  
                    name = "Unknown"

                city = provider.get("city", "")  
                state_abbr = provider.get(  
                    "state_abbr",  
                    provider.get("state", "")  
                )  
                practice = provider.get("practice_name", "")  
                address = provider.get("street_address", "")

                if practice and city:  
                    location = f"{practice}, {city}, {state_abbr}"  
                elif city:  
                    location = f"{city}, {state_abbr}"  
                else:  
                    location = "Location not available"

                phone = provider.get("phone", "")  
                if isinstance(phone, dict):  
                    phone = phone.get("formatted", "")

                url_path = provider.get("url", "")  
                if url_path and not url_path.startswith("http"):  
                    profile_url = (  
                        f"https://www.northwell.edu{url_path}"  
                    )  
                else:  
                    profile_url = url_path or ""

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
                    "gender": provider.get("gender", ""),  
                    "match_type": "DIRECT_SPECIALTY_MATCH",  
                    "relevance_score": 1.0,  
                    "matched_via": specialty,  
                })

            print(f"    Extracted {len(doctors)} doctor(s)")  
            return doctors

        else:  
            print(f"    FAD API error for {specialty}")  
            return []

    except Exception as e:  
        print(f"    Error: {e}")  
        return []


# ============================================================  
# SECTION 4: REPORT GENERATION  
# ============================================================

def build_email_html(approvals, date_from, date_to):  
    """Build HTML email report for Maddie."""  
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
                color: #333; max-width: 950px;  
                margin: 0 auto;  
            }}  
            .header {{  
                background: linear-gradient(  
                    135deg, #0078d4, #00a4ef  
                );  
                color: white; padding: 25px 30px;  
                border-radius: 8px 8px 0 0;  
            }}  
            .header h1 {{ margin: 0; font-size: 22px; }}  
            .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}  
            .summary {{  
                background: #f0f6ff;  
                padding: 15px 30px;  
                border-bottom: 2px solid #0078d4;  
            }}  
            .drug-card {{  
                border: 1px solid #e0e0e0;  
                border-left: 4px solid #0078d4;  
                border-radius: 4px;  
                margin: 20px 30px;  
                background: white; overflow: hidden;  
            }}  
            .drug-header {{  
                background: #f8f9fa;  
                padding: 15px 20px;  
                border-bottom: 1px solid #e0e0e0;  
            }}  
            .drug-header h3 {{  
                color: #0078d4; margin: 0;  
                font-size: 18px;  
            }}  
            .drug-header .meta {{  
                color: #666; font-size: 13px;  
                margin-top: 4px;  
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
                font-size: 13px; line-height: 1.5;  
            }}  
            .doctors {{  
                margin-top: 15px;  
                border-top: 1px solid #e0e0e0;  
                padding-top: 15px;  
            }}  
            .doctors h4 {{  
                color: #333; margin: 0 0 10px 0;  
                font-size: 15px;  
            }}  
            .doc-row {{  
                display: flex; align-items: center;  
                padding: 10px 12px; margin: 4px 0;  
                background: #f8f9fa; border-radius: 4px;  
                border-left: 3px solid #28a745;  
            }}  
            .doc-info {{ flex: 1; }}  
            .doc-name {{  
                font-weight: bold; color: #333;  
                font-size: 14px;  
            }}  
            .doc-detail {{  
                color: #666; font-size: 12px;  
                margin-top: 2px;  
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
                font-weight: bold; color: white;  
            }}  
            .btn-profile {{ background: #28a745; }}  
            .btn-phone {{ background: #6c757d; }}  
            .no-docs {{  
                color: #999; font-style: italic;  
                font-size: 13px; padding: 8px 0;  
            }}  
            .footer {{  
                padding: 20px 30px;  
                font-size: 12px; color: #999;  
                border-top: 1px solid #eee;  
                margin-top: 20px;  
            }}  
        </style>  
    </head>  
    <body>  
        <div class="header">  
            <h1>FDA Daily Drug Approval Report</h1>  
            <p>Northwell Health Physician Matching</p>  
            <p style="font-size:12px;">  
                {from_display} to {to_display}  
            </p>  
        </div>  
        <div class="summary">  
            <strong>{len(approvals)}</strong> Drug Approvals |  
            <strong>{total_doctors}</strong> Matched Physicians |  
            <strong>{len(set(  
                s for a in approvals  
                for s in a.get('matched_specialties', [])  
            ))}</strong> Specialties  
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

        specs = ", ".join(  
            a.get("matched_specialties", ["N/A"])  
        )

        html += f"""  
        <div class="drug-card">  
            <div class="drug-header">  
                <h3>#{i} — {a['drug_name']}</h3>  
                <div class="meta">  
                    {a['generic_name']} |  
                    Approved: {date_disp} |  
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

        doctors = a.get("matched_doctors", [])  
        html += '<div class="doctors">'  
        html += (  
            f'<h4>Matched Northwell Physicians '  
            f'({len(doctors)})</h4>'  
        )

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
                        f'target="_blank">Profile</a>'  
                    )

                html += f"""  
                    <div class="doc-row">  
                        <div class="doc-info">  
                            <div class="doc-name">  
                                {doc['name']}  
                            </div>  
                            <div class="doc-detail">  
                                {doc.get('specialty', '')} |  
                                {doc.get('location', '')} |  
                                Matched via:  
                                {doc.get('matched_via', '')}  
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
                    No matching physicians found.  
                </div>  
            """

        html += '</div></div></div>'

    html += f"""  
        <div class="footer">  
            <p>Generated by FDA Drug Approval Monitor</p>  
            <p>Sources: openFDA API + Northwell FAD API</p>  
            <p>{datetime.now().strftime(  
                '%B %d, %Y at %I:%M %p UTC'  
            )}</p>  
            <p><em>Please review before contacting  
            physicians.</em></p>  
        </div>  
    </body>  
    </html>  
    """

    return html


def send_email(subject, html_body, to_email, from_email,  
               password):  
    """Send HTML email."""  
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
    """Main pipeline."""  
    print("=" * 70)  
    print("FDA DRUG APPROVAL MONITOR — UNIFIED PIPELINE")  
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")  
    print("=" * 70)  
    print()

    # STEP 1: FDA Approvals  
    print("STEP 1: Fetching FDA drug approvals...")  
    print("-" * 50)  
    approvals, date_from, date_to = fetch_fda_approvals(  
        days_back=7  
    )  
    print(f"\nFound {len(approvals)} new approval(s)")  
    print()

    if not approvals:  
        print("No approvals found.")  
        html = build_email_html([], date_from, date_to)  
        with open("fda_report.html", "w") as f:  
            f.write(html)  
        return

    # STEP 2: Specialty Mapping  
    print("STEP 2: Mapping indications to specialties...")  
    print("-" * 50)  
    for a in approvals:  
        specs = map_indication_to_specialties(  
            a["indication"], a["drug_name"], a["route"]  
        )  
        a["matched_specialties"] = specs  
        print(f"  {a['drug_name']}: {', '.join(specs)}")  
    print()

    # STEP 3: Northwell Physicians  
    print("STEP 3: Fetching Northwell physicians...")  
    print("-" * 50)

    all_specs = set()  
    for a in approvals:  
        for s in a["matched_specialties"]:  
            all_specs.add(s)

    print(f"  Specialties: {', '.join(sorted(all_specs))}")  
    print()

    doctors_cache = {}  
    for spec in sorted(all_specs):  
        print(f"  --- Searching: {spec} ---")  
        docs = fetch_northwell_doctors(spec, max_results=5)  
        doctors_cache[spec] = docs  
        print()  
        time.sleep(0.5)

    # STEP 4: Match  
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
        print(f"  {a['drug_name']}: {len(matched)} doctor(s)")  
    print()

    # STEP 5: Report  
    print("STEP 5: Generating report...")  
    print("-" * 50)

    print("\n" + "=" * 70)  
    print("FINAL REPORT")  
    print("=" * 70)  
    for i, a in enumerate(approvals, 1):  
        print(f"\n#{i} {a['drug_name']} ({a['generic_name']})")  
        print(f"   Approved: {a['approval_date']}")  
        print(f"   Specialties: "  
              f"{', '.join(a['matched_specialties'])}")  
        print(f"   Doctors: {len(a['matched_doctors'])}")  
        for doc in a["matched_doctors"][:5]:  
            print(  
                f"     -> {doc['name']}"  
                f" | {doc.get('specialty', '')}"  
                f" | {doc.get('city', '')}"  
                f" | {doc.get('phone', '')}"  
            )

    html = build_email_html(approvals, date_from, date_to)  
    with open("fda_report.html", "w") as f:  
        f.write(html)  
    print("\nHTML report saved to fda_report.html")

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
            f"FDA Report — "  
            f"{datetime.now().strftime('%B %d, %Y')}"  
            f" — {len(approvals)} approvals,"  
            f" {total} doctors"  
        )  
        send_email(  
            subject, html, to_email, from_email, email_password  
        )  
    else:  
        print("\nEmail not configured.")

    print("\n" + "=" * 70)  
    print("PIPELINE COMPLETE")  
    print("=" * 70)


if __name__ == "__main__":  
    main()  
