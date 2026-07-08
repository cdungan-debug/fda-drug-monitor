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
  var months = [  
    "January", "February", "March", "April",  
    "May", "June", "July", "August",  
    "September", "October", "November", "December"  
  ];  
  var parts = dateStr.split("-");  
  if (parts.length === 3) {  
    var mi = parseInt(parts[1]) - 1;  
    return months[mi] + " " + parseInt(parts[2]) +  
      ", " + parts[0];  
  }  
  return dateStr;  
}


function setStatus(type, message) {  
  var el = document.getElementById("status");  
  el.className = "status " + type;  
  if (type === "loading") {  
    el.innerHTML = "" + message;  
  } else {  
    el.innerHTML = message;  
  }  
}


function fetchIndication(appNumber) {  
  return new Promise(function (resolve) {  
    var url =  
      "https://api.fda.gov/drug/label.json?search=openfda.application_number:%22" +  
      appNumber +  
      "%22&limit=1";  
    fetch(url)  
      .then(function (r) {  
        return r.json();  
      })  
      .then(function (data) {  
        var result = {  
          indication: "N/A",  
          pharmClass: ""  
        };  
        if (data.results && data.results[0]) {  
          var label = data.results[0];  
          if (  
            label.indications_and_usage &&  
            label.indications_and_usage[0]  
          ) {  
            result.indication = label.indications_and_usage[0];  
            if (result.indication.length > 500) {  
              result.indication =  
                result.indication.substring(0, 500) + "...";  
            }  
          } else if (label.purpose && label.purpose[0]) {  
            result.indication = label.purpose[0];  
          }  
          var of = label.openfda || {};  
          var classes = [];  
          if (of.pharm_class_epc) {  
            classes = classes.concat(of.pharm_class_epc);  
          }  
          if (of.pharm_class_moa) {  
            classes = classes.concat(of.pharm_class_moa);  
          }  
          if (of.pharm_class_pe) {  
            classes = classes.concat(of.pharm_class_pe);  
          }  
          result.pharmClass = classes.join("; ");  
        }  
        resolve(result);  
      })  
      .catch(function () {  
        resolve({ indication: "N/A", pharmClass: "" });  
      });  
  });  
}


function fetchRxClassByName(drugName) {  
  return new Promise(function (resolve) {  
    if (!drugName || drugName === "Unknown") {  
      resolve("");  
      return;  
    }  
    var cleanName = drugName.split(" ")[0].toLowerCase();  
    var rxNormUrl =  
      "https://rxnav.nlm.nih.gov/REST/rxcui.json?name=" +  
      encodeURIComponent(cleanName) +  
      "&search=2";  
    fetch(rxNormUrl)  
      .then(function (r) {  
        return r.json();  
      })  
      .then(function (data) {  
        var group = data.idGroup || {};  
        var rxcuiList = group.rxnormId || [];  
        if (rxcuiList.length === 0) {  
          resolve("");  
          return;  
        }  
        var rxcui = rxcuiList[0];  
        var classUrl =  
          "https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json?rxcui=" +  
          rxcui +  
          "&relaSource=ATC&relas=may_treat,has_EPC,ci_with";  
        fetch(classUrl)  
          .then(function (r2) {  
            return r2.json();  
          })  
          .then(function (classData) {  
            var entries =  
              (classData.rxclassDrugInfoList || {})  
                .rxclassDrugInfo || [];  
            var classNames = [];  
            for (var i = 0; i < entries.length; i++) {  
              var cn =  
                entries[i].rxclassMinConceptItem || {};  
              if (cn.className) {  
                classNames.push(cn.className);  
              }  
            }  
            resolve(classNames.join("; "));  
          })  
          .catch(function () {  
            resolve("");  
          });  
      })  
      .catch(function () {  
        resolve("");  
      });  
  });  
}


function mapIndicationToSpecialty(indication, drugName, pharmClass) {  
  var text = (  
    indication + " " + drugName + " " + (pharmClass || "")  
  ).toLowerCase();

  var pharmMapping = {  
    "kinase inhibitor": "Hematology & Oncology (Cancer)",  
    "antineoplastic": "Hematology & Oncology (Cancer)",  
    "pd-1": "Hematology & Oncology (Cancer)",  
    "pd-l1": "Hematology & Oncology (Cancer)",  
    "her2": "Hematology & Oncology (Cancer)",  
    "egfr": "Hematology & Oncology (Cancer)",  
    "vegf": "Hematology & Oncology (Cancer)",  
    "bcr-abl": "Hematology & Oncology (Cancer)",  
    "proteasome inhibitor": "Hematology & Oncology (Cancer)",  
    "cd19": "Hematology & Oncology (Cancer)",  
    "cd20": "Hematology & Oncology (Cancer)",  
    "alkylating": "Hematology & Oncology (Cancer)",  
    "cytotoxic": "Hematology & Oncology (Cancer)",  
    "topoisomerase inhibitor": "Hematology & Oncology (Cancer)",  
    "androgen receptor": "Hematology & Oncology (Cancer)",  
    "estrogen receptor": "Hematology & Oncology (Cancer)",  
    "aromatase inhibitor": "Hematology & Oncology (Cancer)",  
    "immunostimulant": "Hematology & Oncology (Cancer)",  
    "selective serotonin reuptake inhibitor": "Psychiatrist",  
    "ssri": "Psychiatrist",  
    "serotonin and norepinephrine reuptake": "Psychiatrist",  
    "snri": "Psychiatrist",  
    "atypical antipsychotic": "Psychiatrist",  
    "typical antipsychotic": "Psychiatrist",  
    "benzodiazepine": "Psychiatrist",  
    "dopamine receptor": "Psychiatrist",  
    "mood stabiliz": "Psychiatrist",  
    "tricyclic antidepressant": "Psychiatrist",  
    "anxiolytic": "Psychiatrist",  
    "angiotensin": "Cardiologist",  
    "ace inhibitor": "Cardiologist",  
    "beta-adrenergic blocker": "Cardiologist",  
    "beta blocker": "Cardiologist",  
    "calcium channel blocker": "Cardiologist",  
    "antiarrhythmic": "Cardiologist",  
    "hmg-coa reductase inhibitor": "Cardiologist",  
    "statin": "Cardiologist",  
    "anticoagulant": "Cardiologist",  
    "factor xa inhibitor": "Cardiologist",  
    "thrombin inhibitor": "Cardiologist",  
    "antiplatelet": "Cardiologist",  
    "vasodilator": "Cardiologist",  
    "diuretic": "Cardiologist",  
    "cardiac glycoside": "Cardiologist",  
    "proton pump inhibitor": "Internal Medicine",  
    "h2 receptor antagonist": "Internal Medicine",  
    "antacid": "Internal Medicine",  
    "laxative": "Internal Medicine",  
    "antiemetic": "Internal Medicine",  
    "5-ht3 receptor antagonist": "Internal Medicine",  
    "aminosalicylate": "Internal Medicine",  
    "tnf blocker": "Rheumatologist",  
    "interleukin inhibitor": "Rheumatologist",  
    "il-6": "Rheumatologist",  
    "il-17": "Rheumatologist",  
    "il-23": "Rheumatologist",  
    "janus kinase inhibitor": "Rheumatologist",  
    "jak inhibitor": "Rheumatologist",  
    "disease-modifying": "Rheumatologist",  
    "immunomodulator": "Rheumatologist",  
    "nonsteroidal anti-inflammatory": "Rheumatologist",  
    "nsaid": "Rheumatologist",  
    "cox-2": "Rheumatologist",  
    "corticosteroid": "Pulmonologist",  
    "beta2-adrenergic agonist": "Pulmonologist",  
    "beta-2 agonist": "Pulmonologist",  
    "bronchodilator": "Pulmonologist",  
    "leukotriene receptor antagonist": "Pulmonologist",  
    "muscarinic antagonist": "Pulmonologist",  
    "phosphodiesterase": "Pulmonologist",  
    "cftr": "Pulmonologist",  
    "anticonvulsant": "Vascular Neurology",  
    "antiepileptic": "Vascular Neurology",  
    "dopamine precursor": "Vascular Neurology",  
    "cholinesterase inhibitor": "Vascular Neurology",  
    "nmda receptor antagonist": "Vascular Neurology",  
    "gaba": "Vascular Neurology",  
    "sodium channel": "Vascular Neurology",  
    "cgrp": "Vascular Neurology",  
    "insulin": "Endocrinologist",  
    "sulfonylurea": "Endocrinologist",  
    "biguanide": "Endocrinologist",  
    "sglt2 inhibitor": "Endocrinologist",  
    "glp-1 receptor agonist": "Endocrinologist",  
    "dpp-4 inhibitor": "Endocrinologist",  
    "thiazolidinedione": "Endocrinologist",  
    "thyroid": "Endocrinologist",  
    "bisphosphonate": "Endocrinologist",  
    "glucocorticoid": "Endocrinologist",  
    "incretin": "Endocrinologist",  
    "nucleoside reverse transcriptase": "Infectious Disease",  
    "protease inhibitor": "Infectious Disease",  
    "integrase inhibitor": "Infectious Disease",  
    "non-nucleoside reverse transcriptase": "Infectious Disease",  
    "neuraminidase inhibitor": "Infectious Disease",  
    "cephalosporin": "Infectious Disease",  
    "penicillin": "Infectious Disease",  
    "fluoroquinolone": "Infectious Disease",  
    "macrolide": "Infectious Disease",  
    "tetracycline": "Infectious Disease",  
    "carbapenem": "Infectious Disease",  
    "aminoglycoside": "Infectious Disease",  
    "antifungal": "Infectious Disease",  
    "azole antifungal": "Infectious Disease",  
    "antimalarial": "Infectious Disease",  
    "antiretroviral": "Infectious Disease",  
    "prostaglandin analog": "Vision Care",  
    "carbonic anhydrase inhibitor": "Vision Care",  
    "ophthalmic": "Vision Care",  
    "calcineurin inhibitor": "Transplant",  
    "mtor inhibitor": "Transplant",  
    "erythropoiesis-stimulating": "Dialysis",  
    "phosphate binder": "Dialysis",  
    "opioid agonist": "Rehabilitation",  
    "opioid antagonist": "Behavioral Health",  
    "opioid": "Rehabilitation",  
    "local anesthetic": "Anesthesiology",  
    "general anesthetic": "Anesthesiology",  
    "neuromuscular block": "Anesthesiology",  
    "antihistamine": "Internal Medicine",  
    "h1 receptor antagonist": "Internal Medicine",  
    "erythropoietin": "Hematology & Oncology (Cancer)",  
    "colony stimulating factor": "Hematology & Oncology (Cancer)",  
    "thrombopoietin": "Hematology & Oncology (Cancer)",  
    "growth factor": "Hematology & Oncology (Cancer)"  
  };

  for (var pharmKey in pharmMapping) {  
    if (text.indexOf(pharmKey) !== -1) {  
      return pharmMapping[pharmKey];  
    }  
  }

  var keywordMapping = {  
    "cancer": "Hematology & Oncology (Cancer)",  
    "tumor": "Hematology & Oncology (Cancer)",  
    "carcinoma": "Hematology & Oncology (Cancer)",  
    "lymphoma": "Hematology & Oncology (Cancer)",  
    "leukemia": "Hematology & Oncology (Cancer)",  
    "melanoma": "Hematology & Oncology (Cancer)",  
    "metastatic": "Hematology & Oncology (Cancer)",  
    "neoplasm": "Hematology & Oncology (Cancer)",  
    "sarcoma": "Hematology & Oncology (Cancer)",  
    "myeloma": "Hematology & Oncology (Cancer)",  
    "anemia": "Hematology & Oncology (Cancer)",  
    "hemophilia": "Hematology & Oncology (Cancer)",  
    "sickle cell": "Hematology & Oncology (Cancer)",  
    "neutropenia": "Hematology & Oncology (Cancer)",  
    "chemotherapy": "Medical Oncologist",  
    "gynecologic cancer": "Gynecologic Oncologist",  
    "ovarian cancer": "Gynecologic Oncologist",  
    "cervical cancer": "Gynecologic Oncologist",  
    "uterine cancer": "Gynecologic Oncologist",  
    "endometrial cancer": "Gynecologic Oncologist",  
    "hypertension": "Cardiologist",  
    "heart failure": "Cardiologist",  
    "cardiac": "Cardiologist",  
    "cardiovascular": "Cardiologist",  
    "angina": "Cardiologist",  
    "arrhythmia": "Cardiologist",  
    "atrial fibrillation": "Cardiologist",  
    "blood pressure": "Cardiologist",  
    "cholesterol": "Cardiologist",  
    "thrombosis": "Cardiologist",  
    "coronary": "Cardiologist",  
    "myocardial": "Cardiologist",  
    "seizure": "Vascular Neurology",  
    "epilepsy": "Vascular Neurology",  
    "neurological": "Vascular Neurology",  
    "multiple sclerosis": "Vascular Neurology",  
    "parkinson": "Vascular Neurology",  
    "migraine": "Vascular Neurology",  
    "neuropathy": "Vascular Neurology",  
    "stroke": "Vascular Neurology",  
    "dementia": "Vascular Neurology",  
    "alzheimer": "Vascular Neurology",  
    "brain injury": "Brain Injury Medicine",  
    "traumatic brain": "Brain Injury Medicine",  
    "concussion": "Brain Injury Medicine",  
    "spinal cord": "Spinal Cord Injury Medicine",  
    "schizophrenia": "Psychiatrist",  
    "bipolar": "Psychiatrist",  
    "depression": "Psychiatrist",  
    "anxiety": "Psychiatrist",  
    "insomnia": "Psychiatrist",  
    "adhd": "Psychiatrist",  
    "ptsd": "Psychiatrist",  
    "psychosis": "Psychiatrist",  
    "obsessive": "Psychiatrist",  
    "substance abuse": "Behavioral Health",  
    "addiction": "Behavioral Health",  
    "opioid use disorder": "Behavioral Health",  
    "alcohol dependence": "Behavioral Health",  
    "mental health": "Mental Health",  
    "autism": "Autism Spectrum Disorder",  
    "asthma": "Pulmonologist",  
    "copd": "Pulmonologist",  
    "pulmonary": "Pulmonologist",  
    "respiratory": "Pulmonologist",  
    "bronchitis": "Pulmonologist",  
    "cystic fibrosis": "Pulmonologist",  
    "emphysema": "Pulmonologist",  
    "arthritis": "Rheumatologist",  
    "rheumatoid": "Rheumatologist",  
    "lupus": "Rheumatologist",  
    "autoimmune": "Rheumatologist",  
    "fibromyalgia": "Rheumatologist",  
    "gout": "Rheumatologist",  
    "psoriasis": "Rheumatologist",  
    "ankylosing": "Rheumatologist",  
    "vasculitis": "Rheumatologist",  
    "glaucoma": "Vision Care",  
    "retinal": "Vision Care",  
    "macular": "Vision Care",  
    "cataract": "Vision Care",  
    "ocular": "Vision Care",  
    "conjunctivitis": "Vision Care",  
    "liver": "Hepatology",  
    "hepatic": "Hepatology",  
    "hepatitis": "Hepatology",  
    "cirrhosis": "Hepatology",  
    "gastrointestinal": "Internal Medicine",  
    "nausea": "Internal Medicine",  
    "ulcer": "Internal Medicine",  
    "crohn": "Internal Medicine",  
    "colitis": "Internal Medicine",  
    "constipation": "Internal Medicine",  
    "reflux": "Internal Medicine",  
    "irritable bowel": "Internal Medicine",  
    "colon": "Colon & Rectal Surgery",  
    "rectal": "Colon & Rectal Surgery",  
    "colorectal": "Colon & Rectal Surgery",  
    "renal": "Dialysis",  
    "kidney": "Dialysis",  
    "dialysis": "Dialysis",  
    "nephrotic": "Dialysis",  
    "diabetes": "Endocrinologist",  
    "thyroid": "Endocrinologist",  
    "osteoporosis": "Endocrinologist",  
    "hormone": "Endocrinologist",  
    "insulin": "Endocrinologist",  
    "glucose": "Endocrinologist",  
    "adrenal": "Endocrinologist",  
    "metabolic": "Endocrinologist",  
    "fertility": "Reproductive Endocrinologist",  
    "infertility": "Reproductive Endocrinologist",  
    "infection": "Infectious Disease",  
    "antibacterial": "Infectious Disease",  
    "antiviral": "Infectious Disease",  
    "antibiotic": "Infectious Disease",  
    "hiv": "Infectious Disease",  
    "pneumonia": "Infectious Disease",  
    "sepsis": "Infectious Disease",  
    "tuberculosis": "Infectious Disease",  
    "influenza": "Infectious Disease",  
    "covid": "Infectious Disease",  
    "transfusion": "Blood Banking & Transfusion Medicine",  
    "prostate": "Urologist",  
    "bladder": "Urologist",  
    "urinary": "Urologist",  
    "erectile": "Urologist",  
    "kidney stone": "Urologist",  
    "orthopedic": "Orthopedic Surgeon",  
    "bone": "Orthopedic Surgeon",  
    "fracture": "Orthopedic Surgeon",  
    "joint": "Orthopedic Surgeon",  
    "musculoskeletal": "Neuromusculoskeletal Medicine",  
    "pregnancy": "Gynecologist",  
    "contracepti": "Gynecologist",  
    "menopausal": "Gynecologist",  
    "prenatal": "Gynecologist",  
    "endometriosis": "Gynecologist",  
    "menstrual": "Gynecologist",  
    "anesthetic": "Anesthesiology",  
    "sedation": "Anesthesiology",  
    "anesthesia": "Anesthesiology",  
    "allergy": "Internal Medicine",  
    "histamine": "Internal Medicine",  
    "contrast": "Diagnostic Imaging Center",  
    "imaging": "Diagnostic Imaging Center",  
    "radiopharmaceutical": "Nuclear Medicine",  
    "nuclear": "Nuclear Medicine",  
    "ultrasound": "Diagnostic Ultrasound",  
    "pediatric": "Family Medicine",  
    "children": "Family Medicine",  
    "infant": "Family Medicine",  
    "neonatal": "Family Medicine",  
    "naloxone": "Emergency Medical Services",  
    "overdose": "Emergency Medical Services",  
    "emergency": "Emergency Medical Services",  
    "hearing": "ENT",  
    "nasal": "ENT",  
    "sinusitis": "ENT",  
    "tinnitus": "ENT",  
    "ear infection": "ENT",  
    "throat": "ENT",  
    "otitis": "ENT",  
    "bariatric": "Bariatric Medicine",  
    "weight loss": "Bariatric Medicine",  
    "obesity": "Bariatric Medicine",  
    "hospice": "Hospice and Palliative Medicine",  
    "palliative": "Hospice and Palliative Medicine",  
    "transplant": "Transplant",  
    "immunosuppressant": "Transplant",  
    "graft": "Transplant",  
    "critical care": "Critical Care Medicine",  
    "icu": "Critical Care Medicine",  
    "toxic": "Medical Toxicology",  
    "poison": "Medical Toxicology",  
    "antidote": "Medical Toxicology",  
    "genetic": "Genetics",  
    "gene therapy": "Genetics",  
    "hereditary": "Genetics",  
    "vaccine": "Preventive Medicine",  
    "prophylaxis": "Preventive Medicine",  
    "infusion": "Infusion Medicine",  
    "intravenous": "Infusion Medicine",  
    "oral surgery": "Oral and Maxillofacial Surgeon",  
    "dental": "Oral and Maxillofacial Surgeon",  
    "rehabilitation": "Rehabilitation",  
    "physical therapy": "Rehabilitation",  
    "pain": "Rehabilitation",  
    "analgesic": "Rehabilitation",  
    "sports injury": "Sports Medicine",  
    "athletic": "Sports Medicine",  
    "acne": "Family Medicine",  
    "dermatitis": "Family Medicine",  
    "eczema": "Family Medicine",  
    "skin": "Family Medicine",  
    "topical": "Family Medicine",  
    "wound": "General Surgeon",  
    "surgical": "General Surgeon",  
    "speech": "Speech Therapy",  
    "swallowing": "Speech Therapy",  
    "audiolog": "Audiologist",  
    "chiropractic": "Chiropractor",  
    "counseling": "Counselor",  
    "neuropsychol": "Neuropsychology",  
    "home health": "Home Health"  
  };

  for (var keyword in keywordMapping) {  
    if (text.indexOf(keyword) !== -1) {  
      return keywordMapping[keyword];  
    }  
  }  
  return "General Practice";  
}


function escapeXml(str) {  
  if (!str) return "";  
  var result = String(str);  
  var out = [];  
  for (var i = 0; i < result.length; i++) {  
    var code = result.charCodeAt(i);  
    if (code === 38) {  
      out.push(String.fromCharCode(38) + "amp;");  
    } else if (code === 60) {  
      out.push(String.fromCharCode(38) + "lt;");  
    } else if (code === 62) {  
      out.push(String.fromCharCode(38) + "gt;");  
    } else if (code === 34) {  
      out.push(String.fromCharCode(38) + "quot;");  
    } else if (code === 39) {  
      out.push(String.fromCharCode(38) + "apos;");  
    } else {  
      out.push(result.charAt(i));  
    }  
  }  
  return out.join("");  
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

  var allResults = [];  
  var skip = 0;  
  var pageLimit = 100;

  function fetchPage() {  
    var url =  
      "https://api.fda.gov/drug/drugsfda.json?" +  
      "search=submissions.submission_status_date:" +  
      "[" + fdaFrom + "+TO+" + fdaTo + "]" +  
      "&limit=" + pageLimit +  
      "&skip=" + skip;

    return fetch(url)  
      .then(function (response) {  
        if (response.status === 404) {  
          return null;  
        }  
        if (!response.ok) {  
          throw new Error("FDA API error: " +  
            response.status);  
        }  
        return response.json();  
      })  
      .then(function (data) {  
        if (!data) return false;

        var results = data.results || [];  
        if (results.length === 0) return false;

        allResults = allResults.concat(results);  
        var totalAvailable =  
          data.meta.results.total || 0;

        setStatus("loading",  
          "Fetching FDA data... " +  
          allResults.length + " of " +  
          totalAvailable + " records");

        skip += pageLimit;  
        if (skip < totalAvailable && skip < 1000) {  
          return fetchPage();  
        }  
        return true;  
      });  
  }

  fetchPage().then(function (success) {  
    if (!success && allResults.length === 0) {  
      setStatus("error",  
        "No approvals found for this date range.");  
      btn.disabled = false;  
      return;  
    }

    var results = allResults;

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

        // Filter out ANDAs (generic drug applications)  
        if (appNum.toUpperCase().indexOf("ANDA") === 0) continue;

        var subType =  
          sub.submission_type || "Unknown";

        // Filter out minor supplementals  
        var subClassCode =  
          sub.submission_class_code || "";  
        var subClassDesc =  
          sub.submission_class_code_description || "";  
        var combinedClass =  
          (subClassCode + " " + subClassDesc).toUpperCase();

        if (subType === "SUPPL") {  
          var isMinor = false;  
          var minorKeywords = [  
            "MANUF", "PACKAGING", "EDITORIAL",  
            "CBE", "ANNUAL REPORT", "STABILITY",  
            "PROCESS", "SITE CHANGE", "SUPPLIER",  
            "CONTAINER", "SPECIFICATION",  
            "EXPIRATION", "IMPURITY", "METHOD",  
            "DISSOLUTION", "BIOEQUIV",  
            "PATENT", "EXCLUSIVITY",  
            "LABELING-REVISION",  
            "LABELING-OTHER",  
            "CHEMISTRY",  
            "CMC"  
          ];  
          for (var mk = 0; mk < minorKeywords.length; mk++) {  
            if (combinedClass.indexOf(minorKeywords[mk]) !== -1) {  
              isMinor = true;  
              break;  
            }  
          }  
          if (isMinor) continue;  
        }

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

        var subTypeDesc = subType;  
        if (subType === "ORIG") {  
          subTypeDesc = "New Drug Application";  
        } else if (subType === "SUPPL") {  
          subTypeDesc = "Supplemental";  
        } else if (subType === "ABBR") {  
          subTypeDesc = "Abbreviated (Generic)";  
        }

        // Add submission classification detail  
        if (subClassDesc) {  
          subTypeDesc = subTypeDesc + " - " + subClassDesc;  
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
          pharmClass: "",  
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
        var result =  
          indMap[approvals[b].application_number]  
          || { indication: "N/A", pharmClass: "" };  
        approvals[b].indication = result.indication;  
        approvals[b].pharmClass = result.pharmClass;  
      }

      setStatus("loading",  
        "Looking up drug classifications via NIH RxClass...");

      var rxPromises = [];  
      var rxIndexes = [];

      for (var c = 0; c < approvals.length; c++) {  
        if (approvals[c].pharmClass === "" &&  
            approvals[c].indication === "N/A") {  
          var lookupName =  
            approvals[c].generic_name !== "Unknown"  
              ? approvals[c].generic_name  
              : approvals[c].drug_name;  
          rxPromises.push(  
            fetchRxClassByName(lookupName)  
          );  
          rxIndexes.push(c);  
        }  
      }

      if (rxPromises.length === 0) {  
        finishReport(approvals, fromDate, toDate, btn);  
        return;  
      }

      Promise.all(rxPromises).then(  
        function (rxResults) {  
          for (var r = 0; r < rxResults.length; r++) {  
            var idx = rxIndexes[r];  
            if (rxResults[r]) {  
              approvals[idx].pharmClass =  
                rxResults[r];  
              if (approvals[idx].indication === "N/A") {  
                approvals[idx].indication =  
                  "RxClass: " + rxResults[r];  
              }  
            }  
          }  
          finishReport(  
            approvals, fromDate, toDate, btn  
          );  
        }  
      );  
    });  
  })  
  .catch(function (err) {  
    setStatus("error", "Error: " + err.message);  
    btn.disabled = false;  
  });  
}


function finishReport(approvals, fromDate, toDate, btn) {  
  for (var b = 0; b < approvals.length; b++) {  
    approvals[b].specialty =  
      mapIndicationToSpecialty(  
        approvals[b].indication,  
        approvals[b].drug_name,  
        approvals[b].pharmClass  
      );  
  }

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
    "Generating formatted report...");  
  generateFormattedExcel(  
    approvals, fromDate, toDate  
  );  
  setStatus("success",  
    "Downloaded " + approvals.length +  
    " drug approval(s).");  
  btn.disabled = false;  
}


function generateFormattedExcel(approvals, fromDate,  
                                 toDate) {  
  var typeCounts = {};  
  var specCounts = {};  
  var sponsorCounts = {};

  for (var i = 0; i < approvals.length; i++) {  
    var a = approvals[i];  
    typeCounts[a.submission_type] =  
      (typeCounts[a.submission_type] || 0) + 1;  
    specCounts[a.specialty] =  
      (specCounts[a.specialty] || 0) + 1;  
    sponsorCounts[a.sponsor] =  
      (sponsorCounts[a.sponsor] || 0) + 1;  
  }

  var specKeys = Object.keys(specCounts).sort(  
    function (a, b) {  
      return specCounts[b] - specCounts[a];  
    }  
  );

  var sponsorKeys = Object.keys(sponsorCounts).sort(  
    function (a, b) {  
      return sponsorCounts[b] - sponsorCounts[a];  
    }  
  );

  var xml = "";  
  xml += '<?xml version="1.0" encoding="UTF-8"?>\n';  
  xml += '<?mso-application progid="Excel.Sheet"?>\n';  
  xml += '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"\n';  
  xml += ' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"\n';  
  xml += ' xmlns:x="urn:schemas-microsoft-com:office:excel">\n';

  xml += '<Styles>\n';

  xml += '<Style ss:ID="Default" ss:Name="Normal">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="11"/>\n';  
  xml += '  <Alignment ss:Vertical="Center" ss:WrapText="1"/>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="title">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="18" ss:Bold="1" ss:Color="#FFFFFF"/>\n';  
  xml += '  <Interior ss:Color="#0078D4" ss:Pattern="Solid"/>\n';  
  xml += '  <Alignment ss:Vertical="Center"/>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="subtitle">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="12" ss:Color="#FFFFFF"/>\n';  
  xml += '  <Interior ss:Color="#0078D4" ss:Pattern="Solid"/>\n';  
  xml += '  <Alignment ss:Vertical="Center"/>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="section">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="13" ss:Bold="1" ss:Color="#0078D4"/>\n';  
  xml += '  <Borders>\n';  
  xml += '    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="2" ss:Color="#0078D4"/>\n';  
  xml += '  </Borders>\n';  
  xml += '  <Alignment ss:Vertical="Center"/>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="header">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#FFFFFF"/>\n';  
  xml += '  <Interior ss:Color="#0078D4" ss:Pattern="Solid"/>\n';  
  xml += '  <Alignment ss:Vertical="Center" ss:WrapText="1"/>\n';  
  xml += '  <Borders>\n';  
  xml += '    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#005A9E"/>\n';  
  xml += '    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#005A9E"/>\n';  
  xml += '    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#005A9E"/>\n';  
  xml += '  </Borders>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="data">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="11"/>\n';  
  xml += '  <Alignment ss:Vertical="Center" ss:WrapText="1"/>\n';  
  xml += '  <Borders>\n';  
  xml += '    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '  </Borders>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="dataAlt">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="11"/>\n';  
  xml += '  <Interior ss:Color="#F2F7FC" ss:Pattern="Solid"/>\n';  
  xml += '  <Alignment ss:Vertical="Center" ss:WrapText="1"/>\n';  
  xml += '  <Borders>\n';  
  xml += '    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '  </Borders>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="drugName">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#333333"/>\n';  
  xml += '  <Alignment ss:Vertical="Center"/>\n';  
  xml += '  <Borders>\n';  
  xml += '    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '  </Borders>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="drugNameAlt">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#333333"/>\n';  
  xml += '  <Interior ss:Color="#F2F7FC" ss:Pattern="Solid"/>\n';  
  xml += '  <Alignment ss:Vertical="Center"/>\n';  
  xml += '  <Borders>\n';  
  xml += '    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '  </Borders>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="infoLabel">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#555555"/>\n';  
  xml += '  <Alignment ss:Vertical="Center"/>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="infoValue">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="11" ss:Color="#333333"/>\n';  
  xml += '  <Alignment ss:Vertical="Center"/>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="countNum">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="11"/>\n';  
  xml += '  <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>\n';  
  xml += '  <Borders>\n';  
  xml += '    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E0E0E0"/>\n';  
  xml += '  </Borders>\n';  
  xml += '</Style>\n';

  xml += '<Style ss:ID="specGroup">\n';  
  xml += '  <Font ss:FontName="Calibri" ss:Size="12" ss:Bold="1" ss:Color="#FFFFFF"/>\n';  
  xml += '  <Interior ss:Color="#28A745" ss:Pattern="Solid"/>\n';  
  xml += '  <Alignment ss:Vertical="Center"/>\n';  
  xml += '</Style>\n';

  xml += '</Styles>\n';

  // SHEET 1: SUMMARY  
  xml += '<Worksheet ss:Name="Summary">\n';  
  xml += '<Table ss:DefaultRowHeight="20">\n';  
  xml += '<Column ss:Width="200"/>\n';  
  xml += '<Column ss:Width="300"/>\n';

  xml += '<Row ss:Height="40">\n';  
  xml += '  <Cell ss:StyleID="title" ss:MergeAcross="1">';  
  xml += '<Data ss:Type="String">FDA Drug Approval Report</Data></Cell>\n';  
  xml += '</Row>\n';

  xml += '<Row ss:Height="25">\n';  
  xml += '  <Cell ss:StyleID="subtitle" ss:MergeAcross="1">';  
  xml += '<Data ss:Type="String">Northwell Health - Business Operations</Data></Cell>\n';  
  xml += '</Row>\n';

  xml += '<Row><Cell><Data ss:Type="String"></Data></Cell></Row>\n';

  xml += '<Row>\n';  
  xml += '  <Cell ss:StyleID="infoLabel"><Data ss:Type="String">Report Generated:</Data></Cell>\n';  
  xml += '  <Cell ss:StyleID="infoValue"><Data ss:Type="String">' +  
    escapeXml(new Date().toLocaleDateString("en-US", {  
      weekday: "long", year: "numeric",  
      month: "long", day: "numeric"  
    })) + '</Data></Cell>\n';  
  xml += '</Row>\n';

  xml += '<Row>\n';  
  xml += '  <Cell ss:StyleID="infoLabel"><Data ss:Type="String">Date Range:</Data></Cell>\n';  
  xml += '  <Cell ss:StyleID="infoValue"><Data ss:Type="String">' +  
    escapeXml(formatDateDisplay(fromDate)) + ' to ' +  
    escapeXml(formatDateDisplay(toDate)) +  
    '</Data></Cell>\n';  
  xml += '</Row>\n';

  xml += '<Row>\n';  
  xml += '  <Cell ss:StyleID="infoLabel"><Data ss:Type="String">Total Approvals:</Data></Cell>\n';  
  xml += '  <Cell ss:StyleID="infoValue"><Data ss:Type="Number">' +  
    approvals.length + '</Data></Cell>\n';  
  xml += '</Row>\n';

  xml += '<Row>\n';  
  xml += '  <Cell ss:StyleID="infoLabel"><Data ss:Type="String">Data Sources:</Data></Cell>\n';  
  xml += '  <Cell ss:StyleID="infoValue"><Data ss:Type="String">OpenFDA API, NIH RxNorm/RxClass API</Data></Cell>\n';  
  xml += '</Row>\n';

  xml += '<Row><Cell><Data ss:Type="String"></Data></Cell></Row>\n';

  xml += '<Row>\n';  
  xml += '  <Cell ss:StyleID="section" ss:MergeAcross="1">';  
  xml += '<Data ss:Type="String">Approvals by Submission Type</Data></Cell>\n';  
  xml += '</Row>\n';

  xml += '<Row>\n';  
  xml += '  <Cell ss:StyleID="header"><Data ss:Type="String">Type</Data></Cell>\n';  
  xml += '  <Cell ss:StyleID="header"><Data ss:Type="String">Count</Data></Cell>\n';  
  xml += '</Row>\n';

  for (var t in typeCounts) {  
    xml += '<Row>\n';  
    xml += '  <Cell ss:StyleID="data"><Data ss:Type="String">' +  
      escapeXml(t) + '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="countNum"><Data ss:Type="Number">' +  
      typeCounts[t] + '</Data></Cell>\n';  
    xml += '</Row>\n';  
  }

  xml += '<Row><Cell><Data ss:Type="String"></Data></Cell></Row>\n';

  xml += '<Row>\n';  
  xml += '  <Cell ss:StyleID="section" ss:MergeAcross="1">';  
  xml += '<Data ss:Type="String">Approvals by Northwell Specialty</Data></Cell>\n';  
  xml += '</Row>\n';

  xml += '<Row>\n';  
  xml += '  <Cell ss:StyleID="header"><Data ss:Type="String">Northwell Specialty</Data></Cell>\n';  
  xml += '  <Cell ss:StyleID="header"><Data ss:Type="String">Count</Data></Cell>\n';  
  xml += '</Row>\n';

  for (var s = 0; s < specKeys.length; s++) {  
    xml += '<Row>\n';  
    xml += '  <Cell ss:StyleID="data"><Data ss:Type="String">' +  
      escapeXml(specKeys[s]) + '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="countNum"><Data ss:Type="Number">' +  
      specCounts[specKeys[s]] + '</Data></Cell>\n';  
    xml += '</Row>\n';  
  }

  xml += '<Row><Cell><Data ss:Type="String"></Data></Cell></Row>\n';

  xml += '<Row>\n';  
  xml += '  <Cell ss:StyleID="section" ss:MergeAcross="1">';  
  xml += '<Data ss:Type="String">Top Sponsors</Data></Cell>\n';  
  xml += '</Row>\n';

  xml += '<Row>\n';  
  xml += '  <Cell ss:StyleID="header"><Data ss:Type="String">Sponsor</Data></Cell>\n';  
  xml += '  <Cell ss:StyleID="header"><Data ss:Type="String">Count</Data></Cell>\n';  
  xml += '</Row>\n';

  var maxSponsors = Math.min(sponsorKeys.length, 10);  
  for (var sp = 0; sp < maxSponsors; sp++) {  
    xml += '<Row>\n';  
    xml += '  <Cell ss:StyleID="data"><Data ss:Type="String">' +  
      escapeXml(sponsorKeys[sp]) + '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="countNum"><Data ss:Type="Number">' +  
      sponsorCounts[sponsorKeys[sp]] + '</Data></Cell>\n';  
    xml += '</Row>\n';  
  }

  xml += '</Table>\n</Worksheet>\n';

  // SHEET 2: ALL APPROVALS  
  xml += '<Worksheet ss:Name="All Approvals">\n';  
  xml += '<Table ss:DefaultRowHeight="22">\n';  
  xml += '<Column ss:Width="30"/>\n';  
  xml += '<Column ss:Width="150"/>\n';  
  xml += '<Column ss:Width="180"/>\n';  
  xml += '<Column ss:Width="130"/>\n';  
  xml += '<Column ss:Width="90"/>\n';  
  xml += '<Column ss:Width="200"/>\n';  
  xml += '<Column ss:Width="170"/>\n';  
  xml += '<Column ss:Width="110"/>\n';  
  xml += '<Column ss:Width="120"/>\n';  
  xml += '<Column ss:Width="80"/>\n';  
  xml += '<Column ss:Width="250"/>\n';  
  xml += '<Column ss:Width="400"/>\n';

  xml += '<Row ss:Height="35">\n';  
  xml += '  <Cell ss:StyleID="title" ss:MergeAcross="11">';  
  xml += '<Data ss:Type="String">FDA Drug Approvals - ' +  
    escapeXml(formatDateDisplay(fromDate)) + ' to ' +  
    escapeXml(formatDateDisplay(toDate)) +  
    '</Data></Cell>\n';  
  xml += '</Row>\n';

  xml += '<Row ss:Height="30">\n';  
  var headers = ["#", "Drug Name", "Generic Name",  
    "Northwell Specialty", "Approval Date", "Submission Type",  
    "Sponsor", "Application #", "Dosage Form",  
    "Route", "Active Ingredients",  
    "Indication / Use"];  
  for (var h = 0; h < headers.length; h++) {  
    xml += '  <Cell ss:StyleID="header">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(headers[h]) +  
      '</Data></Cell>\n';  
  }  
  xml += '</Row>\n';

  for (var d = 0; d < approvals.length; d++) {  
    var app = approvals[d];  
    var isAlt = d % 2 === 1;  
    var rowStyle = isAlt ? "dataAlt" : "data";  
    var nameStyle = isAlt ? "drugNameAlt" : "drugName";

    xml += '<Row>\n';  
    xml += '  <Cell ss:StyleID="' + rowStyle + '">';  
    xml += '<Data ss:Type="Number">' +  
      (d + 1) + '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="' + nameStyle + '">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(app.drug_name) +  
      '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="' + rowStyle + '">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(app.generic_name) +  
      '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="' + rowStyle + '">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(app.specialty) +  
      '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="' + rowStyle + '">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(app.approval_date) +  
      '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="' + rowStyle + '">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(app.submission_type) +  
      '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="' + rowStyle + '">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(app.sponsor) +  
      '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="' + rowStyle + '">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(app.application_number) +  
      '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="' + rowStyle + '">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(app.dosage_form) +  
      '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="' + rowStyle + '">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(app.route) +  
      '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="' + rowStyle + '">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(app.active_ingredients) +  
      '</Data></Cell>\n';  
    xml += '  <Cell ss:StyleID="' + rowStyle + '">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(app.indication) +  
      '</Data></Cell>\n';  
    xml += '</Row>\n';  
  }

  xml += '</Table>\n</Worksheet>\n';

  // SHEET 3: BY SPECIALTY  
  xml += '<Worksheet ss:Name="By Specialty">\n';  
  xml += '<Table ss:DefaultRowHeight="22">\n';  
  xml += '<Column ss:Width="150"/>\n';  
  xml += '<Column ss:Width="180"/>\n';  
  xml += '<Column ss:Width="90"/>\n';  
  xml += '<Column ss:Width="200"/>\n';  
  xml += '<Column ss:Width="170"/>\n';  
  xml += '<Column ss:Width="400"/>\n';

  xml += '<Row ss:Height="35">\n';  
  xml += '  <Cell ss:StyleID="title" ss:MergeAcross="5">';  
  xml += '<Data ss:Type="String">Approvals Grouped by Northwell Specialty</Data></Cell>\n';  
  xml += '</Row>\n';

  for (var sk = 0; sk < specKeys.length; sk++) {  
    var specName = specKeys[sk];

    xml += '<Row ss:Height="28">\n';  
    xml += '  <Cell ss:StyleID="specGroup" ss:MergeAcross="5">';  
    xml += '<Data ss:Type="String">' +  
      escapeXml(specName) + ' (' +  
      specCounts[specName] + ')</Data></Cell>\n';  
    xml += '</Row>\n';

    xml += '<Row>\n';  
    var specHeaders = [  
      "Drug Name", "Generic Name", "Approval Date",  
      "Submission Type", "Sponsor", "Indication"  
    ];  
    for (var sh = 0; sh < specHeaders.length; sh++) {  
      xml += '  <Cell ss:StyleID="header">';  
      xml += '<Data ss:Type="String">' +  
        escapeXml(specHeaders[sh]) +  
        '</Data></Cell>\n';  
    }  
    xml += '</Row>\n';

    var rowCount = 0;  
    for (var sd = 0; sd < approvals.length; sd++) {  
      if (approvals[sd].specialty === specName) {  
        var isAlt2 = rowCount % 2 === 1;  
        var rs = isAlt2 ? "dataAlt" : "data";  
        var ns = isAlt2 ? "drugNameAlt" : "drugName";

        xml += '<Row>\n';  
        xml += '  <Cell ss:StyleID="' + ns + '">';  
        xml += '<Data ss:Type="String">' +  
          escapeXml(approvals[sd].drug_name) +  
          '</Data></Cell>\n';  
        xml += '  <Cell ss:StyleID="' + rs + '">';  
        xml += '<Data ss:Type="String">' +  
          escapeXml(approvals[sd].generic_name) +  
          '</Data></Cell>\n';  
        xml += '  <Cell ss:StyleID="' + rs + '">';  
        xml += '<Data ss:Type="String">' +  
          escapeXml(approvals[sd].approval_date) +  
          '</Data></Cell>\n';  
        xml += '  <Cell ss:StyleID="' + rs + '">';  
        xml += '<Data ss:Type="String">' +  
          escapeXml(approvals[sd].submission_type) +  
          '</Data></Cell>\n';  
        xml += '  <Cell ss:StyleID="' + rs + '">';  
        xml += '<Data ss:Type="String">' +  
          escapeXml(approvals[sd].sponsor) +  
          '</Data></Cell>\n';  
        xml += '  <Cell ss:StyleID="' + rs + '">';  
        xml += '<Data ss:Type="String">' +  
          escapeXml(approvals[sd].indication) +  
          '</Data></Cell>\n';  
        xml += '</Row>\n';  
        rowCount++;  
      }  
    }

    xml += '<Row><Cell><Data ss:Type="String"></Data></Cell></Row>\n';  
  }

  xml += '</Table>\n</Worksheet>\n';

  xml += '</Workbook>';

  var blob = new Blob([xml], {  
    type: "application/vnd.ms-excel"  
  });  
  var url = URL.createObjectURL(blob);  
  var link = document.createElement("a");  
  link.href = url;  
  link.download =  
    "FDA_Drug_Approval_Report_" +  
    fromDate + "_to_" + toDate + ".xls";  
  document.body.appendChild(link);  
  link.click();  
  document.body.removeChild(link);  
  URL.revokeObjectURL(url);  
}  
