import urllib.request  
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
    text = (str(indication) + " " + str(drug_name)).lower()  
    for keyword, specialty in SPECIALTY_MAP.items():  
        if keyword in text:  
            return specialty  
    return "General / Review Needed"


def escape_xml(s):  
    if not s:  
        return ""  
    s = str(s)  
    s = s.replace(chr(38), chr(38) + "amp;")  
    s = s.replace(chr(60), chr(38) + "lt;")  
    s = s.replace(chr(62), chr(38) + "gt;")  
    s = s.replace(chr(34), chr(38) + "quot;")  
    s = s.replace(chr(39), chr(38) + "apos;")  
    return s


def fetch_url(url):  
    try:  
        req = urllib.request.Request(url)  
        req.add_header("User-Agent", "FDA-Monitor/1.0")  
        resp = urllib.request.urlopen(req, timeout=30)  
        return json.loads(resp.read().decode("utf-8"))  
    except urllib.error.HTTPError as e:  
        if e.code == 404:  
            return None  
        print("HTTP Error " + str(e.code))  
        return None  
    except Exception as e:  
        print("Error: " + str(e))  
        return None


def fetch_indication(app_number):  
    url = (  
        "https://api.fda.gov/drug/label.json?"  
        "search=openfda.application_number:%22"  
        + str(app_number)  
        + "%22&limit=1"  
    )  
    try:  
        req = urllib.request.Request(url)  
        req.add_header("User-Agent", "FDA-Monitor/1.0")  
        resp = urllib.request.urlopen(req, timeout=15)  
        data = json.loads(resp.read().decode("utf-8"))  
        results = data.get("results", [])  
        if results:  
            label = results[0]  
            ind = label.get("indications_and_usage", [""])  
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
    print("=" * 60)

    today = datetime.now()  
    two_years_ago = today - timedelta(days=730)  
    date_from = two_years_ago.strftime("%Y%m%d")  
    date_to = today.strftime("%Y%m%d")

    print("Date range: " + date_from + " to " + date_to)

    all_results = []  
    skip = 0  
    limit = 100

    for page in range(50):  
        print("Fetching page " + str(page + 1) + "...")  
        url = (  
            "https://api.fda.gov/drug/drugsfda.json?"  
            "search=submissions.submission_status_date:"  
            "[" + date_from + "+TO+" + date_to + "]"  
            "&limit=" + str(limit)  
            + "&skip=" + str(skip)  
        )  
        data = fetch_url(url)

        if not data:  
            break

        results = data.get("results", [])  
        if not results:  
            break

        all_results.extend(results)  
        total = data.get("meta", {}).get("results", {}).get("total", 0)  
        print("  Got " + str(len(results)) + " of " + str(total))

        skip += limit  
        if skip >= total:  
            break  
        time.sleep(0.3)

    print("Total raw results: " + str(len(all_results)))

    approvals = []  
    seen = {}

    for drug in all_results:  
        submissions = drug.get("submissions", [])  
        products = drug.get("products", [])  
        openfda = drug.get("openfda", {})  
        app_num = drug.get("application_number", "Unknown")

        for sub in submissions:  
            sub_date = sub.get("submission_status_date", "")  
            sub_status = sub.get("submission_status", "")

            if not sub_date or sub_status != "AP":  
                continue

            try:  
                sub_int = int(sub_date)  
                if sub_int < int(date_from) or sub_int > int(date_to):  
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
                drug_name = products[0].get("brand_name", "Unknown")  
                dosage_form = products[0].get("dosage_form", "Unknown")  
                route = products[0].get("route", "Unknown")  
                ais = products[0].get("active_ingredients", [])  
                if ais:  
                    parts = []  
                    for ai in ais:  
                        name = ai.get("name", "Unknown")  
                        strength = ai.get("strength", "")  
                        if strength:  
                            parts.append(name + " (" + strength + ")")  
                        else:  
                            parts.append(name)  
                    ingredients = "; ".join(parts)

            generic = "Unknown"  
            g_names = openfda.get("generic_name", [])  
            if g_names:  
                generic = g_names[0]

            sub_type = sub.get("submission_type", "Unknown")  
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
                    sub_date[4:6] + "/"  
                    + sub_date[6:8] + "/"  
                    + sub_date[0:4]  
                )

            approvals.append({  
                "drug_name": drug_name,  
                "generic_name": generic,  
                "approval_date": date_display,  
                "approval_date_raw": sub_date,  
                "application_number": app_num,  
                "submission_type": type_desc,  
                "sponsor": drug.get("sponsor_name", "Unknown"),  
                "dosage_form": dosage_form,  
                "route": route,  
                "active_ingredients": ingredients,  
                "indication": "",  
                "specialty": "",  
            })

    print("Parsed approvals: " + str(len(approvals)))

    unique_apps = list(set(a["application_number"] for a in approvals))  
    print("Fetching indications for " + str(len(unique_apps)) + " apps...")

    ind_map = {}  
    for i, app_num in enumerate(unique_apps):  
        if (i + 1) % 50 == 0:  
            print("  " + str(i + 1) + "/" + str(len(unique_apps)))  
        ind_map[app_num] = fetch_indication(app_num)  
        time.sleep(0.15)

    for a in approvals:  
        ind = ind_map.get(a["application_number"], "N/A")  
        a["indication"] = ind  
        a["specialty"] = map_specialty(ind, a["drug_name"])

    approvals.sort(key=lambda x: x["approval_date_raw"], reverse=True)

    print("Building Excel report...")

    type_counts = {}  
    spec_counts = {}  
    sponsor_counts = {}

    for a in approvals:  
        st = a["submission_type"]  
        type_counts[st] = type_counts.get(st, 0) + 1  
        sp = a["specialty"]  
        spec_counts[sp] = spec_counts.get(sp, 0) + 1  
        sn = a["sponsor"]  
        sponsor_counts[sn] = sponsor_counts.get(sn, 0) + 1

    spec_sorted = sorted(spec_counts.keys(), key=lambda x: spec_counts[x], reverse=True)  
    sponsor_sorted = sorted(sponsor_counts.keys(), key=lambda x: sponsor_counts[x], reverse=True)

    from_display = two_years_ago.strftime("%B %d, %Y")  
    to_display = today.strftime("%B %d, %Y")  
    updated_display = today.strftime("%A, %B %d, %Y at %I:%M %p")

    x = []  
    Q = chr(34)

    x.append('<?xml version=' + Q + '1.0' + Q + ' encoding=' + Q + 'UTF-8' + Q + '?>')  
    x.append('<?mso-application progid=' + Q + 'Excel.Sheet' + Q + '?>')  
    x.append('<Workbook xmlns=' + Q + 'urn:schemas-microsoft-com:office:spreadsheet' + Q)  
    x.append(' xmlns:ss=' + Q + 'urn:schemas-microsoft-com:office:spreadsheet' + Q + '>')

    # Styles  
    x.append('<Styles>')

    x.append('<Style ss:ID=' + Q + 'Default' + Q + ' ss:Name=' + Q + 'Normal' + Q + '>')  
    x.append('<Font ss:FontName=' + Q + 'Calibri' + Q + ' ss:Size=' + Q + '11' + Q + '/>')  
    x.append('<Alignment ss:Vertical=' + Q + 'Center' + Q + ' ss:WrapText=' + Q + '1' + Q + '/>')  
    x.append('</Style>')

    def add_style(sid, font_size, bold, fg_color, bg_color, halign, wrap, border_color):  
        line = '<Style ss:ID=' + Q + sid + Q + '>'  
        line += '<Font ss:FontName=' + Q + 'Calibri' + Q  
        line += ' ss:Size=' + Q + str(font_size) + Q  
        if bold:  
            line += ' ss:Bold=' + Q + '1' + Q  
        if fg_color:  
            line += ' ss:Color=' + Q + fg_color + Q  
        line += '/>'  
        if bg_color:  
            line += '<Interior ss:Color=' + Q + bg_color + Q  
            line += ' ss:Pattern=' + Q + 'Solid' + Q + '/>'  
        align = '<Alignment ss:Vertical=' + Q + 'Center' + Q  
        if halign:  
            align += ' ss:Horizontal=' + Q + halign + Q  
        if wrap:  
            align += ' ss:WrapText=' + Q + '1' + Q  
        align += '/>'  
        line += align  
        if border_color:  
            line += '<Borders>'  
            line += '<Border ss:Position=' + Q + 'Bottom' + Q  
            line += ' ss:LineStyle=' + Q + 'Continuous' + Q  
            line += ' ss:Weight=' + Q + '1' + Q  
            line += ' ss:Color=' + Q + border_color + Q + '/>'  
            line += '</Borders>'  
        line += '</Style>'  
        x.append(line)

    add_style("title", 18, True, "#FFFFFF", "#0078D4", None, False, None)  
    add_style("subtitle", 12, False, "#FFFFFF", "#0078D4", None, False, None)  
    add_style("section", 13, True, "#0078D4", None, None, False, "#0078D4")  
    add_style("header", 11, True, "#FFFFFF", "#0078D4", None, True, "#005A9E")  
    add_style("data", 11, False, None, None, None, True, "#E0E0E0")  
    add_style("dataAlt", 11, False, None, "#F2F7FC", None, True, "#E0E0E0")  
    add_style("drugName", 11, True, "#333333", None, None, False, "#E0E0E0")  
    add_style("drugNameAlt", 11, True, "#333333", "#F2F7FC", None, False, "#E0E0E0")  
    add_style("infoLabel", 11, True, "#555555", None, None, False, None)  
    add_style("infoValue", 11, False, "#333333", None, None, False, None)  
    add_style("countNum", 11, False, None, None, "Center", False, "#E0E0E0")  
    add_style("specGroup", 12, True, "#FFFFFF", "#28A745", None, False, None)

    x.append('</Styles>')

    def cell(style, data_type, value):  
        return ('<Cell ss:StyleID=' + Q + style + Q + '>'  
                + '<Data ss:Type=' + Q + data_type + Q + '>'  
                + escape_xml(str(value))  
                + '</Data></Cell>')

    def merged_cell(style, cols, value):  
        return ('<Cell ss:StyleID=' + Q + style + Q  
                + ' ss:MergeAcross=' + Q + str(cols) + Q + '>'  
                + '<Data ss:Type=' + Q + 'String' + Q + '>'  
                + escape_xml(str(value))  
                + '</Data></Cell>')

    # SHEET 1: SUMMARY  
    x.append('<Worksheet ss:Name=' + Q + 'Summary' + Q + '>')  
    x.append('<Table ss:DefaultRowHeight=' + Q + '20' + Q + '>')  
    x.append('<Column ss:Width=' + Q + '200' + Q + '/>')  
    x.append('<Column ss:Width=' + Q + '300' + Q + '/>')

    x.append('<Row ss:Height=' + Q + '40' + Q + '>')  
    x.append(merged_cell("title", 1, "FDA Master Drug Approval Report"))  
    x.append('</Row>')

    x.append('<Row ss:Height=' + Q + '25' + Q + '>')  
    x.append(merged_cell("subtitle", 1, "Northwell Health - Business Operations"))  
    x.append('</Row>')

    x.append('<Row><Cell><Data ss:Type=' + Q + 'String' + Q + '></Data></Cell></Row>')

    info_rows = [  
        ("Last Updated:", updated_display),  
        ("Coverage:", from_display + " to " + to_display),  
        ("Total Approvals:", str(len(approvals))),  
        ("Auto-Updated:", "Daily at 9:00 AM EST"),  
    ]  
    for label, value in info_rows:  
        x.append('<Row>')  
        x.append(cell("infoLabel", "String", label))  
        x.append(cell("infoValue", "String", value))  
        x.append('</Row>')

    x.append('<Row><Cell><Data ss:Type=' + Q + 'String' + Q + '></Data></Cell></Row>')

    # By Type  
    x.append('<Row>' + merged_cell("section", 1, "Approvals by Submission Type") + '</Row>')  
    x.append('<Row>' + cell("header", "String", "Type") + cell("header", "String", "Count") + '</Row>')  
    for t in sorted(type_counts.keys(), key=lambda k: type_counts[k], reverse=True):  
        x.append('<Row>' + cell("data", "String", t) + cell("countNum", "Number", str(type_counts[t])) + '</Row>')

    x.append('<Row><Cell><Data ss:Type=' + Q + 'String' + Q + '></Data></Cell></Row>')

    # By Specialty  
    x.append('<Row>' + merged_cell("section", 1, "Approvals by Specialty") + '</Row>')  
    x.append('<Row>' + cell("header", "String", "Specialty") + cell("header", "String", "Count") + '</Row>')  
    for sp in spec_sorted:  
        x.append('<Row>' + cell("data", "String", sp) + cell("countNum", "Number", str(spec_counts[sp])) + '</Row>')

    x.append('<Row><Cell><Data ss:Type=' + Q + 'String' + Q + '></Data></Cell></Row>')

    # Top Sponsors  
    x.append('<Row>' + merged_cell("section", 1, "Top 15 Sponsors") + '</Row>')  
    x.append('<Row>' + cell("header", "String", "Sponsor") + cell("header", "String", "Count") + '</Row>')  
    for sn in sponsor_sorted[:15]:  
        x.append('<Row>' + cell("data", "String", sn) + cell("countNum", "Number", str(sponsor_counts[sn])) + '</Row>')

    x.append('</Table></Worksheet>')

    # SHEET 2: ALL APPROVALS  
    x.append('<Worksheet ss:Name=' + Q + 'All Approvals' + Q + '>')  
    x.append('<Table ss:DefaultRowHeight=' + Q + '22' + Q + '>')  
    widths = [30, 150, 180, 130, 90, 140, 170, 110, 120, 80, 250, 400]  
    for w in widths:  
        x.append('<Column ss:Width=' + Q + str(w) + Q + '/>')

    x.append('<Row ss:Height=' + Q + '35' + Q + '>')  
    x.append(merged_cell("title", 11, "FDA Master Report - All Approvals (" + from_display + " to " + to_display + ")"))  
    x.append('</Row>')

    headers = ["#", "Drug Name", "Generic Name", "Specialty", "Approval Date",  
               "Submission Type", "Sponsor", "Application #", "Dosage Form",  
               "Route", "Active Ingredients", "Indication"]  
    x.append('<Row ss:Height=' + Q + '30' + Q + '>')  
    for h in headers:  
        x.append(cell("header", "String", h))  
    x.append('</Row>')

    for idx, a in enumerate(approvals):  
        is_alt = idx % 2 == 1  
        rs = "dataAlt" if is_alt else "data"  
        ns = "drugNameAlt" if is_alt else "drugName"  
        x.append('<Row>')  
        x.append(cell(rs, "Number", str(idx + 1)))  
        x.append(cell(ns, "String", a["drug_name"]))  
        for f in ["generic_name", "specialty", "approval_date", "submission_type",  
                   "sponsor", "application_number", "dosage_form", "route",  
                   "active_ingredients", "indication"]:  
            x.append(cell(rs, "String", a[f]))  
        x.append('</Row>')

    x.append('</Table></Worksheet>')

    # SHEET 3: BY SPECIALTY  
    x.append('<Worksheet ss:Name=' + Q + 'By Specialty' + Q + '>')  
    x.append('<Table ss:DefaultRowHeight=' + Q + '22' + Q + '>')  
    spec_widths = [150, 180, 90, 140, 170, 400]  
    for w in spec_widths:  
        x.append('<Column ss:Width=' + Q + str(w) + Q + '/>')

    x.append('<Row ss:Height=' + Q + '35' + Q + '>')  
    x.append(merged_cell("title", 5, "Approvals Grouped by Specialty"))  
    x.append('</Row>')

    for sp in spec_sorted:  
        x.append('<Row ss:Height=' + Q + '28' + Q + '>')  
        x.append(merged_cell("specGroup", 5, sp + " (" + str(spec_counts[sp]) + ")"))  
        x.append('</Row>')

        x.append('<Row>')  
        for sh in ["Drug Name", "Generic Name", "Approval Date", "Submission Type", "Sponsor", "Indication"]:  
            x.append(cell("header", "String", sh))  
        x.append('</Row>')

        row_count = 0  
        for a in approvals:  
            if a["specialty"] == sp:  
                is_alt = row_count % 2 == 1  
                rs = "dataAlt" if is_alt else "data"  
                ns = "drugNameAlt" if is_alt else "drugName"  
                x.append('<Row>')  
                x.append(cell(ns, "String", a["drug_name"]))  
                for f in ["generic_name", "approval_date", "submission_type", "sponsor", "indication"]:  
                    x.append(cell(rs, "String", a[f]))  
                x.append('</Row>')  
                row_count += 1

        x.append('<Row><Cell><Data ss:Type=' + Q + 'String' + Q + '></Data></Cell></Row>')

    x.append('</Table></Worksheet>')  
    x.append('</Workbook>')

    xml_content = "\n".join(x)

    os.makedirs("docs", exist_ok=True)

    with open("docs/FDA_Master_Report.xls", "w", encoding="utf-8") as f:  
        f.write(xml_content)

    print("Master report saved: docs/FDA_Master_Report.xls")  
    print("Total approvals: " + str(len(approvals)))

    meta = {  
        "last_updated": today.strftime("%Y-%m-%d %H:%M:%S"),  
        "total_approvals": len(approvals),  
        "date_from": from_display,  
        "date_to": to_display,  
    }  
    with open("docs/master_report_meta.json", "w") as f:  
        json.dump(meta, f, indent=2)

    print("DONE!")


if __name__ == "__main__":  
    main()  
