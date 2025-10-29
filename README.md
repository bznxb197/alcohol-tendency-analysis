# Alcohol Tendency Prediction Project

![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![Machine Learning](https://img.shields.io/badge/Machine-Learning-orange)
![RLMS-HSE](https://img.shields.io/badge/Data-RLMS--HSE-green)
![Web App](https://img.shields.io/badge/Web-App-brightgreen)

Анализ склонности к алкоголю на основе данных RLMS-HSE с применением машинного обучения и статистических методов.

## 📋 О проекте

Проект анализирует данные RLMS-HSE (32-я волна) для выявления склонности к алкоголю с использованием ML и веб-интерфейса для скрининга.

## 🎯 Ключевые результаты

### 🔬 Статистический анализ
- **Мужчины в 2 раза чаще** демонстрируют склонность к алкоголю (56% vs 28%)
- **Статистически значимые различия** (p < 0.0001) подтверждены всеми тестами
- **Мужчины имеют в 3.3 раза выше шансы** развития склонности
- **Алкогольный индекс на 22% выше** у мужчин

### 📊 Машинное обучение

**Сравнение моделей:**

| Model        | AUC    | Accuracy | Precision | Recall  | F1-Score |
|-------------|--------|---------|----------|--------|----------|
| XGBoost+    | 0.9098 | 0.8299  | 0.7668   | 0.8208 | 0.7929   |
| GBoost      | 0.9092 | 0.8263  | 0.7619   | 0.8172 | 0.7886   |
| XGBoost     | 0.9092 | 0.8299  | 0.7693   | 0.8158 | 0.7919   |
| Bagging     | 0.9056 | 0.7871  | 0.6730   | 0.9004 | 0.7703   |

> **Примечание:** Bagging Classifier остаётся отличной моделью для скринингового использования из-за высокого **Recall**, что важно для выявления случаев склонности.

### 🌐 Веб-приложение
- **31 вопрос** для комплексной оценки
- **Мгновенные результаты** с интерпретацией
- **Рекомендации** на основе прогноза модели
- **Доступно онлайн:** [https://alcohol-tendency-analysis-4.onrender.com](https://alcohol-tendency-analysis-4.onrender.com)

### 📱 Главная страница
![Главная страница](screenshots/index.png)

### 📊 Страница тестирования
![Тестирование](screenshots/test.png)

### 📈 Результаты
![Результаты](screenshots/result.png)




## 🚀 Инструкция по запуску

```bash
# Клонирование репозитория
git clone https://github.com/bznxb197/alcohol-tendency-analysis.git
cd alcohol-tendency-analysis

# Установка зависимостей
pip install -r requirements.txt

# Запуск веб-приложения
python alcohol_screening_server.py
# Приложение доступно: http://localhost:8080

# Или анализ в Jupyter
jupyter notebook alcohol_analysis.ipynb
```

## 📊 Методология

- **Статистический анализ**: Z-тест, хи-квадрат, T-тест, отношение шансов
- **ML моделирование**: Bagging Classifier с оценкой feature importance
- **Feature engineering**: Комплексный алкогольный индекс
- **Веб-интерфейс**: Клиент-серверная архитектура для скрининга


## 🗂️ Структура проекта
```
alcohol-tendency-analysis/
├── alcohol_analysis.ipynb          # Анализ данных и ML
├── alcohol_screening_server.py     # Веб-сервер
├── model.joblib                    # Обученная модель
├── screenshots/
│   ├── index.png
│   ├── test.png
│   └── results.png
├── templates/                      # HTML страницы
│   ├── index.html                  # Главная
│   ├── test.html                   # Тестирование
│   └── result.html                 # Результаты
└── data/                           # Данные исследования
```

## 📚 Данные
**RLMS-HSE** (32-я волна, 11,820 респондентов)

---

*Проект предназначен для исследовательских целей и не заменяет медицинскую диагностику.*




