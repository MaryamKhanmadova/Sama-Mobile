# Balansın artırılması və ödənişlər
> doc_id: topup-payments · kateqoriya: ödəniş · qaydalar: R-PAY-01

## Ödəniş üsulları
Səma tətbiqində bank kartı ilə, bank tətbiqlərində, ödəniş terminallarında və satış nöqtələrində. Minimum yükləmə 1 AZN, komissiya yoxdur.
Açar sözlər (RU): пополнить баланс, оплата картой, терминал
Danışıq dilində: balans sıfırdır, pul yükləmək istəyirəm, internet kəsilib çünki pul qalmayıb.

## Balansa düşmə müddəti
Ödəniş adətən dərhal, ən gec 15 dəqiqə ərzində balansa yazılır. Səma Kredit borcu varsa, borc və komissiya yükləmədən avtomatik kəsilir (bax: kredit).
**R-PAY-01:** Ödəniş uğurlu olub (kartdan çıxılıb), amma 30 dəqiqə ərzində balansa yazılmayıbsa, məbləğ ödəniş nömrəsi (payment_id) ilə yoxlanılır və balansa yazılır.
Açar sözlər (RU): деньги не пришли на баланс, списали с карты, платёж не зачислен

## Uğursuz ödəniş
Ödəniş uğursuz olubsa, kartda bloklanan məbləği bank 3–5 iş günü ərzində azad edir.
Açar sözlər (RU): ошибка оплаты, платёж не прошёл
