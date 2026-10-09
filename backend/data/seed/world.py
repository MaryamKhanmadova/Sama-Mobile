"""Synthetic world builder: customers, lines and a realistic event timeline per line.

All data is fictional (Səma Mobile does not exist). Timestamps are ISO-8601 with the Baku offset (+04:00),
so lexicographic order == chronological order.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app import catalog as C

BAKU = timezone(timedelta(hours=4))

FIRST_M = ["Elvin", "Rəşad", "Tural", "Orxan", "Kamran", "Ülvi", "Murad", "Anar", "Ramil", "Emin", "Fərid",
           "Samir", "Vüsal", "Nicat", "Rauf", "Cavid", "İlkin", "Toğrul"]
FIRST_F = ["Aysel", "Leyla", "Nigar", "Günay", "Səbinə", "Fidan", "Lalə", "Nərmin", "Səidə", "Aytən", "Könül",
           "Ülkər", "Şəbnəm", "Arzu", "Gülnar", "Xədicə", "Zəhra", "Aynur"]
LAST = ["Məmmədov", "Əliyev", "Hüseynov", "Quliyev", "Həsənov", "İsmayılov", "Rzayev", "Kərimov", "Abbasov",
        "Nəbiyev", "Cəfərov", "Bayramov", "Süleymanov", "Qasımov", "Mustafayev"]
RU_NAMES = [("Ирина", "Петрова", "F"), ("Сергей", "Иванов", "M"), ("Наталья", "Смирнова", "F"),
            ("Андрей", "Кузнецов", "M"), ("Елена", "Волкова", "F"), ("Дмитрий", "Морозов", "M")]

DEVICES = [
    {"model": "Samsung Galaxy A54", "os": "Android 14", "supports_volte": True, "supports_esim": True, "supports_5g": True},
    {"model": "Xiaomi Redmi Note 12", "os": "Android 13", "supports_volte": True, "supports_esim": False, "supports_5g": False},
    {"model": "iPhone 13", "os": "iOS 18", "supports_volte": True, "supports_esim": True, "supports_5g": True},
    {"model": "iPhone 11", "os": "iOS 17", "supports_volte": True, "supports_esim": True, "supports_5g": False},
    {"model": "Samsung Galaxy A14", "os": "Android 13", "supports_volte": True, "supports_esim": False, "supports_5g": False},
    {"model": "Nokia 105", "os": "Series 30+", "supports_volte": False, "supports_esim": False, "supports_5g": False},
    {"model": "Tecno Spark 10", "os": "Android 13", "supports_volte": False, "supports_esim": False, "supports_5g": False},
]

DATA_CATEGORIES = ["video", "social", "browsing", "music", "messaging", "games", "maps"]


def r2(x: float) -> float:
    return round(x + 1e-9, 2)


class World:
    def __init__(self, now: datetime, seed: int = 42):
        self.now = now
        self.rng = random.Random(seed)
        self.customers: list[dict] = []
        self.lines: list[dict] = []
        self.events: list[dict] = []
        self.incidents: list[dict] = []
        self.tickets: list[dict] = []
        self._eid = 0
        self._msisdn_seq = 0
        self._cust_seq = 0

    # ---------- ids ----------
    def next_event_id(self) -> str:
        self._eid += 1
        return f"E{self._eid:06d}"

    def next_msisdn(self) -> str:
        self._msisdn_seq += 1
        return f"+99498{1000000 + self._msisdn_seq * 137:07d}"[:13]

    def next_customer_id(self) -> str:
        self._cust_seq += 1
        return f"C{self._cust_seq:05d}"

    def ts(self, days_ago: float, hh: int = 12, mm: int = 0, ss: int = 0) -> str:
        base = (self.now - timedelta(days=int(days_ago))).replace(hour=hh, minute=mm, second=ss, microsecond=0)
        if base > self.now:
            base = self.now - timedelta(minutes=5)
        return base.isoformat()

    def incident(self, region: str, start: str, end: str | None, severity: str, services: list[str], summary: str,
                 eta: str | None = None) -> str:
        iid = f"INC-{len(self.incidents) + 1:04d}"
        self.incidents.append({
            "incident_id": iid, "region": region, "start_ts": start, "end_ts": end,
            "status": "resolved" if end else "ongoing", "severity": severity, "services": services,
            "summary_az": summary, "eta": eta,
        })
        return iid


class LineBuilder:
    """Builds one customer + one line with a coherent timeline. Call finalize() at the end."""

    def __init__(self, w: World, *, name: str | None = None, gender: str | None = None, lang: str = "az",
                 tariff: str = "T_PLUS", region: str = "Bakı-Nəsimi", tenure_months: int = 24,
                 birth_year: int | None = None, segment: str = "prepaid", device: dict | None = None,
                 settings: dict | None = None, vulnerable: bool = False, notes: str = "",
                 start_balance: float | None = None, renewal_days_ago: int = 12, base_life: bool = True,
                 data_until_days_ago: float | None = None, sim_type: str = "physical", city: str | None = None,
                 topup_extra: float | None = None):
        self.w = w
        rng = w.rng
        self.msisdn = w.next_msisdn()
        self.customer_id = w.next_customer_id()
        if name is None:
            if lang == "ru":
                fn, ln, gender = rng.choice(RU_NAMES)
                name = f"{fn} {ln}"
            else:
                gender = gender or rng.choice("MF")
                fn = rng.choice(FIRST_M if gender == "M" else FIRST_F)
                ln = rng.choice(LAST) + ("a" if gender == "F" else "")
                name = f"{fn} {ln}"
        self.lang = lang
        self.tariff = tariff
        self.region = region
        self.tenure_months = tenure_months
        self.birth_year = birth_year or rng.randint(1965, 2003)
        self.device = dict(device or rng.choice(DEVICES[:5]))
        self.settings = {"roaming_enabled": False, "data_enabled": True, "volte": self.device["supports_volte"],
                         "auto_renew": True, "premium_sms_blocked": False}
        self.settings.update(settings or {})
        self.events: list[dict] = []
        self.active_vas: set[str] = set()
        self.status = "active"
        self.sim = {"type": sim_type, "iccid_last4": f"{rng.randint(0, 9999):04d}", "pin_status": "ok",
                    "puk": f"{rng.randint(10_000_000, 99_999_999)}"}
        self.postpaid: dict | None = None
        self.renewal_days_ago = renewal_days_ago
        self.start_balance = start_balance
        self.topup_extra = topup_extra
        fin_last4 = f"{rng.randint(1000, 9999)}"
        self.customer = {
            "customer_id": self.customer_id, "full_name": name, "gender": gender, "birth_year": self.birth_year,
            "fin_last4": fin_last4, "language": lang, "city": city or region.split("-")[0],
            "email_masked": f"{name.split()[0][:1].lower()}***@mail.example", "contact_pref": rng.choice(["sms", "call", "app"]),
            "tenure_months": tenure_months, "segment": segment,
            "loyalty_tier": "gold" if tenure_months >= 60 else "silver" if tenure_months >= 24 else "standard",
            "vulnerable": vulnerable, "satisfaction_score": rng.choice([3, 4, 4, 5]),
            "kyc_status": "verified", "consent_marketing": rng.random() < 0.4, "notes": notes,
            "lines": [self.msisdn], "created_at": (w.now - timedelta(days=30 * tenure_months)).isoformat(),
        }
        self.segment = segment
        if base_life:
            self.base_life(data_until_days_ago=data_until_days_ago)

    # ---------- primitive events ----------
    def ev(self, ts: str, type_: str, channel: str | None = None, **data) -> str:
        eid = self.w.next_event_id()
        self.events.append({"msisdn": self.msisdn, "ts": ts, "event_id": eid, "type": type_,
                            "channel": channel, "data": data})
        return eid

    def charge(self, ts: str, amount: float, reason: str, ref: str | None = None, channel: str | None = None,
               **data) -> str:
        if C.TARIFFS[self.tariff].get("postpaid"):
            data["invoice"] = True
        return self.ev(ts, "CHARGE", channel=channel, amount=r2(amount), reason=reason, ref=ref, **data)

    def topup(self, ts: str, amount: float, method: str = "card_app", credited: bool = True,
              promo_grant: bool = True) -> str:
        """PAYMENT (+ TOPUP if credited). App top-ups >= 10 AZN in the current month are eligible for the
        Yüklə-Qazan promo; normally the bonus is granted, promo_grant=False simulates the bug."""
        pid = f"PAY-{self.w.rng.randint(10**7, 10**8 - 1)}"
        self.ev(ts, "PAYMENT", channel=method, payment_id=pid, amount=r2(amount), status="success", purpose="topup")
        if credited:
            self.ev(ts, "TOPUP", channel=method, payment_id=pid, amount=r2(amount))
            promo = C.PROMOS["PR_YUKLE2GB"]
            month_start = self.w.now.replace(day=1, hour=0, minute=0, second=0).isoformat()
            if method == "card_app" and amount >= promo["min_topup"] and ts >= month_start:
                self.ev(ts, "PROMO_ELIGIBLE", channel=method, promo_id="PR_YUKLE2GB", payment_id=pid)
                if promo_grant:
                    t2 = (datetime.fromisoformat(ts) + timedelta(minutes=3)).isoformat()
                    self.ev(t2, "PROMO_GRANTED", channel="system", promo_id="PR_YUKLE2GB", payment_id=pid,
                            bonus_mb=promo["bonus_mb"])
                    self.activate(t2, "PROMO:PR_YUKLE2GB", None, promo["days"], data_mb=promo["bonus_mb"],
                                  kind="promo")
        return pid

    def last_bundle(self) -> dict | None:
        bundles = [e for e in self.events if e["type"] == "PACKAGE_ACTIVATED" and e["data"]["kind"] == "tariff_bundle"]
        return max(bundles, key=lambda e: e["ts"]) if bundles else None

    def data_day(self, days_ago: int, mb: int, *, in_package: bool, country: str = "AZ", hh: int = 22,
                 cats: dict | None = None, charge: float | None = None, reason: str = "oob_data") -> None:
        """One aggregated DATA_USAGE record; optional charge for out-of-bundle / roaming usage."""
        cats = cats or {"browsing": int(mb * 0.4), "social": int(mb * 0.35), "video": mb - int(mb * 0.4) - int(mb * 0.35)}
        ts = self.w.ts(days_ago, hh, 0)
        self.ev(ts, "DATA_USAGE", mb=mb, in_package=in_package, country=country, by_category=cats)
        if charge is not None:
            self.charge(self.w.ts(days_ago, hh, 1), charge, reason, units_mb=mb, country=country, channel="system")

    def activate(self, ts: str, package_id: str, charge_event_id: str | None, days: int, *,
                 data_mb: int | None = None, voice_min: int | None = None, sms: int | None = None,
                 kind: str = "addon") -> str:
        iid = f"PI-{self.w.rng.randint(10**6, 10**7 - 1)}"
        expires = (datetime.fromisoformat(ts) + timedelta(days=days)).isoformat()
        self.ev(ts, "PACKAGE_ACTIVATED", package_id=package_id, instance_id=iid, charge_event_id=charge_event_id,
                expires_at=expires, data_mb=data_mb, voice_min=voice_min, sms=sms, kind=kind)
        return iid

    def buy_package(self, ts: str, package_id: str, channel: str = "app", trigger: str = "manual",
                    activate: bool = True, device: str | None = None) -> tuple[str, str | None]:
        p = C.PACKAGES[package_id]
        self.ev(ts, "PACKAGE_PURCHASE_REQUEST", channel=channel, package_id=package_id, trigger=trigger,
                device=device or self.device["model"])
        cid = self.charge(ts, p["price"], "package_purchase", ref=package_id, channel=channel, trigger=trigger)
        iid = None
        if activate:
            iid = self.activate(ts, package_id, cid, p["days"], data_mb=p.get("data_mb"), sms=p.get("sms"))
        return cid, iid

    def tariff_renewal(self, ts: str) -> str:
        t = C.TARIFFS[self.tariff]
        cid = self.charge(ts, t["monthly_fee"], "monthly_fee", ref=self.tariff, channel="system")
        self.activate(ts, f"TARIFF:{self.tariff}", cid, 30, data_mb=t.get("data_mb") or t.get("fup_mb"),
                      voice_min=t["voice_min"], sms=t["sms"], kind="tariff_bundle")
        return cid

    def set_setting(self, ts: str, key: str, value, channel: str = "app"):
        old = self.settings.get(key)
        self.ev(ts, "SETTING_CHANGE", channel=channel, setting=key, old=old, new=value)
        self.settings[key] = value

    def vas_subscribe(self, ts: str, vas_id: str, source: str, consent: bool, charge_days: int | None = None,
                      until_days_ago: int = 0) -> None:
        consent_ref = f"OPTIN-{self.w.rng.randint(10**5, 10**6 - 1)}" if consent else None
        self.ev(ts, "VAS_SUBSCRIBE", channel=source, vas_id=vas_id, source=source, consent_confirmed=consent,
                consent_ref=consent_ref)
        self.active_vas.add(vas_id)
        v = C.VAS[vas_id]
        start = datetime.fromisoformat(ts)
        if v["period"] == "gün":
            days = charge_days if charge_days is not None else (self.w.now.date() - start.date()).days
            for d in range(1, days + 1):
                t = (start + timedelta(days=d)).replace(hour=6, minute=0)
                if t > self.w.now - timedelta(days=until_days_ago):
                    break
                self.charge(t.isoformat(), v["price"], "vas", ref=vas_id, channel="system")
        else:
            self.charge((start + timedelta(minutes=1)).isoformat(), v["price"], "vas", ref=vas_id, channel="system")

    # ---------- background life ----------
    def base_life(self, data_until_days_ago: float | None = None, days: int = 40):
        """Normal usage: tariff renewals, daily data/voice in package, top-ups before renewals, app logins."""
        rng, w = self.w.rng, self.w
        t = C.TARIFFS[self.tariff]
        if self.tariff != "T_PAYG":
            for r in (self.renewal_days_ago + 30, self.renewal_days_ago):
                if r > days + 30:
                    continue
                if not t.get("postpaid"):
                    self.topup(w.ts(r + 1, rng.randint(9, 21), rng.randint(0, 59)), t["monthly_fee"] + (self.topup_extra if self.topup_extra is not None else rng.choice([0, 5, 10])),
                               method=rng.choice(["card_app", "terminal", "bank_app"]))
                self.tariff_renewal(w.ts(r, 0, 5))
        else:
            self.topup(w.ts(days - 2, 13, 10), 10, method="terminal")
        for d in range(days, 0, -1):
            if data_until_days_ago is not None and d <= data_until_days_ago:
                break
            mb = rng.randint(150, 900) if self.tariff != "T_PAYG" else rng.randint(5, 40)
            cats = rng.sample(DATA_CATEGORIES, 3)
            split = [0.55, 0.3, 0.15]
            if self.tariff == "T_PAYG":
                # PAYG data is billed out of bundle
                amt = r2(min(mb * C.OOB["data_per_mb"], C.OOB["data_daily_cap"]))
                self.ev(w.ts(d, 22, 0), "DATA_USAGE", mb=mb, in_package=False, country="AZ",
                        by_category={c: int(mb * s) for c, s in zip(cats, split)})
                self.charge(w.ts(d, 22, 1), amt, "oob_data", units_mb=mb, channel="system")
            else:
                self.ev(w.ts(d, 22, 0), "DATA_USAGE", mb=mb, in_package=True, country="AZ",
                        by_category={c: int(mb * s) for c, s in zip(cats, split)})
            if rng.random() < 0.75:
                mins = rng.randint(3, 45)
                self.ev(w.ts(d, 21, 0), "VOICE_USAGE", minutes=mins, calls=max(1, mins // 4),
                        in_package=self.tariff != "T_PAYG", dest={"onnet": mins // 2, "offnet": mins - mins // 2})
                if self.tariff == "T_PAYG":
                    self.charge(w.ts(d, 21, 1), mins * C.OOB["voice_per_min"], "oob_voice", units_min=mins,
                                channel="system")
            if rng.random() < 0.15:
                self.ev(w.ts(d, 20, 0), "SMS_USAGE", count=rng.randint(1, 6), in_package=True)
            if rng.random() < 0.12:
                self.ev(w.ts(d, rng.randint(8, 22), rng.randint(0, 59)), "APP_LOGIN", channel="app",
                        device=self.device["model"], ip_city=self.customer["city"])

    # ---------- finalize ----------
    def finalize(self) -> dict:
        self.events.sort(key=lambda e: (e["ts"], e["event_id"]))
        # running balance
        delta = []
        for e in self.events:
            if e["type"] == "TOPUP" or e["type"] == "ADJUSTMENT" or e["type"] == "LOAN_TAKEN":
                delta.append(e["data"]["amount"])
            elif e["type"] == "CHARGE" and not e["data"].get("invoice"):
                delta.append(-e["data"]["amount"])
            else:
                delta.append(0.0)
        running, min_run = 0.0, 0.0
        for d in delta:
            running += d
            min_run = min(min_run, running)
        if self.start_balance is None:
            start = r2(-min_run + self.w.rng.choice([0.4, 1.2, 2.5, 4.0]))
        else:
            # requested final balance; never let the running balance dip below zero
            start = max(r2(self.start_balance - running), r2(-min_run))
        bal = start
        for e, d in zip(self.events, delta):
            bal = r2(bal + d)
            if d:
                e["data"]["balance_after"] = bal
        line = {
            "msisdn": self.msisdn, "customer_id": self.customer_id, "tariff_id": self.tariff,
            "status": self.status, "balance": r2(bal), "segment": self.segment, "region": self.region,
            "language": self.lang, "activated_at": self.customer["created_at"], "settings": self.settings,
            "device": self.device, "sim": self.sim, "active_vas": sorted(self.active_vas),
            "renewal_day_of_month": (self.w.now - timedelta(days=self.renewal_days_ago)).day,
            "postpaid": self.postpaid,
        }
        self.w.customers.append(self.customer)
        self.w.lines.append(line)
        self.w.events.extend(self.events)
        return line
