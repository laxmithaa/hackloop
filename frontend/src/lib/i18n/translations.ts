/**
 * src/lib/i18n/translations.ts
 *
 * Centralized Multilingual Translation System for Healthcare Bill Navigator.
 * Fully supports English (en), Hindi (hi), and Kannada (kn).
 * All UI labels, explanations, errors, and accessibility announcements are localized here.
 */

export type Lang = "en" | "hi" | "kn";

export interface TranslationDictionary {
  common: {
    appName: string;
    appTagline: string;
    demoBanner: string;
    backBtn: string;
    continueBtn: string;
    retryBtn: string;
    cancelBtn: string;
    submitBtn: string;
    loading: string;
    seekHumanHelp: string;
    privacyNotice: string;
    officialNotice: string;
    textSizeToggle: string;
    requiredField: string;
    inrSymbol: string;
  };
  nav: {
    brand: string;
    tagline: string;
    welcome: string;
    patientFlow: string;
    caregiver: string;
    support: string;
    langSelect: string;
    seekHelpBtn: string;
  };
  welcome: {
    title: string;
    subtitle: string;
    primaryCta: string;
    secondaryCta: string;
    feature1Title: string;
    feature1Desc: string;
    feature2Title: string;
    feature2Desc: string;
    feature3Title: string;
    feature3Desc: string;
    disclaimer: string;
  };
  consent: {
    title: string;
    subtitle: string;
    whatUsedTitle: string;
    whatUsedText: string;
    whyNeededTitle: string;
    whyNeededText: string;
    howUsedTitle: string;
    howUsedText: string;
    agreeMeaningTitle: string;
    agreeMeaningText: string;
    declineTitle: string;
    declineText: string;
    agreeBtn: string;
    declineBtn: string;
    declinedNoticeTitle: string;
    declinedNoticeMsg: string;
    reconsiderBtn: string;
  };
  identify: {
    title: string;
    subtitle: string;
    tabUpload: string;
    tabNumber: string;
    uploadInstructions: string;
    uploadDragDrop: string;
    uploadBrowse: string;
    uploadCamera: string;
    uploadLimits: string;
    uploadSelected: string;
    uploadReplace: string;
    uploadRemove: string;
    uploadSubmit: string;
    uploadingProgress: string;
    numberInputLabel: string;
    numberPlaceholder: string;
    numberSubmit: string;
    numberInstructions: string;
    lowBandwidthBadge: string;
    presetExamplesLabel: string;
    states: {
      identifiedTitle: string;
      identifiedDesc: string;
      proceedBtn: string;
      needsVerificationTitle: string;
      needsVerificationDesc: string;
      verifyBtn: string;
      notFoundTitle: string;
      notFoundDesc: string;
      unregisteredTitle: string;
      unregisteredDesc: string;
      unreadableTitle: string;
      unreadableDesc: string;
      incompleteTitle: string;
      incompleteDesc: string;
      temporaryFailureTitle: string;
      temporaryFailureDesc: string;
    };
  };
  verify: {
    title: string;
    subtitle: string;
    inputLabel: string;
    placeholder: string;
    helperText: string;
    submitBtn: string;
    verifying: string;
    attemptsRemaining: string;
    invalidError: string;
    expiredError: string;
    lockedError: string;
    nextStepHelp: string;
    demoHint: string;
  };
  bill: {
    title: string;
    subtitle: string;
    hospitalLabel: string;
    billNumberLabel: string;
    patientNameLabel: string;
    admissionLabel: string;
    dischargeLabel: string;
    billDateLabel: string;
    dueDateLabel: string;
    totalAmountLabel: string;
    insuranceLabel: string;
    paidLabel: string;
    patientPayableLabel: string;
    verifiedBadge: string;
    discrepancyBadge: string;
    incompleteBadge: string;
    discrepancyAlertTitle: string;
    lineItemsTitle: string;
    lineItemsSubtitle: string;
    chargeColumn: string;
    amountColumn: string;
    plainMeaningColumn: string;
    explainCtaBtn: string;
    askQuestionBtn: string;
    needHelpBtn: string;
  };
  explanation: {
    title: string;
    subtitle: string;
    listenBtn: string;
    pauseBtn: string;
    resumeBtn: string;
    stopBtn: string;
    audioPlaying: string;
    audioUnavailable: string;
    simplifyToggle: string;
    simplifyActive: string;
    requiredSourceLabel: string; // "Generated from hospital-provided bill information."
    informationalNotice: string;
    aiBadge: string;
    templateBadge: string;
    backToBillBtn: string;
    askFollowUpBtn: string;
    requestSupportBtn: string;
    retryBtn: string;
  };
  questions: {
    title: string;
    subtitle: string;
    inputLabel: string;
    placeholder: string;
    submitBtn: string;
    examplesLabel: string;
    sample1: string;
    sample2: string;
    sample3: string;
    voiceBtnStart: string;
    voiceBtnStop: string;
    voiceListening: string;
    voiceReviewLabel: string;
    voiceEditHint: string;
    voiceConfirmBtn: string;
    voiceUnavailable: string;
    refusalNotice: string;
    emptyHistory: string;
  };
  caregiver: {
    title: string; // "What You Need to Know"
    subtitle: string;
    billSummaryTitle: string;
    financialTermsTitle: string;
    importantDatesTitle: string;
    clarificationQuestionsTitle: string;
    nextStepsTitle: string;
    nextStep1: string;
    nextStep2: string;
    nextStep3: string;
    requestSupportBtn: string;
    returnToPatientBtn: string;
  };
  help: {
    title: string;
    subtitle: string;
    patientNameLabel: string;
    contactLabel: string;
    billNumberLabel: string;
    langPrefLabel: string;
    callbackTimeLabel: string;
    callbackNow: string;
    callbackMorning: string;
    callbackAfternoon: string;
    callbackEvening: string;
    reasonLabel: string;
    reasonPlaceholder: string;
    consentCheckboxLabel: string;
    submitBtn: string;
    submitting: string;
    successTitle: string;
    successReference: string;
    successMessage: string;
    demoNote: string;
    errorTitle: string;
    errorMessage: string;
  };
  supportDashboard: {
    title: string;
    subtitle: string;
    demoBadge: string;
    searchPlaceholder: string;
    filterAll: string;
    filterNew: string;
    filterScheduled: string;
    filterContacted: string;
    filterResolved: string;
    ticketListHeading: string;
    detailsHeading: string;
    noTickets: string;
    statusLabel: string;
    changeStatusBtn: string;
    addNotePlaceholder: string;
    addNoteBtn: string;
    patientContactLabel: string;
    callbackWindowLabel: string;
    preferredLangLabel: string;
  };
}

export const translations: Record<Lang, TranslationDictionary> = {
  // ────────────────────────────────────────────────────────────
  // ENGLISH
  // ────────────────────────────────────────────────────────────
  en: {
    common: {
      appName: "Healthcare Bill Navigator",
      appTagline: "Simple language guidance for your medical bills",
      demoBanner: "DEMO — Fictional sample information. Not a real hospital bill.",
      backBtn: "Back",
      continueBtn: "Continue",
      retryBtn: "Try Again",
      cancelBtn: "Cancel",
      submitBtn: "Submit",
      loading: "Loading…",
      seekHumanHelp: "Need Human Help?",
      privacyNotice: "Your bill information is handled securely and in-memory with zero persistent credential storage.",
      officialNotice: "This application provides educational explanations and does not replace your official hospital bill or medical advice.",
      textSizeToggle: "Text Size",
      requiredField: "This field is required",
      inrSymbol: "₹",
    },
    nav: {
      brand: "Healthcare Bill Navigator",
      tagline: "Your medical bill, clearly explained.",
      welcome: "Home",
      patientFlow: "My Bill",
      caregiver: "Caregiver View",
      support: "Support Staff",
      langSelect: "Language",
      seekHelpBtn: "Get Human Help",
    },
    welcome: {
      title: "Understand Your Hospital Bill in Simple Words.",
      subtitle: "Medical bills can be confusing and stressful. Healthcare Bill Navigator translates medical codes, checks insurance coverage, and explains what you owe in plain language with text-to-speech support.",
      primaryCta: "Understand My Hospital Bill",
      secondaryCta: "Caregiver Summary",
      feature1Title: "Plain Language Explanations",
      feature1Desc: "Every medical test, doctor fee, and medicine charge translated into easy-to-understand words.",
      feature2Title: "Voice Guidance & Multiple Languages",
      feature2Desc: "Listen aloud in English, Hindi, or Kannada. Designed for easy touch interaction and large readable text.",
      feature3Title: "Human Assistance Ready",
      feature3Desc: "Request a callback from a hospital support worker if you find an error or need payment arrangements.",
      disclaimer: "Healthcare Bill Navigator is an informational companion tool. It helps you understand charges but does not replace the hospital's official paper bill or professional medical advice.",
    },
    consent: {
      title: "Your Privacy & Consent",
      subtitle: "Before we view or explain your bill, please review how your information is handled.",
      whatUsedTitle: "1. What information is used",
      whatUsedText: "We temporarily read the hospital name, printed bill number, and itemized charge labels on your bill.",
      whyNeededTitle: "2. Why this information is needed",
      whyNeededText: "To look up the official hospital tariff definitions and translate complex medical jargon into clear words.",
      howUsedTitle: "3. How the application uses it",
      howUsedText: "Information is processed in-memory during your session. Photos or personal access codes are never permanently stored in browser storage.",
      agreeMeaningTitle: "4. What agreeing means",
      agreeMeaningText: "You allow the application to process your bill details to generate plain-language summaries and audio readings.",
      declineTitle: "5. How you can decline or withdraw consent",
      declineText: "You can decline below at any time. If you decline, you can still request direct assistance from a hospital support worker.",
      agreeBtn: "I Agree & Continue",
      declineBtn: "I Decline",
      declinedNoticeTitle: "Consent Declined",
      declinedNoticeMsg: "You have chosen not to proceed with automated bill analysis. You can reconsider anytime or request a hospital support worker to assist you directly over the phone.",
      reconsiderBtn: "Review Consent Again",
    },
    identify: {
      title: "Identify Your Hospital Bill",
      subtitle: "Choose how you want to find your bill. If you have slow internet, entering the bill number is fastest.",
      tabUpload: "Option A: Upload Bill Photo",
      tabNumber: "Option B: Enter Bill Number",
      uploadInstructions: "Take a clear picture or upload a PDF/photo of your hospital bill.",
      uploadDragDrop: "Drag and drop your bill photo here, or",
      uploadBrowse: "Browse Files",
      uploadCamera: "Take Photo with Camera",
      uploadLimits: "Supported files: JPG, PNG, PDF · Up to 10 MB",
      uploadSelected: "Selected file:",
      uploadReplace: "Replace File",
      uploadRemove: "Remove File",
      uploadSubmit: "Scan & Identify Bill",
      uploadingProgress: "Reading document and finding bill details…",
      numberInputLabel: "Hospital Bill Number",
      numberPlaceholder: "e.g. BILL-2026-001 or INV-2026-0042",
      numberSubmit: "Find Bill",
      numberInstructions: "Look for 'Bill No.', 'Invoice #', or 'Receipt No.' printed near the top right of your hospital receipt.",
      lowBandwidthBadge: "Low-Bandwidth Mode · Uses less than 2 KB of data",
      presetExamplesLabel: "Quick test presets:",
      states: {
        identifiedTitle: "Bill Found Successfully",
        identifiedDesc: "We located your official bill record. Please confirm and continue to review the breakdown.",
        proceedBtn: "View Bill Information",
        needsVerificationTitle: "Additional Verification Required",
        needsVerificationDesc: "For your security, this hospital requires entering the printed access code sent via SMS or shown on your discharge paper.",
        verifyBtn: "Enter Access Code",
        notFoundTitle: "Bill Not Found",
        notFoundDesc: "We could not find an active hospital record with that number. Please double-check the digits or upload a photo instead.",
        unregisteredTitle: "Hospital Not Registered",
        unregisteredDesc: "This healthcare facility is not yet connected to the online navigator system. You can request human assistance to review it.",
        unreadableTitle: "Unreadable Bill Photo",
        unreadableDesc: "The image is too blurry or has excessive glare. Please take a clearer photo in good lighting or enter the bill number manually.",
        incompleteTitle: "Incomplete Bill Record",
        incompleteDesc: "Some charges or itemized breakdowns are missing from the provider record. We recommend reviewing with a billing clerk.",
        temporaryFailureTitle: "Temporary Network Issue",
        temporaryFailureDesc: "The connection to the billing gateway timed out. Your internet may be intermittent. Please try again.",
      },
    },
    verify: {
      title: "Enter Access Code",
      subtitle: "A temporary verification code protects your private financial details.",
      inputLabel: "Printed Access Code",
      placeholder: "e.g. HBN-4921",
      helperText: "Check the 6-character code printed at the bottom of your bill receipt or sent to your mobile phone.",
      submitBtn: "Verify Code",
      verifying: "Verifying with hospital records…",
      attemptsRemaining: "attempts remaining before temporary lock.",
      invalidError: "Invalid code. Please check the characters carefully and try again.",
      expiredError: "This access code has expired. Please request a new code from hospital reception.",
      lockedError: "Verification locked due to multiple incorrect attempts. Please seek assistance.",
      nextStepHelp: "Trouble receiving your access code? Request a callback from a hospital support worker.",
      demoHint: "Demo tip: Enter 'HBN-4921' to verify, 'EXPIRED' for expired state, or any other code to test invalid input.",
    },
    bill: {
      title: "Hospital Bill Summary",
      subtitle: "Here are the verified financial charges provided by the hospital billing desk.",
      hospitalLabel: "Hospital / Healthcare Provider",
      billNumberLabel: "Bill Identifier",
      patientNameLabel: "Patient Name",
      admissionLabel: "Admission Date",
      dischargeLabel: "Discharge Date",
      billDateLabel: "Bill Date",
      dueDateLabel: "Payment Due Date",
      totalAmountLabel: "Total Hospital Charges",
      insuranceLabel: "Covered by Insurance / Govt Scheme",
      paidLabel: "Amount Already Deposited",
      patientPayableLabel: "Amount Payable by Patient",
      verifiedBadge: "Verified Official Record",
      discrepancyBadge: "Amount Discrepancy Flagged",
      incompleteBadge: "Incomplete Information",
      discrepancyAlertTitle: "Discrepancy Notice Detected",
      lineItemsTitle: "Itemized Breakdown of Charges",
      lineItemsSubtitle: "Review each individual item billed during your hospital care.",
      chargeColumn: "Service / Procedure",
      amountColumn: "Billed Amount",
      plainMeaningColumn: "Plain Language Meaning",
      explainCtaBtn: "Explain This Bill in Simple Words",
      askQuestionBtn: "Ask Questions",
      needHelpBtn: "Request Human Help",
    },
    explanation: {
      title: "Understand Your Bill",
      subtitle: "Here is your bill explained in clear, everyday language.",
      listenBtn: "Listen Aloud",
      pauseBtn: "Pause Audio",
      resumeBtn: "Resume Audio",
      stopBtn: "Stop Audio",
      audioPlaying: "Playing voice explanation…",
      audioUnavailable: "Browser voice narration is not supported on this device.",
      simplifyToggle: "Simplify Explanation",
      simplifyActive: "Showing shorter, 5th-grade plain-language version",
      requiredSourceLabel: "Generated from hospital-provided bill information.",
      informationalNotice: "This explanation is informational only and does not replace the hospital's official bill or professional medical/financial advice.",
      aiBadge: "AI-Powered Explanation",
      templateBadge: "Verified Clinical Template",
      backToBillBtn: "Return to Bill Summary",
      askFollowUpBtn: "Ask a Follow-Up Question",
      requestSupportBtn: "Talk to Human Support",
      retryBtn: "Retry Explanation",
    },
    questions: {
      title: "Ask Questions About Your Bill",
      subtitle: "Ask about any charge, medical test, or insurance deduction you do not understand.",
      inputLabel: "Type or speak your question",
      placeholder: "e.g. Why was I charged for Chest X-Ray? Or how does Ayushman Bharat apply?",
      submitBtn: "Ask Question",
      examplesLabel: "Common Questions:",
      sample1: "What does General Consultation Fee mean?",
      sample2: "Is CBC blood test a routine charge?",
      sample3: "Can I pay the patient payable amount in installments?",
      voiceBtnStart: "Speak Question",
      voiceBtnStop: "Stop Recording",
      voiceListening: "Listening… Speak now",
      voiceReviewLabel: "Recognized Speech (Review or Edit):",
      voiceEditHint: "You can click and edit any words before submitting.",
      voiceConfirmBtn: "Confirm & Submit Spoken Question",
      voiceUnavailable: "Voice recognition is not supported in this browser. Please type your question.",
      refusalNotice: "Notice: This assistant can only explain billing and financial charges. For medical diagnosis or treatment choices, please consult your doctor.",
      emptyHistory: "No questions asked yet. Choose a question above or type your own.",
    },
    caregiver: {
      title: "What You Need to Know",
      subtitle: "Caregiver & Family Financial Summary. A quick overview to help you support your loved one.",
      billSummaryTitle: "Essential Bill Numbers",
      financialTermsTitle: "Important Terms on This Bill",
      importantDatesTitle: "Deadlines & Critical Dates",
      clarificationQuestionsTitle: "Questions to Ask the Hospital Billing Desk",
      nextStepsTitle: "Suggested Next Steps",
      nextStep1: "Verify if your insurance pre-authorization letter was fully credited to this bill.",
      nextStep2: "Check medicine receipts against the hospital pharmacy itemized charges.",
      nextStep3: "Inquire at the hospital financial counselor desk about payment installment plans if needed.",
      requestSupportBtn: "Request Hospital Worker Callback",
      returnToPatientBtn: "Back to Patient View",
    },
    help: {
      title: "Request Human Assistance",
      subtitle: "If your bill seems incorrect or confusing, an authorized hospital support worker can call you back.",
      patientNameLabel: "Your Name",
      contactLabel: "Contact Phone Number",
      billNumberLabel: "Hospital Bill Number",
      langPrefLabel: "Preferred Language for Callback",
      callbackTimeLabel: "Preferred Callback Time",
      callbackNow: "As soon as possible",
      callbackMorning: "Morning (9:00 AM – 12:00 PM)",
      callbackAfternoon: "Afternoon (12:00 PM – 4:00 PM)",
      callbackEvening: "Evening (4:00 PM – 8:00 PM)",
      reasonLabel: "Reason for Requesting Help",
      reasonPlaceholder: "Please describe what seems unclear (e.g. charge dispute, insurance issue, discount inquiry)…",
      consentCheckboxLabel: "I explicitly consent to sharing this bill reference and contact phone number with an authorized hospital support worker for this callback.",
      submitBtn: "Submit Support Request",
      submitting: "Submitting request…",
      successTitle: "Support Request Received",
      successReference: "Your Case Reference ID:",
      successMessage: "A hospital patient advocate will review your bill details and call you during your selected time window.",
      demoNote: "DEMO NOTICE: This is a demonstration interface. No real phone call will be placed.",
      errorTitle: "Submission Error",
      errorMessage: "Could not submit your request. Please check that all required fields are filled.",
    },
    supportDashboard: {
      title: "Support-Worker Dashboard",
      subtitle: "Authorized Hospital Staff Portal for Resolving Patient Billing Inquiries",
      demoBadge: "Demo Data · Simulated Staff Access",
      searchPlaceholder: "Search by Patient, Bill #, or Reference ID…",
      filterAll: "All Tickets",
      filterNew: "New",
      filterScheduled: "Callback Scheduled",
      filterContacted: "Contacted",
      filterResolved: "Resolved",
      ticketListHeading: "Inbound Patient Inquiries",
      detailsHeading: "Ticket Details & Case Notes",
      noTickets: "No support tickets match the selected filter.",
      statusLabel: "Current Status:",
      changeStatusBtn: "Update Status",
      addNotePlaceholder: "Add internal staff case note…",
      addNoteBtn: "Save Note",
      patientContactLabel: "Phone Number:",
      callbackWindowLabel: "Preferred Time:",
      preferredLangLabel: "Language:",
    },
  },

  // ────────────────────────────────────────────────────────────
  // HINDI
  // ────────────────────────────────────────────────────────────
  hi: {
    common: {
      appName: "Healthcare Bill Navigator",
      appTagline: "आपके अस्पताल बिल का सरल भाषा में मार्गदर्शन",
      demoBanner: "डेमो डेटा — यह एक काल्पनिक नमूना जानकारी है। यह असली अस्पताल बिल नहीं है।",
      backBtn: "वापस जाएं",
      continueBtn: "आगे बढ़ें",
      retryBtn: "पुनः प्रयास करें",
      cancelBtn: "रद्द करें",
      submitBtn: "जमा करें",
      loading: "लोड हो रहा है…",
      seekHumanHelp: "मानवीय सहायता चाहिए?",
      privacyNotice: "आपकी बिल जानकारी सुरक्षित रखी जाती है और कोई भी गुप्त कोड ब्राउज़र में संचित नहीं किया जाता।",
      officialNotice: "यह ऐप केवल समझाने के उद्देश्य से है और अस्पताल के आधिकारिक बिल या डॉक्टरी सलाह का स्थान नहीं लेता।",
      textSizeToggle: "अक्षर आकार",
      requiredField: "यह विवरण भरना आवश्यक है",
      inrSymbol: "₹",
    },
    nav: {
      brand: "Healthcare Bill Navigator",
      tagline: "आपका अस्पताल बिल, स्पष्ट भाषा में।",
      welcome: "मुख्य पृष्ठ",
      patientFlow: "मेरा बिल",
      caregiver: "देखभालकर्ता सारांश",
      support: "सहायक कर्मचारी",
      langSelect: "भाषा",
      seekHelpBtn: "सहायता प्राप्त करें",
    },
    welcome: {
      title: "अपना अस्पताल बिल सरल शब्दों में समझें।",
      subtitle: "अस्पताल के बिल अक्सर उलझन भरे होते हैं। Healthcare Bill Navigator कठिन मेडिकल शब्दों को आसान बनाता है, बीमा राशि समझाता है, और बोलकर सुनाने की सुविधा देता है।",
      primaryCta: "अपना अस्पताल बिल समझें",
      secondaryCta: "देखभालकर्ता सारांश",
      feature1Title: "सरल भाषा में व्याख्या",
      feature1Desc: "हर टेस्ट, डॉक्टर की फ़ीस और दवाई के शुल्क का सरल हिंदी में अर्थ समझें।",
      feature2Title: "बोलकर सुनाने की सुविधा (ऑडियो)",
      feature2Desc: "हिंदी, कन्नड़ या अंग्रेज़ी में पूरा बिल सुनें। बड़े अक्षरों और आसान बटनों के साथ बनाया गया।",
      feature3Title: "मानवीय सहायता उपलब्ध",
      feature3Desc: "यदि बिल में कोई गलती लगे, तो अस्पताल के सहायक कर्मचारी से कॉल बैक का अनुरोध करें।",
      disclaimer: "यह एप्लिकेशन केवल समझने में मदद करता है। यह अस्पताल के आधिकारिक बिल या कानूनी/चिकित्सकीय सलाह का विकल्प नहीं है।",
    },
    consent: {
      title: "आपकी गोपनीयता और सहमति",
      subtitle: "बिल देखने से पहले, कृपया जानें कि आपकी जानकारी का उपयोग कैसे किया जाता है।",
      whatUsedTitle: "1. कौन सी जानकारी ली जाती है",
      whatUsedText: "हम केवल अस्पताल का नाम, बिल नंबर और बिल पर लिखे शुल्कों के नाम पढ़ते हैं।",
      whyNeededTitle: "2. यह जानकारी क्यों आवश्यक है",
      whyNeededText: "अस्पताल के मेडिकल शब्दों को आम बोलचाल की हिंदी में बदलने के लिए।",
      howUsedTitle: "3. इसका उपयोग कैसे होता है",
      howUsedText: "यह जानकारी केवल आपके सत्र के दौरान उपयोग होती है। आपकी फ़ोटो या पासवर्ड कभी स्थायी रूप से नहीं रखे जाते।",
      agreeMeaningTitle: "4. सहमति देने का क्या अर्थ है",
      agreeMeaningText: "आप ऐप को अपने बिल का विश्लेषण करने और बोलकर सुनाने की अनुमति देते हैं।",
      declineTitle: "5. अस्वीकार कैसे करें",
      declineText: "आप किसी भी समय अस्वीकार कर सकते हैं। अस्वीकार करने पर भी आप सीधे अस्पताल कर्मचारी से बात कर सकते हैं।",
      agreeBtn: "मैं सहमत हूँ, आगे बढ़ें",
      declineBtn: "मैं अस्वीकार करता हूँ",
      declinedNoticeTitle: "सहमति अस्वीकार की गई",
      declinedNoticeMsg: "आपने स्वचालित बिल विश्लेषण के लिए सहमति नहीं दी है। आप कभी भी फिर से विचार कर सकते हैं या अस्पताल कर्मचारी से फ़ोन पर बात कर सकते हैं।",
      reconsiderBtn: "सहमति दोबारा देखें",
    },
    identify: {
      title: "अपना अस्पताल बिल पहचानें",
      subtitle: "बिल खोजने का तरीका चुनें। यदि इंटरनेट धीमा है, तो बिल नंबर दर्ज करना सबसे तेज़ है।",
      tabUpload: "विकल्प A: बिल का फ़ोटो अपलोड करें",
      tabNumber: "विकल्प B: बिल नंबर दर्ज करें",
      uploadInstructions: "अपने अस्पताल बिल की साफ़ फ़ोटो या PDF अपलोड करें।",
      uploadDragDrop: "बिल की फ़ोटो यहाँ खींचें और छोड़ें, या",
      uploadBrowse: "फ़ाइल चुनें",
      uploadCamera: "कैमरे से फ़ोटो लें",
      uploadLimits: "स्वीकृत फ़ाइलें: JPG, PNG, PDF · अधिकतम 10 MB",
      uploadSelected: "चुनी गई फ़ाइल:",
      uploadReplace: "फ़ाइल बदलें",
      uploadRemove: "फ़ाइल हटाएं",
      uploadSubmit: "बिल स्कैन और पहचानें",
      uploadingProgress: "दस्तावेज़ पढ़ा जा रहा है और विवरण खोजा जा रहा है…",
      numberInputLabel: "अस्पताल बिल नंबर",
      numberPlaceholder: "उदा. BILL-2026-001 या INV-2026-0042",
      numberSubmit: "बिल खोजें",
      numberInstructions: "अपनी रसीद पर 'Bill No.' या 'Invoice #' देखें।",
      lowBandwidthBadge: "कम इंटरनेट मोड · 2 KB से कम डेटा का उपयोग",
      presetExamplesLabel: "परीक्षण के लिए उदाहरण:",
      states: {
        identifiedTitle: "बिल सफलतापूर्वक मिल गया",
        identifiedDesc: "हमें आपका आधिकारिक बिल रिकॉर्ड मिल गया है। कृपया विवरण देखें।",
        proceedBtn: "बिल की जानकारी देखें",
        needsVerificationTitle: "अतिरिक्त सत्यापन आवश्यक",
        needsVerificationDesc: "आपकी सुरक्षा के लिए, इस अस्पताल के लिए SMS पर भेजा गया कोड दर्ज करना आवश्यक है।",
        verifyBtn: "सत्यापन कोड दर्ज करें",
        notFoundTitle: "बिल नहीं मिला",
        notFoundDesc: "इस नंबर का कोई सक्रिय रिकॉर्ड नहीं मिला। कृपया नंबर दोबारा जांचें या फ़ोटो अपलोड करें।",
        unregisteredTitle: "अस्पताल पंजीकृत नहीं है",
        unregisteredDesc: "यह अस्पताल अभी नेविगेटर प्रणाली से नहीं जुड़ा है। आप मानवीय सहायता ले सकते हैं।",
        unreadableTitle: "अस्पष्ट बिल फ़ोटो",
        unreadableDesc: "फ़ोटो धुंधली है। कृपया अच्छी रोशनी में साफ़ फ़ोटो लें या बिल नंबर दर्ज करें।",
        incompleteTitle: "अधूरा बिल रिकॉर्ड",
        incompleteDesc: "अस्पताल से कुछ मदों का ब्यौरा अधूरा है। बिलिंग काउंटर से संपर्क करने की सलाह दी जाती है।",
        temporaryFailureTitle: "अस्थायी नेटवर्क समस्या",
        temporaryFailureDesc: "अस्पताल सर्वर से संपर्क नहीं हो सका। कृपया थोड़ी देर बाद पुनः प्रयास करें।",
      },
    },
    verify: {
      title: "सत्यापन कोड दर्ज करें",
      subtitle: "आपके वित्तीय विवरण की सुरक्षा के लिए एक अस्थायी कोड आवश्यक है।",
      inputLabel: "रसीद पर छपा एक्सेस कोड",
      placeholder: "उदा. HBN-4921",
      helperText: "अपनी रसीद के नीचे छपा 6 अक्षरों का कोड या मोबाइल पर आया SMS देखें।",
      submitBtn: "कोड सत्यापित करें",
      verifying: "अस्पताल रिकॉर्ड से मिलान हो रहा है…",
      attemptsRemaining: "प्रयास शेष हैं।",
      invalidError: "गलत कोड। कृपया सही कोड देखकर दोबारा दर्ज करें।",
      expiredError: "यह एक्सेस कोड पुराना (एक्सपायर) हो चुका है। कृपया अस्पताल रिसेप्शन से नया कोड मांगें।",
      lockedError: "कई बार गलत कोड दर्ज करने के कारण सत्यापन रुक गया है। कृपया सहायता मांगें।",
      nextStepHelp: "कोड नहीं मिला? अस्पताल सहायक कर्मचारी से कॉल बैक का अनुरोध करें।",
      demoHint: "डेमो सुझाव: सफल परीक्षण के लिए 'HBN-4921' लिखें, या एक्सपायर के लिए 'EXPIRED' लिखें।",
    },
    bill: {
      title: "अस्पताल बिल सारांश",
      subtitle: "अस्पताल द्वारा प्रमाणित वित्तीय शुल्कों का स्पष्ट विवरण।",
      hospitalLabel: "अस्पताल का नाम",
      billNumberLabel: "बिल पहचान संख्या",
      patientNameLabel: "मरीज़ का नाम",
      admissionLabel: "भर्ती की तिथि",
      dischargeLabel: "छुट्टी (डिस्चार्ज) की तिथि",
      billDateLabel: "बिल जारी तिथि",
      dueDateLabel: "भुगतान की अंतिम तिथि",
      totalAmountLabel: "अस्पताल का कुल बिल",
      insuranceLabel: "बीमा / सरकारी योजना द्वारा कवर",
      paidLabel: "पहले जमा की गई राशि",
      patientPayableLabel: "मरीज़ द्वारा देय शेष राशि",
      verifiedBadge: "सत्यापित आधिकारिक रिकॉर्ड",
      discrepancyBadge: "राशि में अंतर पाया गया",
      incompleteBadge: "अधूरी जानकारी",
      discrepancyAlertTitle: "बिल राशि में अंतर का नोटिस",
      lineItemsTitle: "सभी शुल्कों का मद-वार विवरण",
      lineItemsSubtitle: "अस्पताल में प्रदान की गई प्रत्येक सेवा और दवा का ब्यौरा।",
      chargeColumn: "सेवा / प्रक्रिया",
      amountColumn: "शुल्क राशि",
      plainMeaningColumn: "सरल भाषा में अर्थ",
      explainCtaBtn: "इस बिल को सरल भाषा में समझें",
      askQuestionBtn: "प्रश्न पूछें",
      needHelpBtn: "मानवीय सहायता मांगें",
    },
    explanation: {
      title: "अपना अस्पताल बिल समझें",
      subtitle: "यहाँ आपके बिल की पूरी जानकारी आम बोलचाल की भाषा में दी गई है।",
      listenBtn: "बोलकर सुनें",
      pauseBtn: "ऑडियो रोकें",
      resumeBtn: "ऑडियो जारी रखें",
      stopBtn: "ऑडियो बंद करें",
      audioPlaying: "स्पष्टीकरण सुनाया जा रहा है…",
      audioUnavailable: "आपके ब्राउज़र में आवाज़ सुनाने की सुविधा समर्थित नहीं है।",
      simplifyToggle: "और सरल भाषा में देखें",
      simplifyActive: "अति-सरल 5वीं कक्षा के स्तर का विवरण दिखाया जा रहा है",
      requiredSourceLabel: "Generated from hospital-provided bill information.",
      informationalNotice: "यह स्पष्टीकरण केवल सामान्य जानकारी के लिए है और अस्पताल के आधिकारिक बिल या चिकित्सीय सलाह का स्थान नहीं लेता।",
      aiBadge: "AI-संचालित स्पष्टीकरण",
      templateBadge: "सत्यापित चिकित्सीय प्रारूप",
      backToBillBtn: "बिल सारांश पर लौटें",
      askFollowUpBtn: "कोई अन्य प्रश्न पूछें",
      requestSupportBtn: "अस्पताल कर्मचारी से बात करें",
      retryBtn: "पुनः प्रयास करें",
    },
    questions: {
      title: "अपने बिल के बारे में प्रश्न पूछें",
      subtitle: "किसी भी शुल्क, टेस्ट या बीमा कटौती के बारे में निसंकोच पूछें।",
      inputLabel: "अपना प्रश्न लिखें या बोलें",
      placeholder: "उदा. चेस्ट एक्स-रे का इतना शुल्क क्यों है? या आयुष्मान भारत कैसे लागू होगा?",
      submitBtn: "प्रश्न पूछें",
      examplesLabel: "अक्सर पूछे जाने वाले प्रश्न:",
      sample1: "कंसल्टेशन फ़ीस का क्या मतलब है?",
      sample2: "क्या सीबीसी (CBC) ब्लड टेस्ट एक सामान्य जांच है?",
      sample3: "क्या मैं बची हुई राशि किस्तों में भर सकता हूँ?",
      voiceBtnStart: "बोलकर पूछें",
      voiceBtnStop: "रिकॉर्डिंग रोकें",
      voiceListening: "सुन रहे हैं… अब बोलिए",
      voiceReviewLabel: "पहचानी गई आवाज़ (जांचें या बदलें):",
      voiceEditHint: "आप भेजने से पहले शब्दों को छूकर सुधार सकते हैं।",
      voiceConfirmBtn: "पुष्टि करें और प्रश्न भेजें",
      voiceUnavailable: "आवाज़ पहचान समर्थित नहीं है। कृपया लिखकर पूछें।",
      refusalNotice: "सूचना: यह सहायक केवल बिल और वित्तीय शुल्कों की व्याख्या कर सकता है। बीमारी की जांच या इलाज के लिए कृपया अपने डॉक्टर से संपर्क करें।",
      emptyHistory: "अभी तक कोई प्रश्न नहीं पूछा गया। ऊपर दिए गए प्रश्नों में से चुनें या नया प्रश्न लिखें।",
    },
    caregiver: {
      title: "What You Need to Know",
      subtitle: "देखभालकर्ता और परिवार के लिए मुख्य वित्तीय सारांश।",
      billSummaryTitle: "महत्वपूर्ण बिल आंकड़े",
      financialTermsTitle: "इस बिल के प्रमुख वित्तीय शब्द",
      importantDatesTitle: "अंतिम तिथियां और महत्वपूर्ण दिन",
      clarificationQuestionsTitle: "अस्पताल बिलिंग काउंटर पर पूछने योग्य प्रश्न",
      nextStepsTitle: "सुझाए गए अगले कदम",
      nextStep1: "जांचें कि क्या आपका बीमा पूर्व-अनुमोदन पत्र इस बिल में सही घटाया गया है।",
      nextStep2: "अस्पताल फ़ार्मेसी बिल से डिस्चार्ज समरी में लिखी दवाइयों का मिलान करें।",
      nextStep3: "यदि आवश्यक हो तो अस्पताल के वित्तीय सलाहकार से किस्तों में भुगतान की बात करें।",
      requestSupportBtn: "अस्पताल कर्मचारी से कॉल बैक का अनुरोध करें",
      returnToPatientBtn: "मरीज़ दृश्य पर वापस जाएं",
    },
    help: {
      title: "मानवीय सहायता का अनुरोध करें",
      subtitle: "यदि बिल गलत या भ्रामक लगता है, तो अधिकृत अस्पताल कर्मचारी आपको कॉल बैक कर सकता है।",
      patientNameLabel: "आपका नाम",
      contactLabel: "फ़ोन नंबर",
      billNumberLabel: "अस्पताल बिल नंबर",
      langPrefLabel: "बातचीत के लिए पसंदीदा भाषा",
      callbackTimeLabel: "कॉल बैक का पसंदीदा समय",
      callbackNow: "जितनी जल्दी संभव हो",
      callbackMorning: "सुबह (9:00 AM – 12:00 PM)",
      callbackAfternoon: "दोपहर (12:00 PM – 4:00 PM)",
      callbackEvening: "शाम (4:00 PM – 8:00 PM)",
      reasonLabel: "सहायता का कारण",
      reasonPlaceholder: "कृपया बताएं कि क्या समस्या है (उदा. शुल्क में गलती, बीमा समस्या, छूट की जानकारी)…",
      consentCheckboxLabel: "मैं इस कॉल बैक के लिए अपना बिल नंबर और संपर्क नंबर अधिकृत अस्पताल कर्मचारी के साथ साझा करने की स्पष्ट सहमति देता हूँ।",
      submitBtn: "अनुरोध जमा करें",
      submitting: "अनुरोध भेजा जा रहा है…",
      successTitle: "अनुरोध प्राप्त हुआ",
      successReference: "आपकी केस संदर्भ संख्या (ID):",
      successMessage: "अस्पताल का मरीज़ सहायक आपके बिल की जांच करेगा और आपके चुने हुए समय पर कॉल करेगा।",
      demoNote: "डेमो सूचना: यह केवल एक प्रदर्शन प्रणाली है। कोई वास्तविक कॉल नहीं की जाएगी।",
      errorTitle: "अनुरोध भेजने में त्रुटि",
      errorMessage: "अनुरोध जमा नहीं हो सका। कृपया सुनिश्चित करें कि सभी आवश्यक खाने भरे गए हैं।",
    },
    supportDashboard: {
      title: "Support-Worker Dashboard",
      subtitle: "मरीज़ों के बिलिंग प्रश्नों को हल करने के लिए अधिकृत अस्पताल कर्मचारी पोर्टल",
      demoBadge: "डेमो डेटा · सिमुलेटेड स्टाफ़ एक्सेस",
      searchPlaceholder: "मरीज़, बिल #, या संदर्भ संख्या से खोजें…",
      filterAll: "सभी अनुरोध",
      filterNew: "नए (New)",
      filterScheduled: "कॉल निर्धारित (Callback scheduled)",
      filterContacted: "संपर्क किया गया (Contacted)",
      filterResolved: "हल हो गया (Resolved)",
      ticketListHeading: "मरीज़ों के प्राप्त अनुरोध",
      detailsHeading: "केस विवरण व कर्मचारी टिप्पणियाँ",
      noTickets: "इस फ़िल्टर में कोई अनुरोध नहीं मिला।",
      statusLabel: "वर्तमान स्थिति:",
      changeStatusBtn: "स्थिति अपडेट करें",
      addNotePlaceholder: "आंतरिक कर्मचारी टिप्पणी जोड़ें…",
      addNoteBtn: "टिप्पणी सहेजें",
      patientContactLabel: "फ़ोन नंबर:",
      callbackWindowLabel: "पसंदीदा समय:",
      preferredLangLabel: "भाषा:",
    },
  },

  // ────────────────────────────────────────────────────────────
  // KANNADA
  // ────────────────────────────────────────────────────────────
  kn: {
    common: {
      appName: "Healthcare Bill Navigator",
      appTagline: "ನಿಮ್ಮ ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಬಗ್ಗೆ ಸರಳ ಕನ್ನಡದಲ್ಲಿ ಮಾರ್ಗದರ್ಶನ",
      demoBanner: "ಡೆಮೊ ಡೇಟಾ — ಇದು ಕಾಲ್ಪನಿಕ ಮಾದರಿ ಮಾಹಿತಿಯಾಗಿದೆ. ಇದು ನಿಜವಾದ ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಅಲ್ಲ.",
      backBtn: "ಹಿಂದಕ್ಕೆ",
      continueBtn: "ಮುಂದುವರಿಯಿರಿ",
      retryBtn: "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",
      cancelBtn: "ರದ್ದುಮಾಡಿ",
      submitBtn: "ಸಲ್ಲಿಸಿ",
      loading: "ಲೋಡ್ ಆಗುತ್ತಿದೆ…",
      seekHumanHelp: "ಮಾನವ ನೆರವು ಬೇಕೇ?",
      privacyNotice: "ನಿಮ್ಮ ಬಿಲ್ ಮಾಹಿತಿಯನ್ನು ಸುರಕ್ಷಿತವಾಗಿ ಬಳಸಲಾಗುತ್ತದೆ ಮತ್ತು ಯಾವುದೇ ಪಾಸ್‌ವರ್ಡ್ ಶೇಖರಿಸುವುದಿಲ್ಲ.",
      officialNotice: "ಈ ಅಪ್ಲಿಕೇಶನ್ ವಿವರಣೆಗಾಗಿ ಮಾತ್ರ ಮತ್ತು ಆಸ್ಪತ್ರೆಯ ಅಧಿಕೃತ ಬಿಲ್ ಅಥವಾ ವೈದ್ಯಕೀಯ ಸಲಹೆಯ ಬದಲಿಯಲ್ಲ.",
      textSizeToggle: "ಅಕ್ಷರದ ಗಾತ್ರ",
      requiredField: "ಈ ವಿವರವನ್ನು ಭರ್ತಿ ಮಾಡುವುದು ಕಡ್ಡಾಯ",
      inrSymbol: "₹",
    },
    nav: {
      brand: "Healthcare Bill Navigator",
      tagline: "ನಿಮ್ಮ ವೈದ್ಯಕೀಯ ಬಿಲ್, ಸರಳ ವಿವರಣೆಯಲ್ಲಿ.",
      welcome: "ಮುಖಪುಟ",
      patientFlow: "ನನ್ನ ಬಿಲ್",
      caregiver: "ಆರೈಕೆದಾರರ ಸಾರಾಂಶ",
      support: "ಸಹಾಯಕ ಸಿಬ್ಬಂದಿ",
      langSelect: "ಭಾಷೆ",
      seekHelpBtn: "ಮಾನವ ನೆರವು ಪಡೆಯಿರಿ",
    },
    welcome: {
      title: "ನಿಮ್ಮ ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಅನ್ನು ಸರಳ ಮಾತುಗಳಲ್ಲಿ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ.",
      subtitle: "ವೈದ್ಯಕೀಯ ಬಿಲ್‌ಗಳು ಗೊಂದಲಮಯವಾಗಿರಬಹುದು. Healthcare Bill Navigator ಕಷ್ಟದ ವೈದ್ಯಕೀಯ ಪದಗಳನ್ನು ಸುಲಭಗೊಳಿಸುತ್ತದೆ, ವಿಮಾ ಮೊತ್ತವನ್ನು ವಿವರಿಸುತ್ತದೆ ಮತ್ತು ಆಡಿಯೋ ಮೂಲಕ ಕೇಳಲು ಸಹಕರಿಸುತ್ತದೆ.",
      primaryCta: "ನನ್ನ ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ",
      secondaryCta: "ಆರೈಕೆದಾರರ ಸಾರಾಂಶ",
      feature1Title: "ಸರಳ ಕನ್ನಡ ವಿವರಣೆ",
      feature1Desc: "ಪ್ರತಿಯೊಂದು ಪರೀಕ್ಷೆ, ವೈದ್ಯರ ಶುಲ್ಕ ಮತ್ತು ಔಷಧಿ ದರವನ್ನು ಸರಳ ಭಾಷೆಯಲ್ಲಿ ತಿಳಿಯಿರಿ.",
      feature2Title: "ಧ್ವನಿ ಮಾರ್ಗದರ್ಶನ (ಆಡಿಯೋ)",
      feature2Desc: "ಕನ್ನಡ, ಹಿಂದಿ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಆಲಿಸಿ. ದೊಡ್ಡ ಅಕ್ಷರಗಳು ಮತ್ತು ಸುಲಭ ಸ್ಪರ್ಶದೊಂದಿಗೆ ವಿನ್ಯಾಸಗೊಳಿಸಲಾಗಿದೆ.",
      feature3Title: "ಮಾನವ ನೆರವು ಲಭ್ಯವಿದೆ",
      feature3Desc: "ಬಿಲ್‌ನಲ್ಲಿ ದೋಷ ಕಂಡುಬಂದರೆ ಅಥವಾ ಪಾವತಿ ಕಂತುಗಳ ಸಹಾಯ ಬೇಕಾದರೆ ಆಸ್ಪತ್ರೆ ಸಿಬ್ಬಂದಿಯಿಂದ ಕರೆ ಪಡೆಯಿರಿ.",
      disclaimer: "Healthcare Bill Navigator ಕೇವಲ ಮಾಹಿತಿ ನೀಡುವ ಸಾಧನವಾಗಿದೆ. ಇದು ಆಸ್ಪತ್ರೆಯ ಅಧಿಕೃತ ಬಿಲ್ ಅಥವಾ ವೈದ್ಯಕೀಯ ಸಲಹೆಯಲ್ಲ.",
    },
    consent: {
      title: "ನಿಮ್ಮ ಗೌಪ್ಯತೆ ಮತ್ತು ಒಪ್ಪಿಗೆ",
      subtitle: "ಬಿಲ್ ನೋಡುವ ಮೊದಲು, ನಿಮ್ಮ ಮಾಹಿತಿಯನ್ನು ಹೇಗೆ ಬಳಸಲಾಗುತ್ತದೆ ಎಂಬುದನ್ನು ಪರಿಶೀಲಿಸಿ.",
      whatUsedTitle: "1. ಯಾವ ಮಾಹಿತಿಯನ್ನು ಬಳಸಲಾಗುತ್ತದೆ",
      whatUsedText: "ನಾವು ಆಸ್ಪತ್ರೆ ಹೆಸರು, ಮುದ್ರಿತ ಬಿಲ್ ಸಂಖ್ಯೆ ಮತ್ತು ಶುಲ್ಕಗಳ ಹೆಸರುಗಳನ್ನು ಮಾತ್ರ ಓದುತ್ತೇವೆ.",
      whyNeededTitle: "2. ಈ ಮಾಹಿತಿ ಏಕೆ ಬೇಕು",
      whyNeededText: "ವೈದ್ಯಕೀಯ ಪದಗಳನ್ನು ಸಾಮಾನ್ಯ ಸರಳ ಕನ್ನಡಕ್ಕೆ ಪರಿವರ್ತಿಸಲು ಈ ಮಾಹಿತಿ ಅಗತ್ಯವಿದೆ.",
      howUsedTitle: "3. ಅಪ್ಲಿಕೇಶನ್ ಇದನ್ನು ಹೇಗೆ ಬಳಸುತ್ತದೆ",
      howUsedText: "ಮಾಹಿತಿಯನ್ನು ಕೇವಲ ಪ್ರಸ್ತುತ ಸಮಯದಲ್ಲಿ ಮಾತ್ರ ಪರಿಶೀಲಿಸಲಾಗುತ್ತದೆ. ನಿಮ್ಮ ಫೋಟೋ ಅಥವಾ ಪಾಸ್‌ವರ್ಡ್ ಉಳಿಯುವುದಿಲ್ಲ.",
      agreeMeaningTitle: "4. ಒಪ್ಪಿಗೆ ನೀಡುವುದರ ಅರ್ಥ",
      agreeMeaningText: "ನಿಮ್ಮ ಬಿಲ್ ವಿವರಗಳನ್ನು ಸರಳವಾಗಿ ವಿವರಿಸಲು ಮತ್ತು ಆಡಿಯೋ ಮೂಲಕ ಕೇಳಿಸಲು ಅನುಮತಿ ನೀಡುತ್ತಿದ್ದೀರಿ.",
      declineTitle: "5. ನಿರಾಕರಿಸುವುದು ಹೇಗೆ",
      declineText: "ನೀವು ಯಾವುದೇ ಸಮಯದಲ್ಲಿ ನಿರಾಕರಿಸಬಹುದು. ನಿರಾಕರಿಸಿದರೂ ನೀವು ನೇರವಾಗಿ ಆಸ್ಪತ್ರೆ ಸಹಾಯಕರನ್ನು ಸಂಪರ್ಕಿಸಬಹುದು.",
      agreeBtn: "ನಾನು ಒಪ್ಪುತ್ತೇನೆ, ಮುಂದುವರಿಯಿರಿ",
      declineBtn: "ನಾನು ನಿರಾಕರಿಸುತ್ತೇನೆ",
      declinedNoticeTitle: "ಒಪ್ಪಿಗೆ ನಿರಾಕರಿಸಲಾಗಿದೆ",
      declinedNoticeMsg: "ಸ್ವಯಂಚಾಲಿತ ಬಿಲ್ ವಿಶ್ಲೇಷಣೆಯನ್ನು ನೀವು ನಿರಾಕರಿಸಿದ್ದೀರಿ. ನೀವು ಯಾವುದೇ ಸಮಯದಲ್ಲಿ ಮರುಪರಿಶೀಲಿಸಬಹುದು ಅಥವಾ ಆಸ್ಪತ್ರೆ ಸಿಬ್ಬಂದಿಯಿಂದ ನೇರ ನೆರವು ಪಡೆಯಬಹುದು.",
      reconsiderBtn: "ಒಪ್ಪಿಗೆಯನ್ನು ಮತ್ತೆ ನೋಡಿ",
    },
    identify: {
      title: "ನಿಮ್ಮ ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಗುರುತಿಸಿ",
      subtitle: "ನಿಮ್ಮ ಬಿಲ್ ಹುಡುಕಲು ಒಂದು ವಿಧಾನವನ್ನು ಆಯ್ಕೆಮಾಡಿ. ಇಂಟರ್ನೆಟ್ ನಿಧಾನವಾಗಿದ್ದರೆ ಬಿಲ್ ಸಂಖ್ಯೆ ನಮೂದಿಸುವುದು ಉತ್ತಮ.",
      tabUpload: "ಆಯ್ಕೆ A: ಬಿಲ್ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
      tabNumber: "ಆಯ್ಕೆ B: ಬಿಲ್ ಸಂಖ್ಯೆ ನಮೂದಿಸಿ",
      uploadInstructions: "ನಿಮ್ಮ ಆಸ್ಪತ್ರೆ ಬಿಲ್‌ನ ಸ್ಪಷ್ಟ ಫೋಟೋ ಅಥವಾ PDF ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.",
      uploadDragDrop: "ಬಿಲ್ ಫೋಟೋವನ್ನು ಇಲ್ಲಿಗೆ ಎಳೆಯಿರಿ, ಅಥವಾ",
      uploadBrowse: "ಫೈಲ್ ಆಯ್ಕೆಮಾಡಿ",
      uploadCamera: "ಕ್ಯಾಮೆರಾದಿಂದ ಫೋಟೋ ತೆಗೆಯಿರಿ",
      uploadLimits: "ಸ್ವೀಕರಿಸುವ ಫೈಲ್‌ಗಳು: JPG, PNG, PDF · ಗರಿಷ್ಠ 10 MB",
      uploadSelected: "ಆಯ್ಕೆಯಾದ ಫೈಲ್:",
      uploadReplace: "ಫೈಲ್ ಬದಲಾಯಿಸಿ",
      uploadRemove: "ಫೈಲ್ ತೆಗೆಯಿರಿ",
      uploadSubmit: "ಬಿಲ್ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ ಗುರುತಿಸಿ",
      uploadingProgress: "ದಾಖಲೆ ಓದಲಾಗುತ್ತಿದೆ ಮತ್ತು ವಿವರಗಳನ್ನು ಹುಡುಕಲಾಗುತ್ತಿದೆ…",
      numberInputLabel: "ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಸಂಖ್ಯೆ",
      numberPlaceholder: "ಉದಾ. BILL-2026-001 ಅಥವಾ INV-2026-0042",
      numberSubmit: "ಬಿಲ್ ಹುಡುಕಿ",
      numberInstructions: "ನಿಮ್ಮ ರಶೀದಿಯಲ್ಲಿ ಮುದ್ರಿಸಲಾದ 'Bill No.' ಅಥವಾ 'Receipt No.' ನೋಡಿ.",
      lowBandwidthBadge: "ಕಡಿಮೆ ಡೇಟಾ ಮೋಡ್ · 2 KB ಗಿಂತ ಕಡಿಮೆ ಇಂಟರ್ನೆಟ್ ಬಳಕೆ",
      presetExamplesLabel: "ಪರೀಕ್ಷಾರ್ಥ ಉದಾಹರಣೆಗಳು:",
      states: {
        identifiedTitle: "ಬಿಲ್ ಯಶಸ್ವಿಯಾಗಿ ದೊರೆತಿದೆ",
        identifiedDesc: "ನಿಮ್ಮ ಅಧಿಕೃತ ಆಸ್ಪತ್ರೆ ದಾಖಲೆ ಸಿಕ್ಕಿದೆ. ದಯವಿಟ್ಟು ವಿವರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
        proceedBtn: "ಬಿಲ್ ಮಾಹಿತಿ ವೀಕ್ಷಿಸಿ",
        needsVerificationTitle: "ಹೆಚ್ಚುವರಿ ಪರಿಶೀಲನೆ ಅಗತ್ಯವಿದೆ",
        needsVerificationDesc: "ನಿಮ್ಮ ಸುರಕ್ಷತೆಗಾಗಿ, SMS ಮೂಲಕ ಕಳುಹಿಸಲಾದ ಪ್ರವೇಶ ಕೋಡ್ ಅನ್ನು ನಮೂದಿಸುವುದು ಕಡ್ಡಾಯ.",
        verifyBtn: "ಕೋಡ್ ನಮೂದಿಸಿ",
        notFoundTitle: "ಬಿಲ್ ಸಿಗಲಿಲ್ಲ",
        notFoundDesc: "ಆ ಸಂಖ್ಯೆಯ ಯಾವುದೇ ಸಕ್ರಿಯ ಬಿಲ್ ದಾಖಲೆ ಸಿಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಸಂಖ್ಯೆ ಪರಿಶೀಲಿಸಿ ಅಥವಾ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.",
        unregisteredTitle: "ಆಸ್ಪತ್ರೆ ನೋಂದಾಯಿತವಾಗಿಲ್ಲ",
        unregisteredDesc: "ಈ ಆಸ್ಪತ್ರೆ ಇನ್ನೂ ನಮ್ಮ ಆನ್‌ಲೈನ್ ವ್ಯವಸ್ಥೆಗೆ ಸಂಪರ್ಕ ಹೊಂದಿಲ್ಲ. ಮಾನವ ಸಹಾಯವನ್ನು ಪಡೆಯಿರಿ.",
        unreadableTitle: "ಅಸ್ಪಷ್ಟ ಬಿಲ್ ಚಿತ್ರ",
        unreadableDesc: "ಫೋಟೋ ಮಸುಕಾಗಿದೆ. ದಯವಿಟ್ಟು ಬೆಳಕಿನಲ್ಲಿ ಸ್ಪಷ್ಟ ಚಿತ್ರ ತೆಗೆಯಿರಿ ಅಥವಾ ಬಿಲ್ ಸಂಖ್ಯೆ ಟೈಪ್ ಮಾಡಿ.",
        incompleteTitle: "ಅಪೂರ್ಣ ಬಿಲ್ ದಾಖಲೆ",
        incompleteDesc: "ಆಸ್ಪತ್ರೆಯ ದಾಖಲೆಯಲ್ಲಿ ಕೆಲವು ಶುಲ್ಕಗಳ ವಿವರಗಳು ಅಪೂರ್ಣವಾಗಿವೆ. ಬಿಲ್ಲಿಂಗ್ ವಿಭಾಗವನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        temporaryFailureTitle: "ತಾತ್ಕಾಲಿಕ ನೆಟ್‌ವರ್ಕ್ ಸಮಸ್ಯೆ",
        temporaryFailureDesc: "ಆಸ್ಪತ್ರೆ ಸರ್ವರ್ ಸಂಪರ್ಕ ಕಡಿತಗೊಂಡಿದೆ. ದಯವಿಟ್ಟು ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
      },
    },
    verify: {
      title: "ಪ್ರವೇಶ ಕೋಡ್ ನಮೂದಿಸಿ",
      subtitle: "ನಿಮ್ಮ ಹಣಕಾಸು ವಿವರಗಳ ರಕ್ಷಣೆಗಾಗಿ ಮುದ್ರಿತ ಪರಿಶೀಲನಾ ಕೋಡ್ ಅಗತ್ಯವಿದೆ.",
      inputLabel: "ರಶೀದಿಯಲ್ಲಿ ಮುದ್ರಿಸಲಾದ ಕೋಡ್",
      placeholder: "ಉದಾ. HBN-4921",
      helperText: "ನಿಮ್ಮ ರಶೀದಿಯ ಕೆಳಭಾಗದಲ್ಲಿರುವ 6 ಅಕ್ಷರಗಳ ಕೋಡ್ ಅಥವಾ ಮೊಬೈಲ್‌ಗೆ ಬಂದ SMS ನೋಡಿ.",
      submitBtn: "ಕೋಡ್ ದೃಢೀಕರಿಸಿ",
      verifying: "ಆಸ್ಪತ್ರೆ ದಾಖಲೆಯೊಂದಿಗೆ ತಾಳೆ ನೋಡಲಾಗುತ್ತಿದೆ…",
      attemptsRemaining: "ಪ್ರಯತ್ನಗಳು ಬಾಕಿ ಇವೆ.",
      invalidError: "ತಪ್ಪಾದ ಕೋಡ್. ದಯವಿಟ್ಟು ಅಕ್ಷರಗಳನ್ನು ಸರಿಯಾಗಿ ನೋಡಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
      expiredError: "ಈ ಪ್ರವೇಶ ಕೋಡ್ ಅವಧಿ ಮೀರಿದೆ (Expired). ದಯವಿಟ್ಟು ಆಸ್ಪತ್ರೆಯಿಂದ ಹೊಸ ಕೋಡ್ ಪಡೆಯಿರಿ.",
      lockedError: "ಹಲವು ಬಾರಿ ತಪ್ಪಾದ ಕೋಡ್ ನಮೂದಿಸಿದ್ದರಿಂದ ಪರಿಶೀಲನೆ ನಿಂತಿದೆ. ಸಹಾಯ ಪಡೆಯಿರಿ.",
      nextStepHelp: "ಕೋಡ್ ಸಿಗಲಿಲ್ಲವೇ? ಆಸ್ಪತ್ರೆ ಸಹಾಯಕರಿಂದ ಕರೆ ಪಡೆಯಲು ವಿನಂತಿಸಿ.",
      demoHint: "ಡೆಮೊ ಸುಳಿವು: 'HBN-4921' ನಮೂದಿಸಿ ಯಶಸ್ವಿ ಪರೀಕ್ಷೆಗೆ, ಅಥವಾ 'EXPIRED' ಬರೆಯಿರಿ.",
    },
    bill: {
      title: "ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಸಾರಾಂಶ",
      subtitle: "ಆಸ್ಪತ್ರೆ ಬಿಲ್ಲಿಂಗ್ ವಿಭಾಗದಿಂದ ಪರಿಶೀಲಿಸಲ್ಪಟ್ಟ ಅಧಿಕೃತ ಶುಲ್ಕಗಳು ಇಲ್ಲಿವೆ.",
      hospitalLabel: "ಆಸ್ಪತ್ರೆಯ ಹೆಸರು",
      billNumberLabel: "ಬಿಲ್ ಗುರುತಿನ ಸಂಖ್ಯೆ",
      patientNameLabel: "ರೋಗಿಯ ಹೆಸರು",
      admissionLabel: "ದಾಖಲಾದ ದಿನಾಂಕ",
      dischargeLabel: "ಬಿಡುಗಡೆ (ಡಿಸ್ಚಾರ್ಜ್) ದಿನಾಂಕ",
      billDateLabel: "ಬಿಲ್ ನೀಡಿದ ದಿನಾಂಕ",
      dueDateLabel: "ಪಾವತಿಯ ಕೊನೆಯ ದಿನಾಂಕ",
      totalAmountLabel: "ಒಟ್ಟು ಆಸ್ಪತ್ರೆ ಶುಲ್ಕಗಳು",
      insuranceLabel: "ವಿಮೆ / ಸರ್ಕಾರದ ಯೋಜನೆಯಿಂದ ಕಡಿತ",
      paidLabel: "ಈಗಾಗಲೇ ಪಾವತಿಸಿದ ಹಣ",
      patientPayableLabel: "ರೋಗಿ ಪಾವತಿಸಬೇಕಾದ ಉಳಿದ ಹಣ",
      verifiedBadge: "ಪರಿಶೀಲಿಸಿದ ಅಧಿಕೃತ ದಾಖಲೆ",
      discrepancyBadge: "ಮೊತ್ತದಲ್ಲಿ ವ್ಯತ್ಯಾಸ ಕಂಡುಬಂದಿದೆ",
      incompleteBadge: "ಅಪೂರ್ಣ ಮಾಹಿತಿ",
      discrepancyAlertTitle: "ಮೊತ್ತದ ವ್ಯತ್ಯಾಸದ ಸೂಚನೆ",
      lineItemsTitle: "ಪ್ರತಿಯೊಂದು ಶುಲ್ಕದ ವಿವರವಾದ ಪಟ್ಟಿ",
      lineItemsSubtitle: "ಚಿಕಿತ್ಸೆಯ ಸಮಯದಲ್ಲಿ ವಿಧಿಸಲಾದ ವೈಯಕ್ತಿಕ ಸೇವೆಗಳು ಮತ್ತು ಔಷಧಿಗಳ ವಿವರ.",
      chargeColumn: "ಸೇವೆ / ತಪಾಸಣೆ",
      amountColumn: "ವಿಧಿಸಲಾದ ಮೊತ್ತ",
      plainMeaningColumn: "ಸರಳ ಕನ್ನಡ ವಿವರಣೆ",
      explainCtaBtn: "ಈ ಬಿಲ್ ಅನ್ನು ಸರಳ ಕನ್ನಡದಲ್ಲಿ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ",
      askQuestionBtn: "ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ",
      needHelpBtn: "ಮಾನವ ನೆರವು ವಿನಂತಿಸಿ",
    },
    explanation: {
      title: "ನಿಮ್ಮ ಬಿಲ್ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ",
      subtitle: "ನಿಮ್ಮ ಬಿಲ್‌ನ ಸಂಪೂರ್ಣ ಮಾಹಿತಿ ಸರಳ ದೈನಂದಿನ ಕನ್ನಡದಲ್ಲಿದೆ.",
      listenBtn: "ಧ್ವನಿ ಮೂಲಕ ಆಲಿಸಿ",
      pauseBtn: "ಆಡಿಯೋ ವಿರಾಮಗೊಳಿಸಿ",
      resumeBtn: "ಆಡಿಯೋ ಮುಂದುವರಿಸಿ",
      stopBtn: "ಆಡಿಯೋ ನಿಲ್ಲಿಸಿ",
      audioPlaying: "ವಿವರಣೆಯನ್ನು ಓದಲಾಗುತ್ತಿದೆ…",
      audioUnavailable: "ನಿಮ್ಮ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಓದುವಿಕೆ ಲಭ್ಯವಿಲ್ಲ.",
      simplifyToggle: "ಇನ್ನಷ್ಟು ಸರಳ ವಿವರಣೆ",
      simplifyActive: "ಅತ್ಯಂತ ಸರಳ 5ನೇ ತರಗತಿ ಮಟ್ಟದ ವಿವರಣೆ ತೋರಿಸಲಾಗುತ್ತಿದೆ",
      requiredSourceLabel: "Generated from hospital-provided bill information.",
      informationalNotice: "ಈ ವಿವರಣೆಯು ಕೇವಲ ಮಾಹಿತಿಗಾಗಿ ಮಾತ್ರ ಮತ್ತು ಆಸ್ಪತ್ರೆಯ ಅಧಿಕೃತ ಬಿಲ್ ಅಥವಾ ವೈದ್ಯಕೀಯ ಸಲಹೆಯ ಬದಲಿಯಲ್ಲ.",
      aiBadge: "AI-ಚಾಲಿತ ವಿವರಣೆ",
      templateBadge: "ಪರಿಶೀಲಿಸಿದ ವೈದ್ಯಕೀಯ ಮಾದರಿ",
      backToBillBtn: "ಬಿಲ್ ಸಾರಾಂಶಕ್ಕೆ ಹಿಂತಿರುಗಿ",
      askFollowUpBtn: "ಮುಂದಿನ ಪ್ರಶ್ನೆ ಕೇಳಿ",
      requestSupportBtn: "ಆಸ್ಪತ್ರೆ ಸಿಬ್ಬಂದಿಯೊಂದಿಗೆ ಮಾತನಾಡಿ",
      retryBtn: "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",
    },
    questions: {
      title: "ನಿಮ್ಮ ಬಿಲ್ ಬಗ್ಗೆ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ",
      subtitle: "ಯಾವುದೇ ಶುಲ್ಕ, ಪರೀಕ್ಷೆ ಅಥವಾ ವಿಮೆ ಕಡಿತದ ಬಗ್ಗೆ ನಿಸ್ಸಂಕೋಚವಾಗಿ ಕೇಳಿ.",
      inputLabel: "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಬರೆಯಿರಿ ಅಥವಾ ಮಾತನಾಡಿ",
      placeholder: "ಉದಾ. ಎದೆಯ ಎಕ್ಸ್‌ರೇಗೆ ಈ ದರ ಏಕೆ? ಅಥವಾ ಆಯುಷ್ಮಾನ್ ಭಾರತ್ ಹೇಗೆ ಅನ್ವಯಿಸುತ್ತದೆ?",
      submitBtn: "ಪ್ರಶ್ನೆ ಕೇಳಿ",
      examplesLabel: "ಸಾಮಾನ್ಯ ಪ್ರಶ್ನೆಗಳು:",
      sample1: "ಕನ್ಸಲ್ಟೇಶನ್ ಫೀಸ್ ಅಂದರೆ ಏನು?",
      sample2: "ಸಿಬಿಸಿ (CBC) ರಕ್ತ ಪರೀಕ್ಷೆ ಸಾಮಾನ್ಯವೇ?",
      sample3: "ಉಳಿದ ಮೊತ್ತವನ್ನು ಕಂತುಗಳಲ್ಲಿ ಪಾವತಿಸಬಹುದೇ?",
      voiceBtnStart: "ಮಾತನಾಡಿ ಕೇಳಿ",
      voiceBtnStop: "ರೆಕಾರ್ಡಿಂಗ್ ನಿಲ್ಲಿಸಿ",
      voiceListening: "ಆಲಿಸಲಾಗುತ್ತಿದೆ… ಈಗ ಮಾತನಾಡಿ",
      voiceReviewLabel: "ಗುರುತಿಸಲಾದ ಮಾತು (ಪರಿಶೀಲಿಸಿ ಅಥವಾ ತಿದ್ದಿ):",
      voiceEditHint: "ಸಲ್ಲಿಸುವ ಮೊದಲು ನೀವು ಪದಗಳನ್ನು ತಿದ್ದಬಹುದು.",
      voiceConfirmBtn: "ದೃಢೀಕರಿಸಿ ಮತ್ತು ಪ್ರಶ್ನೆ ಸಲ್ಲಿಸಿ",
      voiceUnavailable: "ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಟೈಪ್ ಮಾಡಿ.",
      refusalNotice: "ಸೂಚನೆ: ಈ ಸಹಾಯಕ ಬಿಲ್ಲಿಂಗ್ ಮತ್ತು ಹಣಕಾಸಿನ ಶುಲ್ಕಗಳನ್ನು ಮಾತ್ರ ವಿವರಿಸಬಲ್ಲದು. ಚಿಕಿತ್ಸೆ ಅಥವಾ ರೋಗನಿರ್ಣಯಕ್ಕಾಗಿ ನಿಮ್ಮ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ.",
      emptyHistory: "ಇನ್ನೂ ಯಾವುದೇ ಪ್ರಶ್ನೆ ಕೇಳಿಲ್ಲ. ಮೇಲಿನ ಪ್ರಶ್ನೆಗಳನ್ನು ಆರಿಸಿ ಅಥವಾ ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ.",
    },
    caregiver: {
      title: "What You Need to Know",
      subtitle: "ಆರೈಕೆದಾರರು ಮತ್ತು ಕುಟುಂಬಕ್ಕಾಗಿ ಮುಖ್ಯ ಹಣಕಾಸು ಸಾರಾಂಶ.",
      billSummaryTitle: "ಮುಖ್ಯ ಬಿಲ್ ಸಂಖ್ಯೆಗಳು",
      financialTermsTitle: "ಈ ಬಿಲ್‌ನಲ್ಲಿರುವ ಪ್ರಮುಖ ಹಣಕಾಸು ಪದಗಳು",
      importantDatesTitle: "ಮುಖ್ಯ ದಿನಾಂಕಗಳು ಮತ್ತು ಗಡುವುಗಳು",
      clarificationQuestionsTitle: "ಆಸ್ಪತ್ರೆ ಬಿಲ್ಲಿಂಗ್ ಕೌಂಟರ್‌ನಲ್ಲಿ ಕೇಳಬೇಕಾದ ಪ್ರಶ್ನೆಗಳು",
      nextStepsTitle: "ಮುಂದಿನ ಹಂತಗಳು",
      nextStep1: "ವಿಮಾ ಅನುಮೋದನೆ ಪತ್ರವನ್ನು ಈ ಬಿಲ್‌ನಲ್ಲಿ ಸರಿಯಾಗಿ ಕಡಿತಗೊಳಿಸಲಾಗಿದೆಯೇ ಎಂದು ಪರಿಶೀಲಿಸಿ.",
      nextStep2: "ಡಿಸ್ಚಾರ್ಜ್ ಸಾರಾಂಶದಲ್ಲಿ ನೀಡಲಾದ ಔಷಧಿಗಳೊಂದಿಗೆ ಬಿಲ್ ತಾಳೆ ನೋಡಿ.",
      nextStep3: "ಅಗತ್ಯವಿದ್ದರೆ ಕಂತುಗಳಲ್ಲಿ ಪಾವತಿಸಲು ಆಸ್ಪತ್ರೆ ಹಣಕಾಸು ವಿಭಾಗದೊಂದಿಗೆ ಮಾತನಾಡಿ.",
      requestSupportBtn: "ಆಸ್ಪತ್ರೆ ಸಿಬ್ಬಂದಿಯಿಂದ ಕಾಲ್ ಬ್ಯಾಕ್ ಪಡೆಯಿರಿ",
      returnToPatientBtn: "ರೋಗಿಯ ವೀಕ್ಷಣೆಗೆ ಹಿಂತಿರುಗಿ",
    },
    help: {
      title: "ಮಾನವ ನೆರವನ್ನು ವಿನಂತಿಸಿ",
      subtitle: "ಬಿಲ್‌ನಲ್ಲಿ ತಪ್ಪಿದ್ದರೆ ಅಥವಾ ಗೊಂದಲವಿದ್ದರೆ ಅಧಿಕೃತ ಆಸ್ಪತ್ರೆ ಸಿಬ್ಬಂದಿ ನಿಮಗೆ ಕರೆ ಮಾಡುತ್ತಾರೆ.",
      patientNameLabel: "ನಿಮ್ಮ ಹೆಸರು",
      contactLabel: "ಸಂಪರ್ಕ ಫೋನ್ ಸಂಖ್ಯೆ",
      billNumberLabel: "ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಸಂಖ್ಯೆ",
      langPrefLabel: "ಮಾತನಾಡಲು ಆದ್ಯತೆಯ ಭಾಷೆ",
      callbackTimeLabel: "ಕರೆಗೆ ಸೂಕ್ತ ಸಮಯ",
      callbackNow: "ಸಾಧ್ಯವಾದಷ್ಟು ಬೇಗ",
      callbackMorning: "ಬೆಳಗ್ಗೆ (9:00 AM – 12:00 PM)",
      callbackAfternoon: "ಮಧ್ಯಾಹ್ನ (12:00 PM – 4:00 PM)",
      callbackEvening: "ಸಂಜೆ (4:00 PM – 8:00 PM)",
      reasonLabel: "ಸಹಾಯದ ವಿವರಣೆ",
      reasonPlaceholder: "ಯಾವ ಗೊಂದಲವಿದೆ ಎಂಬುದನ್ನು ಬರೆಯಿರಿ (ಉದಾ. ಶುಲ್ಕದಲ್ಲಿ ದೋಷ, ವಿಮೆ ಸಮಸ್ಯೆ, ರಿಯಾಯಿತಿ ಮಾಹಿತಿ)…",
      consentCheckboxLabel: "ಈ ಕರೆಗಾಗಿ ಆಸ್ಪತ್ರೆ ಸಿಬ್ಬಂದಿಯೊಂದಿಗೆ ನನ್ನ ಬಿಲ್ ವಿವರ ಮತ್ತು ಫೋನ್ ಸಂಖ್ಯೆ ಹಂಚಿಕೊಳ್ಳಲು ನಾನು ಸ್ಪಷ್ಟ ಒಪ್ಪಿಗೆ ನೀಡುತ್ತೇನೆ.",
      submitBtn: "ವಿನಂತಿ ಸಲ್ಲಿಸಿ",
      submitting: "ಸಲ್ಲಿಸಲಾಗುತ್ತಿದೆ…",
      successTitle: "ವಿನಂತಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ",
      successReference: "ನಿಮ್ಮ ಕೇಸ್ ಉಲ್ಲೇಖ ಸಂಖ್ಯೆ (ID):",
      successMessage: "ಆಸ್ಪತ್ರೆಯ ರೋಗಿ ಸಹಾಯ ಸಿಬ್ಬಂದಿ ನಿಮ್ಮ ಬಿಲ್ ಪರಿಶೀಲಿಸಿ, ನೀವು ಆಯ್ಕೆ ಮಾಡಿದ ಸಮಯದಲ್ಲಿ ಕರೆ ಮಾಡುತ್ತಾರೆ.",
      demoNote: "ಡೆಮೊ ಸೂಚನೆ: ಇದು ಪ್ರದರ್ಶನ ವ್ಯವಸ್ಥೆಯಾಗಿದೆ. ಯಾವುದೇ ನೈಜ ಕರೆ ಬರುವುದಿಲ್ಲ.",
      errorTitle: "ಸಲ್ಲಿಕೆ ದೋಷ",
      errorMessage: "ವಿನಂತಿ ಸಲ್ಲಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಎಲ್ಲ ಅಗತ್ಯ ವಿವರಗಳನ್ನು ಭರ್ತಿ ಮಾಡಿ.",
    },
    supportDashboard: {
      title: "Support-Worker Dashboard",
      subtitle: "ರೋಗಿಗಳ ಬಿಲ್ಲಿಂಗ್ ಪ್ರಶ್ನೆಗಳನ್ನು ಪರಿಹರಿಸಲು ಅಧಿಕೃತ ಆಸ್ಪತ್ರೆ ಸಿಬ್ಬಂದಿ ಪೋರ್ಟಲ್",
      demoBadge: "ಡೆಮೊ ಡೇಟಾ · ಸಿಮ್ಯುಲೇಟೆಡ್ ಸಿಬ್ಬಂದಿ ಪ್ರವೇಶ",
      searchPlaceholder: "ರೋಗಿ, ಬಿಲ್ #, ಅಥವಾ ಉಲ್ಲೇಖ ಸಂಖ್ಯೆಯಿಂದ ಹುಡುಕಿ…",
      filterAll: "ಎಲ್ಲ ವಿನಂತಿಗಳು",
      filterNew: "ಹೊಸತು (New)",
      filterScheduled: "ಕರೆ ನಿಗದಿಯಾಗಿದೆ (Callback scheduled)",
      filterContacted: "ಸಂಪರ್ಕಿಸಲಾಗಿದೆ (Contacted)",
      filterResolved: "ಪರಿಹರಿಸಲಾಗಿದೆ (Resolved)",
      ticketListHeading: "ಬಂದಿರುವ ರೋಗಿ ವಿಚಾರಣೆಗಳು",
      detailsHeading: "ಕೇಸ್ ವಿವರಗಳು ಮತ್ತು ಸಿಬ್ಬಂದಿ ಟಿಪ್ಪಣಿಗಳು",
      noTickets: "ಆಯ್ಕೆಮಾಡಿದ ಫಿಲ್ಟರ್‌ನಲ್ಲಿ ಯಾವುದೇ ವಿನಂತಿಗಳಿಲ್ಲ.",
      statusLabel: "ಪ್ರಸ್ತುತ ಸ್ಥಿತಿ:",
      changeStatusBtn: "ಸ್ಥಿತಿ ನವೀಕರಿಸಿ",
      addNotePlaceholder: "ಸಿಬ್ಬಂದಿ ಆಂತರಿಕ ಟಿಪ್ಪಣಿ ಸೇರಿಸಿ…",
      addNoteBtn: "ಟಿಪ್ಪಣಿ ಉಳಿಸಿ",
      patientContactLabel: "ಫೋನ್ ಸಂಖ್ಯೆ:",
      callbackWindowLabel: "ಆದ್ಯತೆಯ ಸಮಯ:",
      preferredLangLabel: "ಭಾಷೆ:",
    },
  },
};

export type Translations = any;

