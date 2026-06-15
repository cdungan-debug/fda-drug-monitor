import requests  
import json  
import smtplib  
from email.mime.text import MIMEText  
from email.mime.multipart import MIMEMultipart  
from datetime import datetime, timedelta  
import os


def get_date_range(days_back=1):  
    """Get date range for FDA API query."""  
    today = datetime.now()  
    past = today - timedelta(days=days_back)  
    return past.strftime("%Y%m%d"), today.strftime("%Y%m%d")


def fetch_drug_indication(application_number):  
    """Fetch drug indication/purpose from the FDA drug label API."""  
    try:  
        # Try searching by application number  
        app_num = application_number.replace("NDA", "").replace(  
            "ANDA", ""  
        ).replace("BLA", "")

        url = (  
            f"https://api.fda.gov/drug/label.json?"  
            f"search=openfda.application_number:\"{application_number}\""  
            f"&limit=1"  
        )

        response = requests.get(url, timeout=10)

        if response.status_code == 200:  
            data = response.json()  
            results = data.get("results", [])

            if results:  
                label = results[0]

                # Try to get indications  
                indications = label.get(  
                    "indications_and_usage", [""]  
                )  
                if indications and indications[0]:  
                    # Truncate to first 500 chars for readability  
                    indication_text = indications[0][:500]  
                    if len(indications[0]) > 500:  
                        indication_text += "..."  
                    return indication_text

                # Fallback: try purpose field  
                purpose = label.get("purpose", [""])  
                if purpose and purpose[0]:  
                    return purpose[0][:500]

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
            print("No new drug approvals found for this date range.")  
            return []

        response.raise_for_status()  
        data = response.json()  
        results = data.get("results", [])

        print(f"Found {len(results)} drug record(s) from the FDA API.")  
        print()

        approvals = []  
        seen_drugs = set()  # Track unique drugs to avoid duplicates

        for drug in results:  
            submissions = drug.get("submissions", [])  
            products = drug.get("products", [])  
            openfda = drug.get("openfda", {})  
            application_number = drug.get("application_number", "Unknown")

            # Find ONLY submissions within our date range  
            for sub in submissions:  
                sub_date = sub.get("submission_status_date", "")  
                sub_status = sub.get("submission_status", "")

                # Check if this submission date is within our range  
                if not sub_date:  
                    continue

                try:  
                    sub_date_int = int(sub_date)  
                    date_from_int = int(date_from)  
                    date_to_int = int(date_to)

                    if not (date_from_int <= sub_date_int <= date_to_int):  
                        continue  
                except (ValueError, TypeError):  
                    continue

                # Only include actual approvals  
                if sub_status != "AP":  
                    continue

                # Create a unique key to avoid duplicates  
                unique_key = f"{application_number}_{sub_date}"  
                if unique_key in seen_drugs:  
                    continue  
                seen_drugs.add(unique_key)

                # Get drug info from products  
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

                # Get generic name  
                generic_name = "Unknown"  
                generic_names = openfda.get("generic_name", [])  
                if generic_names:  
                    generic_name = generic_names[0]

                # Get submission type description  
                sub_type = sub.get("submission_type", "Unknown")  
                sub_type_desc = {  
                    "ORIG": "Original New Drug Application",  
                    "SUPPL": "Supplemental Application",  
                    "ABBR": "Abbreviated New Drug Application",  
                }.get(sub_type, sub_type)

                approval = {  
                    "drug_name": drug_name,  
                    "generic_name": generic_name,  
                    "approval_date": sub_date,  
                    "application_number": application_number,  
                    "submission_type": sub_type,  
                    "submission_type_description": sub_type_desc,  
                    "submission_status": sub_status,  
                    "sponsor": drug.get("sponsor_name", "Unknown"),  
                    "dosage_form": dosage_form,  
                    "route": route,  
                    "active_ingredients": active_ingredients,  
                    "indication": "",  # Will be filled below  
                }

                approvals.append(approval)

        # Now fetch indications for each unique drug  
        print(f"Found {len(approvals)} new approval(s) in date range.")  
        print("Fetching drug indications from FDA label API...")  
        print()

        fetched_indications = {}  
        for approval in approvals:  
            app_num = approval["application_number"]  
            if app_num not in fetched_indications:  
                print(f"  Looking up indication for {app_num} "  
                      f"({approval['drug_name']})...")  
                indication = fetch_drug_indication(app_num)  
                fetched_indications[app_num] = indication

            approval["indication"] = fetched_indications[app_num]

        return approvals

    except Exception as e:  
        print(f"Error fetching FDA data: {e}")  
        return []


def build_email_html(approvals, date_from, date_to):  
    """Build a formatted HTML email report."""  
    # Format dates for display  
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

    html = f"""  
    <html>  
    <head>  
        <style>  
            body {{  
                font-family: Arial, sans-serif;  
                color: #333;  
                max-width: 900px;  
                margin: 0 auto;  
                padding: 0;  
            }}  
            .header {{  
                background-color: #0078d4;  
                color: white;  
                padding: 25px 30px;  
                border-radius: 8px 8px 0 0;  
            }}  
            .header h1 {{  
                margin: 0;  
                font-size: 22px;  
            }}  
            .header p {{  
                margin: 5px 0 0 0;  
                opacity: 0.9;  
                font-size: 14px;  
            }}  
            .summary {{  
                background-color: #f0f6ff;  
                padding: 15px 30px;  
                border-bottom: 2px solid #0078d4;  
                font-size: 16px;  
            }}  
            .drug-card {{  
                border: 1px solid #e0e0e0;  
                border-left: 4px solid #0078d4;  
                border-radius: 4px;  
                margin: 20px 30px;  
                padding: 20px 25px;  
                background-color: #fafafa;  
            }}  
            .drug-card h3 {{  
                color: #0078d4;  
                margin: 0 0 15px 0;  
                font-size: 18px;  
                border-bottom: 1px solid #e0e0e0;  
                padding-bottom: 10px;  
            }}  
            .drug-card table {{  
                width: 100%;  
                border-collapse: collapse;  
            }}  
            .drug-card td {{  
                padding: 5px 0;  
                vertical-align: top;  
                font-size: 14px;  
            }}  
            .drug-card td:first-child {{  
                font-weight: bold;  
                width: 180px;  
                color: #555;  
            }}  
            .indication-box {{  
                background-color: #fff3cd;  
                border: 1px solid #ffc107;  
                border-radius: 4px;  
                padding: 12px 15px;  
                margin-top: 12px;  
                font-size: 13px;  
                line-height: 1.5;  
            }}  
            .indication-box strong {{  
                color: #856404;  
            }}  
            .no-results {{  
                padding: 40px 30px;  
                text-align: center;  
                color: #666;  
                font-size: 16px;  
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
            <p>Date Range: {from_display} to {to_display}</p>  
        </div>  
        <div class="summary">  
            <strong>{len(approvals)}</strong> new drug approval(s) found  
        </div>  
    """

    if not approvals:  
        html += """  
        <div class="no-results">  
            <p>No new drug approvals were found for this  
            date range.</p>  
            <p>This is normal - not every day has new  
            FDA approvals.</p>  
        </div>  
        """  
    else:  
        for i, a in enumerate(approvals, 1):  
            ingredients_str = ", ".join(  
                [f"{ai['name']} ({ai['strength']})"  
                 for ai in a.get("active_ingredients", [])]  
            ) or "N/A"

            # Format approval date  
            try:  
                approval_date_display = datetime.strptime(  
                    a['approval_date'], "%Y%m%d"  
                ).strftime("%B %d, %Y")  
            except (ValueError, TypeError):  
                approval_date_display = a['approval_date']

            indication_html = ""  
            if (a.get('indication')  
                    and a['indication'] != "Indication not available"):  
                indication_html = f"""  
                <div class="indication-box">  
                    <strong>Indication / Usage:</strong><br>  
                    {a['indication']}  
                </div>  
                """  
            else:  
                indication_html = """  
                <div class="indication-box">  
                    <strong>Indication / Usage:</strong><br>  
                    <em>Not available from FDA label database.  
                    May need manual lookup.</em>  
                </div>  
                """

            html += f"""  
            <div class="drug-card">  
                <h3>#{i} - {a['drug_name']}</h3>  
                <table>  
                    <tr>  
                        <td>Generic Name:</td>  
                        <td>{a['generic_name']}</td>  
                    </tr>  
                    <tr>  
                        <td>Approval Date:</td>  
                        <td>{approval_date_display}</td>  
                    </tr>  
                    <tr>  
                        <td>Application Number:</td>  
                        <td>{a['application_number']}</td>  
                    </tr>  
                    <tr>  
                        <td>Submission Type:</td>  
                        <td>{a['submission_type_description']}</td>  
                    </tr>  
                    <tr>  
                        <td>Sponsor:</td>  
                        <td>{a['sponsor']}</td>  
                    </tr>  
                    <tr>  
                        <td>Dosage Form:</td>  
                        <td>{a['dosage_form']}</td>  
                    </tr>  
                    <tr>  
                        <td>Route:</td>  
                        <td>{a['route']}</td>  
                    </tr>  
                    <tr>  
                        <td>Active Ingredients:</td>  
                        <td>{ingredients_str}</td>  
                    </tr>  
                </table>  
                {indication_html}  
            </div>  
            """

    html += f"""  
        <div class="footer">  
            <p>This report was generated automatically by the  
            FDA Drug Approval Monitor.</p>  
            <p>Data source: openFDA API (https://api.fda.gov)</p>  
            <p>Generated: {datetime.now().strftime(  
                '%B %d, %Y at %I:%M %p UTC'  
            )}</p>  
        </div>  
    </body>  
    </html>  
    """

    return html


def send_email(subject, html_body, to_email, from_email, password):  
    """Send an HTML email via SMTP."""  
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
        print(f"Email sent successfully to {to_email}")  
        return True  
    except Exception as e:  
        print(f"Failed to send email: {e}")  
        return False


def main():  
    """Main function - fetch FDA data, build report, send email."""  
    print("=" * 60)  
    print("FDA Daily Drug Approval Scraper")  
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")  
    print("=" * 60)  
    print()

    # Fetch approvals from the last 7 days  
    days_back = 7  
    approvals = fetch_fda_approvals(days_back)

    date_from, date_to = get_date_range(days_back)

    # Print results to console  
    print()  
    print(f"FINAL RESULTS: {len(approvals)} new approval(s)")  
    print("=" * 60)  
    for i, a in enumerate(approvals, 1):  
        print(f"\n#{i}")  
        print(f"  Drug Name:      {a['drug_name']}")  
        print(f"  Generic Name:   {a['generic_name']}")  
        print(f"  Approval Date:  {a['approval_date']}")  
        print(f"  Application #:  {a['application_number']}")  
        print(f"  Type:           {a['submission_type_description']}")  
        print(f"  Sponsor:        {a['sponsor']}")  
        print(f"  Dosage Form:    {a['dosage_form']}")  
        print(f"  Route:          {a['route']}")  
        indication_preview = a.get('indication', 'N/A')[:100]  
        print(f"  Indication:     {indication_preview}")

    # Save results to JSON file  
    results_data = {  
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  
        "date_range": {"from": date_from, "to": date_to},  
        "total_approvals": len(approvals),  
        "approvals": approvals,  
    }

    with open("fda_results.json", "w") as f:  
        json.dump(results_data, f, indent=2)  
    print("\nResults saved to fda_results.json")

    # Build HTML email  
    html_body = build_email_html(approvals, date_from, date_to)

    # Save HTML report  
    with open("fda_report.html", "w") as f:  
        f.write(html_body)  
    print("HTML report saved to fda_report.html")

    # Send email if credentials are configured  
    to_email = os.environ.get("EMAIL_TO")  
    from_email = os.environ.get("EMAIL_FROM")  
    email_password = os.environ.get("EMAIL_PASSWORD")

    if to_email and from_email and email_password:  
        subject = (  
            f"FDA Drug Approval Report - "  
            f"{datetime.now().strftime('%B %d, %Y')} - "  
            f"{len(approvals)} new approval(s)"  
        )  
        send_email(  
            subject, html_body, to_email, from_email, email_password  
        )  
    else:  
        print("\nEmail credentials not configured.")  
        print("Set EMAIL_TO, EMAIL_FROM, and EMAIL_PASSWORD")  
        print("as repository secrets to enable email delivery.")


if __name__ == "__main__":  
    main()  
