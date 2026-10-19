"""Parses the channel's hymn video titles into year, stage, level and the hymn name."""
import re

AR_DIG = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

STAGES = [  # (regex, id, english)
    (r'حضان[ةه]', 'kg', 'KG'),
    (r'أولى?\s*و\s*(?:ثانية|تانية|ثانيه)|اولى\s*و\s*(?:ثانية|تانية)|أولى وثانية|الحان أولى و ثانية', 'grades-1-2', 'Grades 1–2'),
    (r'ثالث[ةه]\s*و\s*رابع[ةه]', 'grades-3-4', 'Grades 3–4'),
    (r'خامس[ةه]\s*و\s*سادس[ةه]', 'grades-5-6', 'Grades 5–6'),
    (r'إعداد[يى]|اعداد[يى]|الإعدادية|الاعدادية', 'ms', 'Middle school'),
    (r'ثانو[يى]|الثانوية', 'hs', 'High school'),
    (r'جامع[ةه]|الجامعية', 'college', 'College'),
    (r'خريج', 'graduates', 'Graduates'),
    (r'خدام', 'servants', 'Servants'),
    (r'قانا الجليل', 'cana-family', 'Cana of Galilee (families)'),
    (r'سمعان الشي', 'simeon-elders', 'St. Simeon (elders)'),
    (r'ديديموس', 'didymus', 'St. Didymus (visually impaired)'),
    (r'الهمم|القدرات', 'special-needs', 'Special needs'),
    (r'تعليم كبار|تعليم الكبار|حرفي', 'adult-learners', 'Adult learners'),
]

LEVELS = [
    (r'موهوب|موهب|الموهوبين|متميز الفردى|التميز الفردى|تميز فردى|التميز الجماعى|تميز جماعى|مستوى التميز|المستوى المتميز|متميز|التميز', 'gifted', 'Gifted'),
    (r'(?:المستو[يى]|مستو[يى])\s*(?:ال)?(?:أول|اول|الاول|الأول)|م\s*1\b|م١|مستوى1|المستوىالأول|المستوى 1', '1', 'Level 1'),
    (r'(?:المستو[يى]|مستو[يى]|المساوى)\s*(?:ال)?(?:ثان[يى]|تان[يى]|الثانى|التانى|الثاني|التاني)|م\s*2\b|م٢|المستوى2|المستوى 2', '2', 'Level 2'),
    (r'إجبار|اجبار', 'required', 'Required'),
]

def year_of(t):
    t2 = t.translate(AR_DIG)
    m = re.findall(r'20(2[0-9])', t2)
    return int('20' + m[-1]) if m else None

def first(rules, t):
    for rx, i, en in rules:
        if re.search(rx, t): return i
    return None

# pieces of a title that are about the festival, not the hymn
NOISE = [
    r'(?:أ?ال|أ)?[اأ]?لحان\s+مهرجان\s+الكر[اأ]?زة(?:\s+المرقسية)?\s*[0-9٠-٩]*',
    r'مهرجان\s+الكر[اأز]+ة?\s*(?:الم[رو]قسية)?\s*[0-9٠-٩]*', r'مهرجان\s*[0-9٠-٩]+', r'مهوجان.*', r'لمهرجان.*',
    r'(?:أ?ال|أ)?[اأ]?لحان\s+(?:ال)?(?:مرحلة|المرحلة)\s+\S+', r'(?:ال)?مرحل[ةه]\s+\S+(?:\s+و\s*\S+)?(?:\s+ابتدائ[يى])?',
    r'(?:أ?ال|أ)?[اأ]?لحان\s+(?:أسرة|اسرة|آسرة)[^-]*', r'(?:أسرة|اسرة|آسرة)[^-]*', r'(?:أ?ال|أ)?[اأ]?لحان\s+(?:شباب\s+)?(?:ال)?خريج\S*',
    r'شباب\s+الخريج\S*', r'(?:أ?ال|أ)?[اأ]?لحان\s+(?:تعليم|ذوى|خدام|اعداد|قانا|سمعان|ثانوى|أولى|ثالثة|خامسة|المرحلة|مرحلة)[^-]*',
    r'تعليم\s+(?:ال)?كبار[^-]*', r'(?:لذوى|ذوى|ذوي)\s+(?:ال)?(?:همم|القدرات)[^-]*', r'(?:اعداد|إعداد)\s+خدام[^-]*', r'خدام\s+و\s+إعداد\s+خدام',
    r'(?:ال)?مستو[يى][^\s-]*\s*[^\s-]*', r'المساوى\s+[^\s-]+', r'مستوى\s*[^\s-]*', r'\bم\s*[0-9١٢]\b', r'م[١٢]', r'م\s*متميز\s*فردى',
    r'(?:ال)?موهو?بين[^-]*', r'موهوبين[^-]*', r'تميز\s+فردى', r'(?:ال)?تميز\s+(?:ال)?جماعى', r'(?:ال)?لحن\s+(?:ال)?[اإ]جبار[يى](?:\s+للمستويين)?',
    r'(?:ثالثة|خامسة|أولى|اولى)\s+و\s*(?:رابعة|سادسة|ثانية|تانية)(?:\s+ابتدائ[يى])?', r'ابتدائ[يى]', r'حضانة', r'(?:ال)?ثانوية', r'(?:ال)?إعدادية',
    r'(?:ال)?جامعية', r'جامعة', r'ثانوى', r'اعدادى', r'إعدادى', r'المسنين|للمسنين|\(للمسنين\)|\(\s*للأسرة\s*\)|\(للأسرة\)',
    r'بسيط\s+و?متوسط\s+الإعاقة\S*', r'(?:بسيط|متوسط)\s+ال[إأا]عاقة\S*', r'المتميز', r'[0-9٠-٩]{4}', r'^\s*0?[0-9]\s*',
]

def hymn_name(t):
    s = t
    for rx in NOISE:
        s = re.sub(rx, ' - ', s)
    parts = [p.strip(' -–()') for p in re.split(r'\s*[-–]\s*', s)]
    parts = [p for p in parts if p and not re.fullmatch(r'(?:ال)?[اأ]?لحان|م|و|ألحان|الحان|ثانية|ثانيه|الأولمهرجان', p)]
    return ' - '.join(parts).strip()

def parse(videos):
    """One record per titled video; the year falls back to its playlist's, then to the upload date."""
    out = []
    for d in videos:
        t = d['title']
        if not t: continue
        year = year_of(t) or year_of(d.get('playlist') or '') or (int(d['upload_date'][:4]) if d.get('upload_date') else None)
        out.append(dict(id=d['id'], title=t, date=d['upload_date'], avail=d['availability'], duration=d['duration'],
                        year=year, stage=first(STAGES, t), level=first(LEVELS, t), name=hymn_name(t)))
    return out
