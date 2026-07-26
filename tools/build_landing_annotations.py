"""Build an editable RU/EN annotation catalogue for the corpus landing page.

Existing non-empty cells are preserved, so the generated CSV is safe to enrich
manually. Run from the repository root:
    python tools/build_landing_annotations.py
"""

from csv import DictReader, DictWriter
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "conf" / "corpus.json"
CATEGORIES = ROOT / "conf" / "categories.json"
OUTPUT = ROOT / "conf" / "landing_annotations.csv"
FIELDS = [
    "language", "kind", "key", "title_ru", "title_en",
    "description_ru", "description_en",
]

TERMS = {
    "0": ("нулевое лицо", "zero person"),
    "1": ("первое лицо", "first person"),
    "2": ("второе лицо", "second person"),
    "3": ("третье лицо", "third person"),
    "SG": ("единственное число", "singular"),
    "PL": ("множественное число", "plural"),
    "DU": ("двойственное число", "dual"),
    "M": ("мужской род", "masculine"),
    "F": ("женский род", "feminine"),
    "N": ("средний род", "neuter"),
    "NOM": ("именительный падеж", "nominative"),
    "ACC": ("винительный падеж", "accusative"),
    "GEN": ("родительный падеж", "genitive"),
    "DAT": ("дательный падеж", "dative"),
    "LOC": ("местный падеж", "locative"),
    "INS": ("творительный падеж", "instrumental"),
    "INSTR": ("инструменталис", "instrumental"),
    "ABL": ("аблатив", "ablative"),
    "ALL": ("аллатив", "allative"),
    "ILL": ("иллатив", "illative"),
    "EL": ("элатив", "elative"),
    "ELA": ("элатив", "elative"),
    "IN": ("инессив", "inessive"),
    "PROL": ("пролатив", "prolative"),
    "VOC": ("звательный падеж", "vocative"),
    "CAR": ("каритив", "caritive"),
    "COM": ("комитатив", "comitative"),
    "BEN": ("бенефактив", "benefactive"),
    "DATALL": ("датив-аллатив", "dative-allative"),
    "DATLOC": ("датив-локатив", "dative-locative"),
    "PRS": ("настоящее время", "present"),
    "PST": ("прошедшее время", "past"),
    "PRET": ("претерит", "preterite"),
    "FUT": ("будущее время", "future"),
    "NPST": ("непрошедшее время", "non-past"),
    "AOR": ("аорист", "aorist"),
    "PFV": ("совершенный вид", "perfective"),
    "IPFV": ("несовершенный вид", "imperfective"),
    "IMP": ("императив", "imperative"),
    "IMPER": ("императив", "imperative"),
    "IND": ("изъявительное наклонение", "indicative"),
    "INDC": ("изъявительное наклонение", "indicative"),
    "OPT": ("оптатив", "optative"),
    "JUSS": ("юссив", "jussive"),
    "SUBJ": ("субъюнктив", "subjunctive"),
    "COND": ("условное наклонение", "conditional"),
    "INF": ("инфинитив", "infinitive"),
    "CVB": ("конверб", "converb"),
    "PTCP": ("причастие", "participle"),
    "NMLZ": ("номинализация", "nominalization"),
    "ACT": ("действительный залог", "active"),
    "PASS": ("страдательный залог", "passive"),
    "NEG": ("отрицание", "negation"),
    "POSS": ("посессивность", "possessive"),
    "REFL": ("рефлексив", "reflexive"),
    "RFL": ("рефлексив", "reflexive"),
    "CAUS": ("каузатив", "causative"),
    "DETR": ("детранзитив", "detransitivizer"),
    "INCH": ("инхоатив", "inchoative"),
    "ITER": ("итератив", "iterative"),
    "DUR": ("дуратив", "durative"),
    "SIM": ("одновременность", "simultaneous"),
    "LIM": ("ограничительное значение", "limitative"),
    "ANT": ("предшествование", "anterior"),
    "ADD": ("аддитив", "additive"),
    "CONTR": ("контрастив", "contrastive"),
    "EMPH": ("эмфатическая частица", "emphatic"),
    "PTCL": ("частица", "particle"),
    "ATTR": ("атрибутив", "attributive"),
    "ADV": ("наречие", "adverb"),
    "ADJ": ("прилагательное", "adjective"),
    "NOUN": ("существительное", "noun"),
    "VERB": ("глагол", "verb"),
    "NUM": ("числительное", "numeral"),
    "PRON": ("местоимение", "pronoun"),
    "PROPN": ("имя собственное", "proper noun"),
    "ADP": ("адлог", "adposition"),
    "PREP": ("предлог", "preposition"),
    "POST": ("послелог", "postposition"),
    "CONJ": ("союз", "conjunction"),
    "CCONJ": ("сочинительный союз", "coordinating conjunction"),
    "SCONJ": ("подчинительный союз", "subordinating conjunction"),
    "INTJ": ("междометие", "interjection"),
    "PART": ("частица", "particle"),
    "DET": ("определитель", "determiner"),
    "AUX": ("вспомогательный глагол", "auxiliary"),
    "PRED": ("предикатив", "predicative"),
    "ANIM": ("одушевлённость", "animate"),
    "INAN": ("неодушевлённость", "inanimate"),
    "TR": ("переходный глагол", "transitive"),
    "INTR": ("непереходный глагол", "intransitive"),
    "OBJ": ("объектное согласование", "object agreement"),
    "SBJ": ("субъектное согласование", "subject agreement"),
    "EXC": ("эксклюзив", "exclusive"),
    "INC": ("инклюзив", "inclusive"),
    "CORF": ("кореферентность", "coreferential"),
    "TH": ("тематический класс", "thematic class"),
    "NM": ("немужской класс", "non-masculine"),
    "NTH": ("нетематический класс", "non-thematic"),
}

# Frequent corpus-specific and pymorphy/OpenCorpora labels. Keeping these in
# one table makes the generated wording consistent across all corpora.
TERMS.update({
    "ADJF": ("полное прилагательное", "full adjective"),
    "ADJS": ("краткое прилагательное", "short adjective"),
    "ADVB": ("наречие", "adverb"),
    "INFN": ("инфинитив", "infinitive"),
    "PRTF": ("полное причастие", "full participle"),
    "PRTS": ("краткое причастие", "short participle"),
    "GRND": ("деепричастие", "gerund"),
    "NUMR": ("числительное", "numeral"),
    "NPRO": ("местоимение-существительное", "pronominal noun"),
    "PRCL": ("частица", "particle"),
    "LATN": ("токен латиницей", "Latin-script token"),
    "NUMB": ("число", "number"),
    "ROMN": ("римское число", "Roman numeral"),
    "PNCT": ("пунктуация", "punctuation"),
    "UNKN": ("неизвестное слово", "unknown word"),
    "ASPC": ("категория вида", "aspect category"),
    "CASE": ("категория падежа", "case category"),
    "GNDR": ("категория рода", "gender category"),
    "INVL": ("категория неизменяемости", "invariability category"),
    "MOOD": ("категория наклонения", "mood category"),
    "NMBR": ("категория числа", "number category"),
    "PERS": ("категория лица", "person category"),
    "TENS": ("категория времени", "tense category"),
    "TRNS": ("категория переходности", "transitivity category"),
    "VOIC": ("категория залога", "voice category"),
    "NOMN": ("именительный падеж", "nominative"),
    "GENT": ("родительный падеж", "genitive"),
    "DATV": ("дательный падеж", "dative"),
    "ACCS": ("винительный падеж", "accusative"),
    "ABLT": ("творительный падеж", "instrumental"),
    "LOCT": ("предложный падеж", "locative"),
    "VOCT": ("звательная форма", "vocative"),
    "GEN1": ("первый родительный", "first genitive"),
    "GEN2": ("второй родительный", "second genitive"),
    "ACC2": ("второй винительный", "second accusative"),
    "LOC1": ("первый предложный", "first locative"),
    "LOC2": ("второй предложный", "second locative"),
    "SING": ("единственное число", "singular"),
    "PLUR": ("множественное число", "plural"),
    "MASC": ("мужской род", "masculine"),
    "FEMN": ("женский род", "feminine"),
    "NEUT": ("средний род", "neuter"),
    "PRES": ("настоящее время", "present"),
    "PAST": ("прошедшее время", "past"),
    "FUTR": ("будущее время", "future"),
    "IMPF": ("несовершенный вид", "imperfective"),
    "PERF": ("совершенный вид", "perfective"),
    "INDC": ("изъявительное наклонение", "indicative"),
    "IMPR": ("повелительное наклонение", "imperative"),
    "ACTV": ("действительный залог", "active"),
    "PSSV": ("страдательный залог", "passive"),
    "TRAN": ("переходный", "transitive"),
    "INTR": ("непереходный", "intransitive"),
    "1PER": ("первое лицо", "first person"),
    "2PER": ("второе лицо", "second person"),
    "3PER": ("третье лицо", "third person"),
    "INCL": ("говорящий включён", "speaker included"),
    "EXCL": ("говорящий исключён", "speaker excluded"),
    "ABBR": ("аббревиатура", "abbreviation"),
    "NAME": ("имя", "given name"),
    "SURN": ("фамилия", "surname"),
    "PATR": ("отчество", "patronymic"),
    "GEOX": ("топоним", "place name"),
    "ORGN": ("организация", "organization name"),
    "TRAD": ("торговая марка", "trade name"),
    "SUBX": ("субстантивация", "substantivized"),
    "SUPR": ("превосходная степень", "superlative"),
    "QUAL": ("качественное прилагательное", "qualitative adjective"),
    "APRO": ("местоименное прилагательное", "pronominal adjective"),
    "ANUM": ("порядковое числительное", "ordinal adjective"),
    "COUN": ("счётная форма", "counting form"),
    "COLL": ("собирательность", "collective"),
    "DIST": ("искажённая форма", "distorted form"),
    "ATT": ("аттенуатив", "attenuative"),
    "ATTEN": ("аттенуатив", "attenuative"),
    "DISC": ("дисконтинуатив", "discontinuative"),
    "PUN": ("пунктив", "punctive"),
    "SEM": ("семельфактив", "semelfactive"),
    "LAT": ("латив", "lative"),
    "MED": ("медиопассив", "mediopassive"),
    "DENOM": ("отыменный глагол", "denominal verb"),
    "MAN": ("глагол образа действия", "manner verb"),
    "MEAS": ("количественный показатель", "measure"),
    "DEST": ("показатель назначения", "destination marker"),
    "FULL": ("полная форма", "full form"),
    "PROP": ("проприетив", "proprietive"),
    "NACT": ("отглагольное имя", "deverbal noun"),
    "NAG": ("имя деятеля", "agent noun"),
    "AGGR": ("агрегатив", "aggregative"),
    "ORD": ("порядковое числительное", "ordinal"),
    "DEB": ("дебитив", "debitive"),
    "DES": ("дезидератив", "desiderative"),
    "CMPR": ("сравнительная степень", "comparative"),
    "ADVZ": ("адвербиализатор", "adverbializer"),
    "COORD": ("координатив", "coordinative"),
    "DIM": ("диминутив", "diminutive"),
    "EP": ("эпентеза", "epenthesis"),
    "EVID": ("непрямая эвиденциальность", "indirect evidential"),
    "FOC": ("фокусная частица", "focus particle"),
    "HAB": ("хабитуалис", "habitual"),
    "MEL": ("элемент распева", "melodic extension"),
    "PEJ": ("пейоратив", "pejorative"),
    "PLOBJ": ("многообъектный показатель", "multiple-object marker"),
    "PLSBJ": ("многосубъектный показатель", "multiple-subject marker"),
    "PRT": ("причастие", "participle"),
    "PSTN": ("прошедшее повествовательное время", "narrative past"),
    "TRANSL": ("транслатив", "translative"),
    "VBLZ": ("вербализатор", "verbalizer"),
    "EX": ("экзистенциальность", "existential"),
    "INT": ("интенсив", "intensive"),
    "REV": ("реверсив", "reversive"),
    "DUR": ("дуратив", "durative"),
    "APROX": ("аппроксиматив", "approximative"),
    "DEADJ": ("отадъективная деривация", "deadjectival derivation"),
    "ENCL": ("энклитика", "enclitic"),
    "KIN": ("показатель термина родства", "kinship-term marker"),
    "STEM": ("основа", "stem"),
    "PRO": ("местоимение", "pronoun"),
    "INTERJ": ("междометие", "interjection"),
    "IMIT": ("идеофон", "ideophone"),
    "HUM": ("человек", "human"),
    "DEM": ("указательное местоимение", "demonstrative"),
    "RUS": ("русское заимствование", "Russian borrowing"),
    "CARD": ("количественное числительное", "cardinal"),
    "PRAET": ("претерит", "preterite"),
    "DEF": ("определённость", "definite"),
    "INDEF": ("неопределённость", "indefinite"),
    "INTER": ("вопросительное местоимение", "interrogative pronoun"),
    "REL": ("относительное местоимение", "relative pronoun"),
    "TEMP": ("наречие времени", "temporal adverb"),
    "MOD": ("модальное наречие", "modal adverb"),
    "S1": ("субъектный показатель серии 1", "series 1 subject marker"),
    "S2": ("субъектный показатель серии 2", "series 2 subject marker"),
    "S3": ("субъектный показатель серии 3", "series 3 subject marker"),
    "O": ("объектный показатель", "object marker"),
    "O2": ("объектный показатель серии 2", "series 2 object marker"),
    "O3": ("объектный показатель серии 3", "series 3 object marker"),
    "T": ("временной показатель", "tense marker"),
    "LV": ("лёгкий глагол", "light verb"),
    "HES": ("хезитатив", "hesitative"),
    "PARENTH": ("вводная конструкция", "parenthetical"),
    "PREDIC": ("предикатив", "predicative"),
    "ZPL": ("счётное множественное число", "counting plural"),
    "C": ("общий род", "common gender"),
    "TOT": ("тотальное местоимение", "total pronoun"),
    "FREE": ("свободная форма", "free form"),
    "PER": ("лицо", "person"),
    "ELAT": ("элатив", "elative"),
    "I": ("глагольная основа I", "stem I"),
    "II": ("глагольная основа II", "stem II"),
    "III": ("глагольная основа III", "stem III"),
    "IV": ("глагольная основа IV", "stem IV"),
    "IW": ("глагольная основа Iw", "stem Iw"),
    "IY": ("глагольная основа Iy", "stem Iy"),
    "Iʔ": ("глагольная основа Iʔ", "stem Iʔ"),
    "IIW": ("глагольная основа IIw", "stem IIw"),
    "IIY": ("глагольная основа IIy", "stem IIy"),
    "II2": ("глагольная основа II2", "stem II2"),
    "IIIY": ("глагольная основа IIIy", "stem IIIy"),
    "III2": ("глагольная основа III2", "stem III2"),
    "IVY": ("глагольная основа IVy", "stem IVy"),
    "I7": ("глагольная основа I7", "stem I7"),
    "I8": ("глагольная основа I8", "stem I8"),
    "I10": ("глагольная основа I10", "stem I10"),
    "V": ("глагол", "verb"),
    "A": ("прилагательное", "adjective"),
    "S": ("существительное", "noun"),
    "NA": ("неадъективный", "non-adjectival"),
    "D": ("показатель серии D", "D-series marker"),
    "DOPP": ("показатель серии Dopp", "Dopp-series marker"),
    "DOM": ("дифференцированное маркирование объекта", "differential object marking"),
    "HD": ("сопряжённое состояние", "status constructus"),
})
SPECIAL = {
    "DATALL": (
        "датив-аллатив",
        "dative-allative",
        "Совмещённая падежная помета для адресата и направления движения.",
        "A combined case label used for recipient and goal-of-motion contexts.",
    ),
    "DATLOC": (
        "датив-локатив",
        "dative-locative",
        "Совмещённая падежная помета для дативных и локативных контекстов.",
        "A combined case label used in dative and locative contexts.",
    ),
}

SPECIAL.update({
    tag: (ru, en, f"Помета обозначает: {ru}.", f"The tag marks: {en}.")
    for tag, ru, en in [
        ("COMP", "сравнительная степень", "comparative degree"),
        ("ms-f", "общий род", "common gender"),
        ("Ms-f", "общий род как лексический признак", "lexically common gender"),
        ("Sgtm", "только единственное число", "singularia tantum"),
        ("Pltm", "только множественное число", "pluralia tantum"),
        ("Prdx", "предикативность", "predicative use"),
        ("Adjx", "адъективированная форма", "adjectivized form"),
        ("Cmp2", "вторая сравнительная форма", "second comparative form"),
        ("Mult", "многократность", "iterative action"),
        ("intg", "целое число", "integer"),
        ("real", "вещественное число", "real number"),
        ("Infr", "разговорное", "colloquial"),
        ("Slng", "жаргонное", "slang"),
        ("Arch", "устаревшее", "archaic"),
        ("Litr", "литературный вариант", "literary variant"),
        ("Erro", "искажённая форма", "distorted form"),
        ("Ques", "вопросительное", "interrogative"),
        ("Dmns", "указательное", "demonstrative"),
        ("Prnt", "вводное", "parenthetical"),
        ("Fimp", "безличная форма", "impersonal form"),
        ("Impe", "безличный глагол", "impersonal verb"),
        ("Impx", "возможна безличная форма", "potentially impersonal form"),
        ("Inmx", "неизменяемая форма", "invariable form"),
        ("Vpre", "вариант приставки", "prefix variant"),
        ("Anph", "анафорическая форма", "anaphoric form"),
        ("V-be", "форма на -ье", "form ending in -ье"),
        ("V-en", "форма на -енен", "form ending in -енен"),
        ("V-ie", "форма на -ие", "form ending in -ие"),
        ("V-bi", "форма на -би", "form ending in -би"),
        ("V-sh", "форма на -ши", "form ending in -ши"),
        ("V-ey", "форма на -ею", "form ending in -ею"),
        ("V-oy", "форма на -ою", "form ending in -ою"),
        ("V-ej", "форма на -ей", "form ending in -ей"),
        ("Af-p", "форма после предлога", "post-prepositional form"),
        ("Fixd", "неизменяемое", "fixed form"),
        ("Init", "инициал", "initial"),
        ("Hypo", "гипокористическая форма", "hypocoristic form"),
        ("RETR1", "ретроспективный сдвиг, тип 1", "retrospective shift, type 1"),
        ("RETR2", "ретроспективный сдвиг, тип 2", "retrospective shift, type 2"),
        ("POL1", "смягчение категоричности перед императивом, тип 1", "pre-imperative non-categorical marker, type 1"),
        ("POL2", "смягчение категоричности перед императивом, тип 2", "pre-imperative non-categorical marker, type 2"),
        ("=POL1", "энклитическое смягчение категоричности перед императивом", "enclitic pre-imperative non-categorical marker"),
        ("SINCE", "значение «с тех пор»", "meaning ‘since then’"),
        ("RAR", "редкая форма", "rare form"),
        ("O3.3PLCORF", "объектный показатель серии 3: третье лицо, множественное число, кореферентность", "series 3 object marker: third person, plural, coreferential"),
        ("S3.3SH.F", "субъектный показатель серии 3: класс 3SH, женский род?", "series 3 subject marker: 3SH class, feminine?"),
        ("rel_n", "реляционное существительное", "relational noun"),
        ("rel_adj", "реляционное прилагательное", "relational adjective"),
        ("topn", "топоним", "place name"),
        ("persn", "личное имя", "personal name"),
        ("famn", "фамилия", "family name"),
        ("patrn", "отчество", "patronymic"),
        ("supernat", "сверхъестественное существо", "supernatural being"),
        ("transport", "транспорт", "transport"),
        ("body", "часть тела", "body part"),
        ("vn", "отглагольное имя", "verbal noun"),
        ("nloc", "имя места", "nomen loci"),
        ("obl", "косвенная основа", "oblique stem"),
        ("oblin", "облинатив", "oblinative"),
        ("egr", "эгрессив", "egressive"),
        ("term", "терминатив", "terminative"),
        ("app", "аппроксиматив", "approximative"),
        ("rcs", "рецессив", "recessive"),
        ("dms", "лично-локальный показатель «domus»", "“domus” personal-local marker"),
        ("simult", "одновременность", "simultaneous"),
        ("res", "результатив", "resultative"),
        ("mon", "конверб на -mon", "converb in -mon"),
        ("prh", "прохибитив", "prohibitive"),
        ("attr_o", "атрибутивная форма на -o", "attributive form in -o"),
        ("attr_em", "атрибутивная форма на -jem", "attributive form in -jem"),
        ("attr_tem", "отрицательная атрибутивная форма на -tem", "negative attributive form in -tem"),
        ("intensifier", "интенсификатор", "intensifier"),
        ("poss_comp", "посессивное сложение", "possessive compounding"),
        ("case_comp", "падежное сложение", "case compounding"),
        ("comp", "сравнительная степень", "comparative"),
        ("comp2", "вторая сравнительная форма", "second comparative"),
        ("distr", "дистрибутив", "distributive"),
        ("with_instr", "сочетается с инструменталисом", "used with instrumental"),
        ("with_dat", "сочетается с дативом", "used with dative"),
        ("with_el", "сочетается с элативом", "used with elative"),
        ("with_ill", "сочетается с иллативом", "used with illative"),
        ("with_gen2", "сочетается со вторым генитивом", "used with second genitive"),
        ("with_inf", "сочетается с инфинитивом", "used with infinitive"),
        ("impers", "безличная форма", "impersonal"),
        ("period", "период на -skən", "period in -skən"),
        ("cvb,simult", "конверб одновременности на -ku", "simultaneous converb in -ku"),
        ("PRAEDIC", "предикатив", "predicative"),
        ("SPRO", "местоимение-существительное", "substantive pronoun"),
        ("ADVPRO", "местоименное наречие", "adverbial pronoun"),
        ("PRAEDICPRO", "местоимение-предикатив", "predicative pronoun"),
        ("PR", "предлог", "preposition"),
        ("INIT", "инициал", "initial"),
        ("adnum", "счётная форма", "adnumeral"),
        ("mf", "общий род", "common gender"),
        ("indic", "изъявительное наклонение", "indicative"),
        ("partcp", "причастие", "participle"),
        ("ger", "деепричастие", "gerund"),
        ("praes", "настоящее время", "present"),
        ("1p", "первое лицо", "first person"),
        ("2p", "второе лицо", "second person"),
        ("3p", "третье лицо", "third person"),
        ("mid", "средний залог", "middle voice"),
        ("pf", "совершенный вид", "perfective"),
        ("ipf", "несовершенный вид", "imperfective"),
        ("super", "превосходная степень", "superlative"),
        ("plen", "полная форма", "full form"),
        ("brev", "краткая форма", "short form"),
        ("zoon", "зооним", "zoonym"),
        ("digit", "цифровая запись", "numeric token"),
        ("anom", "аномальная форма", "anomalous form"),
        ("distort", "искажённая форма", "distorted form"),
        ("norm", "словарное слово", "dictionary word"),
        ("bastard", "несловарное слово", "out-of-dictionary word"),
        ("geo", "географическое название", "geographical name"),
        ("inpraes", "ненастоящее время", "non-present"),
        ("inform", "разговорная форма", "informal"),
        ("rare", "редкая форма", "rare"),
        ("obsc", "малоупотребительная форма", "obscure"),
        ("obsol", "устаревшая форма", "obsolete"),
        ("unfinished", "незавершённая форма", "unfinished"),
        ("other", "прочий тип наречия", "other adverb type"),
        ("COM.VIT", "комитативный падеж на -vit", "comitative case in -vit"),
        ("DIR", "директив", "directive case"),
        ("DLOC", "директив-локатив", "directive-locative case"),
        ("EQU", "экватив", "equative case"),
        ("DST", "дестинатив", "destinative"),
        ("AL", "аллативно-посессивный показатель", "allative possessive"),
        ("TENSE", "любой показатель времени", "any tense marker"),
        ("NFUT", "небудущее время", "non-future tense"),
        ("DFUT", "отдалённое будущее время", "distant future"),
        ("DERIV", "любая глагольная деривация", "any verbal derivation"),
        ("PST_ANY", "любой показатель прошедшего времени", "any past marker"),
        ("FUT_ANY", "любой показатель будущего времени", "any future marker"),
        ("RES", "результатив", "resultative"),
        ("CVB.MON", "конверб на -mon", "converb in -mon"),
    ]
})

GROUPS = {
    "pos": ("Части речи", "Parts of speech"),
    "case": ("Падеж", "Case"),
    "Cases": ("Падежи", "Cases"),
    "number": ("Число", "Number"),
    "Number": ("Число", "Number"),
    "gender": ("Род", "Gender"),
    "person": ("Лицо", "Person"),
    "tense": ("Время", "Tense"),
    "Tense": ("Время", "Tense"),
    "mood": ("Наклонение", "Mood"),
    "Mood": ("Наклонение", "Mood"),
    "aspect": ("Вид", "Aspect"),
    "Aspect": ("Вид", "Aspect"),
    "Agreement": ("Согласование", "Agreement"),
    "Negation": ("Отрицание", "Negation"),
    "Non-finite": ("Нефинитные формы", "Non-finite forms"),
    "Valency derivation": ("Изменение валентности", "Valency-changing derivation"),
    "Denominal derivation": ("Отыменная деривация", "Denominal derivation"),
    "Nominal derivation": ("Именная деривация", "Nominal derivation"),
    "Numerals": ("Числительные", "Numerals"),
    "Particles": ("Частицы", "Particles"),
    "Possessiveness": ("Посессивность", "Possessiveness"),
    "Other tags": ("Прочие пометы", "Other tags"),
}


def has_cyrillic(value):
    return bool(re.search(r"[А-Яа-яЁё]", value or ""))


def clean_sentence(value):
    value = (value or "").strip()
    if not value:
        return ""
    return value if value[-1] in ".?!" else value + "."


def expand(tag):
    if tag in SPECIAL:
        return SPECIAL[tag]
    normalized = tag.lstrip("=")
    parts = [part for part in re.split(r"[.,=/()-]+", normalized) if part]
    translated = []
    for part in parts:
        upper = part.upper()
        direct = TERMS.get(upper)
        if direct:
            translated.append(direct)
            continue
        agreement = re.fullmatch(r"([123])([CFM])([PS])", upper)
        if agreement:
            gender = {"C": ("общий род", "common gender"),
                      "F": ("женский род", "feminine"),
                      "M": ("мужской род", "masculine")}[agreement.group(2)]
            number = {"P": ("множественное число", "plural"),
                      "S": ("единственное число", "singular")}[agreement.group(3)]
            translated.extend((TERMS[agreement.group(1)], gender, number))
            continue
        match = re.fullmatch(r"([123])([A-Z]{1,3})", upper)
        if match and match.group(1) in TERMS and match.group(2) in TERMS:
            translated.extend((TERMS[match.group(1)], TERMS[match.group(2)]))
            continue
        base = re.sub(r"\d+$", "", upper)
        if base in TERMS:
            translated.append(TERMS[base])
            continue
        return (
            f"Специальная помета {tag}?",
            f"Corpus-specific tag {tag}?",
            f"Значение пометы {tag} требует уточнения у составителей корпуса?",
            f"The meaning of {tag} should be confirmed with the corpus compilers?",
        )
    if not translated:
        return (
            f"Специальная помета {tag}?",
            f"Corpus-specific tag {tag}?",
            f"Значение пометы {tag} требует уточнения у составителей корпуса?",
            f"The meaning of {tag} should be confirmed with the corpus compilers?",
        )
    ru = ", ".join(item[0] for item in translated)
    en = ", ".join(item[1] for item in translated)
    return ru, en, f"Помета обозначает: {ru}.", f"The tag marks: {en}."


def tag_row(language, tag, tooltip):
    title_ru, title_en, description_ru, description_en = expand(tag)
    tooltip = (tooltip or "").strip()
    if tooltip and tooltip.casefold() != tag.casefold():
        if has_cyrillic(tooltip):
            title_ru = tooltip
            description_ru = clean_sentence(tooltip)
        else:
            title_en = tooltip
            description_en = clean_sentence(tooltip)
    return {
        "language": language, "kind": "tag", "key": tag,
        "title_ru": title_ru, "title_en": title_en,
        "description_ru": description_ru, "description_en": description_en,
    }


def collect(config, categories):
    rows = []
    names_ru = config.get("landing_language_names", {})
    names_en = config.get("landing_language_names_en", {})
    for language in config.get("languages", []):
        rows.append({
            "language": language, "kind": "language", "key": language,
            "title_ru": names_ru.get(language, language.replace("_", " ").title()),
            "title_en": names_en.get(language, language.replace("_", " ").title()),
            "description_ru": "", "description_en": "",
        })
        seen_groups = set()
        seen_tags = set()
        props = config.get("lang_props", {}).get(language, {})
        for selector_name in ("gramm_selection", "gloss_selection"):
            selector = props.get(selector_name, {})
            for column in selector.get("columns", []):
                for item in column:
                    if item.get("type") == "header":
                        group = item.get("value", "")
                        if group and group not in seen_groups:
                            ru, en = GROUPS.get(
                                group, (group.replace("_", " ").title(), group.replace("_", " ").title())
                            )
                            rows.append({
                                "language": language, "kind": "group", "key": group,
                                "title_ru": ru, "title_en": en,
                                "description_ru": "", "description_en": "",
                            })
                            seen_groups.add(group)
                    elif item.get("type") in {"gramm", "gloss", "tag"}:
                        tag = item.get("value", "")
                        if tag and tag not in seen_tags:
                            rows.append(tag_row(language, tag, item.get("tooltip", "")))
                            seen_tags.add(tag)
        for tag, group in categories.get(language, {}).items():
            if not tag:
                continue
            if group and group not in seen_groups:
                ru, en = GROUPS.get(
                    group, (group.replace("_", " ").title(), group.replace("_", " ").title())
                )
                rows.append({
                    "language": language, "kind": "group", "key": group,
                    "title_ru": ru, "title_en": en,
                    "description_ru": "", "description_en": "",
                })
                seen_groups.add(group)
            if tag not in seen_tags:
                rows.append(tag_row(language, tag, ""))
                seen_tags.add(tag)
    return rows


def existing_rows():
    if not OUTPUT.exists():
        return {}
    with OUTPUT.open(encoding="utf-8-sig", newline="") as source:
        return {
            (row["language"], row["kind"], row["key"]): row
            for row in DictReader(source)
        }


def read_tab_file(path):
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.count("\t") == 1:
            key, value = line.split("\t")
            if key.strip() and value.strip():
                values[key.strip()] = value.strip()
    return values


def write_search_tooltips(config, rows):
    """Synchronize search-page selector tooltips with the bilingual catalogue."""
    by_key = {
        (row["language"], row["kind"], row["key"]): row
        for row in rows
    }
    generated = {"ru": {}, "en": {}}
    for language in config.get("languages", []):
        props = config.get("lang_props", {}).get(language, {})
        for selector_name in ("gramm_selection", "gloss_selection"):
            for column in props.get(selector_name, {}).get("columns", []):
                for item in column:
                    kind = "group" if item.get("type") == "header" else "tag"
                    key = item.get("value", "")
                    source_key = item.get("tooltip") or key
                    row = by_key.get((language, kind, key))
                    if not row or not source_key:
                        continue
                    for locale in generated:
                        value = row.get(f"title_{locale}", "").strip()
                        if value:
                            generated[locale].setdefault(source_key, value)
    translations_root = ROOT / "search" / "web_app" / "translations"
    for locale, new_values in generated.items():
        path = translations_root / locale / "tooltips.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        values = read_tab_file(path)
        # Generated entries replace empty or identity tooltips; explicit manual
        # translations remain authoritative.
        for key, value in new_values.items():
            if (
                key not in values
                or values[key] == key
                or values[key].startswith("Специальная помета ")
                or values[key].startswith("Corpus-specific tag ")
            ):
                values[key] = value
        text = "".join(f"{key}\t{values[key]}\n" for key in sorted(values, key=str.casefold))
        path.write_text(text, encoding="utf-8-sig")


def main():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    categories = (
        json.loads(CATEGORIES.read_text(encoding="utf-8"))
        if CATEGORIES.exists() else {}
    )
    old = existing_rows()
    rows = collect(config, categories)
    for row in rows:
        previous = old.get((row["language"], row["kind"], row["key"]), {})
        for field in FIELDS[3:]:
            previous_value = previous.get(field, "").strip()
            if (
                previous_value
                and not previous_value.startswith("Специальная помета ")
                and not previous_value.startswith("Corpus-specific tag ")
                and "требует уточнения у составителей корпуса?" not in previous_value
                and "should be confirmed with the corpus compilers?" not in previous_value
            ):
                row[field] = previous_value
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as target:
        writer = DictWriter(target, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    write_search_tooltips(config, rows)
    uncertain = sum(
        row["kind"] == "tag"
        and ("?" in row["title_ru"] or "?" in row["title_en"])
        for row in rows
    )
    print(f"Wrote {len(rows)} rows to {OUTPUT}")
    print("Synchronized RU/EN search-page tooltips")
    print(f"Tags requiring expert confirmation: {uncertain}")


if __name__ == "__main__":
    main()
