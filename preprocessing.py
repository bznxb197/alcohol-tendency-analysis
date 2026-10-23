"""Единый препроцессинг для ноутбука и сервера.

Всё, что должно совпадать между обучением и продом (список и порядок признаков,
кодировка личностных черт), живёт только здесь.
"""
import pandas as pd

TRAIT_COLS = [
    'talkativeness', 'work_accuracy', 'creativity', 'reserved_opinions',
    'stress_tolerance', 'task_completion', 'exploitability', 'work_ethic',
    'forgiveness', 'anxiety', 'curiosity', 'preference_leisure',
    'long_term_focus', 'aesthetic_appreciation', 'future_orientation',
    'politeness', 'work_efficiency', 'nervousness', 'generosity',
    'sociability', 'decision_carefulness', 'perceived_hostility',
]

# Шкалы риска 0–10; «затрудняюсь ответить» передаётся как пропуск (NaN),
# модель обучена с индикаторами пропуска для этих признаков.
RISK_COLS = ['general_risk', 'driving_risk', 'financial_risk', 'health_risk', 'future_sacrifice']

FEATURE_COLUMNS = [
    # Демография
    'age', 'gender', 'education_level',
    # Личностные характеристики
    'talkativeness', 'work_accuracy', 'creativity', 'stress_tolerance',
    'task_completion', 'work_ethic', 'forgiveness', 'curiosity',
    'long_term_focus', 'aesthetic_appreciation', 'future_orientation',
    'politeness', 'work_efficiency', 'generosity', 'sociability',
    'decision_carefulness', 'reserved_opinions', 'exploitability',
    'anxiety', 'preference_leisure', 'nervousness', 'perceived_hostility',
    # Рисковое поведение
    'general_risk', 'drives', 'driving_risk', 'financial_risk', 'health_risk',
    'future_sacrifice',
    # Здоровье и курение
    'self_rated_health', 'is_smoker',
]

assert set(TRAIT_COLS) <= set(FEATURE_COLUMNS)
assert set(RISK_COLS) <= set(FEATURE_COLUMNS)


def encode_traits(df: pd.DataFrame) -> pd.DataFrame:
    """Шкала RLMS: 1 = «почти всегда» ... 4 = «почти никогда».
    Переворачиваем, чтобы у всех черт 4 = черта выражена сильнее всего.
    NaN остаётся NaN."""
    df = df.copy()
    df[TRAIT_COLS] = 5 - df[TRAIT_COLS]
    return df

