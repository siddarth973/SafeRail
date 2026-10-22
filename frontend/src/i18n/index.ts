import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      appName: "SafeRail",
      tagline: "AI Agent Safety & Control",
      nav: {
        overview: "Overview",
        actionApprovals: "Action Approvals",
        oversightHealth: "Oversight Health",
        auditTrail: "Audit Trail",
        evidenceReports: "Evidence Reports",
        settings: "Settings"
      },
      header: {
        title: "Security Operations",
        subtitle: "Monitor, control and keep your AI agents safe.",
        searchPlaceholder: "Search actions, agents, users...",
        gatewayOnline: "Gateway Online",
        allSystemsOperational: "All systems operational"
      }
    }
  },
  kn: {
    translation: {
      appName: "SafeRail",
      tagline: "ಎಐ ಏಜೆಂಟ್ ಸುರಕ್ಷತೆ ಮತ್ತು ನಿಯಂತ್ರಣ",
      nav: {
        overview: "ಅವಲೋಕನ",
        actionApprovals: "ಕ್ರಿಯೆ ಅನುಮೋದನೆಗಳು",
        oversightHealth: "ಮೇಲ್ವಿಚಾರಣಾ ಕ್ಷಮತೆ",
        auditTrail: "ಆಡಿಟ್ ವಿವರಗಳು",
        evidenceReports: "ಪುರಾವೆ ವರದಿಗಳು",
        settings: "ಸಂಯೋಜನೆಗಳು"
      },
      header: {
        title: "ಸುರಕ್ಷತಾ ಕಾರ್ಯಾಚರಣೆಗಳು",
        subtitle: "ನಿಮ್ಮ AI ಏಜೆಂಟ್‌ಗಳನ್ನು ಮೇಲ್ವಿಚಾರಣೆ ಮಾಡಿ, ನಿಯಂತ್ರಿಸಿ ಮತ್ತು ಸುರಕ್ಷಿತವಾಗಿರಿಸಿ.",
        searchPlaceholder: "ಕ್ರಿಯೆಗಳು, ಏಜೆಂಟ್‌ಗಳು, ಬಳಕೆದಾರರನ್ನು ಹುಡುಕಿ...",
        gatewayOnline: "ಗೇಟ್‌ವೇ ಸಕ್ರಿಯವಾಗಿದೆ",
        allSystemsOperational: "ಎಲ್ಲಾ ವ್ಯವಸ್ಥೆಗಳು ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತಿವೆ"
      }
    }
  },
  hi: {
    translation: {
      appName: "SafeRail",
      tagline: "एआई एजेंट सुरक्षा एवं नियंत्रण",
      nav: {
        overview: "अवलोकन",
        actionApprovals: "कार्रवाई अनुमोदन",
        oversightHealth: "निगरानी स्वास्थ्य",
        auditTrail: "ऑडिट ट्रेल",
        evidenceReports: "साक्ष्य रिपोर्ट",
        settings: "सेटिंग्स"
      },
      header: {
        title: "सुरक्षा संचालन",
        subtitle: "अपने एआई एजेंटों की निगरानी करें, नियंत्रित करें और उन्हें सुरक्षित रखें।",
        searchPlaceholder: "कार्रवाइयां, एजेंट, उपयोगकर्ता खोजें...",
        gatewayOnline: "गेटवे ऑनलाइन",
        allSystemsOperational: "सभी प्रणालियां चालू हैं"
      }
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
