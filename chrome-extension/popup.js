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
            if (text.length > 300) {  
              text = text.substring(0, 300) + "...";  
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
            subTypeDesc =  
              "Original New Drug Application";  
          } else if (subType === "SUPPL") {  
            subTypeDesc =  
              "Supplemental Application";  
          } else if (subType === "ABBR") {  
            subTypeDesc =  
              "Abbreviated New Drug Application";  
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
            application_number: appNum,  
            submission_type: subTypeDesc,  
            sponsor:  
              drug.sponsor_name || "Unknown",  
            dosage_form: dosageForm,  
            route: route,  
            active_ingredients: ingredients,  
            indication: ""  
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
          approvals[b].indication =  
            indMap[approvals[b].application_number]  
            || "N/A";  
        }

        setStatus("loading",  
          "Generating Excel file...");  
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

  var headers = [  
    "Drug Name",  
    "Generic Name",  
    "Approval Date",  
    "Application Number",  
    "Submission Type",  
    "Sponsor",  
    "Dosage Form",  
    "Route",  
    "Active Ingredients",  
    "Indication"  
  ];

  var rows = [headers];

  for (var i = 0; i < approvals.length; i++) {  
    var a = approvals[i];  
    rows.push([  
      a.drug_name,  
      a.generic_name,  
      a.approval_date,  
      a.application_number,  
      a.submission_type,  
      a.sponsor,  
      a.dosage_form,  
      a.route,  
      a.active_ingredients,  
      a.indication  
    ]);  
  }

  var ws = XLSX.utils.aoa_to_sheet(rows);

  ws["!cols"] = [  
    { wch: 20 },  
    { wch: 25 },  
    { wch: 14 },  
    { wch: 18 },  
    { wch: 30 },  
    { wch: 20 },  
    { wch: 18 },  
    { wch: 15 },  
    { wch: 40 },  
    { wch: 50 }  
  ];

  XLSX.utils.book_append_sheet(  
    wb, ws, "FDA Approvals"  
  );

  var filename =  
    "FDA_Drug_Approvals_" +  
    fromDate + "_to_" + toDate + ".xlsx";

  XLSX.writeFile(wb, filename);  
}  
