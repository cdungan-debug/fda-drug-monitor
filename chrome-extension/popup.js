document.addEventListener("DOMContentLoaded", function () {  
  var today = new Date();  
  var weekAgo = new Date();  
  weekAgo.setDate(today.getDate() - 7);

  document.getElementById("dateTo").value =  
    formatDateInput(today);  
  document.getElementById("dateFrom").value =  
    formatDateInput(weekAgo);

  document.getElementById("downloadBtn")  
    .addEventListener("click", fetchAndDownload);  
});


function formatDateInput(date) {  
  var y = date.getFullYear();  
  var m = String(date.getMonth() + 1).padStart(2, "0");  
  var d = String(date.getDate()).padStart(2, "0");  
  return y + "-" + m + "-" + d;  
}


function formatDateFDA(dateStr) {  
  return dateStr.replace(/-/g, "");  
}


function formatDateDisplay(dateStr) {  
  if (!dateStr) return "N/A";  
  var parts = dateStr.split("-");  
  if (parts.length === 3) {  
    return parts[1] + "/" + parts[2] + "/" + parts[0];  
  }  
  return dateStr;  
}


function setStatus(type, message) {  
  var el = document.getElementById("status");  
  el.className = "status " + type;  
  if (type === "loading") {  
    el.innerHTML =  
      '<span class="spinner"></span>' + message;  
  } else {  
    el.innerHTML = message;  
  }  
}


function fetchIndication(appNumber) {  
  var url =  
    "https://api.fda.gov/drug/label.json?" +  
    "search=openfda.application_number:\"" +  
    appNumber + "\"&limit=1";

  return fetch(url)  
    .then(function (response) {  
      if (!response.ok) return "N/A";  
      return response.json().then(function (data) {  
        var results = data.results || [];  
        if (results.length > 0) {  
          var label = results[0];  
          var ind = label.indications_and_usage || [""];  
          if (ind[0]) {  
            var text = ind[0];  
            if (text.length > 500) {  
              text = text.substring(0, 500) + "...";  
            }  
            return text;  
          }  
          var purp = label.purpose || [""];  
          if (purp[0]) return purp[0];  
        }  
        return "N/A";  
      });  
    })  
    .catch(function () {  
      return "N/A";  
    });  
}


function mapIndicationToSpecialty(indication, drugName) {  
  var text = (indication + " " + drugName).toLowerCase();

  var mapping = {  
    "hypertension": "Cardiology",  
    "heart failure": "Cardiology",  
    "cardiac": "Cardiology",  
    "cardiovascular": "Cardiology",  
    "angina": "Cardiology",  
    "arrhythmia": "Cardiology",  
    "atrial fibrillation": "Cardiology",  
    "anticoagulant": "Cardiology",  
    "blood pressure": "Cardiology",  
    "cancer": "Oncology",  
    "tumor": "Oncology",  
    "carcinoma": "Oncology",  
    "lymphoma": "Oncology",  
    "leukemia": "Oncology",  
    "melanoma": "Oncology / Dermatology",  
    "metastatic": "Oncology",  
    "neoplasm": "Oncology",  
    "seizure": "Neurology",  
    "epilepsy": "Neurology",  
    "neurological": "Neurology",  
    "anticonvulsant": "Neurology",  
    "multiple sclerosis": "Neurology",  
    "schizophrenia": "Psychiatry",  
    "bipolar": "Psychiatry",  
    "antipsychotic": "Psychiatry",  
    "depression": "Psychiatry",  
    "anxiety": "Psychiatry",  
    "acne": "Dermatology",  
    "dermatitis": "Dermatology",  
    "psoriasis": "Dermatology",  
    "eczema": "Dermatology",  
    "asthma": "Pulmonology",  
    "copd": "Pulmonology",  
    "pulmonary": "Pulmonology",  
    "respiratory": "Pulmonology",  
    "arthritis": "Rheumatology",  
    "rheumatoid": "Rheumatology",  
    "lupus": "Rheumatology",  
    "autoimmune": "Rheumatology",  
    "glaucoma": "Ophthalmology",  
    "ophthalmic": "Ophthalmology",  
    "retinal": "Ophthalmology",  
    "liver": "Gastroenterology",  
    "hepatic": "Gastroenterology",  
    "gastrointestinal": "Gastroenterology",  
    "nausea": "Gastroenterology",  
    "renal": "Nephrology",  
    "kidney": "Nephrology",  
    "diabetes": "Endocrinology",  
    "thyroid": "Endocrinology",  
    "osteoporosis": "Endocrinology",  
    "hormone": "Endocrinology",  
    "infection": "Infectious Disease",  
    "antibacterial": "Infectious Disease",  
    "antiviral": "Infectious Disease",  
    "antibiotic": "Infectious Disease",  
    "naloxone": "Emergency Medicine",  
    "opioid": "Emergency Medicine",  
    "contrast": "Radiology",  
    "imaging": "Radiology",  
    "pregnancy": "OB/GYN",  
    "contracepti": "OB/GYN",  
    "estradiol": "OB/GYN",  
    "menopausal": "OB/GYN",  
  };

  for (var keyword in mapping) {  
    if (text.indexOf(keyword) !== -1) {  
      return mapping[keyword];  
    }  
  }  
  return "General / Review Needed";  
}


function fetchAndDownload() {  
  var btn = document.getElementById("downloadBtn");  
  btn.disabled = true;

  var fromDate = document.getElementById("dateFrom").value;  
  var toDate = document.getElementById("dateTo").value;

  if (!fromDate || !toDate) {  
    setStatus("error", "Please select both dates.");  
    btn.disabled = false;  
    return;  
  }

  var fdaFrom = formatDateFDA(fromDate);  
  var fdaTo = formatDateFDA(toDate);

  setStatus("loading", "Fetching FDA approvals...");

  var url =  
    "https://api.fda.gov/drug/drugsfda.json?" +  
    "search=submissions.submission_status_date:" +  
    "[" + fdaFrom + "+TO+" + fdaTo + "]" +  
    "&limit=100";

  fetch(url)  
    .then(function (response) {  
      if (response.status === 404) {  
        setStatus("error",  
          "No approvals found for this date range.");  
        btn.disabled = false;  
        return null;  
      }  
      if (!response.ok) {  
        throw new Error(  
          "FDA API error: " + response.status  
        );  
      }  
      return response.json();  
    })  
    .then(function (data) {  
      if (!data) return;

      var results = data.results || [];  
      if (results.length === 0) {  
        setStatus("error", "No drug records found.");  
        btn.disabled = false;  
        return;  
      }

      setStatus("loading",  
        "Processing " + results.length +  
        " drug record(s)...");

      var approvals = [];  
      var seen = {};

      for (var i = 0; i < results.length; i++) {  
        var drug = results[i];  
        var submissions = drug.submissions || [];  
        var products = drug.products || [];  
        var openfda = drug.openfda || {};  
        var appNum =  
          drug.application_number || "Unknown";

        for (var j = 0; j < submissions.length; j++) {  
          var sub = submissions[j];  
          var subDate =  
            sub.submission_status_date || "";  
          var subStatus =  
            sub.submission_status || "";

          if (!subDate || subStatus !== "AP") continue;

          var subInt = parseInt(subDate);  
          if (subInt < parseInt(fdaFrom) ||  
              subInt > parseInt(fdaTo)) continue;

          var key = appNum + "_" + subDate;  
          if (seen[key]) continue;  
          seen[key] = true;

          var drugName = "Unknown";  
          var dosageForm = "Unknown";  
          var route = "Unknown";  
          var ingredients = "N/A";

          if (products.length > 0) {  
            drugName =  
              products[0].brand_name || "Unknown";  
            dosageForm =  
              products[0].dosage_form || "Unknown";  
            route = products[0].route || "Unknown";

            var ais =  
              products[0].active_ingredients || [];  
            if (ais.length > 0) {  
              var parts = [];  
              for (var k = 0; k < ais.length; k++) {  
                var aiName =  
                  ais[k].name || "Unknown";  
                var aiStr =  
                  ais[k].strength || "";  
                if (aiStr) {  
                  parts.push(  
                    aiName + " (" + aiStr + ")"  
                  );  
                } else {  
                  parts.push(aiName);  
                }  
              }  
              ingredients = parts.join("; ");  
            }  
          }

          var genericName = "Unknown";  
          var gNames = openfda.generic_name || [];  
          if (gNames.length > 0) {  
            genericName = gNames[0];  
          }

          var subType =  
            sub.submission_type || "Unknown";  
          var subTypeDesc = subType;  
          if (subType === "ORIG") {  
            subTypeDesc = "New Drug Application";  
          } else if (subType === "SUPPL") {  
            subTypeDesc = "Supplemental";  
          } else if (subType === "ABBR") {  
            subTypeDesc = "Abbreviated (Generic)";  
          }

          var dateDisplay = subDate;  
          if (subDate.length === 8) {  
            dateDisplay =  
              subDate.substring(4, 6) + "/" +  
              subDate.substring(6, 8) + "/" +  
              subDate.substring(0, 4);  
          }

          approvals.push({  
            drug_name: drugName,  
            generic_name: genericName,  
            approval_date: dateDisplay,  
            approval_date_raw: subDate,  
            application_number: appNum,  
            submission_type: subTypeDesc,  
            sponsor:  
              drug.sponsor_name || "Unknown",  
            dosage_form: dosageForm,  
            route: route,  
            active_ingredients: ingredients,  
            indication: "",  
            specialty: ""  
          });  
        }  
      }

      if (approvals.length === 0) {  
        setStatus("error",  
          "No approved drugs found in range.");  
        btn.disabled = false;  
        return;  
      }

      setStatus("loading",  
        "Fetching indications for " +  
        approvals.length + " drug(s)...");

      var fetchedApps = {};  
      for (var a = 0; a < approvals.length; a++) {  
        var thisApp =  
          approvals[a].application_number;  
        if (!fetchedApps[thisApp]) {  
          fetchedApps[thisApp] =  
            fetchIndication(thisApp);  
        }  
      }

      var appKeys = Object.keys(fetchedApps);  
      Promise.all(  
        appKeys.map(function (k) {  
          return fetchedApps[k];  
        })  
      ).then(function (indResults) {  
        var indMap = {};  
        for (var x = 0; x < appKeys.length; x++) {  
          indMap[appKeys[x]] = indResults[x];  
        }  
        for (var b = 0; b < approvals.length; b++) {  
          var ind =  
            indMap[approvals[b].application_number]  
            || "N/A";  
          approvals[b].indication = ind;  
          approvals[b].specialty =  
            mapIndicationToSpecialty(  
              ind, approvals[b].drug_name  
            );  
        }

        // Sort by date then drug name  
        approvals.sort(function (a, b) {  
          if (a.approval_date_raw !==  
              b.approval_date_raw) {  
            return a.approval_date_raw  
              .localeCompare(b.approval_date_raw);  
          }  
          return a.drug_name  
            .localeCompare(b.drug_name);  
        });

        setStatus("loading",  
          "Generating Excel report...");  
        generateExcel(approvals, fromDate, toDate);  
        setStatus("success",  
          "Downloaded " + approvals.length +  
          " drug approval(s).");  
        btn.disabled = false;  
      });  
    })  
    .catch(function (err) {  
      setStatus("error", "Error: " + err.message);  
      btn.disabled = false;  
    });  
}


function generateExcel(approvals, fromDate, toDate) {  
  var wb = XLSX.utils.book_new();

  // =============================================  
  // SHEET 1: SUMMARY  
  // =============================================  
  var summaryRows = [];

  summaryRows.push(["FDA DRUG APPROVAL REPORT"]);  
  summaryRows.push(["Northwell Health — " +  
    "Business Operations"]);  
  summaryRows.push([""]);  
  summaryRows.push(["Report Date:",  
    new Date().toLocaleDateString("en-US", {  
      weekday: "long",  
      year: "numeric",  
      month: "long",  
      day: "numeric"  
    })  
  ]);  
  summaryRows.push(["Date Range:",  
    formatDateDisplay(fromDate) + " to " +  
    formatDateDisplay(toDate)  
  ]);  
  summaryRows.push(["Total Approvals:",  
    approvals.length  
  ]);  
  summaryRows.push([""]);

  // Count by submission type  
  var typeCounts = {};  
  var specCounts = {};  
  var sponsorCounts = {};

  for (var i = 0; i < approvals.length; i++) {  
    var a = approvals[i];

    var st = a.submission_type;  
    typeCounts[st] = (typeCounts[st] || 0) + 1;

    var sp = a.specialty;  
    specCounts[sp] = (specCounts[sp] || 0) + 1;

    var sn = a.sponsor;  
    sponsorCounts[sn] = (sponsorCounts[sn] || 0) + 1;  
  }

  summaryRows.push(["APPROVALS BY TYPE", ""]);  
  summaryRows.push(["Type", "Count"]);  
  for (var t in typeCounts) {  
    summaryRows.push([t, typeCounts[t]]);  
  }  
  summaryRows.push([""]);

  summaryRows.push(["APPROVALS BY SPECIALTY", ""]);  
  summaryRows.push(["Specialty", "Count"]);

  var specKeys = Object.keys(specCounts).sort(  
    function (a, b) {  
      return specCounts[b] - specCounts[a];  
    }  
  );  
  for (var s = 0; s < specKeys.length; s++) {  
    summaryRows.push([  
      specKeys[s], specCounts[specKeys[s]]  
    ]);  
  }  
  summaryRows.push([""]);

  summaryRows.push(["TOP SPONSORS", ""]);  
  summaryRows.push(["Sponsor", "Count"]);

  var sponsorKeys = Object.keys(sponsorCounts).sort(  
    function (a, b) {  
      return sponsorCounts[b] - sponsorCounts[a];  
    }  
  );  
  for (var sp2 = 0;  
       sp2 < Math.min(sponsorKeys.length, 10);  
       sp2++) {  
    summaryRows.push([  
      sponsorKeys[sp2],  
      sponsorCounts[sponsorKeys[sp2]]  
    ]);  
  }

  var wsSummary = XLSX.utils.aoa_to_sheet(summaryRows);  
  wsSummary["!cols"] = [  
    { wch: 35 },  
    { wch: 40 }  
  ];

  XLSX.utils.book_append_sheet(  
    wb, wsSummary, "Summary"  
  );

  // =============================================  
  // SHEET 2: ALL APPROVALS (DETAILED)  
  // =============================================  
  var detailRows = [];

  detailRows.push([  
    "#",  
    "Drug Name",  
    "Generic Name",  
    "Mapped Specialty",  
    "Approval Date",  
    "Submission Type",  
    "Sponsor",  
    "Application #",  
    "Dosage Form",  
    "Route",  
    "Active Ingredients",  
    "Indication / Use"  
  ]);

  for (var d = 0; d < approvals.length; d++) {  
    var app = approvals[d];  
    detailRows.push([  
      d + 1,  
      app.drug_name,  
      app.generic_name,  
      app.specialty,  
      app.approval_date,  
      app.submission_type,  
      app.sponsor,  
      app.application_number,  
      app.dosage_form,  
      app.route,  
      app.active_ingredients,  
      app.indication  
    ]);  
  }

  var wsDetail = XLSX.utils.aoa_to_sheet(detailRows);  
  wsDetail["!cols"] = [  
    { wch: 4 },  
    { wch: 22 },  
    { wch: 28 },  
    { wch: 22 },  
    { wch: 14 },  
    { wch: 20 },  
    { wch: 25 },  
    { wch: 16 },  
    { wch: 18 },  
    { wch: 12 },  
    { wch: 40 },  
    { wch: 60 }  
  ];

  XLSX.utils.book_append_sheet(  
    wb, wsDetail, "All Approvals"  
  );

  // =============================================  
  // SHEET 3: BY SPECIALTY  
  // =============================================  
  var specRows = [];

  specRows.push([  
    "Specialty",  
    "#",  
    "Drug Name",  
    "Generic Name",  
    "Approval Date",  
    "Submission Type",  
    "Sponsor",  
    "Indication / Use"  
  ]);

  for (var sk = 0; sk < specKeys.length; sk++) {  
    var specName = specKeys[sk];  
    var isFirst = true;

    for (var d2 = 0; d2 < approvals.length; d2++) {  
      if (approvals[d2].specialty === specName) {  
        specRows.push([  
          isFirst ? specName : "",  
          d2 + 1,  
          approvals[d2].drug_name,  
          approvals[d2].generic_name,  
          approvals[d2].approval_date,  
          approvals[d2].submission_type,  
          approvals[d2].sponsor,  
          approvals[d2].indication  
        ]);  
        isFirst = false;  
      }  
    }

    // Add blank row between specialties  
    specRows.push([""]);  
  }

  var wsSpec = XLSX.utils.aoa_to_sheet(specRows);  
  wsSpec["!cols"] = [  
    { wch: 22 },  
    { wch: 4 },  
    { wch: 22 },  
    { wch: 28 },  
    { wch: 14 },  
    { wch: 20 },  
    { wch: 25 },  
    { wch: 60 }  
  ];

  XLSX.utils.book_append_sheet(  
    wb, wsSpec, "By Specialty"  
  );

  // =============================================  
  // SHEET 4: NEW DRUG APPLICATIONS ONLY  
  // =============================================  
  var ndaRows = [];

  ndaRows.push([  
    "#",  
    "Drug Name",  
    "Generic Name",  
    "Mapped Specialty",  
    "Approval Date",  
    "Sponsor",  
    "Dosage Form",  
    "Route",  
    "Active Ingredients",  
    "Indication / Use"  
  ]);

  var ndaCount = 0;  
  for (var n = 0; n < approvals.length; n++) {  
    if (approvals[n].submission_type ===  
        "New Drug Application" ||  
        approvals[n].submission_type ===  
        "Abbreviated (Generic)") {  
      ndaCount++;  
      ndaRows.push([  
        ndaCount,  
        approvals[n].drug_name,  
        approvals[n].generic_name,  
        approvals[n].specialty,  
        approvals[n].approval_date,  
        approvals[n].sponsor,  
        approvals[n].dosage_form,  
        approvals[n].route,  
        approvals[n].active_ingredients,  
        approvals[n].indication  
      ]);  
    }  
  }

  if (ndaCount === 0) {  
    ndaRows.push([  
      "", "No new drug applications in this period",  
      "", "", "", "", "", "", "", ""  
    ]);  
  }

  var wsNDA = XLSX.utils.aoa_to_sheet(ndaRows);  
  wsNDA["!cols"] = [  
    { wch: 4 },  
    { wch: 22 },  
    { wch: 28 },  
    { wch: 22 },  
    { wch: 14 },  
    { wch: 25 },  
    { wch: 18 },  
    { wch: 12 },  
    { wch: 40 },  
    { wch: 60 }  
  ];

  XLSX.utils.book_append_sheet(  
    wb, wsNDA, "New Drugs Only"  
  );

  // =============================================  
  // GENERATE FILE  
  // =============================================  
  var filename =  
    "FDA_Drug_Approval_Report_" +  
    fromDate + "_to_" + toDate + ".xlsx";

  XLSX.writeFile(wb, filename);  
}  
