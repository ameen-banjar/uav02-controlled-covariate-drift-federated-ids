# تصميم مجمَّد — الورقة الثانية: Controlled Concept/Channel Drift في FL

**تاريخ التجميد:** 2026-09-25
**الحالة:** مجمَّد ومُختَّم زمنيًا (git commit + tag `uav02-confirmatory-freeze-v1` + `SHA256SUMS`) **قبل أي تنفيذ confirmatory**. لا يُعدَّل إلا بقرار صريح موثَّق في سجل التعديلات أدناه.
**نطاق هذا الملف:** يفصل صراحة بين **calibration phase** (v2/v3، منجزة، بذرة 11) و**confirmatory phase** (5 بذور جديدة، لم تبدأ عند كتابة هذا الملف)، ويحدد الـendpoints والـgates والكود والإعدادات قبل تشغيل أول بذرة.

**قاعدة الصياغة (ملزمة):** في الورقة تُستخدم عبارة **"pre-specified and frozen before confirmatory execution (commit `<hash>`, tag `uav02-confirmatory-freeze-v1`)"**. كلمة **"pre-registered"** لا تُستخدم إلا إذا وُجد سجل عام مؤرَّخ (Zenodo/GitHub release/OSF) يثبت ذلك؛ الـcommit المحلي وحده لا يكفي لهذه الكلمة.

---

## 0. القرار: GO — Freeze, timestamp, then run five fresh confirmatory seeds

لا pilot إضافي. لا تغيير في magnitude ولا schedules ولا features ولا الخوارزميات ولا الجولات ولا recovery windows ولا قائمة البذور. **حتى لو جاءت النتائج التأكيدية أضعف من pilot لا تُعاد calibration** — هذا هو الاختبار الفعلي لـUAV-02، وأي divergence عن pilot **تصبح نتيجة** (كما في UAV-01) لا سببًا لإعادة الضبط.

**لا يُستشهد بأي رقم من v2/v3 في الورقة كدليل تأكيدي.** أي رقم منهما يُوسَم "calibration pilot, single development seed, not confirmatory".

---

## 1. Calibration Phase (v2/v3) — مُنجزة، مُغلقة، غير قابلة للاستشهاد كدليل

### الغرض (موثَّق بأثر رجعي قبل أي تشغيل تأكيدي)
استُخدم v2 (بذرة واحدة، بلا recovery phase لـsudden/gradual، magnitude=0.40/0.35) ثم v3 (نفس البذرة 11، بعد تعديلين قررهما الباحث بعد رؤية v2: إضافة recovery phases، ورفع magnitude إلى 0.60/0.50) لضبط: (1) identifiability، (2) onset، (3) recovery window، (4) non-catastrophic magnitude. **لأن magnitude والـschedules عُدِّلت بعد رؤية pilot، فنتائج v2/v3 ليست confirmatory بطبيعتها.**

### ما لا يجوز اعتباره v2/v3
دليل تأكيدي على أي ادعاء رقمي؛ أو مصدرًا للتباين بين البذور (بذرة واحدة فقط).

### 1.1 ملاحظات calibration الوصفية (seed=11) — مقيَّدة الصياغة
- **Recovery (صياغة ملزمة):** "The Regular-class effect is rapidly reversible after drift removal, while aggregate performance approaches the clean-control trajectory over subsequent rounds."
- **Regular→MITM:** ~1–2% في window1 إلى 22–54% في window2 (recurring)؛ متسق بين FedAvg/FedProx.
- **Class-specificity:** DoS غير متأثر (0.00–0.01%)؛ Injection وUnauth انخفضتا في window2؛ Video وRegular تصاعدتا. **ضد** "الـperturbation تصنع MITM آليًا" — تُسجَّل كـclass-specific response.
- **الفحص الهندسي:** مختلط (IAT/Drate/flow_active_time تقترب من MITM؛ Rate/Srate/Duration/Entropy تبتعد). العبارة: "a partial, feature-specific overlap, not a wholesale geometric conversion."
- **Model-state susceptibility:** انهيار logit margin (Regular−MITM) أكبر ~3× عند round30 مقارنة بround15 تحت نفس perturbation (FedAvg −1.94→−5.99؛ FedProx −1.76→−5.38) بينما الأداء النظيف لا يتدهور؛ ونموذج `none` (بلا تعرض لأي drift) أظهر النمط نفسه (FedAvg −1.97→−6.10؛ FedProx −1.77→−5.53).
  **الصياغة الملزمة:** "strongly supports / is consistent with a training-stage susceptibility explanation and directly distinguishes it from prior-drift-exposure accumulation under the tested protocol." **ممنوع:** "proves", "conclusively".
- **ما اكتُشف في pilot لا يُقدَّم لاحقًا كفرضية أصلية للمشروع.** H1 وH2 (§3.3) اكتُشفتا في calibration؛ تُختبران prospectively في بذور جديدة، وتُذكران في الورقة بهذه الصفة صراحة.

---

## 2. سياسة البذور

- **seed=11:** "development/calibration seed". **لا تدخل** في أي اختبار أو تقدير أو CI confirmatory.
- **البذور المجمَّدة:** **`21, 32, 43, 54, 65`** — جديدة كليًا، لا تتقاطع مع 11.
- **لا استبدال ولا حذف ولا إعادة سحب:** لا تُستبدل بذرة إذا أعطت نتيجة سيئة أو divergence أو انهيارًا؛ الـdivergence نفسها outcome تُبلَّغ كما هي (سابقة UAV-01: FedAvg انهارت في بذرتين وأُبلغ ذلك).
- كل جدول/رقم في الورقة يذكر البذور المستخدمة.

---

## 3. الـEndpoints (مُعرَّفة مسبقًا) — هرم واضح

### 3.0 ثلاث طبقات منفصلة (لا تُخلط، لمنع تكرار خطأ recovery metric القديم)
| الطبقة | السؤال | التعريف | البيانات |
|---|---|---|---|
| **L1 Immediate drift effect** | ما أثر الـdrift على **نفس حالة النموذج** الآن؟ | `DriftResponse_{m,r} = M^drifted_r − M^clean_r` (نفس النموذج، نفس صفوف Validation، الميزات فقط تُحرَّف — counterfactual داخل التشغيل) | schedule run |
| **L2 Training-history effect** | هل التدريب تحت drift غيّر النموذج نفسه (على بيانات نظيفة)؟ | `HistGap_{m,r} = M^schedule_clean,r − M^none_clean,r` أثناء فترة التعرض (strength>0) | schedule run مقابل `none` بنفس البذرة/الخوارزمية/الجولة |
| **L3 Recovery** | هل يعود الأداء النظيف بعد إزالة الـdrift؟ | `RecoveryGap_{m,r} = M^schedule_clean,r − M^none_clean,r` فقط داخل فترات strength==0 بعد الإزالة | نفسه |

ملاحظة: `delta` داخل الجولة نفسها **لا يصلح** لقياس recovery — يساوي 0 بالبناء متى عاد strength=0 (drifted≡clean). لذلك L3 دائمًا مقابل `none`. قبل onset يجب أن يكون `gap≈0` (trajectories متطابقة بنفس البذرة) — يُبلَّغ كفحص سلامة.
`m` ∈ {macro-F1 (على 9 فئات موجودة في Validation؛ Password Cracking غائبة عنها)، Regular recall}. الإشارة: سالب = عجز.

### 3.1 PRIMARY — Controlled drift response (L1)
- **المقياسان:** `ΔmacroF1` و`ΔRegular recall` (class-level outcome المحدد مسبقًا؛ Regular لأن عملاء الـdrift هم أعلى 5 عملاء حصةً منها، وهو مقياس خطة الورقة منذ البداية).
- **الإحصاءة لكل (بذرة، خوارزمية، schedule):** متوسط `DriftResponse` على **كل جولات full-strength** (strength==1): sudden 15–29؛ gradual 20–24؛ recurring 15–21 و30–36 معًا.
- **يُبلَّغ دائمًا:** لكل بذرة على حدة، المتوسط، SD، min/max، فاصل t وصفي 95% عبر البذور، effect size `d_z = mean/SD`؛ بالإضافة إلى **profile الفئات** (Δ recall لكل فئة) كوصف class-level. لا p-values.
- **Directional replication gate (ليس اختبار دلالة):** الأثر سالب في ≥4 من 5 بذور لكلا المقياسين، لكل (خوارزمية × schedule). الـgate يثبت الاتجاه فقط؛ حجم الأثر يُفسَّر من effect sizes لا من العدّ.
- ملاحظة صريحة: macro-F1 قد يُخفي التأثير لأن MITM recall يرتفع تحت الـdrift (في pilot)؛ لهذا Regular recall وprofile الفئات جزء من الـendpoint الأساسي.

### 3.2 SECONDARY — L2 و L3
- **L2:** `HistGap` متوسطًا على جولات التعرض، لكل بذرة.
- **L3 RecoveryGap — نقاط القياس (مُعرَّفة الآن، تصحيح قبل التجميد):** لكل فترة استعادة `[a, b]` (سلسلة جولات strength==0 بعد الإزالة): **immediate = a**؛ **+5 = a+5** و**+10 = a+10** فقط إن وقعت داخل نفس الفترة؛ **residual = b** (آخر clean round في الفترة). الفترات: sudden [30,45]؛ gradual [35,45]؛ recurring [22,29] و[37,45]. (بذلك لا يقع +10 من round22 داخل window2.)
- نفس التقارير: per-seed، mean، SD، range، فاصل وصفي، `d_z`.

### 3.3 H1 و H2 — فرضيات ثانوية prospective (اكتُشفتا في pilot، لذلك ليستا primary ولا "أصلية")
**H1 — training-stage susceptibility.** *For an identical drift transform, susceptibility may increase with training stage even without prior drift exposure.*
- الاختبار: checkpoints جدول **`none`** عند جولات ثابتة، تحت **strength=1 اصطناعي** (نفس `apply_drift`). `margin = mean(logit[Regular] − logit[MITM])` على صفوف Regular الحقيقية في Validation؛ `drop_r = margin(strength=1) − margin(clean)`؛ التباين `S = drop_30 − drop_15` (سالب = انهيار أكبر لاحقًا). الجولات المسجلة {5,10,…,45} للوصف؛ **التباين المؤكِّد فقط 15 مقابل 30**.
- **Gate اتجاهي:** `S<0` في ≥4/5 بذور **في كل خوارزمية**. يُبلَّغ معه `S` per-seed، mean، SD، range، `d_z`، ومنحنى الجرعة الوصفي.

**H2 — class-specific drift response toward MITM.**
`Δ(c→MITM) = rate_drifted − rate_clean` للفئة الحقيقية c، متوسطًا على كل جولات full-strength مجمَّعة عبر الجداول الثلاثة (كل جولة بوزن متساوٍ).
- **H2a (class-specificity):** `Δ(DoS→MITM) < 0.01` و`max_c Δ > 0.10`.
- **H2b (الانتقالات المراقَبة):** `Δ(Regular→MITM) ≥ 0.05` و`Δ(Video→MITM) ≥ 0.05`.
- كلٌّ منهما: ≥4/5 بذور في كل خوارزمية. **لا يصبح finding إلا إذا تكرر عبر البذور.** لا تعديل على drift generator بناءً على calibration وحدها.

**قاعدة عامة لكل الـgates:** "≥4/5" gate اتجاهي مجمَّد الآن، وليس دلالة إحصائية؛ يُقرن دائمًا بـeffect sizes وتوزيع القيم عبر البذور، لا بالعدّ وحده. الفواصل وصفية (t، n=5).

---

## 4. عناصر مجمَّدة والكود ومسار التنفيذ

| العنصر | القيمة المجمَّدة |
|---|---|
| Magnitude | `MAX_MULTIPLICATIVE_SHIFT=0.60`, `MAX_ENTROPY_SHIFT=0.50` |
| Sudden | step فوري: strength=1 للجولات 15–29، 0 بعدها |
| Gradual | ramp-up 10→20، hold حتى 25، ramp-down 25→35 |
| Recurring | نوافذ `[(15,22),(30,37)]` |
| Features | Down: Rate,Srate,Drate — Up: IAT,flow_active_time,Duration — Entropy (floor عند P5) |
| عملاء الـdrift | `[11,1,14,10,9]` |
| الخوارزميات | FedAvg، FedProx (μ=0.01) |
| الجولات | 45 ثابتة، بلا اختيار أفضل checkpoint؛ `held_out_test` لا يُمَس |
| البذور | 21, 32, 43, 54, 65 |

**الكود المجمَّد** (نسخ في `code/` بنفس البنية النسبية، مع `SHA256SUMS`): `drift.py`, `data.py`, `model.py`, `algorithms.py`, `run_drift_confirmatory.py`, `analyze_confirmatory.py`, `prepare_isot.py`, `federated_clients_manifest.json`.
- `run_drift_confirmatory.py` **يرفض التشغيل** ما لم: (أ) البذرة ضمن القائمة المجمَّدة، (ب) hash كل ملف مصدر يطابق `SHA256SUMS`، (ج) مستودع التجميد نظيف وHEAD موسوم `uav02-confirmatory-freeze-v1`. ويكتب `provenance_seed*.json` (commit + hashes) مع النتائج.
- التشغيل: عملية لكل بذرة (بالتوازي حتى 3 عمليات)؛ التوازي لا يغيّر التصميم لأن كل بذرة مستقلة بالكامل.
- **اختبارات ما قبل التجميد (ليست confirmatory):** (1) smoke test للـrunner ببذرة وهمية 999 و3 جولات وdrift قسري، في مجلد مؤقت خارج مجلد النتائج؛ (2) اختبار `analyze_confirmatory.py` على بيانات اصطناعية مشتقة من v3 pilot لفحص المنطق فقط.
- **بعد الـcommit:** لا تعديل على هذه الملفات أثناء التشغيل إلا لخلل تنفيذي موثَّق لا يغيّر التصميم: يُسجَّل في السجل أدناه (الخلل، الدليل أنه لا يمس التصميم)، ويصدر commit/tag جديد، وتُعاد فقط التشغيلات المتأثرة **بنفس البذرة**. تعديل أي عنصر من الجدول أعلاه ليس "خللًا تنفيذيًا".
- **أقوى provenance (اختياري، بقرار الباحث):** GitHub release / Zenodo snapshot للـtag؛ عندها فقط تصح كلمة pre-registered.

---

## 5. بوابات القرار بعد اكتمال البذور الخمس

| الملاحظة (عبر البذور) | القرار |
|---|---|
| Primary gates ناجحة مع effect sizes ذات معنى؛ L3 قريب من صفر؛ H1/H2 متكررة | ورقة كاملة: drift response قابل للتحديد + recovery + H1/H2 كـfindings ثانوية مؤكَّدة اتجاهيًا |
| Primary ناجح، H1 و/أو H2 لم تتكرر | تُبلَّغ كـ"calibration-pilot observation, not replicated" في Limitations؛ لا تُحذف |
| Primary ضعيف/غير متسق عبر البذور أو الخوارزميتين | يُبلَّغ كما هو (divergence = outcome)؛ لا إعادة calibration ولا تغيير magnitude/schedules؛ تُعاد صياغة الادعاء ليطابق ما تحمله البيانات |
| L3 لا يقترب من الصفر بثبات | لا يُوصف الأثر "reversible"؛ يُوصف كعجز متبقٍّ بحجمه |
| تباين كبير بين البذور | يُعرض التوزيع الكامل per-seed؛ لا يُخفى وراء متوسط |

---

## سجل التعديلات

- 2026-09-25 (أ): إنشاء التصميم المجمَّد بعد six-diagnostic protocol على v3 (calibration، seed=11) واختبار ضابط `none`. قرار GO.
- 2026-09-25 (ب) — **مراجعة قبل الـcommit، بلا أي تنفيذ confirmatory:** (1) هيكلة الـendpoints: Primary = controlled drift response (L1)؛ RecoveryGap وL2 ثانويان؛ H1/H2 ثانويتان prospective (اكتُشفتا في pilot). (2) حذف endpoint "onset detectability = pre-onset delta≈0" من المسودة (أ) لأنه tautological بالبناء (strength=0 ⇒ drifted≡clean). (3) تصحيح نقاط recovery: +k وresidual داخل فترة strength==0 نفسها (المسودة (أ) كانت تضع +10 من round22 داخل window2، وresidual=45 لكل الحالات). (4) استبدال "pre-registered" بـ"pre-specified and frozen" وتحديد شرط استخدام الكلمة الأولى. (5) تثبيت البذور 21,32,43,54,65 ومنع الاستبدال. (6) إضافة كود runner/analysis وآلية الرفض عند عدم تطابق الـhash. (7) إضافة عتبات H2 (0.01/0.10/0.05) وتعريف H1 gate. عُدِّل أيضًا `results_drift/analyze_v3.py` (calibration فقط) بنفس تصحيح نقاط recovery.
