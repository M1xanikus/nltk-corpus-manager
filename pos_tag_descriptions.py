# model/pos_tag_descriptions.py

# Словарь для перевода NLTK Penn Treebank POS-тегов в читаемые описания (на русском)
# См. https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
POS_TAG_DESCRIPTIONS = {
    'CC': 'Союз сочинительный',
    'CD': 'Числительное количественное',
    'DT': 'Определитель (артикль, детерминатив)',
    'EX': 'Существование "there"',
    'FW': 'Иностранное слово',
    'IN': 'Предлог или союз подчинительный',
    'JJ': 'Прилагательное',
    'JJR': 'Прилагательное, сравнительная степень',
    'JJS': 'Прилагательное, превосходная степень',
    'LS': 'Маркер списка',
    'MD': 'Модальный глагол',
    'NN': 'Существительное, единственное число или неисчисляемое',
    'NNS': 'Существительное, множественное число',
    'NNP': 'Имя собственное, единственное число',
    'NNPS': 'Имя собственное, множественное число',
    'PDT': 'Предопределитель (pre-determiner)',
    'POS': 'Притяжательный падеж (окончание \'s)',
    'PRP': 'Местоимение личное',
    'PRP$': 'Местоимение притяжательное',
    'RB': 'Наречие',
    'RBR': 'Наречие, сравнительная степень',
    'RBS': 'Наречие, превосходная степень',
    'RP': 'Частица (глагольная)',
    'SYM': 'Символ',
    'TO': 'Частица "to"',
    'UH': 'Междометие',
    'VB': 'Глагол, базовая форма (инфинитив)',
    'VBD': 'Глагол, прошедшее время',
    'VBG': 'Глагол, герундий или причастие настоящего времени',
    'VBN': 'Глагол, причастие прошедшего времени',
    'VBP': 'Глагол, настоящее время, не 3-е л. ед.ч.',
    'VBZ': 'Глагол, настоящее время, 3-е л. ед.ч.',
    'WDT': 'Wh-определитель (what, which, that)',
    'WP': 'Wh-местоимение (who, whom, what, which)',
    'WP$': 'Wh-притяжательное местоимение (whose)',
    'WRB': 'Wh-наречие (where, when, why, how)',
    '.': 'Пунктуация . ! ?',
    ',': 'Пунктуация ,',
    ':': 'Пунктуация :',
    '(': 'Пунктуация (',
    ')': 'Пунктуация )',
    '#': 'Пунктуация #',
    '$': 'Пунктуация $',
    '"': 'Пунктуация "',
    "''": 'Пунктуация \'',
    '``': 'Пунктуация `',
    # Дополнительные или менее частые теги можно добавить при необходимости
}

def get_pos_description(tag):
    """ Возвращает русское описание для NLTK тега или сам тег, если описания нет. """
    return POS_TAG_DESCRIPTIONS.get(tag, tag) # Возвращаем сам тег, если нет описания