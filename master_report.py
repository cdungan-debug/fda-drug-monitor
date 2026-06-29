"""  
FDA Master Report Generator  
Runs daily via GitHub Actions at 9am EST  
Fetches ALL FDA drug approvals for the last 2 years  
Generates a formatted Excel XML file  
"""

import urllib.request  
import urllib.parse  
import json  
import time  
import os  
from datetime import datetime, timedelta


SPECIALTY_MAP = {  
    "hypertension": "Cardiology",  
    "heart failure": "Cardiology",  
    "cardiac": "Cardiology",  
    "cardiovascular": "Cardiology",  
    "angina": "Cardiology",  
    "arrhythmia": "Cardiology",  
    "atrial fibrillation": "Cardiology",  
    "blood pressure": "Cardiology",  
    "cholesterol": "Cardiology",  
    "statin": "Cardiology",  
    "anticoagulant": "Cardiology",  
    "thrombosis": "Cardiology",  
    "cancer": "Oncology",  
    "tumor": "Oncology",  
    "carcinoma": "Oncology",  
    "lymphoma": "Oncology",  
    "leukemia": "Oncology",  
    "melanoma": "Oncology",  
    "metastatic": "Oncology",  
    "neoplasm": "Oncology",  
    "sarcoma": "Oncology",  
    "myeloma": "Oncology",  
    "chemotherapy": "Oncology",  
    "seizure": "Neurology",  
    "epilepsy": "Neurology",  
    "neurological": "Neurology",  
    "anticonvulsant": "Neurology",  
    "multiple sclerosis": "Neurology",  
    "parkinson": "Neurology",  
    "migraine": "Neurology",  
    "neuropathy": "Neurology",  
    "schizophrenia": "Psychiatry",  
    "bipolar": "Psychiatry",  
    "antipsychotic": "Psychiatry",  
    "depression": "Psychiatry",  
    "anxiety": "Psychiatry",  
    "antidepressant": "Psychiatry",  
    "insomnia": "Psychiatry",  
    "adhd": "Psychiatry",  
    "acne": "Dermatology",  
    "dermatitis": "Dermatology",  
    "psoriasis": "Dermatology",  
    "eczema": "Dermatology",  
    "rosacea": "Dermatology",  
    "skin": "Dermatology",  
    "topical": "Dermatology",  
    "asthma": "Pulmonology",  
    "copd": "Pulmonology",  
    "pulmonary": "Pulmonology",  
    "respiratory": "Pulmonology",  
    "bronchitis": "Pulmonology",  
    "inhaler": "Pulmonology",  
    "arthritis": "Rheumatology",  
    "rheumatoid": "Rheumatology",  
    "lupus": "Rheumatology",  
    "autoimmune": "Rheumatology",  
    "fibromyalgia": "Rheumatology",  
    "gout": "Rheumatology",  
    "glaucoma": "Ophthalmology",  
    "ophthalmic": "Ophthalmology",  
    "retinal": "Ophthalmology",  
    "macular": "Ophthalmology",  
    "eye drops": "Ophthalmology",  
    "liver": "Gastroenterology",  
    "hepatic": "Gastroenterology",  
    "hepatitis": "Gastroenterology",  
    "gastrointestinal": "Gastroenterology",  
    "nausea": "Gastroenterology",  
    "ulcer": "Gastroenterology",  
    "crohn": "Gastroenterology",  
    "colitis": "Gastroenterology",  
    "constipation": "Gastroenterology",  
    "renal": "Nephrology",  
    "kidney": "Nephrology",  
    "dialysis": "Nephrology",  
    "diabetes": "Endocrinology",  
    "thyroid": "Endocrinology",  
    "osteoporosis": "Endocrinology",  
    "hormone": "Endocrinology",  
    "insulin": "Endocrinology",  
    "glucose": "Endocrinology",  
    "infection": "Infectious Disease",  
    "antibacterial": "Infectious Disease",  
    "antiviral": "Infectious Disease",  
    "antibiotic": "Infectious Disease",  
    "antifungal": "Infectious Disease",  
    "hiv": "Infectious Disease",  
    "pneumonia": "Infectious Disease",  
    "sepsis": "Infectious Disease",  
    "anemia": "Hematology",  
    "hemophilia": "Hematology",  
    "platelet": "Hematology",  
    "blood disorder": "Hematology",  
    "sickle cell": "Hematology",  
    "prostate": "Urology",  
    "bladder": "Urology",  
    "urinary": "Urology",  
    "erectile": "Urology",  
    "orthopedic": "Orthopedics",  
    "bone": "Orthopedics",  
    "fracture": "Orthopedics",  
    "joint": "Orthopedics",  
    "pregnancy": "OB/GYN",  
    "contracepti": "OB/GYN",  
    "estradiol": "OB/GYN",  
    "menopausal": "OB/GYN",  
    "fertility": "OB/GYN",  
    "pain": "Pain Medicine",  
    "analgesic": "Pain Medicine",  
    "anesthetic": "Anesthesiology",  
    "sedation": "Anesthesiology",  
    "allergy": "Allergy/Immunology",  
    "immunotherapy": "Allergy/Immunology",  
    "histamine": "Allergy/Immunology",  
    "contrast": "Radiology",  
    "imaging": "Radiology",  
    "pediatric": "Pediatrics",  
    "children": "Pediatrics",  
    "infant": "Pediatrics",  
    "neonatal": "Pediatrics",  
    "hearing": "ENT",  
    "nasal": "ENT",  
    "sinusitis": "ENT",  
    "tinnitus": "ENT",  
    "naloxone": "Emergency Medicine",  
    "overdose": "Emergency Medicine",  
}


def map_specialty(indication, drug_name):  
    text = (str(indication) + " " +  
            str(drug_name)).lower()  
    for keyword, specialty in SPECIALTY_MAP.items():  
        if keyword in text:  
            return specialty  
    return "General / Review Needed"


def escape_xml(s):  
    if not s:  
        return ""  
    s = str(s)  
    s = s.replace("&", "&")  
    s = s.replace("<", "<")  
    s = s.replace(">", ">")  
    s = s.replace('"', """)  
    s = s.replace("'", "'")  
    return s


def fetch_fda_page(date_from, date_to, skip, limit):  
    url = (  
        "https://api.fda.gov/drug/drugsfda.json?"  
        "search=submissions.submission_status_date:"  
        "[" + date_from + "+TO+" + date_to + "]"  
        "&limit=" + str(limit) +  
        "&skip=" + str(skip)  
    )  
    try:  
        req = urllib.request.Request(url)  
        req.add_header("User-Agent", "FDA-Monitor/1.0")  
        resp = urllib.request.urlopen(req, timeout=30)  
        data = json.loads(resp.read().decode("utf-8"))  
        return data  
    except urllib.error.HTTPError as e:  
        if e.code == 404:  
            return None  
        print("  HTTP Error " + str(e.code) +  
              " at skip=" + str(skip))  
        return None  
    except Exception as e:  
        print("  Error: " + str(e))  
        return None


def fetch_indication(app_number):  
    url = (  
        "https://api.fda.gov/drug/label.json?"  
        "search=openfda.application_number:%22" +  
        str(app_number) + "%22&limit=1"  
    )  
    try:  
        req = urllib.request.Request(url)  
        req.add_header("User-Agent", "FDA-Monitor/1.0")  
        resp = urllib.request.urlopen(req, timeout=15)  
        data = json.loads(resp.read().decode("utf-8"))  
        results = data.get("results", [])  
        if results:  
            label = results[0]  
            ind = label.get(  
                "indications_and_usage", [""]  
            )  
            if ind and ind[0]:  
                text = ind[0]  
                if len(text) > 500:  
                    text = text[:500] + "..."  
                return text  
            purp = label.get("purpose", [""])  
            if purp and purp[0]:  
                return purp[0]  
        return "N/A"  
    except Exception:  
        return "N/A"


def main():  
    print("=" * 60)  
    print("FDA MASTER REPORT GENERATOR")  
    print("Run: " + datetime.now().strftime(  
        "%Y-%m-%d %H:%M:%S"  
    ))  
    print("=" * 60)

    # Calculate date range (last 2 years)  
    today = datetime.now()  
    two_years_ago = today - timedelta(days=730)  
    date_from = two_years_ago.strftime("%Y%m%d")  
    date_to = today.strftime("%Y%m%d")

    print("Date range: " + date_from + " to " + date_to)  
    print()

    # Fetch all approvals with pagination  
    all_results = []  
    skip = 0  
    limit = 100  
    max_pages = 50

    for page in range(max_pages):  
        print("Fetching page " + str(page + 1) +  
              " (skip=" + str(skip) + ")...")  
        data = fetch_fda_page(  
            date_from, date_to, skip, limit  
        )

        if not data:  
            print("  No more results.")  
            break

        results = data.get("results", [])  
        if not results:  
            print("  Empty page.")  
            break

        all_results.extend(results)  
        total = data.get("meta", {}).get(  
            "results", {}  
        ).get("total", 0)

        print("  Got " + str(len(results)) +  
              " results. Total available: " +  
              str(total))

        skip += limit  
        if skip >= total:  
            break

        time.sleep(0.3)

    print()  
    print("Total raw results: " +  
          str(len(all_results)))

    # Parse approvals  
    approvals = []  
    seen = {}

    for drug in all_results:  
        submissions = drug.get("submissions", [])  
        products = drug.get("products", [])  
        openfda = drug.get("openfda", {})  
        app_num = drug.get(  
            "application_number", "Unknown"  
        )

        for sub in submissions:  
            sub_date = sub.get(  
                "submission_status_date", ""  
            )  
            sub_status = sub.get(  
                "submission_status", ""  
            )

            if not sub_date or sub_status != "AP":  
                continue

            try:  
                sub_int = int(sub_date)  
                if (sub_int < int(date_from) or  
                        sub_int > int(date_to)):  
                    continue  
            except ValueError:  
                continue

            key = app_num + "_" + sub_date  
            if key in seen:  
                continue  
            seen[key] = True

            drug_name = "Unknown"  
            dosage_form = "Unknown"  
            route = "Unknown"  
            ingredients = "N/A"

            if products:  
                drug_name = products[0].get(  
                    "brand_name", "Unknown"  
                )  
                dosage_form = products[0].get(  
                    "dosage_form", "Unknown"  
                )  
                route = products[0].get(  
                    "route", "Unknown"  
                )  
                ais = products[0].get(  
                    "active_ingredients", []  
                )  
                if ais:  
                    parts = []  
                    for ai in ais:  
                        name = ai.get(  
                            "name", "Unknown"  
                        )  
                        strength = ai.get(  
                            "strength", ""  
                        )  
                        if strength:  
                            parts.append(  
                                name + " (" +  
                                strength + ")"  
                            )  
                        else:  
                            parts.append(name)  
                    ingredients = "; ".join(parts)

            generic = "Unknown"  
            g_names = openfda.get(  
                "generic_name", []  
            )  
            if g_names:  
                generic = g_names[0]

            sub_type = sub.get(  
                "submission_type", "Unknown"  
            )  
            type_desc = sub_type  
            if sub_type == "ORIG":  
                type_desc = "New Drug Application"  
            elif sub_type == "SUPPL":  
                type_desc = "Supplemental"  
            elif sub_type == "ABBR":  
                type_desc = "Abbreviated (Generic)"

            date_display = sub_date  
            if len(sub_date) == 8:  
                date_display = (  
                    sub_date[4:6] + "/" +  
                    sub_date[6:8] + "/" +  
                    sub_date[0:4]  
                )

            approvals.append({  
                "drug_name": drug_name,  
                "generic_name": generic,  
                "approval_date": date_display,  
                "approval_date_raw": sub_date,  
                "application_number": app_num,  
                "submission_type": type_desc,  
                "sponsor": drug.get(  
                    "sponsor_name", "Unknown"  
                ),  
                "dosage_form": dosage_form,  
                "route": route,  
                "active_ingredients": ingredients,  
                "indication": "",  
                "specialty": "",  
            })

    print("Parsed approvals: " + str(len(approvals)))

    # Fetch indications (unique app numbers only)  
    unique_apps = list(set(  
        a["application_number"] for a in approvals  
    ))  
    print("Fetching indications for " +  
          str(len(unique_apps)) +  
          " unique applications...")

    ind_map = {}  
    for i, app_num in enumerate(unique_apps):  
        if (i + 1) % 50 == 0:  
            print("  " + str(i + 1) + "/" +  
                  str(len(unique_apps)))  
        ind_map[app_num] = fetch_indication(app_num)  
        time.sleep(0.15)

    # Apply indications and specialties  
    for a in approvals:  
        ind = ind_map.get(  
            a["application_number"], "N/A"  
        )  
        a["indication"] = ind  
        a["specialty"] = map_specialty(  
            ind, a["drug_name"]  
        )

    # Sort by date descending (newest first)  
    approvals.sort(  
        key=lambda x: x["approval_date_raw"],  
        reverse=True  
    )

    print()  
    print("Building Excel report...")

    # Count stats  
    type_counts = {}  
    spec_counts = {}  
    sponsor_counts = {}

    for a in approvals:  
        st = a["submission_type"]  
        type_counts[st] = type_counts.get(st, 0) + 1  
        sp = a["specialty"]  
        spec_counts[sp] = spec_counts.get(sp, 0) + 1  
        sn = a["sponsor"]  
        sponsor_counts[sn] = (  
            sponsor_counts.get(sn, 0) + 1  
        )

    spec_sorted = sorted(  
        spec_counts.keys(),  
        key=lambda x: spec_counts[x],  
        reverse=True  
    )  
    sponsor_sorted = sorted(  
        sponsor_counts.keys(),  
        key=lambda x: sponsor_counts[x],  
        reverse=True  
    )

    from_display = (  
        two_years_ago.strftime("%B %d, %Y")  
    )  
    to_display = today.strftime("%B %d, %Y")

    # Build XML  
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'  
    xml += '<?mso-application progid="Excel.Sheet"?>\n'  
    xml += '<Workbook xmlns="urn:schemas-microsoft-com'  
    xml += ':office:spreadsheet"\n'  
    xml += ' xmlns:ss="urn:schemas-microsoft-com'  
    xml += ':office:spreadsheet">\n'

    # Styles  
    xml += '<Styles>\n'  
    xml += '<Style ss:ID="Default" ss:Name="Normal">\n'  
    xml += '  <Font ss:FontName="Calibri" '  
    xml += 'ss:Size="11"/>\n'  
    xml += '  <Alignment ss:Vertical="Center" '  
    xml += 'ss:WrapText="1"/>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="title">\n'  
    xml += '  <Font ss:FontName="Calibri" ss:Size="18"'  
    xml += ' ss:Bold="1" ss:Color="#FFFFFF"/>\n'  
    xml += '  <Interior ss:Color="#0078D4" '  
    xml += 'ss:Pattern="Solid"/>\n'  
    xml += '  <Alignment ss:Vertical="Center"/>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="subtitle">\n'  
    xml += '  <Font ss:FontName="Calibri" ss:Size="12"'  
    xml += ' ss:Color="#FFFFFF"/>\n'  
    xml += '  <Interior ss:Color="#0078D4" '  
    xml += 'ss:Pattern="Solid"/>\n'  
    xml += '  <Alignment ss:Vertical="Center"/>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="section">\n'  
    xml += '  <Font ss:FontName="Calibri" ss:Size="13"'  
    xml += ' ss:Bold="1" ss:Color="#0078D4"/>\n'  
    xml += '  <Borders><Border ss:Position="Bottom" '  
    xml += 'ss:LineStyle="Continuous" ss:Weight="2" '  
    xml += 'ss:Color="#0078D4"/></Borders>\n'  
    xml += '  <Alignment ss:Vertical="Center"/>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="header">\n'  
    xml += '  <Font ss:FontName="Calibri" ss:Size="11"'  
    xml += ' ss:Bold="1" ss:Color="#FFFFFF"/>\n'  
    xml += '  <Interior ss:Color="#0078D4" '  
    xml += 'ss:Pattern="Solid"/>\n'  
    xml += '  <Alignment ss:Vertical="Center" '  
    xml += 'ss:WrapText="1"/>\n'  
    xml += '  <Borders>'  
    xml += '<Border ss:Position="Bottom" '  
    xml += 'ss:LineStyle="Continuous" ss:Weight="1" '  
    xml += 'ss:Color="#005A9E"/>'  
    xml += '<Border ss:Position="Left" '  
    xml += 'ss:LineStyle="Continuous" ss:Weight="1" '  
    xml += 'ss:Color="#005A9E"/>'  
    xml += '<Border ss:Position="Right" '  
    xml += 'ss:LineStyle="Continuous" ss:Weight="1" '  
    xml += 'ss:Color="#005A9E"/>'  
    xml += '</Borders>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="data">\n'  
    xml += '  <Font ss:FontName="Calibri" '  
    xml += 'ss:Size="11"/>\n'  
    xml += '  <Alignment ss:Vertical="Center" '  
    xml += 'ss:WrapText="1"/>\n'  
    xml += '  <Borders>'  
    xml += '<Border ss:Position="Bottom" '  
    xml += 'ss:LineStyle="Continuous" ss:Weight="1" '  
    xml += 'ss:Color="#E0E0E0"/>'  
    xml += '</Borders>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="dataAlt">\n'  
    xml += '  <Font ss:FontName="Calibri" '  
    xml += 'ss:Size="11"/>\n'  
    xml += '  <Interior ss:Color="#F2F7FC" '  
    xml += 'ss:Pattern="Solid"/>\n'  
    xml += '  <Alignment ss:Vertical="Center" '  
    xml += 'ss:WrapText="1"/>\n'  
    xml += '  <Borders>'  
    xml += '<Border ss:Position="Bottom" '  
    xml += 'ss:LineStyle="Continuous" ss:Weight="1" '  
    xml += 'ss:Color="#E0E0E0"/>'  
    xml += '</Borders>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="drugName">\n'  
    xml += '  <Font ss:FontName="Calibri" ss:Size="11"'  
    xml += ' ss:Bold="1" ss:Color="#333333"/>\n'  
    xml += '  <Alignment ss:Vertical="Center"/>\n'  
    xml += '  <Borders>'  
    xml += '<Border ss:Position="Bottom" '  
    xml += 'ss:LineStyle="Continuous" ss:Weight="1" '  
    xml += 'ss:Color="#E0E0E0"/>'  
    xml += '</Borders>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="drugNameAlt">\n'  
    xml += '  <Font ss:FontName="Calibri" ss:Size="11"'  
    xml += ' ss:Bold="1" ss:Color="#333333"/>\n'  
    xml += '  <Interior ss:Color="#F2F7FC" '  
    xml += 'ss:Pattern="Solid"/>\n'  
    xml += '  <Alignment ss:Vertical="Center"/>\n'  
    xml += '  <Borders>'  
    xml += '<Border ss:Position="Bottom" '  
    xml += 'ss:LineStyle="Continuous" ss:Weight="1" '  
    xml += 'ss:Color="#E0E0E0"/>'  
    xml += '</Borders>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="infoLabel">\n'  
    xml += '  <Font ss:FontName="Calibri" ss:Size="11"'  
    xml += ' ss:Bold="1" ss:Color="#555555"/>\n'  
    xml += '  <Alignment ss:Vertical="Center"/>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="infoValue">\n'  
    xml += '  <Font ss:FontName="Calibri" ss:Size="11"'  
    xml += ' ss:Color="#333333"/>\n'  
    xml += '  <Alignment ss:Vertical="Center"/>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="countNum">\n'  
    xml += '  <Font ss:FontName="Calibri" '  
    xml += 'ss:Size="11"/>\n'  
    xml += '  <Alignment ss:Horizontal="Center" '  
    xml += 'ss:Vertical="Center"/>\n'  
    xml += '</Style>\n'

    xml += '<Style ss:ID="specGroup">\n'  
    xml += '  <Font ss:FontName="Calibri" ss:Size="12"'  
    xml += ' ss:Bold="1" ss:Color="#FFFFFF"/>\n'  
    xml += '  <Interior ss:Color="#28A745" '  
    xml += 'ss:Pattern="Solid"/>\n'  
    xml += '  <Alignment ss:Vertical="Center"/>\n'  
    xml += '</Style>\n'

    xml += '</Styles>\n'

    # SHEET 1: SUMMARY  
    xml += '<Worksheet ss:Name="Summary">\n'  
    xml += '<Table ss:DefaultRowHeight="20">\n'  
    xml += '<Column ss:Width="200"/>\n'  
    xml += '<Column ss:Width="300"/>\n'

    xml += '<Row ss:Height="40">'  
    xml += '<Cell ss:StyleID="title" '  
    xml += 'ss:MergeAcross="1">'  
    xml += '<Data ss:Type="String">'  
    xml += 'FDA Master Drug Approval Report'  
    xml += '</Data></Cell></Row>\n'

    xml += '<Row ss:Height="25">'  
    xml += '<Cell ss:StyleID="subtitle" '  
    xml += 'ss:MergeAcross="1">'  
    xml += '<Data ss:Type="String">'  
    xml += 'Northwell Health - Business Operations'  
    xml += '</Data></Cell></Row>\n'

    xml += '<Row><Cell><Data ss:Type="String">'  
    xml += '</Data></Cell></Row>\n'

    xml += '<Row>'  
    xml += '<Cell ss:StyleID="infoLabel">'  
    xml += '<Data ss:Type="String">Last Updated:'  
    xml += '</Data></Cell>'  
    xml += '<Cell ss:StyleID="infoValue">'  
    xml += '<Data ss:Type="String">'  
    xml += escape_xml(today.strftime(  
        "%A, %B %d, %Y at %I:%M %p"  
    ))  
    xml += '</Data></Cell></Row>\n'

    xml += '<Row>'  
    xml += '<Cell ss:StyleID="infoLabel">'  
    xml += '<Data ss:Type="String">Coverage:</Data>'  
    xml += '</Cell>'  
    xml += '<Cell ss:StyleID="infoValue">'  
    xml += '<Data ss:Type="String">'  
    xml += escape_xml(from_display)  
    xml += ' to '  
    xml += escape_xml(to_display)  
    xml += '</Data></Cell></Row>\n'

    xml += '<Row>'  
    xml += '<Cell ss:StyleID="infoLabel">'  
    xml += '<Data ss:Type="String">Total Approvals:'  
    xml += '</Data></Cell>'  
    xml += '<Cell ss:StyleID="infoValue">'  
    xml += '<Data ss:Type="Number">'  
    xml += str(len(approvals))  
    xml += '</Data></Cell></Row>\n'

    xml += '<Row>'  
    xml += '<Cell ss:StyleID="infoLabel">'  
    xml += '<Data ss:Type="String">Auto-Updated:'  
    xml += '</Data></Cell>'  
    xml += '<Cell ss:StyleID="infoValue">'  
    xml += '<Data ss:Type="String">'  
    xml += 'Daily at 9:00 AM EST'  
    xml += '</Data></Cell></Row>\n'

    xml += '<Row><Cell><Data ss:Type="String">'  
    xml += '</Data></Cell></Row>\n'

    # By Type  
    xml += '<Row><Cell ss:StyleID="section" '  
    xml += 'ss:MergeAcross="1">'  
    xml += '<Data ss:Type="String">'  
    xml += 'Approvals by Submission Type'  
    xml += '</Data></Cell></Row>\n'

    xml += '<Row>'  
    xml += '<Cell ss:StyleID="header">'  
    xml += '<Data ss:Type="String">Type</Data></Cell>'  
    xml += '<Cell ss:StyleID="header">'  
    xml += '<Data ss:Type="String">Count</Data></Cell>'  
    xml += '</Row>\n'

    for t, c in sorted(  
        type_counts.items(),  
        key=lambda x: x[1],  
        reverse=True  
    ):  
        xml += '<Row>'  
        xml += '<Cell ss:StyleID="data">'  
        xml += '<Data ss:Type="String">'  
        xml += escape_xml(t) + '</Data></Cell>'  
        xml += '<Cell ss:StyleID="countNum">'  
        xml += '<Data ss:Type="Number">'  
        xml += str(c) + '</Data></Cell>'  
        xml += '</Row>\n'

    xml += '<Row><Cell><Data ss:Type="String">'  
    xml += '</Data></Cell></Row>\n'

    # By Specialty  
    xml += '<Row><Cell ss:StyleID="section" '  
    xml += 'ss:MergeAcross="1">'  
    xml += '<Data ss:Type="String">'  
    xml += 'Approvals by Specialty'  
    xml += '</Data></Cell></Row>\n'

    xml += '<Row>'  
    xml += '<Cell ss:StyleID="header">'  
    xml += '<Data ss:Type="String">Specialty'  
    xml += '</Data></Cell>'  
    xml += '<Cell ss:StyleID="header">'  
    xml += '<Data ss:Type="String">Count</Data></Cell>'  
    xml += '</Row>\n'

    for sp in spec_sorted:  
        xml += '<Row>'  
        xml += '<Cell ss:StyleID="data">'  
        xml += '<Data ss:Type="String">'  
        xml += escape_xml(sp) + '</Data></Cell>'  
        xml += '<Cell ss:StyleID="countNum">'  
        xml += '<Data ss:Type="Number">'  
        xml += str(spec_counts[sp])  
        xml += '</Data></Cell></Row>\n'

    xml += '<Row><Cell><Data ss:Type="String">'  
    xml += '</Data></Cell></Row>\n'

    # Top Sponsors  
    xml += '<Row><Cell ss:StyleID="section" '  
    xml += 'ss:MergeAcross="1">'  
    xml += '<Data ss:Type="String">'  
    xml += 'Top 15 Sponsors'  
    xml += '</Data></Cell></Row>\n'

    xml += '<Row>'  
    xml += '<Cell ss:StyleID="header">'  
    xml += '<Data ss:Type="String">Sponsor'  
    xml += '</Data></Cell>'  
    xml += '<Cell ss:StyleID="header">'  
    xml += '<Data ss:Type="String">Count</Data></Cell>'  
    xml += '</Row>\n'

    for sn in sponsor_sorted[:15]:  
        xml += '<Row>'  
        xml += '<Cell ss:StyleID="data">'  
        xml += '<Data ss:Type="String">'  
        xml += escape_xml(sn) + '</Data></Cell>'  
        xml += '<Cell ss:StyleID="countNum">'  
        xml += '<Data ss:Type="Number">'  
        xml += str(sponsor_counts[sn])  
        xml += '</Data></Cell></Row>\n'

    xml += '</Table>\n</Worksheet>\n'

    # SHEET 2: ALL APPROVALS  
    xml += '<Worksheet ss:Name="All Approvals">\n'  
    xml += '<Table ss:DefaultRowHeight="22">\n'  
    xml += '<Column ss:Width="30"/>\n'  
    xml += '<Column ss:Width="150"/>\n'  
    xml += '<Column ss:Width="180"/>\n'  
    xml += '<Column ss:Width="130"/>\n'  
    xml += '<Column ss:Width="90"/>\n'  
    xml += '<Column ss:Width="140"/>\n'  
    xml += '<Column ss:Width="170"/>\n'  
    xml += '<Column ss:Width="110"/>\n'  
    xml += '<Column ss:Width="120"/>\n'  
    xml += '<Column ss:Width="80"/>\n'  
    xml += '<Column ss:Width="250"/>\n'  
    xml += '<Column ss:Width="400"/>\n'

    xml += '<Row ss:Height="35">'  
    xml += '<Cell ss:StyleID="title" '  
    xml += 'ss:MergeAcross="11">'  
    xml += '<Data ss:Type="String">'  
    xml += 'FDA Master Report - All Approvals ('  
    xml += escape_xml(from_display) + ' to '  
    xml += escape_xml(to_display) + ')'  
    xml += '</Data></Cell></Row>\n'

    headers = [  
        "#", "Drug Name", "Generic Name",  
        "Specialty", "Approval Date",  
        "Submission Type", "Sponsor",  
        "Application #", "Dosage Form",  
        "Route", "Active Ingredients",  
        "Indication"  
    ]

    xml += '<Row ss:Height="30">'  
    for h in headers:  
        xml += '<Cell ss:StyleID="header">'  
        xml += '<Data ss:Type="String">'  
        xml += escape_xml(h) + '</Data></Cell>'  
    xml += '</Row>\n'

    for idx, a in enumerate(approvals):  
        is_alt = idx % 2 == 1  
        rs = "dataAlt" if is_alt else "data"  
        ns = "drugNameAlt" if is_alt else "drugName"

        xml += '<Row>'  
        xml += '<Cell ss:StyleID="' + rs + '">'  
        xml += '<Data ss:Type="Number">'  
        xml += str(idx + 1) + '</Data></Cell>'  
        xml += '<Cell ss:StyleID="' + ns + '">'  
        xml += '<Data ss:Type="String">'  
        xml += escape_xml(a["drug_name"])  
        xml += '</Data></Cell>'

        for field in [  
            "generic_name", "specialty",  
            "approval_date", "submission_type",  
            "sponsor", "application_number",  
            "dosage_form", "route",  
            "active_ingredients", "indication"  
        ]:  
            xml += '<Cell ss:StyleID="' + rs + '">'  
            xml += '<Data ss:Type="String">'  
            xml += escape_xml(a[field])  
            xml += '</Data></Cell>'

        xml += '</Row>\n'

    xml += '</Table>\n</Worksheet>\n'

    # SHEET 3: BY SPECIALTY  
    xml += '<Worksheet ss:Name="By Specialty">\n'  
    xml += '<Table ss:DefaultRowHeight="22">\n'  
    xml += '<Column ss:Width="150"/>\n'  
    xml += '<Column ss:Width="180"/>\n'  
    xml += '<Column ss:Width="90"/>\n'  
    xml += '<Column ss:Width="140"/>\n'  
    xml += '<Column ss:Width="170"/>\n'  
    xml += '<Column ss:Width="400"/>\n'

    xml += '<Row ss:Height="35">'  
    xml += '<Cell ss:StyleID="title" '  
    xml += 'ss:MergeAcross="5">'  
    xml += '<Data ss:Type="String">'  
    xml += 'Approvals Grouped by Specialty'  
    xml += '</Data></Cell></Row>\n'

    for sp in spec_sorted:  
        xml += '<Row ss:Height="28">'  
        xml += '<Cell ss:StyleID="specGroup" '  
        xml += 'ss:MergeAcross="5">'  
        xml += '<Data ss:Type="String">'  
        xml += escape_xml(sp) + ' ('  
        xml += str(spec_counts[sp]) + ')'  
        xml += '</Data></Cell></Row>\n'

        xml += '<Row>'  
        for sh in [  
            "Drug Name", "Generic Name",  
            "Approval Date", "Submission Type",  
            "Sponsor", "Indication"  
        ]:  
            xml += '<Cell ss:StyleID="header">'  
            xml += '<Data ss:Type="String">'  
            xml += escape_xml(sh) + '</Data></Cell>'  
        xml += '</Row>\n'

        row_count = 0  
        for a in approvals:  
            if a["specialty"] == sp:  
                is_alt = row_count % 2 == 1  
                rs = "dataAlt" if is_alt else "data"  
                ns = ("drugNameAlt" if is_alt  
                      else "drugName")

                xml += '<Row>'  
                xml += '<Cell ss:StyleID="' + ns + '">'  
                xml += '<Data ss:Type="String">'  
                xml += escape_xml(a["drug_name"])  
                xml += '</Data></Cell>'

                for f in [  
                    "generic_name", "approval_date",  
                    "submission_type", "sponsor",  
                    "indication"  
                ]:  
                    xml += '<Cell ss:StyleID="'  
                    xml += rs + '">'  
                    xml += '<Data ss:Type="String">'  
                    xml += escape_xml(a[f])  
                    xml += '</Data></Cell>'

                xml += '</Row>\n'  
                row_count += 1

        xml += '<Row><Cell>'  
        xml += '<Data ss:Type="String"></Data>'  
        xml += '</Cell></Row>\n'

    xml += '</Table>\n</Worksheet>\n'  
    xml += '</Workbook>'

    # Save to docs folder for GitHub Pages  
    os.makedirs("docs", exist_ok=True)

    filepath = "docs/FDA_Master_Report.xls"  
    with open(filepath, "w", encoding="utf-8") as f:  
        f.write(xml)

    print()  
    print("Master report saved: " + filepath)  
    print("Total approvals: " + str(len(approvals)))

    # Also save a small JSON metadata file  
    meta = {  
        "last_updated": today.strftime(  
            "%Y-%m-%d %H:%M:%S"  
        ),  
        "total_approvals": len(approvals),  
        "date_from": from_display,  
        "date_to": to_display,  
        "specialty_counts": spec_counts,  
        "type_counts": type_counts,  
    }

    meta_path = "docs/master_report_meta.json"  
    with open(meta_path, "w") as f:  
        json.dump(meta, f, indent=2)

    print("Metadata saved: " + meta_path)

        # Create index.html for GitHub Pages  
    index_lines = []  
    index_lines.append("<!DOCTYPE html>")  
    index_lines.append("<html><head>")  
    index_lines.append("<title>FDA Master Report</title>")  
    index_lines.append("<style>")  
    index_lines.append("body { font-family: Arial; ")  
    index_lines.append("max-width: 600px; ")  
    index_lines.append("margin: 50px auto; ")  
    index_lines.append("text-align: center; }")  
    index_lines.append("h1 { color: #0078D4; }")  
    index_lines.append(".btn { display: inline-block; ")  
    index_lines.append("padding: 15px 40px; ")  
    index_lines.append("background: #0078D4; ")  
    index_lines.append("color: white; ")  
    index_lines.append("text-decoration: none; ")  
    index_lines.append("border-radius: 8px; ")  
    index_lines.append("font-size: 18px; ")  
    index_lines.append("margin: 20px; }")  
    index_lines.append(".btn:hover { background: #006abc; }")  
    index_lines.append(".info { color: #666; ")  
    index_lines.append("font-size: 14px; }")  
    index_lines.append("</style>")  
    index_lines.append("</head><body>")  
    index_lines.append("<h1>FDA Drug Approval ")  
    index_lines.append("Master Report</h1>")  
    index_lines.append("<p>Northwell Health - ")  
    index_lines.append("Business Operations</p>")  
    index_lines.append('<a class="btn" ')  
    index_lines.append('href="FDA_Master_Report.xls" ')  
    index_lines.append('download>Download ')  
    index_lines.append("Master Report</a>")  
    index_lines.append('<p class="info">')  
    index_lines.append("Last updated: ")  
    index_lines.append(today.strftime("%B %d, %Y"))  
    index_lines.append("<br>Auto-updates daily ")  
    index_lines.append("at 9:00 AM EST</p>")  
    index_lines.append("</body></html>")

    index_html = "\n".join(index_lines)

    with open("docs/index.html", "w") as f:  
        f.write(index_html)  

    print("GitHub Pages index saved: docs/index.html")  
    print()  
    print("DONE!")


if __name__ == "__main__":  
    main()  
