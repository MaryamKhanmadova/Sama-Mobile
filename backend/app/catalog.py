"""Səma Mobile (fictional operator) — single source of truth for products, prices and policy parameters.

The seed generator, the policy engine and the RAG knowledge base (data/kb/*.md) all use these
numbers. If you change a price here, update the matching KB document too.
"""

CURRENCY = "AZN"

TARIFFS = {
    "T_START": {"name": "Səma Start", "monthly_fee": 9.00, "data_mb": 10_240, "voice_min": 300, "sms": 100},
    "T_PLUS": {"name": "Səma Plus", "monthly_fee": 15.00, "data_mb": 25_600, "voice_min": 800, "sms": 300},
    "T_MAX": {"name": "Səma Max", "monthly_fee": 25.00, "data_mb": None, "fup_mb": 61_440,
              "voice_min": 1500, "sms": 500},
    "T_GENC": {"name": "Səma Gənc", "monthly_fee": 7.00, "data_mb": 12_288, "voice_min": 200, "sms": 100,
               "max_age": 25},
    "T_PAYG": {"name": "Səma Sərbəst", "monthly_fee": 0.0, "data_mb": 0, "voice_min": 0, "sms": 0},
    "T_BIZNES": {"name": "Səma Biznes", "monthly_fee": 30.00, "data_mb": 40_960, "voice_min": 2000, "sms": 500,
                 "postpaid": True},
}

PACKAGES = {
    "P_NET5": {"name": "İnternet 5 GB / 7 gün", "price": 3.00, "data_mb": 5_120, "days": 7},
    "P_NET20": {"name": "İnternet 20 GB / 30 gün", "price": 10.00, "data_mb": 20_480, "days": 30},
    "P_GECE": {"name": "Gecə 10 GB (01:00–07:00) / 30 gün", "price": 2.00, "data_mb": 10_240, "days": 30},
    "P_SOSIAL": {"name": "Sosial 10 GB / 30 gün", "price": 4.00, "data_mb": 10_240, "days": 30},
    "P_SMS200": {"name": "200 SMS / 30 gün", "price": 1.50, "sms": 200, "days": 30},
    "P_TR1": {"name": "Rouminq Türkiyə 1 GB / 7 gün", "price": 8.00, "data_mb": 1_024, "days": 7, "country": "TR"},
    "P_GE1": {"name": "Rouminq Gürcüstan 1 GB / 7 gün", "price": 6.00, "data_mb": 1_024, "days": 7, "country": "GE"},
    "P_EU2": {"name": "Rouminq Avropa 2 GB / 10 gün", "price": 20.00, "data_mb": 2_048, "days": 10, "zone": "Z2"},
    "P_FUP10": {"name": "Max sürət əlavəsi 10 GB", "price": 5.00, "data_mb": 10_240, "days": 30},
}

VAS = {
    "V_FAL": {"name": "Ulduz Falı", "price": 0.20, "period": "gün"},
    "V_MELODIYA": {"name": "Səma Melodiya", "price": 1.50, "period": "ay"},
    "V_XEBER": {"name": "Xəbər+", "price": 0.10, "period": "gün"},
    "V_OYUN": {"name": "Oyun Klubu", "price": 0.30, "period": "gün"},
    "V_QORUMA": {"name": "Səma Qoruma", "price": 2.00, "period": "ay"},
}

ROAMING_ZONES = {
    "Z1": {"countries": ["TR", "GE", "RU", "IR"], "data_per_mb": 0.50, "call_out": 0.60, "call_in": 0.30, "sms": 0.20},
    "Z2": {"countries": ["DE", "FR", "IT", "ES", "AE", "GB", "NL"], "data_per_mb": 1.00, "call_out": 1.20,
           "call_in": 0.60, "sms": 0.30},
    "Z3": {"countries": ["*"], "data_per_mb": 3.00, "call_out": 3.00, "call_in": 1.50, "sms": 0.50},
}
COUNTRY_NAMES = {"TR": "Türkiyə", "GE": "Gürcüstan", "RU": "Rusiya", "IR": "İran", "DE": "Almaniya",
                 "FR": "Fransa", "IT": "İtaliya", "ES": "İspaniya", "AE": "BƏƏ", "GB": "Böyük Britaniya",
                 "NL": "Niderland", "US": "ABŞ", "AZ": "Azərbaycan"}

INTL_CALL_RATES = {"TR": 0.45, "RU": 0.40, "GE": 0.35, "EU": 0.70, "OTHER": 1.20}

OOB = {"data_per_mb": 0.05, "data_daily_cap": 3.00, "voice_per_min": 0.08, "sms": 0.05}

LOAN = {"amounts": {1: 0.10, 2: 0.20, 3: 0.30}, "min_tenure_months": 3}
BALANCE_TRANSFER = {"fee": 0.10, "min": 0.50, "max_per_day": 20.00}
LATE_FEE = 2.00

PROMOS = {"PR_YUKLE2GB": {"name": "Yüklə-Qazan: 10 AZN+ yükləməyə 2 GB bonus", "bonus_mb": 2_048, "days": 7,
                          "min_topup": 10.00, "channel": "app"}}

# Policy parameters (referenced by rule IDs in data/kb/billing-refunds.md and app/agent/policy.py)
POLICY = {
    "auto_credit_max_per_case": 20.00,      # R-ADJ-01
    "auto_credits_per_30d": 2,              # R-ADJ-02
    "goodwill_min_tenure_months": 24,       # R-GW-01
    "goodwill_share": 0.5,
    "goodwill_max": 3.00,
    "goodwill_cooldown_days": 180,
    "topup_credit_grace_min": 30,           # R-PAY-01
    "package_activation_grace_min": 10,     # R-PKG-02
    "outage_tiers": [(24, 5.00), (12, 3.00), (4, 1.00)],  # R-NET-02: (min hours, AZN)
    "repeat_contact_threshold": 2,          # R-ESC-02
}

TEAMS = {
    "BILLING": {"az": "hesablaşma üzrə mütəxəssis", "ru": "специалист по расчётам", "sla_az": "2 saat",
                "sla_ru": "2 часов"},
    "NETWORK": {"az": "şəbəkə mühəndisi", "ru": "сетевой инженер", "sla_az": "24 saat", "sla_ru": "24 часов"},
    "SECURITY": {"az": "təhlükəsizlik qrupu", "ru": "служба безопасности", "sla_az": "15 dəqiqə",
                 "sla_ru": "15 минут"},
    "PORTING": {"az": "nömrə köçürmə üzrə mütəxəssis", "ru": "специалист по переносу номера",
                "sla_az": "4 saat", "sla_ru": "4 часов"},
    "CORPORATE": {"az": "korporativ müştəri meneceri", "ru": "менеджер корпоративных клиентов",
                  "sla_az": "4 iş saatı", "sla_ru": "4 рабочих часов"},
    "COMPLAINTS": {"az": "şikayətlər üzrə baş mütəxəssis", "ru": "старший специалист по жалобам",
                   "sla_az": "1 iş günü", "sla_ru": "1 рабочего дня"},
    "RECORDS": {"az": "müştəri qeydləri şöbəsi", "ru": "отдел клиентских данных", "sla_az": "1 iş günü",
                "sla_ru": "1 рабочего дня"},
    "DEVICE": {"az": "cihaz və nisyə ödəniş üzrə mütəxəssis", "ru": "специалист по рассрочке устройств",
               "sla_az": "4 saat", "sla_ru": "4 часов"},
}

REGIONS = ["Bakı-Nəsimi", "Bakı-Xətai", "Bakı-Yasamal", "Bakı-Nərimanov", "Sumqayıt", "Gəncə", "Şəki",
           "Lənkəran", "Quba", "Mingəçevir", "Şamaxı", "Qəbələ"]


def zone_for(country: str) -> str:
    for zone, z in ROAMING_ZONES.items():
        if country in z["countries"]:
            return zone
    return "Z3"
