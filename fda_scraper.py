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

        for drug in results:  
            submissions = drug.get("submissions", [])  
            products = drug.get("products", [])  
            openfda = drug.get("openfda", {})

            for sub in submissions:  
                is_approval = (  
                    sub.get("submission_type") == "ORIG"  
                    or sub.get("submission_status") == "AP"  
                )

                if is_approval:  
                    # Get drug info from products  
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

                    # Get generic name  
                    generic_name = "Unknown"  
                    generic_names = openfda.get("generic_name", [])  
                    if generic_names:  
                        generic_name = generic_names[0]

                    approval = {  
                        "drug_name": drug_name,  
                        "generic_name": generic_name,  
                        "approval_date": sub.get(  
                            "submission_status_date", "Unknown"  
                        ),  
                        "application_number": drug.get(  
                            "application_number", "Unknown"  
                        ),  
                        "submission_type": sub.get(  
                            "submission_type", "Unknown"  
                        ),  
                        "submission_status": sub.get(  
                            "submission_status", "Unknown"  
                        ),  
                        "sponsor": drug.get("sponsor_name", "Unknown"),  
                        "dosage_form": dosage_form,  
                        "route": route,  
                        "active_ingredients": active_ingredients,  
                    }

                    approvals.append(approval)

        return approvals

    except Exception as e:  
        print(f"Error fetching FDA data: {e}")  
        return []


def build_email_html(approvals, date_from, date_to):  
    """Build a formatted HTML email report."""  
    html = f"""  
    <html>  
    <head>  
        <style>  
            body {{  
                font-family: Arial, sans-serif;  
                color: #333;  
                max-width: 800px;  
                margin: 0 auto;  
            }}  
            .header {{  
                background-color: #0078d4;  
                color: white;  
                padding: 20px;  
                border-radius: 8px 8px 0 0;  
            }}  
            .header h1 {{  
                margin: 0;  
                font-size: 24px;  
            }}  
            .header p {{  
                margin: 5px 0 0 0;  
                opacity: 0.9;  
            }}  
            .summary {{  
                background-color: #f0f0f0;  
                padding: 15px 20px;  
                border-bottom: 1px solid #ddd;  
            }}  
            .drug-card {{  
                border: 1px solid #e0e0e0;  
                border-radius: 8px;  
                margin: 15px 20px;  
                padding: 20px;  
                background-color: #fafafa;  
            }}  
            .drug-card h3 {{  
                color: #0078d4;  
                margin: 0 0 10px 0;  
                font-size: 18px;  
            }}  
            .drug-card table {{  
                width: 100%;  
                border-collapse: collapse;  
            }}  
            .drug-card td {{  
                padding: 4px 0;  
                vertical-align: top;  
            }}  
            .drug-card td:first-child {{  
                font-weight: bold;  
                width: 160px;  
                color: #555;  
            }}  
            .no-results {{  
                padding: 30px 20px;  
                text-align: center;  
                color: #666;  
            }}  
            .footer {{  
                padding: 15px 20px;  
                font-size: 12px;  
                color: #999;  
                border-top: 1px solid #eee;  
            }}  
        </style>  
    </head>  
    <body>  
        <div class="header">  
            <h1>FDA Daily Drug Approval Report</h1>  
            <p>Date Range: {date_from} to {date_to}</p>  
        </div>  
        <div class="summary">  
            <strong>{len(approvals)}</strong> drug approval(s) found  
        </div>  
    """

    if not approvals:  
        html += """  
        <div class="no-results">  
            <p>No new drug approvals were found for this date range.</p>  
            <p>This is normal — not every day has new FDA approvals.</p>  
        </div>  
        """  
    else:  
        for i, a in enumerate(approvals, 1):  
            ingredients_str = ", ".join(  
                [f"{ai['name']} ({ai['strength']})"  
                 for ai in a.get("active_ingredients", [])]  
            ) or "N/A"

            html += f"""  
            <div class="drug-card">  
                <h3>#{i} — {a['drug_name']}</h3>  
                <table>  
                    <tr>  
                        <td>Generic Name:</td>  
                        <td>{a['generic_name']}</td>  
                    </tr>  
                    <tr>  
                        <td>Approval Date:</td>  
                        <td>{a['approval_date']}</td>  
                    </tr>  
                    <tr>  
                        <td>Application #:</td>  
                        <td>{a['application_number']}</td>  
                    </tr>  
                    <tr>  
                        <td>Submission Type:</td>  
                        <td>{a['submission_type']}</td>  
                    </tr>  
                    <tr>  
                        <td>Status:</td>  
                        <td>{a['submission_status']}</td>  
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
            </div>  
            """

    html += f"""  
        <div class="footer">  
            <p>This report was generated automatically by the  
            FDA Drug Approval Monitor.</p>  
            <p>Data source: openFDA API  
            (https://api.fda.gov)</p>  
            <p>Generated at: {datetime.now().strftime(  
                '%Y-%m-%d %H:%M:%S UTC'  
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
        # Using Gmail SMTP — change if using a different provider  
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
    """Main function — fetch FDA data, build report, send email."""  
    print("=" * 60)  
    print("FDA Daily Drug Approval Scraper")  
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")  
    print("=" * 60)  
    print()

    # Fetch approvals from the last 7 days  
    # (Using 7 days to ensure we catch approvals even  
    #  if the workflow misses a day)  
    days_back = 7  
    approvals = fetch_fda_approvals(days_back)

    date_from, date_to = get_date_range(days_back)

    # Print results to console  
    print(f"\nFound {len(approvals)} approval(s):")  
    print("-" * 40)  
    for i, a in enumerate(approvals, 1):  
        print(f"\n#{i}")  
        print(f"  Drug Name:     {a['drug_name']}")  
        print(f"  Generic Name:  {a['generic_name']}")  
        print(f"  Approval Date: {a['approval_date']}")  
        print(f"  Application #: {a['application_number']}")  
        print(f"  Sponsor:       {a['sponsor']}")  
        print(f"  Dosage Form:   {a['dosage_form']}")  
        print(f"  Route:         {a['route']}")

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

    # Send email if credentials are configured  
    to_email = os.environ.get("EMAIL_TO")  
    from_email = os.environ.get("EMAIL_FROM")  
    email_password = os.environ.get("EMAIL_PASSWORD")

    if to_email and from_email and email_password:  
        subject = (  
            f"FDA Drug Approval Report — "  
            f"{datetime.now().strftime('%B %d, %Y')} — "  
            f"{len(approvals)} approval(s) found"  
        )  
        send_email(subject, html_body, to_email, from_email, email_password)  
    else:  
        print("\nEmail credentials not configured.")  
        print("Set EMAIL_TO, EMAIL_FROM, and EMAIL_PASSWORD")  
        print("as repository secrets to enable email delivery.")  
        print("\nSaving HTML report to file instead...")  
        with open("fda_report.html", "w") as f:  
            f.write(html_body)  
        print("Report saved to fda_report.html")


if __name__ == "__main__":  
    main()  
