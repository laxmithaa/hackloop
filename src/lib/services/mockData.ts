/**
 * src/lib/services/mockData.ts
 *
 * Fictional demonstration data for Healthcare Bill Navigator.
 * All records are fictional and clearly marked for user awareness.
 */

import type { HospitalBill, SupportTicket, BillExplanation, Lang } from "../types/billing";

export const DEMO_NOTICE_TEXT = "DEMO — Fictional sample information. Not a real hospital bill.";

// Standard Verified Hospital Bill
export const MOCK_VERIFIED_BILL: HospitalBill = {
  hospitalName: "Sunrise Community Hospital",
  billNumber: "BILL-2026-001",
  patientName: "Ramesh Sharma (Demo)",
  totalAmountInr: 3100,
  insuranceCoveredInr: 1800,
  paidAmountInr: 500,
  patientPayableInr: 800,
  admissionDate: "2026-10-22",
  dischargeDate: "2026-10-24",
  billDate: "2026-10-24",
  dueDate: "2026-11-05",
  state: "verified",
  isDemo: true,
  items: [
    {
      id: "item-1",
      chargeLabel: "General Consultation Fee",
      amountInr: "800",
      explanation: "A standard charge for your examination, vital checks, and medical advice by the attending general physician.",
      simpleExplanation: "Money paid for talking with and getting checked by the doctor.",
      category: "Doctor Services",
      confident: true,
    },
    {
      id: "item-2",
      chargeLabel: "Complete Blood Count (CBC)",
      amountInr: "450",
      explanation: "A routine diagnostic blood test evaluating red cells, white cells, and platelets to detect infection or anemia.",
      simpleExplanation: "A standard blood test to check if you have an infection or weakness.",
      category: "Laboratory",
      confident: true,
    },
    {
      id: "item-3",
      chargeLabel: "Chest X-Ray (PA View)",
      amountInr: "1200",
      explanation: "A standard radiologic scan of your chest to assess lung clarity and heart outline.",
      simpleExplanation: "An image scan taken of your chest to make sure your lungs are clear.",
      category: "Radiology",
      confident: true,
    },
    {
      id: "item-4",
      chargeLabel: "Pharmacy - Antibiotics & Analgesics",
      amountInr: "650",
      explanation: "Doctor-prescribed oral medications dispensed during hospital stay for pain relief and preventing bacterial infection.",
      simpleExplanation: "Medicines given to you for fever, pain relief, and fighting germs.",
      category: "Medications",
      confident: true,
    },
  ],
};

// Discrepancy Bill
export const MOCK_DISCREPANCY_BILL: HospitalBill = {
  hospitalName: "City General Hospital",
  billNumber: "DISC-2026-902",
  patientName: "Ananya Patel (Demo)",
  totalAmountInr: 5200,
  insuranceCoveredInr: 2500,
  paidAmountInr: 1000,
  patientPayableInr: 2200, // Notice 5200 - 2500 - 1000 = 1700, discrepancy of 500
  admissionDate: "2026-10-18",
  dischargeDate: "2026-10-20",
  billDate: "2026-10-20",
  dueDate: "2026-11-01",
  state: "discrepancy",
  discrepancyNotice: "Calculated patient payable balance (₹ 1,700) does not match the printed summary amount (₹ 2,200). A difference of ₹ 500 requires billing desk clarification.",
  isDemo: true,
  items: [
    {
      id: "item-d1",
      chargeLabel: "Emergency Room Triage & Assessment",
      amountInr: "1500",
      explanation: "Initial assessment and stabilization upon arrival at the emergency wing.",
      simpleExplanation: "Emergency doctor fee when you first entered the hospital.",
      category: "Emergency",
      confident: true,
    },
    {
      id: "item-d2",
      chargeLabel: "ECG (Electrocardiogram)",
      amountInr: "700",
      explanation: "Diagnostic recording of heart electrical activity.",
      simpleExplanation: "Heart rhythm recording graph.",
      category: "Diagnostics",
      confident: true,
    },
    {
      id: "item-d3",
      chargeLabel: "Observation Bed (12 Hours)",
      amountInr: "3000",
      explanation: "Daycare monitoring bed charges including nursing surveillance.",
      simpleExplanation: "Charge for resting in the hospital bed while staff watched your recovery.",
      category: "Room & Nursing",
      confident: true,
    },
  ],
};

// Incomplete Information Bill
export const MOCK_INCOMPLETE_BILL: HospitalBill = {
  hospitalName: "Apex Memorial Hospital",
  billNumber: "INC-2026-104",
  patientName: "Patient Record Incomplete",
  totalAmountInr: 1850,
  insuranceCoveredInr: 0,
  paidAmountInr: 0,
  patientPayableInr: 1850,
  admissionDate: "2026-10-15",
  dischargeDate: "2026-10-15",
  billDate: "2026-10-15",
  dueDate: "2026-10-30",
  state: "incomplete",
  discrepancyNotice: "Insurance policy identification and itemized pharmacy breakdown were not transmitted by the provider.",
  isDemo: true,
  items: [
    {
      id: "item-i1",
      chargeLabel: "Outpatient Surgical Dressing",
      amountInr: "1850",
      explanation: "Wound care and sterile dressing change.",
      simpleExplanation: "Cleaning and bandaging your wound.",
      category: "Procedure",
      confident: false,
    },
  ],
};

export function getMockBill(billNumber: string): HospitalBill | null {
  const clean = billNumber.trim().toUpperCase();
  if (clean === "BILL-2026-001" || clean === "INV-2026-0042" || clean === "2026001") {
    return MOCK_VERIFIED_BILL;
  }
  if (clean === "DISC-2026-902" || clean === "DISC902") {
    return MOCK_DISCREPANCY_BILL;
  }
  if (clean === "INC-2026-104" || clean === "INC104") {
    return MOCK_INCOMPLETE_BILL;
  }
  if (clean.includes("UNREG") || clean === "UNREG-770") {
    return null; // Signals unregistered hospital
  }
  // Default to standard verified bill for easy testing with any input
  if (clean.length > 0 && !clean.includes("NOTFOUND")) {
    return {
      ...MOCK_VERIFIED_BILL,
      billNumber: clean,
    };
  }
  return null;
}

export function getMockExplanation(bill: HospitalBill, lang: Lang): BillExplanation {
  if (lang === "hi") {
    return {
      heading: "अपना अस्पताल बिल समझें",
      summaryText: `यह बिल ${bill.hospitalName} द्वारा जारी किया गया है। कुल बिल राशि ₹ ${bill.totalAmountInr.toLocaleString("en-IN")} है। इसमें से बीमा द्वारा ₹ ${bill.insuranceCoveredInr.toLocaleString("en-IN")} और पूर्व भुगतान द्वारा ₹ ${bill.paidAmountInr.toLocaleString("en-IN")} घटाने के बाद, आपको केवल ₹ ${bill.patientPayableInr.toLocaleString("en-IN")} का भुगतान करना है।`,
      simplifiedSummaryText: `अस्पताल का कुल खर्चा ₹ ${bill.totalAmountInr.toLocaleString("en-IN")} बना था। बीमा कंपनी ने ₹ ${bill.insuranceCoveredInr.toLocaleString("en-IN")} दे दिए हैं। आपने पहले ₹ ${bill.paidAmountInr.toLocaleString("en-IN")} दिए थे। अब आपकी जेब से केवल ₹ ${bill.patientPayableInr.toLocaleString("en-IN")} देने बाकी हैं।`,
      breakdownSections: bill.items.map((it) => ({
        title: it.chargeLabel,
        description: it.explanation,
        simpleDescription: it.simpleExplanation || it.explanation,
      })),
      sourceLabel: "Generated from hospital-provided bill information.",
      isAiGenerated: true,
      disclaimer: "यह स्पष्टीकरण केवल सामान्य जानकारी के लिए है और यह अस्पताल का आधिकारिक बिल या पेशेवर चिकित्सा या कानूनी सलाह नहीं है।",
    };
  }

  if (lang === "kn") {
    return {
      heading: "ನಿಮ್ಮ ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ",
      summaryText: `ಈ ಬಿಲ್ ಅನ್ನು ${bill.hospitalName} ನೀಡಿದೆ. ಒಟ್ಟು ಮೊತ್ತ ₹ ${bill.totalAmountInr.toLocaleString("en-IN")}. ವಿಮೆಯಿಂದ ₹ ${bill.insuranceCoveredInr.toLocaleString("en-IN")} ಮತ್ತು ಮುಂಗಡ ₹ ${bill.paidAmountInr.toLocaleString("en-IN")} ಕಳೆದು, ನೀವು ಪಾವತಿಸಬೇಕಾದ ನಿವ್ವಳ ಬಾಕಿ ₹ ${bill.patientPayableInr.toLocaleString("en-IN")}.`,
      simplifiedSummaryText: `ಒಟ್ಟು ಬಿಲ್ ₹ ${bill.totalAmountInr.toLocaleString("en-IN")} ಆಗಿದೆ. ವಿಮೆ ಕಂಪನಿಯು ₹ ${bill.insuranceCoveredInr.toLocaleString("en-IN")} ಭರಿಸಿದೆ. ನೀವು ಈಗಾಗಲೇ ₹ ${bill.paidAmountInr.toLocaleString("en-IN")} ಕೊಟ್ಟಿದ್ದೀರಿ. ನೀವು ಈಗ ಕೊಡಬೇಕಾದ ಉಳಿದ ಹಣ ₹ ${bill.patientPayableInr.toLocaleString("en-IN")}.`,
      breakdownSections: bill.items.map((it) => ({
        title: it.chargeLabel,
        description: it.explanation,
        simpleDescription: it.simpleExplanation || it.explanation,
      })),
      sourceLabel: "Generated from hospital-provided bill information.",
      isAiGenerated: true,
      disclaimer: "ಈ ವಿವರಣೆಯು ಕೇವಲ ಮಾಹಿತಿಗಾಗಿ ಮಾತ್ರ ಮತ್ತು ಇದು ಆಸ್ಪತ್ರೆಯ ಅಧಿಕೃತ ಬಿಲ್ ಅಥವಾ ವೃತ್ತಿಪರ ವೈದ್ಯಕೀಯ/ಕಾನೂನು ಸಲಹೆಯಲ್ಲ.",
    };
  }

  // English
  return {
    heading: "Understand Your Bill",
    summaryText: `This statement from ${bill.hospitalName} reflects a total charge of ₹ ${bill.totalAmountInr.toLocaleString("en-IN")}. After applying approved health insurance coverage of ₹ ${bill.insuranceCoveredInr.toLocaleString("en-IN")} and prior deposits of ₹ ${bill.paidAmountInr.toLocaleString("en-IN")}, the remaining balance payable by you is ₹ ${bill.patientPayableInr.toLocaleString("en-IN")}.`,
    simplifiedSummaryText: `Your total hospital bill was ₹ ${bill.totalAmountInr.toLocaleString("en-IN")}. Your health insurance paid ₹ ${bill.insuranceCoveredInr.toLocaleString("en-IN")}. You already paid ₹ ${bill.paidAmountInr.toLocaleString("en-IN")}. That leaves ₹ ${bill.patientPayableInr.toLocaleString("en-IN")} left for you to pay.`,
    breakdownSections: bill.items.map((it) => ({
      title: it.chargeLabel,
      description: it.explanation,
      simpleDescription: it.simpleExplanation || it.explanation,
    })),
    sourceLabel: "Generated from hospital-provided bill information.",
    isAiGenerated: true,
    disclaimer: "This explanation is provided for general informational purposes only and does not replace the hospital's official bill or professional medical/legal advice.",
  };
}

// Initial Support Tickets for Worker Dashboard
export const INITIAL_SUPPORT_TICKETS: SupportTicket[] = [
  {
    ticketId: "TCK-8492",
    referenceId: "REF-2026-8812",
    patientName: "Ramesh Sharma",
    contactNumber: "+91 98765 43210",
    hospitalId: "HOSP-SUNRISE-01",
    hospitalName: "Sunrise Community Hospital",
    billNumber: "BILL-2026-001",
    patientNote: "Patient seeks clarification on whether the Chest X-Ray charge (₹ 1,200) qualifies for Ayushman Bharat PM-JAY co-pay waiver.",
    preferredLanguage: "hi",
    preferredCallbackTime: "morning",
    consentVerified: true,
    status: "New",
    createdAt: "2026-10-27 10:15 AM",
    staffNotes: ["Queued for Morning Outreach Nurse"],
    isDemo: true,
  },
  {
    ticketId: "TCK-7120",
    referenceId: "REF-2026-6419",
    patientName: "Meenakshi Sundaram",
    contactNumber: "+91 94432 10987",
    hospitalId: "HOSP-SUNRISE-01",
    hospitalName: "Sunrise Community Hospital",
    billNumber: "INV-2026-0038",
    patientNote: "Needs explanation of why generic medicine alternatives were not used in the final pharmacy calculation.",
    preferredLanguage: "kn",
    preferredCallbackTime: "afternoon",
    consentVerified: true,
    status: "Callback scheduled",
    createdAt: "2026-10-26 03:40 PM",
    staffNotes: ["Scheduled callback call for 2:30 PM with pharmacy supervisor"],
    isDemo: true,
  },
  {
    ticketId: "TCK-9031",
    referenceId: "REF-2026-5501",
    patientName: "Ananya Patel",
    contactNumber: "+91 98210 54321",
    hospitalId: "HOSP-CITY-001",
    hospitalName: "City General Hospital",
    billNumber: "DISC-2026-902",
    patientNote: "Patient noticed ₹ 500 discrepancy between line item tally and summary total.",
    preferredLanguage: "en",
    preferredCallbackTime: "now",
    consentVerified: true,
    status: "Contacted",
    createdAt: "2026-10-27 11:00 AM",
    staffNotes: ["Spoke with patient; submitted billing correction form to accounts desk"],
    isDemo: true,
  },
  {
    ticketId: "TCK-4811",
    referenceId: "REF-2026-1190",
    patientName: "Basavaraj Patil",
    contactNumber: "+91 99001 22334",
    hospitalId: "HOSP-SUNRISE-01",
    hospitalName: "Sunrise Community Hospital",
    billNumber: "BILL-2026-001",
    patientNote: "Requested assistance setting up a 3-month installment plan for patient payable share.",
    preferredLanguage: "kn",
    preferredCallbackTime: "evening",
    consentVerified: true,
    status: "Resolved",
    createdAt: "2026-10-25 04:15 PM",
    staffNotes: ["Installment schedule approved and sent via SMS receipt."],
    isDemo: true,
  },
];
