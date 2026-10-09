# Sama Care UI localization

AZ, EN and RU are active on both pages through the header buttons. The selection is saved under `sama-care-ui-locale` in localStorage, survives navigation/reload, and updates the HTML language and document title. Switching UI language does not reconnect a text session, clear its draft, or translate the customer/agent transcript.

The first supplied attachment contains Azerbaijani text despite its later described filename; the second contains English text. They are stored as `src/locales/az.json` and `en.json` according to their actual content. Russian copy was prepared for `ru.json`, with the same keys and placeholders. No English file is labelled Russian.

`src/lib/i18n-core.ts` flattens catalogs, interpolates named placeholders and validates catalog consistency. `src/lib/i18n.ts` maintains the locale store and translates static UI labels/errors. `src/components/LanguageSwitcher.tsx` provides keyboard-accessible AZ / EN / RU buttons. Root subscribes once so both pages and their child panels update without remounting the session.

Edit only the `messages` values in each JSON. Preserve identical keys, month-array order, and `{count}`, `{name}`, `{amount}`, etc. Unknown languages fall back to AZ; missing keys fall back to the AZ catalog. Tests reject missing translations and mismatched placeholders.

Backend greetings, scenario descriptions, status labels, case summaries, citations and AI replies remain backend content in their own language. The UI language and the customer's conversation language are independent. ElevenLabs widget internals are controlled by ElevenLabs; its surrounding controls/help are localized here.
